"""
Cross-tenant RLS integration tests.

These tests verify that PostgreSQL Row-Level Security policies correctly
isolate data between companies and sub-brands. Data is seeded via a
superuser session and COMMITTED (so the RLS-enforced session on a separate
connection can see it). Each test creates its own data and cleans up after.

Coverage:
- Company A cannot see Company B's data (and vice versa)
- Sub-Brand A1 cannot see Sub-Brand A2's data (within same company)
- Corporate admin (empty sub_brand_id) sees all sub-brands in their company
- reel48_admin (empty company_id) sees all companies
- Isolation applies to: Module 1 tables (users, companies, sub_brands, invites, org_codes),
  Module 7 (invoices), Module 9 (notifications, wishlists)
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.invite import Invite
from app.models.invoice import Invoice
from app.models.notification import Notification
from app.models.org_code import OrgCode
from app.models.product import Product
from app.models.sub_brand import SubBrand
from app.models.user import User
from app.models.wishlist import Wishlist


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
async def _set_tenant_context(session, company_id: str | None, sub_brand_id: str | None):
    """Set RLS session variables on a non-superuser session."""
    cid = company_id or ""
    sbid = sub_brand_id or ""
    await session.execute(text(f"SET LOCAL app.current_company_id = '{cid}'"))
    await session.execute(text(f"SET LOCAL app.current_sub_brand_id = '{sbid}'"))


async def _create_two_companies(session: AsyncSession):
    """Create two companies with sub-brands. Returns dict."""
    uid = uuid4().hex[:6]
    co_a = Company(
        name=f"IsoCoA-{uid}", slug=f"iso-a-{uid}", is_active=True
    )
    session.add(co_a)
    await session.flush()

    slug_a1 = f"iso-a1-{uuid4().hex[:6]}"
    slug_a2 = f"iso-a2-{uuid4().hex[:6]}"
    brand_a1 = SubBrand(
        company_id=co_a.id, name="Iso A1",
        slug=slug_a1, is_default=True, is_active=True,
    )
    brand_a2 = SubBrand(
        company_id=co_a.id, name="Iso A2",
        slug=slug_a2, is_default=False, is_active=True,
    )
    session.add_all([brand_a1, brand_a2])
    await session.flush()

    uid_b = uuid4().hex[:6]
    co_b = Company(
        name=f"IsoCoB-{uid_b}", slug=f"iso-b-{uid_b}", is_active=True
    )
    session.add(co_b)
    await session.flush()

    brand_b1 = SubBrand(
        company_id=co_b.id, name="Iso B1",
        slug=f"iso-b1-{uuid4().hex[:6]}",
        is_default=True, is_active=True,
    )
    session.add(brand_b1)
    await session.flush()

    return {
        "co_a": co_a, "brand_a1": brand_a1,
        "brand_a2": brand_a2,
        "co_b": co_b, "brand_b1": brand_b1,
    }


async def _cleanup_companies(session: AsyncSession, company_ids: list):
    """Delete all data for the given companies (reverse FK order)."""
    for cid in company_ids:
        cid_str = str(cid)
        await session.execute(text(f"DELETE FROM wishlists WHERE company_id = '{cid_str}'"))
        await session.execute(text(f"DELETE FROM notifications WHERE company_id = '{cid_str}'"))
        await session.execute(text(f"DELETE FROM invoices WHERE company_id = '{cid_str}'"))
        await session.execute(text(f"DELETE FROM invites WHERE company_id = '{cid_str}'"))
        await session.execute(text(f"DELETE FROM org_codes WHERE company_id = '{cid_str}'"))
        await session.execute(text(f"DELETE FROM products WHERE company_id = '{cid_str}'"))
        await session.execute(text(f"DELETE FROM users WHERE company_id = '{cid_str}'"))
        await session.execute(text(f"DELETE FROM sub_brands WHERE company_id = '{cid_str}'"))
        await session.execute(text(f"DELETE FROM companies WHERE id = '{cid_str}'"))
    await session.commit()


# ---------------------------------------------------------------------------
# Users table isolation
# ---------------------------------------------------------------------------
class TestUsersIsolation:
    async def test_company_b_cannot_see_company_a_users(self, setup_database):
        """Cross-company isolation: Company B sees zero Company A users."""
        admin_factory = setup_database["admin_factory"]
        app_factory = setup_database["app_factory"]

        # Seed and commit
        async with admin_factory() as seed:
            data = await _create_two_companies(seed)
            seed.add(User(
                company_id=data["co_a"].id, sub_brand_id=data["brand_a1"].id,
                cognito_sub=str(uuid4()), email=f"a-{uuid4().hex[:6]}@a.com",
                full_name="User A", role="employee",
            ))
            seed.add(User(
                company_id=data["co_b"].id, sub_brand_id=data["brand_b1"].id,
                cognito_sub=str(uuid4()), email=f"b-{uuid4().hex[:6]}@b.com",
                full_name="User B", role="employee",
            ))
            await seed.commit()

        try:
            # Query as Company B (RLS-enforced session)
            co_b_id = str(data["co_b"].id)
            b1_id = str(data["brand_b1"].id)
            async with app_factory() as app_sess:
                async with app_sess.begin():
                    await _set_tenant_context(app_sess, co_b_id, b1_id)
                    rows = (await app_sess.execute(select(User))).scalars().all()
                    assert len(rows) >= 1
                    for user in rows:
                        assert user.company_id == data["co_b"].id
        finally:
            async with admin_factory() as cleanup:
                await _cleanup_companies(cleanup, [data["co_a"].id, data["co_b"].id])

    async def test_brand_a2_cannot_see_brand_a1_users(self, setup_database):
        """Cross-sub-brand isolation within the same company."""
        admin_factory = setup_database["admin_factory"]
        app_factory = setup_database["app_factory"]

        async with admin_factory() as seed:
            data = await _create_two_companies(seed)
            seed.add(User(
                company_id=data["co_a"].id, sub_brand_id=data["brand_a1"].id,
                cognito_sub=str(uuid4()), email=f"a1-{uuid4().hex[:6]}@a.com",
                full_name="User A1", role="employee",
            ))
            seed.add(User(
                company_id=data["co_a"].id, sub_brand_id=data["brand_a2"].id,
                cognito_sub=str(uuid4()), email=f"a2-{uuid4().hex[:6]}@a.com",
                full_name="User A2", role="employee",
            ))
            await seed.commit()

        try:
            co_a_id = str(data["co_a"].id)
            a2_id = str(data["brand_a2"].id)
            async with app_factory() as app_sess:
                async with app_sess.begin():
                    await _set_tenant_context(app_sess, co_a_id, a2_id)
                    rows = (await app_sess.execute(select(User))).scalars().all()
                    for user in rows:
                        assert user.sub_brand_id == data["brand_a2"].id
        finally:
            async with admin_factory() as cleanup:
                await _cleanup_companies(cleanup, [data["co_a"].id, data["co_b"].id])

    async def test_corporate_admin_sees_all_sub_brands(self, setup_database):
        """Corporate admin (empty sub_brand_id) sees users in all sub-brands."""
        admin_factory = setup_database["admin_factory"]
        app_factory = setup_database["app_factory"]

        async with admin_factory() as seed:
            data = await _create_two_companies(seed)
            seed.add(User(
                company_id=data["co_a"].id, sub_brand_id=data["brand_a1"].id,
                cognito_sub=str(uuid4()), email=f"ca1-{uuid4().hex[:6]}@a.com",
                full_name="Corp A1", role="employee",
            ))
            seed.add(User(
                company_id=data["co_a"].id, sub_brand_id=data["brand_a2"].id,
                cognito_sub=str(uuid4()), email=f"ca2-{uuid4().hex[:6]}@a.com",
                full_name="Corp A2", role="employee",
            ))
            await seed.commit()

        try:
            co_a_id = str(data["co_a"].id)
            async with app_factory() as app_sess:
                async with app_sess.begin():
                    await _set_tenant_context(app_sess, co_a_id, None)
                    rows = (await app_sess.execute(select(User))).scalars().all()
                    sb_ids = {u.sub_brand_id for u in rows}
                    a1 = data["brand_a1"].id
                    a2 = data["brand_a2"].id
                    assert a1 in sb_ids or a2 in sb_ids
                    for user in rows:
                        assert user.company_id == data["co_a"].id
        finally:
            async with admin_factory() as cleanup:
                await _cleanup_companies(cleanup, [data["co_a"].id, data["co_b"].id])

    async def test_reel48_admin_sees_all_companies(self, setup_database):
        """reel48_admin (empty company_id) sees users across all companies."""
        admin_factory = setup_database["admin_factory"]
        app_factory = setup_database["app_factory"]

        async with admin_factory() as seed:
            data = await _create_two_companies(seed)
            seed.add(User(
                company_id=data["co_a"].id, sub_brand_id=data["brand_a1"].id,
                cognito_sub=str(uuid4()), email=f"ra-{uuid4().hex[:6]}@a.com",
                full_name="R48 A", role="employee",
            ))
            seed.add(User(
                company_id=data["co_b"].id, sub_brand_id=data["brand_b1"].id,
                cognito_sub=str(uuid4()), email=f"rb-{uuid4().hex[:6]}@b.com",
                full_name="R48 B", role="employee",
            ))
            await seed.commit()

        try:
            async with app_factory() as app_sess:
                async with app_sess.begin():
                    await _set_tenant_context(app_sess, None, None)
                    rows = (await app_sess.execute(select(User))).scalars().all()
                    company_ids = {user.company_id for user in rows}
                    assert data["co_a"].id in company_ids
                    assert data["co_b"].id in company_ids
        finally:
            async with admin_factory() as cleanup:
                await _cleanup_companies(cleanup, [data["co_a"].id, data["co_b"].id])


# ---------------------------------------------------------------------------
# Companies table isolation
# ---------------------------------------------------------------------------
class TestCompaniesIsolation:
    async def test_tenant_sees_only_own_company(self, setup_database):
        """A tenant user sees only their own company row."""
        admin_factory = setup_database["admin_factory"]
        app_factory = setup_database["app_factory"]

        async with admin_factory() as seed:
            data = await _create_two_companies(seed)
            await seed.commit()

        try:
            co_a_id = str(data["co_a"].id)
            a1_id = str(data["brand_a1"].id)
            async with app_factory() as app_sess:
                async with app_sess.begin():
                    await _set_tenant_context(app_sess, co_a_id, a1_id)
                    rows = (await app_sess.execute(select(Company))).scalars().all()
                    assert len(rows) == 1
                    assert rows[0].id == data["co_a"].id
        finally:
            async with admin_factory() as cleanup:
                await _cleanup_companies(cleanup, [data["co_a"].id, data["co_b"].id])

    async def test_reel48_admin_sees_all_companies(self, setup_database):
        """reel48_admin sees all companies."""
        admin_factory = setup_database["admin_factory"]
        app_factory = setup_database["app_factory"]

        async with admin_factory() as seed:
            data = await _create_two_companies(seed)
            await seed.commit()

        try:
            async with app_factory() as app_sess:
                async with app_sess.begin():
                    await _set_tenant_context(app_sess, None, None)
                    rows = (await app_sess.execute(select(Company))).scalars().all()
                    ids = {c.id for c in rows}
                    assert data["co_a"].id in ids
                    assert data["co_b"].id in ids
        finally:
            async with admin_factory() as cleanup:
                await _cleanup_companies(cleanup, [data["co_a"].id, data["co_b"].id])


# ---------------------------------------------------------------------------
# Sub-brands table isolation
# ---------------------------------------------------------------------------
class TestSubBrandsIsolation:
    async def test_company_b_cannot_see_company_a_sub_brands(self, setup_database):
        admin_factory = setup_database["admin_factory"]
        app_factory = setup_database["app_factory"]

        async with admin_factory() as seed:
            data = await _create_two_companies(seed)
            await seed.commit()

        try:
            co_b_id = str(data["co_b"].id)
            b1_id = str(data["brand_b1"].id)
            async with app_factory() as app_sess:
                async with app_sess.begin():
                    await _set_tenant_context(app_sess, co_b_id, b1_id)
                    rows = (await app_sess.execute(select(SubBrand))).scalars().all()
                    for sb in rows:
                        assert sb.company_id == data["co_b"].id
        finally:
            async with admin_factory() as cleanup:
                await _cleanup_companies(cleanup, [data["co_a"].id, data["co_b"].id])


# ---------------------------------------------------------------------------
# Invites table isolation
# ---------------------------------------------------------------------------
class TestInvitesIsolation:
    async def test_company_b_cannot_see_company_a_invites(self, setup_database):
        admin_factory = setup_database["admin_factory"]
        app_factory = setup_database["app_factory"]

        async with admin_factory() as seed:
            data = await _create_two_companies(seed)
            # Need a user for created_by FK
            user_a = User(
                company_id=data["co_a"].id, sub_brand_id=data["brand_a1"].id,
                cognito_sub=str(uuid4()), email=f"inv-{uuid4().hex[:6]}@a.com",
                full_name="Inviter A", role="sub_brand_admin",
            )
            seed.add(user_a)
            await seed.flush()

            seed.add(Invite(
                company_id=data["co_a"].id, target_sub_brand_id=data["brand_a1"].id,
                email="invite-a@a.com", role="employee",
                token=uuid4().hex + uuid4().hex, expires_at=datetime.now(UTC) + timedelta(hours=72),
                created_by=user_a.id,
            ))
            await seed.commit()

        try:
            co_b_id = str(data["co_b"].id)
            b1_id = str(data["brand_b1"].id)
            async with app_factory() as app_sess:
                async with app_sess.begin():
                    await _set_tenant_context(app_sess, co_b_id, b1_id)
                    rows = (await app_sess.execute(select(Invite))).scalars().all()
                    for invite in rows:
                        assert invite.company_id == data["co_b"].id
        finally:
            async with admin_factory() as cleanup:
                await _cleanup_companies(cleanup, [data["co_a"].id, data["co_b"].id])


# ---------------------------------------------------------------------------
# Org codes table isolation
# ---------------------------------------------------------------------------
class TestOrgCodesIsolation:
    async def test_company_b_cannot_see_company_a_org_codes(self, setup_database):
        admin_factory = setup_database["admin_factory"]
        app_factory = setup_database["app_factory"]

        async with admin_factory() as seed:
            data = await _create_two_companies(seed)
            user_a = User(
                company_id=data["co_a"].id, sub_brand_id=data["brand_a1"].id,
                cognito_sub=str(uuid4()), email=f"oc-{uuid4().hex[:6]}@a.com",
                full_name="OC Creator", role="corporate_admin",
            )
            seed.add(user_a)
            await seed.flush()

            seed.add(OrgCode(
                company_id=data["co_a"].id, code=uuid4().hex[:8].upper(),
                is_active=True, created_by=user_a.id,
            ))
            await seed.commit()

        try:
            co_b_id = str(data["co_b"].id)
            b1_id = str(data["brand_b1"].id)
            async with app_factory() as app_sess:
                async with app_sess.begin():
                    await _set_tenant_context(app_sess, co_b_id, b1_id)
                    rows = (await app_sess.execute(select(OrgCode))).scalars().all()
                    for oc in rows:
                        assert oc.company_id == data["co_b"].id
        finally:
            async with admin_factory() as cleanup:
                await _cleanup_companies(cleanup, [data["co_a"].id, data["co_b"].id])


# ---------------------------------------------------------------------------
# Invoices table isolation
# ---------------------------------------------------------------------------
class TestInvoicesIsolation:
    async def _create_users_and_invoices(self, session, data):
        """Helper: create a user per company and an invoice per sub-brand."""
        user_a = User(
            company_id=data["co_a"].id, sub_brand_id=data["brand_a1"].id,
            cognito_sub=str(uuid4()), email=f"inv-a-{uuid4().hex[:6]}@a.com",
            full_name="Inv A", role="employee",
        )
        user_b = User(
            company_id=data["co_b"].id, sub_brand_id=data["brand_b1"].id,
            cognito_sub=str(uuid4()), email=f"inv-b-{uuid4().hex[:6]}@b.com",
            full_name="Inv B", role="employee",
        )
        session.add_all([user_a, user_b])
        await session.flush()

        inv_a1 = Invoice(
            company_id=data["co_a"].id, sub_brand_id=data["brand_a1"].id,
            stripe_invoice_id=f"in_iso_a1_{uuid4().hex[:8]}",
            billing_flow="assigned", status="draft",
            total_amount=100, created_by=user_a.id,
        )
        inv_a2 = Invoice(
            company_id=data["co_a"].id, sub_brand_id=data["brand_a2"].id,
            stripe_invoice_id=f"in_iso_a2_{uuid4().hex[:8]}",
            billing_flow="assigned", status="draft",
            total_amount=200, created_by=user_a.id,
        )
        inv_b = Invoice(
            company_id=data["co_b"].id, sub_brand_id=data["brand_b1"].id,
            stripe_invoice_id=f"in_iso_b_{uuid4().hex[:8]}",
            billing_flow="assigned", status="draft",
            total_amount=300, created_by=user_b.id,
        )
        session.add_all([inv_a1, inv_a2, inv_b])
        await session.flush()
        return {"inv_a1": inv_a1, "inv_a2": inv_a2, "inv_b": inv_b}

    async def test_invoices_company_isolation_rls(self, setup_database):
        """Set company_id A, verify no company B invoices visible."""
        admin_factory = setup_database["admin_factory"]
        app_factory = setup_database["app_factory"]

        async with admin_factory() as seed:
            data = await _create_two_companies(seed)
            invs = await self._create_users_and_invoices(seed, data)
            await seed.commit()

        try:
            co_a_id = str(data["co_a"].id)
            a1_id = str(data["brand_a1"].id)
            async with app_factory() as app_sess:
                async with app_sess.begin():
                    await _set_tenant_context(app_sess, co_a_id, a1_id)
                    rows = (await app_sess.execute(select(Invoice))).scalars().all()
                    for inv in rows:
                        assert inv.company_id == data["co_a"].id
                    # Company B invoice must not appear
                    ids = {inv.id for inv in rows}
                    assert invs["inv_b"].id not in ids
        finally:
            async with admin_factory() as cleanup:
                await _cleanup_companies(cleanup, [data["co_a"].id, data["co_b"].id])

    async def test_invoices_sub_brand_scoping_rls(self, setup_database):
        """Set sub_brand_id A1, verify no A2 invoices visible."""
        admin_factory = setup_database["admin_factory"]
        app_factory = setup_database["app_factory"]

        async with admin_factory() as seed:
            data = await _create_two_companies(seed)
            invs = await self._create_users_and_invoices(seed, data)
            await seed.commit()

        try:
            co_a_id = str(data["co_a"].id)
            a1_id = str(data["brand_a1"].id)
            async with app_factory() as app_sess:
                async with app_sess.begin():
                    await _set_tenant_context(app_sess, co_a_id, a1_id)
                    rows = (await app_sess.execute(select(Invoice))).scalars().all()
                    for inv in rows:
                        assert inv.sub_brand_id == data["brand_a1"].id
                    ids = {inv.id for inv in rows}
                    assert invs["inv_a2"].id not in ids
        finally:
            async with admin_factory() as cleanup:
                await _cleanup_companies(cleanup, [data["co_a"].id, data["co_b"].id])

    async def test_invoices_reel48_admin_bypass_rls(self, setup_database):
        """Empty company_id sees invoices across all companies."""
        admin_factory = setup_database["admin_factory"]
        app_factory = setup_database["app_factory"]

        async with admin_factory() as seed:
            data = await _create_two_companies(seed)
            invs = await self._create_users_and_invoices(seed, data)
            await seed.commit()

        try:
            async with app_factory() as app_sess:
                async with app_sess.begin():
                    await _set_tenant_context(app_sess, None, None)
                    rows = (await app_sess.execute(select(Invoice))).scalars().all()
                    company_ids = {inv.company_id for inv in rows}
                    assert data["co_a"].id in company_ids
                    assert data["co_b"].id in company_ids
        finally:
            async with admin_factory() as cleanup:
                await _cleanup_companies(cleanup, [data["co_a"].id, data["co_b"].id])


# ---------------------------------------------------------------------------
# Notifications table isolation
# ---------------------------------------------------------------------------
class TestNotificationsIsolation:
    async def _create_users_and_notifications(self, session, data):
        """Create users and notifications across companies/sub-brands."""
        user_a = User(
            company_id=data["co_a"].id, sub_brand_id=data["brand_a1"].id,
            cognito_sub=str(uuid4()), email=f"notif-a-{uuid4().hex[:6]}@a.com",
            full_name="Notif A", role="sub_brand_admin",
        )
        user_b = User(
            company_id=data["co_b"].id, sub_brand_id=data["brand_b1"].id,
            cognito_sub=str(uuid4()), email=f"notif-b-{uuid4().hex[:6]}@b.com",
            full_name="Notif B", role="sub_brand_admin",
        )
        session.add_all([user_a, user_b])
        await session.flush()

        notif_a1 = Notification(
            company_id=data["co_a"].id, sub_brand_id=data["brand_a1"].id,
            title="A1 Notification", body="Body A1",
            notification_type="announcement", target_scope="sub_brand",
            created_by=user_a.id,
        )
        notif_a2 = Notification(
            company_id=data["co_a"].id, sub_brand_id=data["brand_a2"].id,
            title="A2 Notification", body="Body A2",
            notification_type="announcement", target_scope="sub_brand",
            created_by=user_a.id,
        )
        notif_b = Notification(
            company_id=data["co_b"].id, sub_brand_id=data["brand_b1"].id,
            title="B Notification", body="Body B",
            notification_type="announcement", target_scope="sub_brand",
            created_by=user_b.id,
        )
        session.add_all([notif_a1, notif_a2, notif_b])
        await session.flush()
        return {"notif_a1": notif_a1, "notif_a2": notif_a2, "notif_b": notif_b}

    async def test_notifications_company_isolation_rls(self, setup_database):
        """Company A context cannot see Company B notifications."""
        admin_factory = setup_database["admin_factory"]
        app_factory = setup_database["app_factory"]

        async with admin_factory() as seed:
            data = await _create_two_companies(seed)
            notifs = await self._create_users_and_notifications(seed, data)
            await seed.commit()

        try:
            co_a_id = str(data["co_a"].id)
            a1_id = str(data["brand_a1"].id)
            async with app_factory() as app_sess:
                async with app_sess.begin():
                    await _set_tenant_context(app_sess, co_a_id, a1_id)
                    rows = (await app_sess.execute(select(Notification))).scalars().all()
                    for n in rows:
                        assert n.company_id == data["co_a"].id
                    ids = {n.id for n in rows}
                    assert notifs["notif_b"].id not in ids
        finally:
            async with admin_factory() as cleanup:
                await _cleanup_companies(cleanup, [data["co_a"].id, data["co_b"].id])

    async def test_notifications_sub_brand_scoping_rls(self, setup_database):
        """Sub-brand A1 context cannot see A2 notifications."""
        admin_factory = setup_database["admin_factory"]
        app_factory = setup_database["app_factory"]

        async with admin_factory() as seed:
            data = await _create_two_companies(seed)
            notifs = await self._create_users_and_notifications(seed, data)
            await seed.commit()

        try:
            co_a_id = str(data["co_a"].id)
            a1_id = str(data["brand_a1"].id)
            async with app_factory() as app_sess:
                async with app_sess.begin():
                    await _set_tenant_context(app_sess, co_a_id, a1_id)
                    rows = (await app_sess.execute(select(Notification))).scalars().all()
                    for n in rows:
                        assert n.sub_brand_id == data["brand_a1"].id
                    ids = {n.id for n in rows}
                    assert notifs["notif_a2"].id not in ids
        finally:
            async with admin_factory() as cleanup:
                await _cleanup_companies(cleanup, [data["co_a"].id, data["co_b"].id])

    async def test_notifications_reel48_admin_bypass_rls(self, setup_database):
        """Empty company_id sees notifications across all companies."""
        admin_factory = setup_database["admin_factory"]
        app_factory = setup_database["app_factory"]

        async with admin_factory() as seed:
            data = await _create_two_companies(seed)
            notifs = await self._create_users_and_notifications(seed, data)
            await seed.commit()

        try:
            async with app_factory() as app_sess:
                async with app_sess.begin():
                    await _set_tenant_context(app_sess, None, None)
                    rows = (await app_sess.execute(select(Notification))).scalars().all()
                    company_ids = {n.company_id for n in rows}
                    assert data["co_a"].id in company_ids
                    assert data["co_b"].id in company_ids
        finally:
            async with admin_factory() as cleanup:
                await _cleanup_companies(cleanup, [data["co_a"].id, data["co_b"].id])


# ---------------------------------------------------------------------------
# Wishlists table isolation
# ---------------------------------------------------------------------------
class TestWishlistsIsolation:
    async def _create_users_products_and_wishlists(self, session, data):
        """Create users, products, and wishlist entries across companies/sub-brands."""
        user_a = User(
            company_id=data["co_a"].id, sub_brand_id=data["brand_a1"].id,
            cognito_sub=str(uuid4()), email=f"wl-a-{uuid4().hex[:6]}@a.com",
            full_name="WL A", role="employee",
        )
        user_a2 = User(
            company_id=data["co_a"].id, sub_brand_id=data["brand_a2"].id,
            cognito_sub=str(uuid4()), email=f"wl-a2-{uuid4().hex[:6]}@a.com",
            full_name="WL A2", role="employee",
        )
        user_b = User(
            company_id=data["co_b"].id, sub_brand_id=data["brand_b1"].id,
            cognito_sub=str(uuid4()), email=f"wl-b-{uuid4().hex[:6]}@b.com",
            full_name="WL B", role="employee",
        )
        session.add_all([user_a, user_a2, user_b])
        await session.flush()

        prod_a1 = Product(
            company_id=data["co_a"].id, sub_brand_id=data["brand_a1"].id,
            name="Product A1", sku=f"SKU-A1-{uuid4().hex[:6]}",
            unit_price=10, status="active", created_by=user_a.id,
        )
        prod_a2 = Product(
            company_id=data["co_a"].id, sub_brand_id=data["brand_a2"].id,
            name="Product A2", sku=f"SKU-A2-{uuid4().hex[:6]}",
            unit_price=20, status="active", created_by=user_a2.id,
        )
        prod_b = Product(
            company_id=data["co_b"].id, sub_brand_id=data["brand_b1"].id,
            name="Product B", sku=f"SKU-B-{uuid4().hex[:6]}",
            unit_price=30, status="active", created_by=user_b.id,
        )
        session.add_all([prod_a1, prod_a2, prod_b])
        await session.flush()

        wl_a1 = Wishlist(
            company_id=data["co_a"].id, sub_brand_id=data["brand_a1"].id,
            user_id=user_a.id, product_id=prod_a1.id,
        )
        wl_a2 = Wishlist(
            company_id=data["co_a"].id, sub_brand_id=data["brand_a2"].id,
            user_id=user_a2.id, product_id=prod_a2.id,
        )
        wl_b = Wishlist(
            company_id=data["co_b"].id, sub_brand_id=data["brand_b1"].id,
            user_id=user_b.id, product_id=prod_b.id,
        )
        session.add_all([wl_a1, wl_a2, wl_b])
        await session.flush()
        return {"wl_a1": wl_a1, "wl_a2": wl_a2, "wl_b": wl_b}

    async def test_wishlists_company_isolation_rls(self, setup_database):
        """Company A context cannot see Company B wishlist entries."""
        admin_factory = setup_database["admin_factory"]
        app_factory = setup_database["app_factory"]

        async with admin_factory() as seed:
            data = await _create_two_companies(seed)
            wls = await self._create_users_products_and_wishlists(seed, data)
            await seed.commit()

        try:
            co_a_id = str(data["co_a"].id)
            a1_id = str(data["brand_a1"].id)
            async with app_factory() as app_sess:
                async with app_sess.begin():
                    await _set_tenant_context(app_sess, co_a_id, a1_id)
                    rows = (await app_sess.execute(select(Wishlist))).scalars().all()
                    for w in rows:
                        assert w.company_id == data["co_a"].id
                    ids = {w.id for w in rows}
                    assert wls["wl_b"].id not in ids
        finally:
            async with admin_factory() as cleanup:
                await _cleanup_companies(cleanup, [data["co_a"].id, data["co_b"].id])

    async def test_wishlists_sub_brand_scoping_rls(self, setup_database):
        """Sub-brand A1 context cannot see A2 wishlist entries."""
        admin_factory = setup_database["admin_factory"]
        app_factory = setup_database["app_factory"]

        async with admin_factory() as seed:
            data = await _create_two_companies(seed)
            wls = await self._create_users_products_and_wishlists(seed, data)
            await seed.commit()

        try:
            co_a_id = str(data["co_a"].id)
            a1_id = str(data["brand_a1"].id)
            async with app_factory() as app_sess:
                async with app_sess.begin():
                    await _set_tenant_context(app_sess, co_a_id, a1_id)
                    rows = (await app_sess.execute(select(Wishlist))).scalars().all()
                    for w in rows:
                        assert w.sub_brand_id == data["brand_a1"].id
                    ids = {w.id for w in rows}
                    assert wls["wl_a2"].id not in ids
        finally:
            async with admin_factory() as cleanup:
                await _cleanup_companies(cleanup, [data["co_a"].id, data["co_b"].id])

    async def test_wishlists_reel48_admin_bypass_rls(self, setup_database):
        """Empty company_id sees wishlists across all companies."""
        admin_factory = setup_database["admin_factory"]
        app_factory = setup_database["app_factory"]

        async with admin_factory() as seed:
            data = await _create_two_companies(seed)
            wls = await self._create_users_products_and_wishlists(seed, data)
            await seed.commit()

        try:
            async with app_factory() as app_sess:
                async with app_sess.begin():
                    await _set_tenant_context(app_sess, None, None)
                    rows = (await app_sess.execute(select(Wishlist))).scalars().all()
                    company_ids = {w.company_id for w in rows}
                    assert data["co_a"].id in company_ids
                    assert data["co_b"].id in company_ids
        finally:
            async with admin_factory() as cleanup:
                await _cleanup_companies(cleanup, [data["co_a"].id, data["co_b"].id])
