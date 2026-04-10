"""Tests for the Employee Profiles CRUD endpoints (Module 2)."""

from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from tests.conftest import create_test_token

# ---------------------------------------------------------------------------
# Functional Tests
# ---------------------------------------------------------------------------


class TestGetMyProfile:
    async def test_get_my_profile_returns_own_profile(
        self,
        client: AsyncClient,
        user_a1_employee_token: str,
        user_a1_employee,
    ):
        # First create a profile via PUT /me
        await client.put(
            "/api/v1/profiles/me",
            json={"department": "Engineering", "shirt_size": "L"},
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )

        response = await client.get(
            "/api/v1/profiles/me",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["department"] == "Engineering"
        assert data["shirt_size"] == "L"
        assert data["user_id"] == str(user_a1_employee.id)

    async def test_get_my_profile_returns_404_when_no_profile(
        self,
        client: AsyncClient,
        user_a1_employee_token: str,
        user_a1_employee,
    ):
        response = await client.get(
            "/api/v1/profiles/me",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 404

    async def test_get_my_profile_unauthenticated_returns_401(
        self,
        client: AsyncClient,
    ):
        response = await client.get("/api/v1/profiles/me")
        assert response.status_code == 401


class TestUpsertMyProfile:
    async def test_put_me_creates_profile(
        self,
        client: AsyncClient,
        user_a1_employee_token: str,
        user_a1_employee,
    ):
        response = await client.put(
            "/api/v1/profiles/me",
            json={
                "department": "Sales",
                "job_title": "Account Manager",
                "shirt_size": "M",
                "pant_size": "32x30",
                "shoe_size": "10",
                "delivery_address_line1": "123 Main St",
                "delivery_city": "Austin",
                "delivery_state": "TX",
                "delivery_zip": "78701",
            },
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["department"] == "Sales"
        assert data["job_title"] == "Account Manager"
        assert data["shirt_size"] == "M"
        assert data["pant_size"] == "32x30"
        assert data["delivery_city"] == "Austin"
        assert data["user_id"] == str(user_a1_employee.id)
        assert data["company_id"] == str(user_a1_employee.company_id)
        assert data["onboarding_complete"] is False

    async def test_put_me_updates_existing_profile(
        self,
        client: AsyncClient,
        user_a1_employee_token: str,
        user_a1_employee,
    ):
        # Create initial profile
        await client.put(
            "/api/v1/profiles/me",
            json={"department": "Sales", "shirt_size": "M"},
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )

        # Update with new data
        response = await client.put(
            "/api/v1/profiles/me",
            json={"department": "Engineering", "shirt_size": "L"},
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["department"] == "Engineering"
        assert data["shirt_size"] == "L"

    async def test_put_me_with_empty_body_creates_profile(
        self,
        client: AsyncClient,
        user_a1_employee_token: str,
        user_a1_employee,
    ):
        response = await client.put(
            "/api/v1/profiles/me",
            json={},
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["user_id"] == str(user_a1_employee.id)
        assert data["department"] is None

    async def test_shirt_size_validation_rejects_invalid(
        self,
        client: AsyncClient,
        user_a1_employee_token: str,
        user_a1_employee,
    ):
        response = await client.put(
            "/api/v1/profiles/me",
            json={"shirt_size": "XXL"},
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 422

    async def test_shirt_size_accepts_valid_sizes(
        self,
        client: AsyncClient,
        user_a1_employee_token: str,
        user_a1_employee,
    ):
        for size in ["XS", "S", "M", "L", "XL", "2XL", "3XL"]:
            response = await client.put(
                "/api/v1/profiles/me",
                json={"shirt_size": size},
                headers={"Authorization": f"Bearer {user_a1_employee_token}"},
            )
            assert response.status_code == 200
            assert response.json()["data"]["shirt_size"] == size


class TestListProfiles:
    async def test_admin_can_list_profiles(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
        user_a1_employee_token: str,
        user_a1_employee,
    ):
        # Create a profile for the employee
        await client.put(
            "/api/v1/profiles/me",
            json={"department": "Engineering"},
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )

        response = await client.get(
            "/api/v1/profiles/",
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["meta"]["total"] >= 1
        assert len(data["data"]) >= 1

    async def test_pagination_works(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
        user_a1_employee_token: str,
        user_a1_employee,
    ):
        # Create a profile
        await client.put(
            "/api/v1/profiles/me",
            json={"department": "Sales"},
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )

        response = await client.get(
            "/api/v1/profiles/?page=1&per_page=1",
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["meta"]["per_page"] == 1
        assert len(data["data"]) <= 1


class TestGetProfileById:
    async def test_admin_can_get_profile(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
        user_a1_employee_token: str,
        user_a1_employee,
    ):
        # Create a profile
        create_resp = await client.put(
            "/api/v1/profiles/me",
            json={"department": "Engineering"},
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        profile_id = create_resp.json()["data"]["id"]

        response = await client.get(
            f"/api/v1/profiles/{profile_id}",
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["id"] == profile_id

    async def test_employee_can_get_own_profile_by_id(
        self,
        client: AsyncClient,
        user_a1_employee_token: str,
        user_a1_employee,
    ):
        create_resp = await client.put(
            "/api/v1/profiles/me",
            json={"department": "Sales"},
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        profile_id = create_resp.json()["data"]["id"]

        response = await client.get(
            f"/api/v1/profiles/{profile_id}",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["id"] == profile_id


class TestUpdateProfile:
    async def test_admin_can_update_profile(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
        user_a1_employee_token: str,
        user_a1_employee,
    ):
        # Create a profile
        create_resp = await client.put(
            "/api/v1/profiles/me",
            json={"department": "Sales"},
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        profile_id = create_resp.json()["data"]["id"]

        response = await client.patch(
            f"/api/v1/profiles/{profile_id}",
            json={"department": "Engineering", "job_title": "Senior Dev"},
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["department"] == "Engineering"
        assert data["job_title"] == "Senior Dev"

    async def test_admin_can_set_onboarding_complete(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
        user_a1_employee_token: str,
        user_a1_employee,
    ):
        create_resp = await client.put(
            "/api/v1/profiles/me",
            json={},
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        profile_id = create_resp.json()["data"]["id"]

        response = await client.patch(
            f"/api/v1/profiles/{profile_id}",
            json={"onboarding_complete": True},
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["onboarding_complete"] is True


class TestDeleteProfile:
    async def test_admin_can_soft_delete_profile(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
        user_a1_employee_token: str,
        user_a1_employee,
    ):
        create_resp = await client.put(
            "/api/v1/profiles/me",
            json={"department": "Sales"},
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        profile_id = create_resp.json()["data"]["id"]

        response = await client.delete(
            f"/api/v1/profiles/{profile_id}",
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["id"] == profile_id

    async def test_deleted_profile_excluded_from_get_me(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
        user_a1_employee_token: str,
        user_a1_employee,
    ):
        # Create and then delete
        create_resp = await client.put(
            "/api/v1/profiles/me",
            json={"department": "Sales"},
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        profile_id = create_resp.json()["data"]["id"]

        await client.delete(
            f"/api/v1/profiles/{profile_id}",
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )

        # GET /me should now return 404
        response = await client.get(
            "/api/v1/profiles/me",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Complete Onboarding Tests
# ---------------------------------------------------------------------------


class TestCompleteOnboarding:
    async def test_complete_onboarding_sets_flag_true(
        self,
        client: AsyncClient,
        user_a1_employee_token: str,
        user_a1_employee,
    ):
        # Create a profile first
        await client.put(
            "/api/v1/profiles/me",
            json={"department": "Sales"},
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )

        response = await client.post(
            "/api/v1/profiles/me/complete-onboarding",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["onboarding_complete"] is True

    async def test_complete_onboarding_idempotent(
        self,
        client: AsyncClient,
        user_a1_employee_token: str,
        user_a1_employee,
    ):
        # Create profile and complete onboarding
        await client.put(
            "/api/v1/profiles/me",
            json={"department": "Sales"},
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        await client.post(
            "/api/v1/profiles/me/complete-onboarding",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )

        # Call again — should still return 200
        response = await client.post(
            "/api/v1/profiles/me/complete-onboarding",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["onboarding_complete"] is True

    async def test_complete_onboarding_creates_profile_if_none_exists(
        self,
        client: AsyncClient,
        user_a1_employee_token: str,
        user_a1_employee,
    ):
        # No profile exists yet
        response = await client.post(
            "/api/v1/profiles/me/complete-onboarding",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["onboarding_complete"] is True
        assert data["user_id"] == str(user_a1_employee.id)

    async def test_complete_onboarding_unauthenticated_returns_401(
        self,
        client: AsyncClient,
    ):
        response = await client.post("/api/v1/profiles/me/complete-onboarding")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Authorization Tests
# ---------------------------------------------------------------------------


class TestProfileAuthorization:
    async def test_employee_cannot_list_profiles(
        self,
        client: AsyncClient,
        user_a1_employee_token: str,
        user_a1_employee,
    ):
        response = await client.get(
            "/api/v1/profiles/",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 403

    async def test_employee_cannot_patch_other_profile(
        self,
        client: AsyncClient,
        user_a1_employee_token: str,
        user_a1_employee,
        user_a1_admin_token: str,
        user_a1_admin,
    ):
        # Create admin's own profile
        create_resp = await client.put(
            "/api/v1/profiles/me",
            json={"department": "Management"},
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        profile_id = create_resp.json()["data"]["id"]

        # Employee tries to PATCH it
        response = await client.patch(
            f"/api/v1/profiles/{profile_id}",
            json={"department": "Hacked"},
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 403

    async def test_employee_cannot_delete_profile(
        self,
        client: AsyncClient,
        user_a1_employee_token: str,
        user_a1_employee,
    ):
        # Create own profile first
        create_resp = await client.put(
            "/api/v1/profiles/me",
            json={"department": "Sales"},
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        profile_id = create_resp.json()["data"]["id"]

        response = await client.delete(
            f"/api/v1/profiles/{profile_id}",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 403

    async def test_employee_cannot_get_other_users_profile(
        self,
        client: AsyncClient,
        user_a1_employee_token: str,
        user_a1_employee,
        user_a1_admin_token: str,
        user_a1_admin,
    ):
        # Create admin's profile
        create_resp = await client.put(
            "/api/v1/profiles/me",
            json={"department": "Management"},
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        profile_id = create_resp.json()["data"]["id"]

        # Employee tries to GET it by ID
        response = await client.get(
            f"/api/v1/profiles/{profile_id}",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 403

    async def test_employee_can_use_me_endpoints(
        self,
        client: AsyncClient,
        user_a1_employee_token: str,
        user_a1_employee,
    ):
        # PUT /me works
        put_resp = await client.put(
            "/api/v1/profiles/me",
            json={"department": "Sales"},
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert put_resp.status_code == 200

        # GET /me works
        get_resp = await client.get(
            "/api/v1/profiles/me",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert get_resp.status_code == 200

    async def test_sub_brand_admin_can_manage_profiles_in_own_brand(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
        user_a1_employee_token: str,
        user_a1_employee,
    ):
        # Create a profile for the employee
        create_resp = await client.put(
            "/api/v1/profiles/me",
            json={"department": "Engineering"},
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        profile_id = create_resp.json()["data"]["id"]

        # sub_brand_admin can PATCH
        response = await client.patch(
            f"/api/v1/profiles/{profile_id}",
            json={"onboarding_complete": True},
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Isolation Tests
# ---------------------------------------------------------------------------


class TestProfileIsolation:
    async def test_company_b_cannot_see_company_a_profiles(
        self,
        client: AsyncClient,
        user_a1_employee_token: str,
        user_a1_employee,
        user_b1_employee,
        company_b,
        admin_db_session,
    ):
        # Create a profile in Company A
        await client.put(
            "/api/v1/profiles/me",
            json={"department": "Engineering"},
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )

        # Company B admin tries to list profiles — should see 0 Company A profiles
        company_b_obj, brand_b1 = company_b
        b_admin = await _create_admin_user(
            admin_db_session, company_b_obj.id, brand_b1.id
        )
        b_admin_token = create_test_token(
            user_id=b_admin.cognito_sub,
            company_id=str(company_b_obj.id),
            sub_brand_id=str(brand_b1.id),
            role="sub_brand_admin",
        )

        response = await client.get(
            "/api/v1/profiles/",
            headers={"Authorization": f"Bearer {b_admin_token}"},
        )
        assert response.status_code == 200
        assert response.json()["meta"]["total"] == 0

    async def test_brand_a2_admin_cannot_see_brand_a1_profiles_in_list(
        self,
        client: AsyncClient,
        user_a1_employee_token: str,
        user_a1_employee,
        company_a,
        admin_db_session,
    ):
        # Create a profile in Brand A1
        await client.put(
            "/api/v1/profiles/me",
            json={"department": "Engineering"},
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )

        # Brand A2 admin should not see Brand A1 profiles in list
        _company, _a1, brand_a2 = company_a
        a2_admin = await _create_admin_user(
            admin_db_session, _company.id, brand_a2.id
        )
        a2_admin_token = create_test_token(
            user_id=a2_admin.cognito_sub,
            company_id=str(_company.id),
            sub_brand_id=str(brand_a2.id),
            role="sub_brand_admin",
        )

        response = await client.get(
            "/api/v1/profiles/",
            headers={"Authorization": f"Bearer {a2_admin_token}"},
        )
        assert response.status_code == 200
        assert response.json()["meta"]["total"] == 0

    async def test_corporate_admin_sees_all_sub_brand_profiles(
        self,
        client: AsyncClient,
        user_a1_employee_token: str,
        user_a1_employee,
        user_a_corporate_admin_token: str,
        user_a_corporate_admin,
        company_a,
        admin_db_session,
    ):
        # Create profile in Brand A1
        await client.put(
            "/api/v1/profiles/me",
            json={"department": "Engineering"},
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )

        # Create a user in Brand A2 and their profile
        _company, _a1, brand_a2 = company_a
        a2_employee = await _create_employee_user(
            admin_db_session, _company.id, brand_a2.id
        )
        a2_token = create_test_token(
            user_id=a2_employee.cognito_sub,
            company_id=str(_company.id),
            sub_brand_id=str(brand_a2.id),
            role="employee",
        )
        await client.put(
            "/api/v1/profiles/me",
            json={"department": "Marketing"},
            headers={"Authorization": f"Bearer {a2_token}"},
        )

        # Corporate admin should see both
        response = await client.get(
            "/api/v1/profiles/",
            headers={"Authorization": f"Bearer {user_a_corporate_admin_token}"},
        )
        assert response.status_code == 200
        assert response.json()["meta"]["total"] >= 2


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


async def _create_admin_user(
    db: AsyncSession, company_id, sub_brand_id
) -> User:
    user = User(
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        cognito_sub=str(uuid4()),
        email=f"admin-{uuid4().hex[:6]}@test.com",
        full_name="Test Admin",
        role="sub_brand_admin",
    )
    db.add(user)
    await db.flush()
    return user


async def _create_employee_user(
    db: AsyncSession, company_id, sub_brand_id
) -> User:
    user = User(
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        cognito_sub=str(uuid4()),
        email=f"employee-{uuid4().hex[:6]}@test.com",
        full_name="Test Employee",
        role="employee",
    )
    db.add(user)
    await db.flush()
    return user


# ---------------------------------------------------------------------------
# Profile Photo Management Tests (Phase 3: S3 Storage Integration)
# ---------------------------------------------------------------------------


class TestSetProfilePhoto:
    async def test_set_photo_returns_200_with_updated_url(
        self,
        client: AsyncClient,
        user_a1_employee_token: str,
        user_a1_employee,
        company_a,
    ):
        company, brand_a1, _brand_a2 = company_a
        # Create profile first
        await client.put(
            "/api/v1/profiles/me",
            json={"department": "Engineering"},
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )

        s3_key = f"{company.id}/{brand_a1.slug}/profiles/{uuid4()}.png"
        response = await client.post(
            "/api/v1/profiles/me/photo",
            json={"s3_key": s3_key},
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["profile_photo_url"] == s3_key

    async def test_set_photo_overwrites_previous(
        self,
        client: AsyncClient,
        user_a1_employee_token: str,
        user_a1_employee,
        company_a,
    ):
        company, brand_a1, _brand_a2 = company_a
        await client.put(
            "/api/v1/profiles/me",
            json={"department": "Sales"},
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )

        first_key = f"{company.id}/{brand_a1.slug}/profiles/{uuid4()}.png"
        await client.post(
            "/api/v1/profiles/me/photo",
            json={"s3_key": first_key},
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )

        second_key = f"{company.id}/{brand_a1.slug}/profiles/{uuid4()}.jpeg"
        response = await client.post(
            "/api/v1/profiles/me/photo",
            json={"s3_key": second_key},
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["profile_photo_url"] == second_key

    async def test_set_photo_when_no_profile_returns_404(
        self,
        client: AsyncClient,
        user_a1_employee_token: str,
        user_a1_employee,
        company_a,
    ):
        company, brand_a1, _brand_a2 = company_a
        s3_key = f"{company.id}/{brand_a1.slug}/profiles/{uuid4()}.png"
        response = await client.post(
            "/api/v1/profiles/me/photo",
            json={"s3_key": s3_key},
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 404

    async def test_set_photo_wrong_company_prefix_returns_403(
        self,
        client: AsyncClient,
        user_a1_employee_token: str,
        user_a1_employee,
        company_a,
    ):
        company, brand_a1, _brand_a2 = company_a
        # Create profile first
        await client.put(
            "/api/v1/profiles/me",
            json={"department": "Engineering"},
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )

        # Use a different company_id in the s3_key
        wrong_company_id = uuid4()
        s3_key = f"{wrong_company_id}/{brand_a1.slug}/profiles/{uuid4()}.png"
        response = await client.post(
            "/api/v1/profiles/me/photo",
            json={"s3_key": s3_key},
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 403

    async def test_set_photo_wrong_category_returns_422(
        self,
        client: AsyncClient,
        user_a1_employee_token: str,
        user_a1_employee,
        company_a,
    ):
        company, brand_a1, _brand_a2 = company_a
        await client.put(
            "/api/v1/profiles/me",
            json={"department": "Engineering"},
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )

        # Use 'products' category instead of 'profiles'
        s3_key = f"{company.id}/{brand_a1.slug}/products/{uuid4()}.png"
        response = await client.post(
            "/api/v1/profiles/me/photo",
            json={"s3_key": s3_key},
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 422

    async def test_set_photo_unauthenticated_returns_401(
        self,
        client: AsyncClient,
    ):
        response = await client.post(
            "/api/v1/profiles/me/photo",
            json={"s3_key": "some/path/profiles/photo.png"},
        )
        assert response.status_code == 401


class TestRemoveProfilePhoto:
    async def test_remove_photo_returns_200_with_null_url(
        self,
        client: AsyncClient,
        user_a1_employee_token: str,
        user_a1_employee,
        company_a,
    ):
        company, brand_a1, _brand_a2 = company_a
        # Create profile and set a photo
        await client.put(
            "/api/v1/profiles/me",
            json={"department": "Engineering"},
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        s3_key = f"{company.id}/{brand_a1.slug}/profiles/{uuid4()}.png"
        await client.post(
            "/api/v1/profiles/me/photo",
            json={"s3_key": s3_key},
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )

        # Remove the photo
        response = await client.delete(
            "/api/v1/profiles/me/photo",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["profile_photo_url"] is None

    async def test_remove_photo_when_no_photo_set_returns_200(
        self,
        client: AsyncClient,
        user_a1_employee_token: str,
        user_a1_employee,
    ):
        # Create profile without photo
        await client.put(
            "/api/v1/profiles/me",
            json={"department": "Engineering"},
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )

        response = await client.delete(
            "/api/v1/profiles/me/photo",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["profile_photo_url"] is None

    async def test_remove_photo_when_no_profile_returns_404(
        self,
        client: AsyncClient,
        user_a1_employee_token: str,
        user_a1_employee,
    ):
        response = await client.delete(
            "/api/v1/profiles/me/photo",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 404

    async def test_remove_photo_unauthenticated_returns_401(
        self,
        client: AsyncClient,
    ):
        response = await client.delete("/api/v1/profiles/me/photo")
        assert response.status_code == 401


class TestProfilePhotoAuthorization:
    async def test_any_role_can_set_photo(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
        user_a1_manager_token: str,
        user_a1_manager,
        company_a,
    ):
        company, brand_a1, _brand_a2 = company_a

        # Admin can set photo
        await client.put(
            "/api/v1/profiles/me",
            json={"department": "Management"},
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        s3_key = f"{company.id}/{brand_a1.slug}/profiles/{uuid4()}.png"
        response = await client.post(
            "/api/v1/profiles/me/photo",
            json={"s3_key": s3_key},
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 200

        # Manager can set photo
        await client.put(
            "/api/v1/profiles/me",
            json={"department": "Operations"},
            headers={"Authorization": f"Bearer {user_a1_manager_token}"},
        )
        s3_key = f"{company.id}/{brand_a1.slug}/profiles/{uuid4()}.png"
        response = await client.post(
            "/api/v1/profiles/me/photo",
            json={"s3_key": s3_key},
            headers={"Authorization": f"Bearer {user_a1_manager_token}"},
        )
        assert response.status_code == 200

    async def test_endpoint_is_me_scoped(
        self,
        client: AsyncClient,
        user_a1_employee_token: str,
        user_a1_employee,
        company_a,
    ):
        """POST /me/photo only affects the authenticated user's profile."""
        company, brand_a1, _brand_a2 = company_a
        await client.put(
            "/api/v1/profiles/me",
            json={"department": "Sales"},
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )

        s3_key = f"{company.id}/{brand_a1.slug}/profiles/{uuid4()}.png"
        response = await client.post(
            "/api/v1/profiles/me/photo",
            json={"s3_key": s3_key},
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["user_id"] == str(user_a1_employee.id)
