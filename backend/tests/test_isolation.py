"""
Cross-tenant RLS integration tests.

These tests verify that PostgreSQL Row-Level Security policies correctly
isolate data between companies and sub-brands. Data is seeded via a
superuser session (bypasses RLS), then queried via the `reel48_app` role
(RLS enforced) with session variables set to simulate different tenant contexts.

Coverage:
- Company A cannot see Company B's data (and vice versa)
- Sub-Brand A1 cannot see Sub-Brand A2's data (within same company)
- Corporate admin (empty sub_brand_id) sees all sub-brands in their company
- reel48_admin (empty company_id) sees all companies
- Isolation applies to all 5 Module 1 tables
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import func, select, text

from app.models.company import Company
from app.models.invite import Invite
from app.models.org_code import OrgCode
from app.models.sub_brand import SubBrand
from app.models.user import User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
async def _set_tenant_context(session, company_id: str | None, sub_brand_id: str | None):
    """Set RLS session variables on a non-superuser session."""
    cid = company_id or ""
    sbid = sub_brand_id or ""
    await session.execute(text("SET LOCAL app.current_company_id = :cid"), {"cid": cid})
    await session.execute(text("SET LOCAL app.current_sub_brand_id = :sbid"), {"sbid": sbid})


# ---------------------------------------------------------------------------
# Users table isolation
# ---------------------------------------------------------------------------
class TestUsersIsolation:
    async def test_company_b_cannot_see_company_a_users(
        self, admin_db_session, db_session, company_a, company_b
    ):
        """Cross-company isolation: Company B sees zero Company A users."""
        co_a, brand_a1, _ = company_a
        co_b, brand_b1 = company_b

        # Seed users in both companies (via superuser)
        admin_db_session.add(
            User(
                company_id=co_a.id, sub_brand_id=brand_a1.id, cognito_sub=str(uuid4()),
                email=f"a-{uuid4().hex[:6]}@a.com", full_name="User A", role="employee",
            )
        )
        admin_db_session.add(
            User(
                company_id=co_b.id, sub_brand_id=brand_b1.id, cognito_sub=str(uuid4()),
                email=f"b-{uuid4().hex[:6]}@b.com", full_name="User B", role="employee",
            )
        )
        await admin_db_session.flush()

        # Query as Company B (RLS-enforced session)
        await _set_tenant_context(db_session, str(co_b.id), str(brand_b1.id))
        result = await db_session.execute(select(func.count()).select_from(User))
        count = result.scalar()

        # Should see only Company B's user(s), not Company A's
        assert count >= 1
        rows = (await db_session.execute(select(User))).scalars().all()
        for user in rows:
            assert user.company_id == co_b.id

    async def test_brand_a2_cannot_see_brand_a1_users(
        self, admin_db_session, db_session, company_a
    ):
        """Cross-sub-brand isolation within the same company."""
        co_a, brand_a1, brand_a2 = company_a

        admin_db_session.add(
            User(
                company_id=co_a.id, sub_brand_id=brand_a1.id, cognito_sub=str(uuid4()),
                email=f"a1-{uuid4().hex[:6]}@a.com", full_name="User A1", role="employee",
            )
        )
        admin_db_session.add(
            User(
                company_id=co_a.id, sub_brand_id=brand_a2.id, cognito_sub=str(uuid4()),
                email=f"a2-{uuid4().hex[:6]}@a.com", full_name="User A2", role="employee",
            )
        )
        await admin_db_session.flush()

        # Query as Brand A2 employee
        await _set_tenant_context(db_session, str(co_a.id), str(brand_a2.id))
        rows = (await db_session.execute(select(User))).scalars().all()

        for user in rows:
            assert user.sub_brand_id == brand_a2.id

    async def test_corporate_admin_sees_all_sub_brands(
        self, admin_db_session, db_session, company_a
    ):
        """Corporate admin (empty sub_brand_id) sees users in all sub-brands."""
        co_a, brand_a1, brand_a2 = company_a

        admin_db_session.add(
            User(
                company_id=co_a.id, sub_brand_id=brand_a1.id, cognito_sub=str(uuid4()),
                email=f"ca1-{uuid4().hex[:6]}@a.com", full_name="Corp A1", role="employee",
            )
        )
        admin_db_session.add(
            User(
                company_id=co_a.id, sub_brand_id=brand_a2.id, cognito_sub=str(uuid4()),
                email=f"ca2-{uuid4().hex[:6]}@a.com", full_name="Corp A2", role="employee",
            )
        )
        await admin_db_session.flush()

        # Corporate admin: company_id set, sub_brand_id empty (sees all sub-brands)
        await _set_tenant_context(db_session, str(co_a.id), None)
        rows = (await db_session.execute(select(User))).scalars().all()

        sub_brand_ids = {user.sub_brand_id for user in rows}
        assert brand_a1.id in sub_brand_ids or brand_a2.id in sub_brand_ids
        # All users belong to Company A
        for user in rows:
            assert user.company_id == co_a.id

    async def test_reel48_admin_sees_all_companies(
        self, admin_db_session, db_session, company_a, company_b
    ):
        """reel48_admin (empty company_id) sees users across all companies."""
        co_a, brand_a1, _ = company_a
        co_b, brand_b1 = company_b

        admin_db_session.add(
            User(
                company_id=co_a.id, sub_brand_id=brand_a1.id, cognito_sub=str(uuid4()),
                email=f"ra-{uuid4().hex[:6]}@a.com", full_name="R48 A", role="employee",
            )
        )
        admin_db_session.add(
            User(
                company_id=co_b.id, sub_brand_id=brand_b1.id, cognito_sub=str(uuid4()),
                email=f"rb-{uuid4().hex[:6]}@b.com", full_name="R48 B", role="employee",
            )
        )
        await admin_db_session.flush()

        # reel48_admin: both empty strings (RLS bypass)
        await _set_tenant_context(db_session, None, None)
        rows = (await db_session.execute(select(User))).scalars().all()

        company_ids = {user.company_id for user in rows}
        assert co_a.id in company_ids
        assert co_b.id in company_ids


# ---------------------------------------------------------------------------
# Companies table isolation
# ---------------------------------------------------------------------------
class TestCompaniesIsolation:
    async def test_tenant_sees_only_own_company(
        self, admin_db_session, db_session, company_a, company_b
    ):
        """A tenant user sees only their own company row."""
        co_a, brand_a1, _ = company_a
        co_b, _ = company_b

        await _set_tenant_context(db_session, str(co_a.id), str(brand_a1.id))
        rows = (await db_session.execute(select(Company))).scalars().all()

        assert len(rows) == 1
        assert rows[0].id == co_a.id

    async def test_reel48_admin_sees_all_companies(
        self, admin_db_session, db_session, company_a, company_b
    ):
        """reel48_admin sees all companies."""
        co_a, _, _ = company_a
        co_b, _ = company_b

        await _set_tenant_context(db_session, None, None)
        rows = (await db_session.execute(select(Company))).scalars().all()

        ids = {c.id for c in rows}
        assert co_a.id in ids
        assert co_b.id in ids


# ---------------------------------------------------------------------------
# Sub-brands table isolation
# ---------------------------------------------------------------------------
class TestSubBrandsIsolation:
    async def test_company_b_cannot_see_company_a_sub_brands(
        self, admin_db_session, db_session, company_a, company_b
    ):
        co_a, _, _ = company_a
        co_b, brand_b1 = company_b

        await _set_tenant_context(db_session, str(co_b.id), str(brand_b1.id))
        rows = (await db_session.execute(select(SubBrand))).scalars().all()

        for sb in rows:
            assert sb.company_id == co_b.id


# ---------------------------------------------------------------------------
# Invites table isolation
# ---------------------------------------------------------------------------
class TestInvitesIsolation:
    async def test_company_b_cannot_see_company_a_invites(
        self, admin_db_session, db_session, company_a, company_b, user_a1_employee
    ):
        co_a, brand_a1, _ = company_a
        co_b, brand_b1 = company_b

        admin_db_session.add(
            Invite(
                company_id=co_a.id,
                target_sub_brand_id=brand_a1.id,
                email="invite-a@a.com",
                role="employee",
                token=uuid4().hex,
                expires_at=datetime.now(UTC) + timedelta(hours=72),
                created_by=user_a1_employee.id,
            )
        )
        await admin_db_session.flush()

        await _set_tenant_context(db_session, str(co_b.id), str(brand_b1.id))
        rows = (await db_session.execute(select(Invite))).scalars().all()

        for invite in rows:
            assert invite.company_id == co_b.id


# ---------------------------------------------------------------------------
# Org codes table isolation
# ---------------------------------------------------------------------------
class TestOrgCodesIsolation:
    async def test_company_b_cannot_see_company_a_org_codes(
        self, admin_db_session, db_session, company_a, company_b, user_a1_employee
    ):
        co_a, _, _ = company_a
        co_b, brand_b1 = company_b

        admin_db_session.add(
            OrgCode(
                company_id=co_a.id,
                code=uuid4().hex[:8].upper(),
                is_active=True,
                created_by=user_a1_employee.id,
            )
        )
        await admin_db_session.flush()

        await _set_tenant_context(db_session, str(co_b.id), str(brand_b1.id))
        rows = (await db_session.execute(select(OrgCode))).scalars().all()

        for oc in rows:
            assert oc.company_id == co_b.id
