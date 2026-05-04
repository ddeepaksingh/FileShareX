import os
import mimetypes
from django.core.exceptions import ValidationError

# Try to import python-magic for accurate header-based detection.
# Falls back to mimetypes (stdlib) if not installed.
try:
    import magic as _magic
    _MAGIC_AVAILABLE = True
except ImportError:
    _MAGIC_AVAILABLE = False

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB

BLOCKED_EXTENSIONS = frozenset({
    '.exe', '.bat', '.cmd', '.sh', '.ps1', '.msi', '.com', '.scr',
    '.dll', '.so', '.dylib', '.jar', '.war',
    '.vbs', '.wsf', '.hta',
    '.pif', '.cpl', '.reg',
})

BLOCKED_MIME_TYPES = frozenset({
    'application/x-msdownload',
    'application/x-msdos-program',
    'application/x-sh',
    'text/x-shellscript',
    'application/x-executable',
    'application/x-dosexec',
})


def detect_mime_type(file_obj):
    """Detect MIME type from file header bytes, falling back to extension."""
    header = file_obj.read(2048)
    file_obj.seek(0)

    if _MAGIC_AVAILABLE:
        return _magic.from_buffer(header, mime=True)

    guessed, _ = mimetypes.guess_type(file_obj.name)
    return guessed or 'application/octet-stream'


def validate_file_upload(file_obj):
    """
    Validate size, extension, and MIME type of an uploaded file.
    Raises ValidationError on failure.
    """
    if file_obj.size > MAX_FILE_SIZE:
        mb = file_obj.size / (1024 * 1024)
        raise ValidationError(
            f"File exceeds the 100 MB limit (your file: {mb:.1f} MB)."
        )

    ext = os.path.splitext(file_obj.name)[1].lower()
    if ext in BLOCKED_EXTENSIONS:
        raise ValidationError(
            f"File type '{ext}' is not allowed for security reasons."
        )

    detected_mime = detect_mime_type(file_obj)
    if detected_mime in BLOCKED_MIME_TYPES:
        raise ValidationError(
            f"File content type '{detected_mime}' is not allowed."
        )
