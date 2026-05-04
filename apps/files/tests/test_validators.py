import pytest
from django.core.exceptions import ValidationError
from apps.files.validators import validate_file_upload, MAX_FILE_SIZE, BLOCKED_EXTENSIONS


class _FakeFile:
    """Minimal file-like object for validator tests."""
    def __init__(self, name, size, content=b'\x00'):
        self.name    = name
        self.size    = size
        self._content = content
        self._pos    = 0

    def read(self, n=-1):
        if n == -1:
            return self._content
        chunk = self._content[self._pos:self._pos + n]
        self._pos += len(chunk)
        return chunk

    def seek(self, pos):
        self._pos = pos


class TestValidateFileUpload:

    def test_valid_txt(self):
        f = _FakeFile('readme.txt', 100, b'Hello world')
        validate_file_upload(f)  # should not raise

    def test_valid_pdf(self):
        f = _FakeFile('doc.pdf', 1024, b'%PDF-1.4 content')
        validate_file_upload(f)

    def test_blocked_extension_exe(self):
        f = _FakeFile('virus.exe', 100, b'MZ')
        with pytest.raises(ValidationError, match="not allowed"):
            validate_file_upload(f)

    def test_blocked_extension_ps1(self):
        f = _FakeFile('script.ps1', 100, b'# powershell')
        with pytest.raises(ValidationError, match="not allowed"):
            validate_file_upload(f)

    def test_blocked_extension_bat(self):
        f = _FakeFile('run.bat', 50, b'@echo off')
        with pytest.raises(ValidationError, match="not allowed"):
            validate_file_upload(f)

    def test_file_too_large(self):
        f = _FakeFile('big.zip', MAX_FILE_SIZE + 1, b'PK')
        with pytest.raises(ValidationError, match="100 MB"):
            validate_file_upload(f)

    def test_exactly_at_limit_ok(self):
        f = _FakeFile('ok.zip', MAX_FILE_SIZE, b'PK')
        validate_file_upload(f)  # should not raise

    def test_all_blocked_extensions(self):
        for ext in BLOCKED_EXTENSIONS:
            f = _FakeFile(f'file{ext}', 50, b'\x00')
            with pytest.raises(ValidationError):
                validate_file_upload(f)
