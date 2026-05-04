import os
import pytest
from apps.files.models import ChunkUpload, File, Folder
from apps.files.services import FileUploadService, QuotaExceededError, TrashService


@pytest.fixture
def upload_service():
    return FileUploadService()


@pytest.fixture
def trash_service():
    return TrashService()


@pytest.fixture
def simple_file_record(user):
    """A File DB record (no real file on disk)."""
    return File.objects.create(
        owner=user,
        title='Test File',
        original_filename='test.txt',
        file='uploads/2026/01/01/fake.txt',
        file_hash='deadbeef',
        file_size=100,
        mime_type='text/plain',
        extension='.txt',
    )


# ------------------------------------------------------------------ #
# Chunked upload                                                       #
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestReceiveChunk:

    def test_creates_chunk_upload_record(self, user, tmp_path, settings, upload_service):
        settings.MEDIA_ROOT = str(tmp_path)

        upload = upload_service.receive_chunk(
            upload_id='uid-001',
            chunk_index=0,
            chunk_data=b'hello',
            owner=user,
            original_filename='hello.txt',
            total_chunks=2,
            file_size=10,
        )
        assert upload.received_chunks == 1
        assert upload.total_chunks == 2
        assert ChunkUpload.objects.filter(upload_id='uid-001').exists()

    def test_chunk_file_written_to_disk(self, user, tmp_path, settings, upload_service):
        settings.MEDIA_ROOT = str(tmp_path)

        upload_service.receive_chunk(
            upload_id='uid-002',
            chunk_index=0,
            chunk_data=b'chunk-data',
            owner=user,
            original_filename='file.bin',
            total_chunks=1,
            file_size=10,
        )
        cu = ChunkUpload.objects.get(upload_id='uid-002')
        chunk_path = os.path.join(cu.temp_dir, 'chunk_00000')
        assert os.path.exists(chunk_path)
        assert open(chunk_path, 'rb').read() == b'chunk-data'

    def test_increments_received_chunks(self, user, tmp_path, settings, upload_service):
        settings.MEDIA_ROOT = str(tmp_path)

        for i in range(3):
            u = upload_service.receive_chunk(
                upload_id='uid-003',
                chunk_index=i,
                chunk_data=b'x',
                owner=user,
                original_filename='multi.txt',
                total_chunks=3,
                file_size=3,
            )
        assert u.received_chunks == 3


@pytest.mark.django_db
class TestFinalizeUpload:

    def test_assembles_and_saves_file(self, user, tmp_path, settings, upload_service):
        settings.MEDIA_ROOT = str(tmp_path)
        content = b'Hello, World!'

        upload_service.receive_chunk(
            upload_id='fin-001',
            chunk_index=0,
            chunk_data=content,
            owner=user,
            original_filename='hello.txt',
            total_chunks=1,
            file_size=len(content),
        )

        f = upload_service.finalize_upload(
            upload_id='fin-001',
            owner=user,
            title='My Hello',
        )

        assert isinstance(f, File)
        assert f.owner == user
        assert f.title == 'My Hello'
        assert f.file_size == len(content)
        assert len(f.file_hash) == 64  # SHA-256 hex

    def test_uses_filename_as_title_when_blank(self, user, tmp_path, settings, upload_service):
        settings.MEDIA_ROOT = str(tmp_path)

        upload_service.receive_chunk(
            upload_id='fin-002',
            chunk_index=0,
            chunk_data=b'data',
            owner=user,
            original_filename='untitled.txt',
            total_chunks=1,
            file_size=4,
        )
        f = upload_service.finalize_upload('fin-002', owner=user, title='')
        assert f.title == 'untitled.txt'

    def test_cleans_up_temp_dir(self, user, tmp_path, settings, upload_service):
        settings.MEDIA_ROOT = str(tmp_path)

        upload_service.receive_chunk(
            upload_id='fin-003',
            chunk_index=0,
            chunk_data=b'clean',
            owner=user,
            original_filename='clean.txt',
            total_chunks=1,
            file_size=5,
        )
        cu = ChunkUpload.objects.get(upload_id='fin-003')
        temp_dir = cu.temp_dir

        upload_service.finalize_upload('fin-003', owner=user)
        assert not os.path.exists(temp_dir)
        assert not ChunkUpload.objects.filter(upload_id='fin-003').exists()

    def test_updates_storage_used(self, user, tmp_path, settings, upload_service):
        settings.MEDIA_ROOT = str(tmp_path)
        initial = user.storage_used

        upload_service.receive_chunk(
            upload_id='fin-004',
            chunk_index=0,
            chunk_data=b'storage',
            owner=user,
            original_filename='s.txt',
            total_chunks=1,
            file_size=7,
        )
        upload_service.finalize_upload('fin-004', owner=user)

        user.refresh_from_db()
        assert user.storage_used == initial + 7

    def test_quota_exceeded_raises(self, user, tmp_path, settings, upload_service):
        settings.MEDIA_ROOT = str(tmp_path)
        user.storage_quota = 5
        user.storage_used  = 4
        user.save()

        upload_service.receive_chunk(
            upload_id='fin-005',
            chunk_index=0,
            chunk_data=b'toolarge',
            owner=user,
            original_filename='big.txt',
            total_chunks=1,
            file_size=8,
        )
        with pytest.raises(QuotaExceededError, match="quota exceeded"):
            upload_service.finalize_upload('fin-005', owner=user)

    def test_incomplete_upload_raises(self, user, tmp_path, settings, upload_service):
        settings.MEDIA_ROOT = str(tmp_path)

        upload_service.receive_chunk(
            upload_id='fin-006',
            chunk_index=0,
            chunk_data=b'part1',
            owner=user,
            original_filename='partial.txt',
            total_chunks=2,
            file_size=10,
        )
        with pytest.raises(Exception, match="[Ii]ncomplete"):
            upload_service.finalize_upload('fin-006', owner=user)

    def test_missing_upload_id_raises(self, user, upload_service):
        with pytest.raises(Exception):
            upload_service.finalize_upload('does-not-exist', owner=user)


# ------------------------------------------------------------------ #
# TrashService                                                         #
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestTrashService:

    def test_soft_delete_sets_flags(self, user, simple_file_record, trash_service):
        trash_service.soft_delete(simple_file_record, user)
        simple_file_record.refresh_from_db()
        assert simple_file_record.is_deleted is True
        assert simple_file_record.deleted_at is not None

    def test_restore_clears_flags(self, user, simple_file_record, trash_service):
        trash_service.soft_delete(simple_file_record, user)
        trash_service.restore(simple_file_record, user)
        simple_file_record.refresh_from_db()
        assert simple_file_record.is_deleted is False
        assert simple_file_record.deleted_at is None

    def test_permanent_delete_removes_record(self, user, simple_file_record, trash_service):
        fid = simple_file_record.id
        trash_service.soft_delete(simple_file_record, user)
        trash_service.permanent_delete(simple_file_record, user)
        assert not File.objects.filter(id=fid).exists()

    def test_permanent_delete_reclaims_quota(self, user, simple_file_record, trash_service):
        user.storage_used = 500
        user.save()

        size = simple_file_record.file_size
        trash_service.soft_delete(simple_file_record, user)
        trash_service.permanent_delete(simple_file_record, user)

        user.refresh_from_db()
        assert user.storage_used == 500 - size

    def test_soft_delete_wrong_user_raises(self, user, simple_file_record, trash_service):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        other = User.objects.create_user(
            username='other', email='other@test.com', password='pass'
        )
        with pytest.raises(PermissionError):
            trash_service.soft_delete(simple_file_record, other)
