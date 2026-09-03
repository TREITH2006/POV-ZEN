from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from auth.dependencies import Identity, require_approved_user, require_owner
from database import get_db
from schemas.rent import RentCreate, RentOut, RentPaymentCreate, RentPaymentOut, RentUpdate
from services import rent_service

router = APIRouter(prefix="/api/rent", tags=["rent"])


@router.post("", response_model=RentOut, status_code=201)
def create_rent(payload: RentCreate, identity: Identity = Depends(require_owner), db: Session = Depends(get_db)):
    return rent_service.create_rent(db, identity, payload)


@router.put("/{rent_id}", response_model=RentOut)
def update_rent(
    rent_id: str, payload: RentUpdate, identity: Identity = Depends(require_owner), db: Session = Depends(get_db)
):
    return rent_service.update_rent(db, identity, rent_id, payload)


@router.get("", response_model=list[RentOut])
def list_group_rent(identity: Identity = Depends(require_owner), db: Session = Depends(get_db)):
    return rent_service.list_rent_for_owner(db, identity)


@router.get("/mine", response_model=list[RentOut])
def list_my_rent(identity: Identity = Depends(require_approved_user), db: Session = Depends(get_db)):
    return rent_service.list_rent_for_user(db, identity)


@router.post("/{rent_id}/payments", response_model=RentPaymentOut, status_code=201)
def add_payment(
    rent_id: str,
    payload: RentPaymentCreate,
    identity: Identity = Depends(require_owner),
    db: Session = Depends(get_db),
):
    return rent_service.add_payment(db, identity, rent_id, payload)


@router.get("/{rent_id}/payments", response_model=list[RentPaymentOut])
def list_payments(rent_id: str, identity: Identity = Depends(require_owner), db: Session = Depends(get_db)):
    return rent_service.list_payments(db, identity, rent_id)
