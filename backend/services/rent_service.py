from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from auth.dependencies import Identity
from models.rent import Rent
from models.rent_payment import RentPayment
from models.user import User
from schemas.rent import RentCreate, RentPaymentCreate, RentUpdate


def create_rent(db: Session, identity: Identity, payload: RentCreate) -> Rent:
    # Confirm the target user actually belongs to this Owner's group before
    # creating a rent record for them.
    user = db.query(User).filter(User.user_id == payload.user_id, User.group_id == identity.group_id).first()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found in your PG group")

    rent = Rent(
        user_id=payload.user_id,
        group_id=identity.group_id,
        monthly_rent=payload.monthly_rent,
        due_date=payload.due_date,
        status=payload.status,
    )
    db.add(rent)
    db.commit()
    db.refresh(rent)
    return rent


def _get_owned(db: Session, identity: Identity, rent_id: str) -> Rent:
    rent = db.query(Rent).filter(Rent.id == rent_id, Rent.group_id == identity.group_id).first()
    if not rent:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rent record not found")
    return rent


def update_rent(db: Session, identity: Identity, rent_id: str, payload: RentUpdate) -> Rent:
    rent = _get_owned(db, identity, rent_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(rent, field, value)
    db.commit()
    db.refresh(rent)
    return rent


def list_rent_for_owner(db: Session, identity: Identity) -> list[Rent]:
    return db.query(Rent).filter(Rent.group_id == identity.group_id).order_by(Rent.due_date.desc()).all()


def list_rent_for_user(db: Session, identity: Identity) -> list[Rent]:
    return (
        db.query(Rent)
        .filter(Rent.user_id == identity.ref_id, Rent.group_id == identity.group_id)
        .order_by(Rent.due_date.desc())
        .all()
    )


def add_payment(db: Session, identity: Identity, rent_id: str, payload: RentPaymentCreate) -> RentPayment:
    rent = _get_owned(db, identity, rent_id)
    payment = RentPayment(rent_id=rent.id, **payload.model_dump())
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


def list_payments(db: Session, identity: Identity, rent_id: str) -> list[RentPayment]:
    _get_owned(db, identity, rent_id)
    return db.query(RentPayment).filter(RentPayment.rent_id == rent_id).order_by(RentPayment.payment_date.desc()).all()
