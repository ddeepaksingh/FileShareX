import pytest
from django.contrib.auth import get_user_model


@pytest.fixture
def user(db):
    """A standard authenticated user for tests."""
    User = get_user_model()
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='TestPass123!',
        storage_quota=5 * 1024 * 1024 * 1024,  # 5 GB
        storage_used=0,
    )
