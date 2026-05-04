import json
import pytest
from django.urls import reverse
from apps.files.models import File, Folder


@pytest.fixture
def auth_client(client, user):
    client.force_login(user)
    return client


@pytest.fixture
def file_record(user):
    return File.objects.create(
        owner=user,
        title='My Doc',
        original_filename='doc.txt',
        file='uploads/2026/01/01/doc.txt',
        file_hash='cafebabe',
        file_size=256,
        mime_type='text/plain',
        extension='.txt',
    )


# ------------------------------------------------------------------ #
# Authentication guard                                                 #
# ------------------------------------------------------------------ #

class TestAuthRequired:

    def test_my_files_redirects_anon(self, client):
        resp = client.get(reverse('files:my_files'))
        assert resp.status_code == 302
        assert '/accounts/login' in resp['Location']

    def test_upload_redirects_anon(self, client):
        resp = client.get(reverse('files:upload'))
        assert resp.status_code == 302

    def test_trash_redirects_anon(self, client):
        resp = client.get(reverse('files:trash'))
        assert resp.status_code == 302


# ------------------------------------------------------------------ #
# My Files                                                             #
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestMyFilesView:

    def test_renders_ok(self, auth_client):
        resp = auth_client.get(reverse('files:my_files'))
        assert resp.status_code == 200

    def test_file_appears_in_listing(self, auth_client, file_record):
        resp = auth_client.get(reverse('files:my_files'))
        assert b'My Doc' in resp.content

    def test_trashed_file_excluded(self, auth_client, user, file_record):
        file_record.is_deleted = True
        file_record.save()
        resp = auth_client.get(reverse('files:my_files'))
        assert b'My Doc' not in resp.content

    def test_search_filters_by_title(self, auth_client, file_record):
        File.objects.create(
            owner=file_record.owner,
            title='Other File',
            original_filename='other.pdf',
            file='uploads/other.pdf',
            file_hash='111',
            file_size=10,
            mime_type='application/pdf',
            extension='.pdf',
        )
        resp = auth_client.get(reverse('files:my_files') + '?q=My+Doc')
        assert b'My Doc' in resp.content
        assert b'Other File' not in resp.content

    def test_search_no_results(self, auth_client, file_record):
        resp = auth_client.get(reverse('files:my_files') + '?q=xyzzy123')
        assert b'My Doc' not in resp.content

    def test_type_filter(self, auth_client, file_record):
        File.objects.create(
            owner=file_record.owner,
            title='Photo',
            original_filename='photo.jpg',
            file='uploads/photo.jpg',
            file_hash='222',
            file_size=50,
            mime_type='image/jpeg',
            extension='.jpg',
        )
        resp = auth_client.get(reverse('files:my_files') + '?type=image')
        assert b'Photo' in resp.content
        assert b'My Doc' not in resp.content


# ------------------------------------------------------------------ #
# Upload                                                               #
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestUploadViews:

    def test_upload_page_renders(self, auth_client):
        resp = auth_client.get(reverse('files:upload'))
        assert resp.status_code == 200
        assert b'drop-zone' in resp.content

    def test_receive_chunk_no_file(self, auth_client):
        resp = auth_client.post(
            reverse('files:upload_chunk'),
            {'upload_id': 'x', 'chunk_index': '0', 'total_chunks': '1',
             'file_name': 'a.txt', 'file_size': '5'},
        )
        assert resp.status_code == 400

    def test_finalize_missing_upload_id(self, auth_client):
        resp = auth_client.post(
            reverse('files:upload_finalize'),
            data=json.dumps({'upload_id': 'no-such-id'}),
            content_type='application/json',
        )
        assert resp.status_code == 400


# ------------------------------------------------------------------ #
# File detail                                                          #
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestFileDetailView:

    def test_renders_ok(self, auth_client, file_record):
        resp = auth_client.get(reverse('files:detail', args=[file_record.id]))
        assert resp.status_code == 200
        assert b'My Doc' in resp.content

    def test_404_for_other_user(self, client, file_record):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        other = User.objects.create_user(
            username='stranger', email='stranger@test.com', password='pass'
        )
        client.force_login(other)
        resp = client.get(reverse('files:detail', args=[file_record.id]))
        assert resp.status_code == 404

    def test_increments_view_count(self, auth_client, file_record):
        auth_client.get(reverse('files:detail', args=[file_record.id]))
        file_record.refresh_from_db()
        assert file_record.view_count == 1


# ------------------------------------------------------------------ #
# Soft delete / restore / trash                                        #
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestTrashViews:

    def test_delete_moves_to_trash(self, auth_client, file_record):
        auth_client.post(reverse('files:delete', args=[file_record.id]))
        file_record.refresh_from_db()
        assert file_record.is_deleted is True
        assert file_record.deleted_at is not None

    def test_delete_form_redirects_to_my_files(self, auth_client, file_record):
        resp = auth_client.post(reverse('files:delete', args=[file_record.id]))
        assert resp.status_code == 302
        assert '/files/' in resp['Location']
        # Must NOT redirect to the detail page (which would 404 after soft-delete)
        assert str(file_record.id) not in resp['Location']

    def test_delete_ajax_returns_json(self, auth_client, file_record):
        resp = auth_client.post(
            reverse('files:delete', args=[file_record.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['success'] is True
        assert data['title'] == 'My Doc'

    def test_delete_ajax_file_is_trashed(self, auth_client, file_record):
        auth_client.post(
            reverse('files:delete', args=[file_record.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        file_record.refresh_from_db()
        assert file_record.is_deleted is True

    def test_trash_page_shows_deleted_file(self, auth_client, file_record):
        file_record.is_deleted = True
        from django.utils import timezone
        file_record.deleted_at = timezone.now()
        file_record.save()
        resp = auth_client.get(reverse('files:trash'))
        assert b'My Doc' in resp.content

    def test_restore_file(self, auth_client, file_record):
        from django.utils import timezone
        file_record.is_deleted = True
        file_record.deleted_at = timezone.now()
        file_record.save()

        auth_client.post(reverse('files:restore', args=[file_record.id]))
        file_record.refresh_from_db()
        assert file_record.is_deleted is False

    def test_destroy_removes_record(self, auth_client, file_record):
        from django.utils import timezone
        fid = file_record.id
        file_record.is_deleted = True
        file_record.deleted_at = timezone.now()
        file_record.save()

        auth_client.post(reverse('files:destroy', args=[fid]))
        assert not File.objects.filter(id=fid).exists()


# ------------------------------------------------------------------ #
# Folder creation                                                      #
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestCreateFolder:

    def test_creates_folder(self, auth_client, user):
        auth_client.post(reverse('files:create_folder'), {'name': 'Projects'})
        assert Folder.objects.filter(owner=user, name='Projects').exists()

    def test_blank_name_rejected(self, auth_client, user):
        auth_client.post(reverse('files:create_folder'), {'name': ''})
        assert not Folder.objects.filter(owner=user, name='').exists()
