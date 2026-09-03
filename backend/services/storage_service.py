"""File storage abstraction.

Only a local-disk backend is implemented today (per the project's local-dev
requirement). To add cloud/object storage later, implement the same
save_file()/delete_file() signatures in a new class and switch it in from
config via STORAGE_BACKEND — no caller code should need to change.
"""

import os
import uuid
from pathlib import Path

from fastapi import UploadFile

from config import get_settings

settings = get_settings()

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_DOCUMENT_TYPES = {"image/jpeg", "image/png", "application/pdf"}
MAX_UPLOAD_BYTES = settings.max_upload_size_mb * 1024 * 1024


class UnsupportedFileError(ValueError):
    pass


def _validate(file: UploadFile, contents: bytes, allowed_types: set[str]) -> None:
    if len(contents) == 0:
        raise UnsupportedFileError("Uploaded file is empty")
    if len(contents) > MAX_UPLOAD_BYTES:
        raise UnsupportedFileError(f"File exceeds the {settings.max_upload_size_mb}MB limit")
    # Do not trust the client-supplied filename or declared content_type alone;
    # sniff the actual magic bytes of common formats we accept.
    sniffed = _sniff_mime(contents)
    if sniffed not in allowed_types:
        raise UnsupportedFileError("Unsupported or unrecognized file type")


def _sniff_mime(contents: bytes) -> str | None:
    if contents.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if contents.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if contents[:4] == b"RIFF" and contents[8:12] == b"WEBP":
        return "image/webp"
    if contents.startswith(b"%PDF-"):
        return "application/pdf"
    return None


def save_upload(file: UploadFile, contents: bytes, *, subfolder: str, allowed_types: set[str]) -> str:
    """Validates and persists an upload. Returns a relative path safe to store in the DB."""
    _validate(file, contents, allowed_types)

    extension = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "application/pdf": ".pdf",
    }[_sniff_mime(contents)]

    target_dir = Path(settings.upload_dir) / subfolder
    target_dir.mkdir(parents=True, exist_ok=True)

    # Random filename: never trust or reuse the client-supplied name.
    filename = f"{uuid.uuid4().hex}{extension}"
    target_path = target_dir / filename
    with open(target_path, "wb") as f:
        f.write(contents)

    return str(Path(subfolder) / filename)


def delete_upload(relative_path: str) -> None:
    full_path = Path(settings.upload_dir) / relative_path
    try:
        os.remove(full_path)
    except FileNotFoundError:
        pass


def resolve_path(relative_path: str) -> Path:
    return Path(settings.upload_dir) / relative_path
