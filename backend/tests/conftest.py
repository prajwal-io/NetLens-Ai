"""Tests authenticate as a fixed user unless a security test removes the override."""
import pytest

from app.core.auth import Principal, require_user
from app.main import app

TEST_USER = "2a17d1c4-b2a8-4da5-976d-f5d46078b756"


@pytest.fixture(autouse=True)
def authenticated_api_user():
    previous = app.dependency_overrides.get(require_user)
    app.dependency_overrides[require_user] = lambda: Principal(TEST_USER, "test-access-token")
    yield
    if previous is None:
        app.dependency_overrides.pop(require_user, None)
    else:
        app.dependency_overrides[require_user] = previous
