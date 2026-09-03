import hashlib
import hmac
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from config import get_settings

settings = get_settings()
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

COOKIE_NAME = "access_token"


def hash_password(plain_password: str) -> str:
    """Slow, salted hash — appropriate for low-entropy, human-chosen passwords."""
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return _pwd_context.verify(plain_password, password_hash)


def hash_secret(plain_value: str) -> str:
    """Keyed hash for high-entropy, server-generated secrets (PG access keys).

    Access keys are random 12-character values (~60 bits of entropy), so a
    fast keyed hash (HMAC with the server's SECRET_KEY as pepper) is both
    secure and allows an indexed O(1) lookup — unlike bcrypt, which would
    force an expensive linear scan across every PG group to find a match.
    """
    return hmac.new(settings.secret_key.encode(), plain_value.encode(), hashlib.sha256).hexdigest()


def verify_secret(plain_value: str, secret_hash: str) -> bool:
    return hmac.compare_digest(hash_secret(plain_value), secret_hash)


def create_access_token(*, account_id: str, role: str, ref_id: str) -> str:
    # group_id is deliberately NOT embedded here: a User's group_id can change
    # the moment an Owner approves a join request, and a stale token must not
    # be able to grant/deny access based on an outdated value. Every request
    # re-reads the current group_id from the database via ref_id instead.
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": account_id,
        "role": role,
        "ref_id": ref_id,
        "exp": expire,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
