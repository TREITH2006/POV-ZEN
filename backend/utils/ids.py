import secrets
import uuid

_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # unambiguous chars only


def new_uuid() -> str:
    return uuid.uuid4().hex


def new_code(prefix: str, length: int = 5) -> str:
    """Human-friendly, non-sequential identifier, e.g. PG-X7K92."""
    suffix = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(length))
    return f"{prefix}-{suffix}"


def new_access_key(length: int = 12) -> str:
    """Secret credential handed out by an Owner to prospective members."""
    return "".join(secrets.choice(_CODE_ALPHABET) for _ in range(length))
