import pytest
from django.contrib.auth import get_user_model

from apps.groups.models import Group, GroupMembership

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username='alice', email='alice@example.com', password='pass1234')


@pytest.fixture
def other_user(db):
    return User.objects.create_user(username='bob', email='bob@example.com', password='pass1234')


@pytest.fixture
def group(user):
    return Group.objects.create(name='Test Group', owner=user)


class TestGroupModel:

    def test_str(self, group):
        assert str(group) == 'Test Group'

    def test_storage_used_percent_zero(self, group):
        assert group.storage_used_percent() == 0

    def test_storage_used_percent(self, group):
        group.storage_quota = 1000
        group.storage_used = 500
        assert group.storage_used_percent() == 50

    def test_storage_used_percent_capped_at_100(self, group):
        group.storage_quota = 100
        group.storage_used = 200
        assert group.storage_used_percent() == 100

    def test_bytes_to_human_mb(self, group):
        assert 'MB' in group._bytes_to_human(2 * 1024 * 1024)

    def test_is_member_false_for_non_member(self, group, other_user):
        assert not group.is_member(other_user)

    def test_is_member_true_after_membership(self, group, other_user):
        GroupMembership.objects.create(user=other_user, group=group)
        assert group.is_member(other_user)

    def test_get_membership_returns_none_for_non_member(self, group, other_user):
        assert group.get_membership(other_user) is None

    def test_can_manage_owner(self, group, user):
        assert group.can_manage(user)

    def test_can_manage_admin_member(self, group, other_user):
        GroupMembership.objects.create(user=other_user, group=group, role=GroupMembership.ROLE_ADMIN)
        assert group.can_manage(other_user)

    def test_cannot_manage_regular_member(self, group, other_user):
        GroupMembership.objects.create(user=other_user, group=group, role=GroupMembership.ROLE_MEMBER)
        assert not group.can_manage(other_user)


class TestGroupMembership:

    def test_str(self, group, other_user):
        m = GroupMembership.objects.create(user=other_user, group=group)
        assert 'bob' in str(m)
        assert 'Test Group' in str(m)

    def test_is_admin_false_for_member(self, group, other_user):
        m = GroupMembership.objects.create(user=other_user, group=group, role=GroupMembership.ROLE_MEMBER)
        assert not m.is_admin()

    def test_is_admin_true_for_admin(self, group, other_user):
        m = GroupMembership.objects.create(user=other_user, group=group, role=GroupMembership.ROLE_ADMIN)
        assert m.is_admin()

    def test_unique_together_enforced(self, group, other_user):
        GroupMembership.objects.create(user=other_user, group=group)
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            GroupMembership.objects.create(user=other_user, group=group)
