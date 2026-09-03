from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from auth.dependencies import Identity, get_current_identity
from database import get_db
from schemas.terms import CURRENT_TERMS_VERSION, TermsAcceptRequest
from services import terms_service

router = APIRouter(prefix="/api/terms", tags=["terms"])


@router.post("/accept")
def accept_terms(
    payload: TermsAcceptRequest = TermsAcceptRequest(),
    identity: Identity = Depends(get_current_identity),
    db: Session = Depends(get_db),
):
    terms_service.accept_terms(db, identity, payload.version)
    return {"status": "accepted", "version": payload.version}


@router.get("/status")
def terms_status(identity: Identity = Depends(get_current_identity), db: Session = Depends(get_db)):
    accepted = terms_service.has_accepted(db, identity, CURRENT_TERMS_VERSION)
    return {"accepted": accepted, "version": CURRENT_TERMS_VERSION}
