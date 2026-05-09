import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.groups.models import Group, GroupMembership

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username='alice', email='alice@example.com', password='pass1234')


@pytest.fixture
def other_user(db):
    return User.objects.create_user(username='bob', email='bob@example.com', password='pass1234')


@pytest.fixture
def auth_client(client, user):
    client.force_login(user)
    return client


@pytest.fixture
def group(user):
    g = Group.objects.create(name='Alpha Group', owner=user)
    GroupMembership.objects.create(user=user, group=g, role=GroupMembership.ROLE_ADMIN)
    return g


# ── my_groups ──────────────────────────────────────────────────────────


class TestMyGroups:

    def test_redirects_anonymous(self, client):
        resp = client.get(reverse('groups:my_groups'))
        assert resp.status_code == 302

    def test_renders_for_authenticated(self, auth_client):
        resp = auth_client.get(reverse('groups:my_groups'))
        assert resp.status_code == 200

    def test_owned_group_appears(self, auth_client, group):
        resp = auth_client.get(reverse('groups:my_groups'))
        assert 'Alpha Group' in resp.content.decode()


# ── create_group ───────────────────────────────────────────────────────


class TestCreateGroup:

    def test_get_renders_form(self, auth_client):
        resp = auth_client.get(reverse('groups:create'))
        assert resp.status_code == 200

    def test_post_creates_group_and_admin_membership(self, auth_client, user):
        resp = auth_client.post(reverse('groups:create'), {
            'name': 'New Group',
            'description': 'Test',
            'privacy': 'private',
        })
        assert resp.status_code == 302
        g = Group.objects.get(name='New Group')
        assert g.owner == user
        membership = GroupMembership.objects.get(user=user, group=g)
        assert membership.role == GroupMembership.ROLE_ADMIN

    def test_post_invalid_name_too_short(self, auth_client):
        resp = auth_client.post(reverse('groups:create'), {
            'name': 'A',
            'privacy': 'private',
        })
        assert resp.status_code == 200
        assert not Group.objects.filter(name='A').exists()

    def test_post_redirects_to_detail(self, auth_client):
        resp = auth_client.post(reverse('groups:create'), {
            'name': 'My Team',
            'privacy': 'private',
        })
        g = Group.objects.get(name='My Team')
        assert resp['Location'] == reverse('groups:detail', kwargs={'group_id': g.id})


# ── group_detail ───────────────────────────────────────────────────────


class TestGroupDetail:

    def test_owner_can_access(self, auth_client, group):
        resp = auth_client.get(reverse('groups:detail', kwargs={'group_id': group.id}))
        assert resp.status_code == 200

    def test_non_member_gets_403(self, client, other_user, group):
        client.force_login(other_user)
        resp = client.get(reverse('groups:detail', kwargs={'group_id': group.id}))
        assert resp.status_code == 403

    def test_member_can_access(self, client, other_user, group):
        GroupMembership.objects.create(user=other_user, group=group, role=GroupMembership.ROLE_MEMBER)
        client.force_login(other_user)
        resp = client.get(reverse('groups:detail', kwargs={'group_id': group.id}))
        assert resp.status_code == 200

    def test_files_tab_default(self, auth_client, group):
        resp = auth_client.get(reverse('groups:detail', kwargs={'group_id': group.id}))
        assert resp.context['tab'] == 'files'

    def test_members_tab(self, auth_client, group):
        resp = auth_client.get(
            reverse('groups:detail', kwargs={'group_id': group.id}) + '?tab=members'
        )
        assert resp.context['tab'] == 'members'


# ── archive_group ──────────────────────────────────────────────────────


class TestArchiveGroup:

    def test_owner_can_archive(self, auth_client, group):
        resp = auth_client.post(reverse('groups:archive', kwargs={'group_id': group.id}))
        group.refresh_from_db()
        assert group.is_archived
        assert resp.status_code == 302

    def test_owner_can_unarchive(self, auth_client, group):
        group.is_archived = True
        group.save()
        auth_client.post(reverse('groups:archive', kwargs={'group_id': group.id}))
        group.refresh_from_db()
        assert not group.is_archived

    def test_non_owner_cannot_archive(self, client, other_user, group):
        GroupMembership.objects.create(user=other_user, group=group, role=GroupMembership.ROLE_MEMBER)
        client.force_login(other_user)
        resp = client.post(reverse('groups:archive', kwargs={'group_id': group.id}))
        assert resp.status_code == 404
        group.refresh_from_db()
        assert not group.is_archived

    def test_archived_group_in_archived_tab(self, auth_client, user, group):
        group.is_archived = True
        group.save()
        resp = auth_client.get(reverse('groups:my_groups'))
        assert group in resp.context['archived_groups']


# ── add_member ─────────────────────────────────────────────────────────


class TestAddMember:

    def test_admin_can_add_member_by_username(self, auth_client, group, other_user):
        resp = auth_client.post(
            reverse('groups:add_member', kwargs={'group_id': group.id}),
            {'username_or_email': other_user.username},
        )
        assert resp.status_code == 302
        assert GroupMembership.objects.filter(user=other_user, group=group).exists()

    def test_admin_can_add_member_by_email(self, auth_client, group, other_user):
        resp = auth_client.post(
            reverse('groups:add_member', kwargs={'group_id': group.id}),
            {'username_or_email': other_user.email},
        )
        assert resp.status_code == 302
        assert GroupMembership.objects.filter(user=other_user, group=group).exists()

    def test_duplicate_member_rejected(self, auth_client, group, other_user):
        GroupMembership.objects.create(user=other_user, group=group)
        resp = auth_client.post(
            reverse('groups:add_member', kwargs={'group_id': group.id}),
            {'username_or_email': other_user.username},
        )
        assert resp.status_code == 302
        assert GroupMembership.objects.filter(user=other_user, group=group).count() == 1

    def test_unknown_user_shows_error(self, auth_client, group):
        resp = auth_client.post(
            reverse('groups:add_member', kwargs={'group_id': group.id}),
            {'username_or_email': 'nobody@nowhere.com'},
        )
        assert resp.status_code == 302

    def test_non_admin_cannot_add_member(self, client, other_user, group):
        third = User.objects.create_user(username='charlie', email='charlie@example.com', password='pass1234')
        GroupMembership.objects.create(user=other_user, group=group, role=GroupMembership.ROLE_MEMBER)
        client.force_login(other_user)
        resp = client.post(
            reverse('groups:add_member', kwargs={'group_id': group.id}),
            {'username_or_email': third.username},
        )
        assert resp.status_code == 403


# ── edit_group ─────────────────────────────────────────────────────────


class TestEditGroup:

    def test_owner_can_edit(self, auth_client, group):
        resp = auth_client.post(
            reverse('groups:edit', kwargs={'group_id': group.id}),
            {'name': 'Renamed Group', 'privacy': 'public', 'description': ''},
        )
        group.refresh_from_db()
        assert group.name == 'Renamed Group'
        assert resp.status_code == 302

    def test_non_admin_cannot_edit(self, client, other_user, group):
        GroupMembership.objects.create(user=other_user, group=group, role=GroupMembership.ROLE_MEMBER)
        client.force_login(other_user)
        resp = client.post(
            reverse('groups:edit', kwargs={'group_id': group.id}),
            {'name': 'Hacked', 'privacy': 'public', 'description': ''},
        )
        assert resp.status_code == 403
        group.refresh_from_db()
        assert group.name == 'Alpha Group'


# ── Storage quota integration ──────────────────────────────────────────


class TestStorageQuota:

    @pytest.mark.django_db
    def test_group_storage_quota_display(self, group):
        assert 'GB' in group.storage_quota_display()

    @pytest.mark.django_db
    def test_group_storage_used_zero(self, group):
        assert group.storage_used == 0

    @pytest.mark.django_db
    def test_member_in_joined_groups(self, user, other_user):
        g = Group.objects.create(name='Shared', owner=user)
        GroupMembership.objects.create(user=user, group=g, role=GroupMembership.ROLE_ADMIN)
        GroupMembership.objects.create(user=other_user, group=g, role=GroupMembership.ROLE_MEMBER)

        client_b = pytest.importorskip('django.test').Client()
        client_b.force_login(other_user)
        resp = client_b.get(reverse('groups:my_groups'))
        assert g in resp.context['joined_groups']
