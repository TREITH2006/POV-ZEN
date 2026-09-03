from sqlalchemy.orm import Session

from auth.dependencies import Identity
from auth.security import hash_secret
from models.owner import Owner
from models.pg_group import PGGroup
from models.user import User
from utils.ids import new_access_key


def rotate_access_key(db: Session, identity: Identity) -> str:
    group = db.get(PGGroup, identity.group_id)
    plaintext = new_access_key()
    group.access_key_hash = hash_secret(plaintext)
    db.commit()
    return plaintext


def get_owner_contact(db: Session, group_id: str) -> Owner:
    group = db.get(PGGroup, group_id)
    return group.owner


def list_group_users(db: Session, identity: Identity) -> list[User]:
    return db.query(User).filter(User.group_id == identity.group_id).order_by(User.name.asc()).all()
