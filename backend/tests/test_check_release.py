from scripts import check_release


def test_release_check_authenticates_with_supabase_test_account(monkeypatch):
    monkeypatch.setattr(check_release.settings, "supabase_url", "https://auth.example.test/")
    monkeypatch.setattr(check_release.settings, "supabase_publishable_key", "test-publishable-key")
    requested = {}

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"access_token": "test-access-token"}

    def post(url, *, headers, json, timeout):
        requested.update(url=url, headers=headers, payload=json, timeout=timeout)
        return Response()

    monkeypatch.setattr(check_release.httpx, "post", post)

    assert check_release.authenticate_test_account("demo@example.test", "secret") == "test-access-token"
    assert requested == {
        "url": "https://auth.example.test/auth/v1/token?grant_type=password",
        "headers": {"apikey": "test-publishable-key"},
        "payload": {"email": "demo@example.test", "password": "secret"},
        "timeout": 10,
    }
