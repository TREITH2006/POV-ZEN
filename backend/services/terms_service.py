from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from auth.dependencies import Identity
from models.terms_acceptance import TermsAcceptance


def accept_terms(db: Session, identity: Identity, version: str) -> TermsAcceptance:
    """Idempotent: repeated or concurrent acceptance of the same
    (account_id, version) never creates a duplicate row. A plain
    check-then-insert handles the common case; the IntegrityError fallback
    (backed by the DB unique constraint) covers a genuine race between two
    concurrent requests for the same account+version."""
    existing = (
        db.query(TermsAcceptance)
        .filter(TermsAcceptance.account_id == identity.account_id, TermsAcceptance.version == version)
        .first()
    )
    if existing:
        return existing

    record = TermsAcceptance(account_id=identity.account_id, version=version)
    db.add(record)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = (
            db.query(TermsAcceptance)
            .filter(TermsAcceptance.account_id == identity.account_id, TermsAcceptance.version == version)
            .first()
        )
        if existing:
            return existing
        raise
    db.refresh(record)
    return record


def has_accepted(db: Session, identity: Identity, version: str) -> bool:
    return (
        db.query(TermsAcceptance)
        .filter(TermsAcceptance.account_id == identity.account_id, TermsAcceptance.version == version)
        .first()
        is not None
    )
