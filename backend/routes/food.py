from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from auth.dependencies import Identity, require_group_member, require_owner, require_approved_user
from database import get_db
from schemas.food import FoodFeedbackCreate, FoodFeedbackOut, FoodMenuCreate, FoodMenuOut, FoodMenuUpdate
from services import food_service

router = APIRouter(prefix="/api/food", tags=["food"])


@router.post("", response_model=FoodMenuOut, status_code=201)
def create_or_update_menu(
    payload: FoodMenuCreate, identity: Identity = Depends(require_owner), db: Session = Depends(get_db)
):
    return food_service.upsert_menu(db, identity, payload)


@router.put("/{menu_id}", response_model=FoodMenuOut)
def update_menu(
    menu_id: str,
    payload: FoodMenuUpdate,
    identity: Identity = Depends(require_owner),
    db: Session = Depends(get_db),
):
    return food_service.update_menu(db, identity, menu_id, payload)


@router.get("/today", response_model=FoodMenuOut | None)
def get_today_menu(identity: Identity = Depends(require_group_member), db: Session = Depends(get_db)):
    return food_service.get_menu_for_date(db, identity, date.today())


@router.post("/{menu_id}/feedback", response_model=FoodFeedbackOut, status_code=201)
def submit_feedback(
    menu_id: str,
    payload: FoodFeedbackCreate,
    identity: Identity = Depends(require_approved_user),
    db: Session = Depends(get_db),
):
    return food_service.submit_feedback(db, identity, menu_id, payload)


@router.get("/{menu_id}/feedback", response_model=list[FoodFeedbackOut])
def list_feedback(menu_id: str, identity: Identity = Depends(require_owner), db: Session = Depends(get_db)):
    return food_service.list_feedback_for_menu(db, identity, menu_id)
