from sqlalchemy.orm import Session

from auth.dependencies import Identity
from models.terms_acceptance import TermsAcceptance


def accept_terms(db: Session, identity: Identity, version: str) -> TermsAcceptance:
    record = TermsAcceptance(account_id=identity.account_id, version=version)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def has_accepted(db: Session, identity: Identity, version: str) -> bool:
    return (
        db.query(TermsAcceptance)
        .filter(TermsAcceptance.account_id == identity.account_id, TermsAcceptance.version == version)
        .first()
        is not None
    )
