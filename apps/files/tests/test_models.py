import pytest
from apps.files.models import File, Folder


@pytest.mark.django_db
class TestFolderModel:

    def test_str(self, user):
        folder = Folder.objects.create(owner=user, name='Documents')
        assert str(folder) == 'Documents'

    def test_get_path_root(self, user):
        folder = Folder.objects.create(owner=user, name='Root')
        assert folder.get_path() == 'Root'

    def test_get_path_nested(self, user):
        parent = Folder.objects.create(owner=user, name='A')
        child  = Folder.objects.create(owner=user, name='B', parent=parent)
        assert child.get_path() == 'A / B'

    def test_unique_together(self, user):
        # unique_together is enforced when parent is non-null (NULL != NULL in SQL)
        parent = Folder.objects.create(owner=user, name='Parent')
        Folder.objects.create(owner=user, name='Child', parent=parent)
        with pytest.raises(Exception):
            Folder.objects.create(owner=user, name='Child', parent=parent)


@pytest.mark.django_db
class TestFileModel:

    def _make_file(self, user, **kwargs):
        defaults = dict(
            owner=user,
            title='Test',
            original_filename='test.txt',
            file='uploads/2026/01/01/test.txt',
            file_hash='abc123',
            file_size=1024,
            mime_type='text/plain',
            extension='.txt',
        )
        defaults.update(kwargs)
        return File.objects.create(**defaults)

    def test_str(self, user):
        f = self._make_file(user, title='My Doc')
        assert str(f) == 'My Doc'

    def test_is_image(self, user):
        f = self._make_file(user, mime_type='image/jpeg', extension='.jpg')
        assert f.is_image is True
        assert f.is_pdf is False

    def test_is_pdf(self, user):
        f = self._make_file(user, mime_type='application/pdf', extension='.pdf')
        assert f.is_pdf is True
        assert f.is_video is False

    def test_is_video(self, user):
        f = self._make_file(user, mime_type='video/mp4', extension='.mp4')
        assert f.is_video is True

    def test_is_audio(self, user):
        f = self._make_file(user, mime_type='audio/mpeg', extension='.mp3')
        assert f.is_audio is True

    def test_human_size_bytes(self, user):
        f = self._make_file(user, file_size=512)
        assert 'B' in f.human_size()

    def test_human_size_mb(self, user):
        f = self._make_file(user, file_size=5 * 1024 * 1024)
        assert 'MB' in f.human_size()

    def test_icon_image(self, user):
        f = self._make_file(user, mime_type='image/png', extension='.png')
        assert f.icon == '🖼'

    def test_icon_archive(self, user):
        f = self._make_file(user, mime_type='application/zip', extension='.zip')
        assert f.icon == '📦'

    def test_soft_delete_default_false(self, user):
        f = self._make_file(user)
        assert f.is_deleted is False
        assert f.deleted_at is None
