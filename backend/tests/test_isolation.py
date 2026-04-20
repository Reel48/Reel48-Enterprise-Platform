"""Cross-company RLS isolation tests.

Data is seeded via a superuser session and COMMITTED (so the RLS-enforced
session on a separate connection can see it). Each test creates its own
data and cleans up after.
"""

import secrets
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.invite import Invite
from app.models.org_code import OrgCode
from app.models.user import User


async def _set_company(session, company_id: str | None) -> None:
    cid = company_id or ""
    await session.execute(text(f"SET LOCAL app.current_company_id = '{cid}'"))


async def _cleanup(session: AsyncSession, company_ids: list) -> None:
    for cid in company_ids:
        cid_str = str(cid)
        await session.execute(text(f"DELETE FROM notifications WHERE company_id = '{cid_str}'"))
        await session.execute(text(f"DELETE FROM employee_profiles WHERE company_id = '{cid_str}'"))
        await session.execute(text(f"DELETE FROM invites WHERE company_id = '{cid_str}'"))
        await session.execute(text(f"DELETE FROM org_codes WHERE company_id = '{cid_str}'"))
        await session.execute(text(f"DELETE FROM users WHERE company_id = '{cid_str}'"))
        await session.execute(text(f"DELETE FROM companies WHERE id = '{cid_str}'"))
    await session.commit()


@pytest.mark.asyncio
async def test_company_b_cannot_see_company_a_users(setup_database) -> None:
    admin_factory = setup_database["admin_factory"]
    app_factory = setup_database["app_factory"]

    co_a_id: str | None = None
    co_b_id: str | None = None

    async with admin_factory() as seed:
        uid = uuid4().hex[:6]
        co_a = Company(name=f"IsoA-{uid}", slug=f"iso-a-{uid}", is_active=True)
        co_b = Company(name=f"IsoB-{uid}", slug=f"iso-b-{uid}", is_active=True)
        seed.add_all([co_a, co_b])
        await seed.flush()
        co_a_id, co_b_id = co_a.id, co_b.id

        seed.add(User(
            company_id=co_a.id,
            cognito_sub=str(uuid4()),
            email=f"a-{uuid4().hex[:6]}@a.com",
            full_name="A user",
            role="employee",
        ))
        seed.add(User(
            company_id=co_b.id,
            cognito_sub=str(uuid4()),
            email=f"b-{uuid4().hex[:6]}@b.com",
            full_name="B user",
            role="employee",
        ))
        await seed.commit()

    try:
        async with app_factory() as app_session:
            async with app_session.begin():
                await _set_company(app_session, str(co_b_id))
                result = await app_session.execute(
                    text("SELECT company_id FROM users")
                )
                company_ids = {row.company_id for row in result.all()}
                assert co_b_id in company_ids
                assert co_a_id not in company_ids
    finally:
        async with admin_factory() as cleanup:
            await _cleanup(cleanup, [co_a_id, co_b_id])


# NOTE: reel48_admin cross-company access (empty string app.current_company_id)
# is exercised through the platform/ endpoints via the superuser DB connection,
# which has BYPASSRLS implicitly. Testing the empty-string path on the
# reel48_app non-superuser role hits a PostgreSQL OR short-circuit quirk
# (`::uuid` cast runs even though `= ''` is true), per the harness rule in
# .claude/rules/testing.md ("Always pass a real UUID.").


@pytest.mark.asyncio
async def test_invites_and_org_codes_isolated_by_company(setup_database) -> None:
    admin_factory = setup_database["admin_factory"]
    app_factory = setup_database["app_factory"]

    async with admin_factory() as seed:
        uid = uuid4().hex[:6]
        co_a = Company(name=f"IsoA-{uid}", slug=f"iso-a-{uid}", is_active=True)
        co_b = Company(name=f"IsoB-{uid}", slug=f"iso-b-{uid}", is_active=True)
        seed.add_all([co_a, co_b])
        await seed.flush()
        co_a_id, co_b_id = co_a.id, co_b.id

        admin_user = User(
            company_id=co_a.id,
            cognito_sub=str(uuid4()),
            email=f"admin-{uid}@a.com",
            full_name="A admin",
            role="company_admin",
        )
        seed.add(admin_user)
        await seed.flush()

        org_a = OrgCode(
            company_id=co_a.id,
            code=f"C{uid[:7].upper()}",
            is_active=True,
            created_by=admin_user.id,
        )
        invite_a = Invite(
            company_id=co_a.id,
            email="inv@a.com",
            role="employee",
            token=secrets.token_hex(32),
            expires_at=datetime.now(UTC) + timedelta(hours=72),
            created_by=admin_user.id,
        )
        seed.add_all([org_a, invite_a])
        await seed.commit()

    try:
        async with app_factory() as app_session:
            async with app_session.begin():
                await _set_company(app_session, str(co_b_id))
                invites_rows = (await app_session.execute(
                    text("SELECT id FROM invites")
                )).all()
                org_rows = (await app_session.execute(
                    text("SELECT id FROM org_codes")
                )).all()
                assert len(invites_rows) == 0
                assert len(org_rows) == 0
    finally:
        async with admin_factory() as cleanup:
            await _cleanup(cleanup, [co_a_id, co_b_id])
