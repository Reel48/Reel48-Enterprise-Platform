from __future__ import annotations

import secrets
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.models.catalog import Catalog
from app.models.catalog_product import CatalogProduct
from app.models.employee_profile import EmployeeProfile
from app.models.order import Order
from app.models.order_line_item import OrderLineItem
from app.models.product import Product
from app.schemas.order import OrderCreate
from app.services.helpers import resolve_current_user_id


class OrderService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_order(
        self,
        data: OrderCreate,
        company_id: UUID,
        sub_brand_id: UUID | None,
        cognito_sub: str,
    ) -> tuple[Order, list[OrderLineItem]]:
        """Place an order against an active catalog.

        Steps:
        1. Resolve the employee's local user_id from cognito_sub
        2. Validate catalog (exists, active, buying window if applicable)
        3. Validate each line item (product in catalog, active, price, size, decoration)
        4. Resolve shipping address (from request or employee profile)
        5. Generate unique order number
        6. Create Order + OrderLineItem records
        """
        # 1. Resolve local user_id
        user_id = await resolve_current_user_id(self.db, cognito_sub)

        # 2. Validate catalog
        catalog = await self._validate_catalog(data.catalog_id, company_id)

        # 3. Validate line items and collect snapshots
        line_item_data = await self._validate_line_items(data, catalog)

        # 4. Resolve shipping address
        shipping = self._resolve_shipping_address(data)
        if shipping is None:
            shipping = await self._shipping_from_profile(user_id)

        # 5. Generate unique order number
        order_number = await self._generate_order_number()

        # 6. Calculate totals
        subtotal = sum(item["line_total"] for item in line_item_data)
        total_amount = subtotal  # No tax/shipping in initial build

        # 7. Create Order
        order = Order(
            company_id=company_id,
            sub_brand_id=sub_brand_id,
            user_id=user_id,
            catalog_id=data.catalog_id,
            order_number=order_number,
            status="pending",
            shipping_address_line1=shipping.get("line1") if shipping else None,
            shipping_address_line2=shipping.get("line2") if shipping else None,
            shipping_city=shipping.get("city") if shipping else None,
            shipping_state=shipping.get("state") if shipping else None,
            shipping_zip=shipping.get("zip") if shipping else None,
            shipping_country=shipping.get("country") if shipping else None,
            notes=data.notes,
            subtotal=subtotal,
            total_amount=total_amount,
        )
        self.db.add(order)
        await self.db.flush()
        await self.db.refresh(order)

        # 8. Create OrderLineItem records
        line_items: list[OrderLineItem] = []
        for item in line_item_data:
            li = OrderLineItem(
                company_id=company_id,
                sub_brand_id=sub_brand_id,
                order_id=order.id,
                product_id=item["product_id"],
                product_name=item["product_name"],
                product_sku=item["product_sku"],
                unit_price=item["unit_price"],
                quantity=item["quantity"],
                size=item["size"],
                decoration=item["decoration"],
                line_total=item["line_total"],
            )
            self.db.add(li)
            line_items.append(li)

        await self.db.flush()
        for li in line_items:
            await self.db.refresh(li)

        return order, line_items

    async def _validate_catalog(self, catalog_id: UUID, company_id: UUID) -> Catalog:
        """Validate catalog exists, belongs to company, is active, and buying window is open."""
        result = await self.db.execute(
            select(Catalog).where(
                Catalog.id == catalog_id,
                Catalog.company_id == company_id,
                Catalog.deleted_at.is_(None),
            )
        )
        catalog = result.scalar_one_or_none()
        if catalog is None:
            raise NotFoundError("Catalog", str(catalog_id))
        if catalog.status != "active":
            raise ForbiddenError("Catalog is not active")

        # Check buying window for invoice_after_close catalogs
        if catalog.payment_model == "invoice_after_close":
            now = datetime.now(UTC)
            if catalog.buying_window_opens_at and catalog.buying_window_opens_at > now:
                raise ValidationError("Buying window is not open yet")
            if catalog.buying_window_closes_at and catalog.buying_window_closes_at < now:
                raise ValidationError("Buying window has closed")

        return catalog

    async def _validate_line_items(
        self, data: OrderCreate, catalog: Catalog
    ) -> list[dict]:
        """Validate each line item and return snapshot data."""
        items: list[dict] = []

        for li in data.line_items:
            # Check product is in catalog
            cp_result = await self.db.execute(
                select(CatalogProduct).where(
                    CatalogProduct.catalog_id == catalog.id,
                    CatalogProduct.product_id == li.product_id,
                )
            )
            catalog_product = cp_result.scalar_one_or_none()
            if catalog_product is None:
                raise NotFoundError("Product", str(li.product_id))

            # Fetch product — must be active
            prod_result = await self.db.execute(
                select(Product).where(
                    Product.id == li.product_id,
                    Product.deleted_at.is_(None),
                )
            )
            product = prod_result.scalar_one_or_none()
            if product is None:
                raise NotFoundError("Product", str(li.product_id))
            if product.status != "active":
                raise ValidationError(
                    f"Product '{product.name}' is not active (status: {product.status})"
                )

            # Resolve price: catalog override or product price
            unit_price: Decimal
            if catalog_product.price_override is not None:
                unit_price = Decimal(str(catalog_product.price_override))
            else:
                unit_price = Decimal(str(product.unit_price))

            # Validate size if provided
            if li.size is not None and product.sizes:
                if li.size not in product.sizes:
                    raise ValidationError(
                        f"Invalid size '{li.size}' for product '{product.name}'. "
                        f"Available sizes: {product.sizes}"
                    )

            # Validate decoration if provided
            if li.decoration is not None and product.decoration_options:
                if li.decoration not in product.decoration_options:
                    raise ValidationError(
                        f"Invalid decoration '{li.decoration}' for product '{product.name}'. "
                        f"Available options: {product.decoration_options}"
                    )

            line_total = unit_price * li.quantity

            items.append({
                "product_id": li.product_id,
                "product_name": product.name,
                "product_sku": product.sku,
                "unit_price": unit_price,
                "quantity": li.quantity,
                "size": li.size,
                "decoration": li.decoration,
                "line_total": line_total,
            })

        return items

    @staticmethod
    def _resolve_shipping_address(data: OrderCreate) -> dict | None:
        """Extract shipping address from request data, or None if not provided."""
        if data.shipping_address_line1 is not None:
            return {
                "line1": data.shipping_address_line1,
                "line2": data.shipping_address_line2,
                "city": data.shipping_city,
                "state": data.shipping_state,
                "zip": data.shipping_zip,
                "country": data.shipping_country,
            }
        return None

    async def _shipping_from_profile(self, user_id: UUID) -> dict | None:
        """Look up employee profile and extract delivery address."""
        result = await self.db.execute(
            select(EmployeeProfile).where(
                EmployeeProfile.user_id == user_id,
                EmployeeProfile.deleted_at.is_(None),
            )
        )
        profile = result.scalar_one_or_none()
        if profile is None or profile.delivery_address_line1 is None:
            return None
        return {
            "line1": profile.delivery_address_line1,
            "line2": profile.delivery_address_line2,
            "city": profile.delivery_city,
            "state": profile.delivery_state,
            "zip": profile.delivery_zip,
            "country": profile.delivery_country,
        }

    async def _generate_order_number(self) -> str:
        """Generate a unique order number: ORD-YYYYMMDD-XXXX."""
        date_str = datetime.now(UTC).strftime("%Y%m%d")
        for _ in range(5):
            random_part = secrets.token_hex(2).upper()
            order_number = f"ORD-{date_str}-{random_part}"
            # Check uniqueness
            result = await self.db.execute(
                select(Order.id).where(Order.order_number == order_number)
            )
            if result.scalar_one_or_none() is None:
                return order_number
        # Extremely unlikely — 5 collisions in a row
        raise ValidationError("Could not generate a unique order number. Please try again.")
