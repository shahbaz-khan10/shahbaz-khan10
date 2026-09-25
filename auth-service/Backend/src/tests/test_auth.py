from .conftest import PASSWORD, login


class TestLogin:
    def test_login_success(self, client, user):
        res = login(client, "tester", PASSWORD)
        assert res.status_code == 200
        body = res.json()
        assert body["access_token"]
        assert body["refresh_token"]
        assert body["user"]["username"] == "tester"

    def test_login_with_email(self, client, user):
        res = login(client, "tester@fct.local", PASSWORD)
        assert res.status_code == 200

    def test_login_wrong_password(self, client, user):
        res = login(client, "tester", "WrongPass@1")
        assert res.status_code == 401

    def test_login_unknown_user(self, db, client):
        res = login(client, "nobody", PASSWORD)
        assert res.status_code == 401

    def test_login_inactive_user(self, client, user):
        user.is_active = False
        user.save(update_fields=["is_active", "updated_at"])
        res = login(client, "tester", PASSWORD)
        assert res.status_code == 401


class TestSession:
    def test_me(self, auth_client):
        res = auth_client["client"].get("/api/auth/me")
        assert res.status_code == 200
        assert res.json()["username"] == "root"
        assert "Super Admin" in res.json()["roles"]

    def test_refresh_rotates(self, client, user):
        login_res = login(client, "tester", PASSWORD)
        refresh_token = login_res.json()["refresh_token"]

        res = client.post(
            "/api/auth/refresh",
            data={"refresh_token": refresh_token},
            content_type="application/json",
        )
        assert res.status_code == 200
        assert res.json()["access_token"]

        res = client.post(
            "/api/auth/refresh",
            data={"refresh_token": refresh_token},
            content_type="application/json",
        )
        assert res.status_code == 401

    def test_logout_blocks_refresh(self, client, user, auth_client):
        login_res = login(client, "tester", PASSWORD)
        refresh_token = login_res.json()["refresh_token"]

        res = auth_client["client"].post(
            "/api/auth/logout",
            data={"refresh_token": refresh_token},
            content_type="application/json",
        )
        assert res.status_code == 200

        res = client.post(
            "/api/auth/refresh",
            data={"refresh_token": refresh_token},
            content_type="application/json",
        )
        assert res.status_code == 401


class TestPasswords:
    def test_change_password(self, client, user):
        res = login(client, "tester", PASSWORD)
        token = res.json()["access_token"]
        client.defaults["HTTP_AUTHORIZATION"] = f"Bearer {token}"

        res = client.post(
            "/api/auth/change-password",
            data={"current_password": PASSWORD, "new_password": "NewPass@456"},
            content_type="application/json",
        )
        assert res.status_code == 200

        assert login(client, "tester", "NewPass@456").status_code == 200
        assert login(client, "tester", PASSWORD).status_code == 401

    def test_reset_password(self, client, user, auth_client):
        res = auth_client["client"].post(
            "/api/auth/reset-password",
            data={"user_id": user.id, "new_password": "ResetPass@789"},
            content_type="application/json",
        )
        assert res.status_code == 200
        assert login(client, "tester", "ResetPass@789").status_code == 200