from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from auth.dependencies import Identity
from models.food_feedback import FoodFeedback
from models.food_menu import FoodMenu
from schemas.food import FoodFeedbackCreate, FoodMenuCreate, FoodMenuUpdate


def upsert_menu(db: Session, identity: Identity, payload: FoodMenuCreate) -> FoodMenu:
    menu = (
        db.query(FoodMenu)
        .filter(FoodMenu.group_id == identity.group_id, FoodMenu.menu_date == payload.menu_date)
        .first()
    )
    if menu:
        menu.breakfast = payload.breakfast
        menu.lunch = payload.lunch
        menu.dinner = payload.dinner
    else:
        menu = FoodMenu(group_id=identity.group_id, **payload.model_dump())
        db.add(menu)
    db.commit()
    db.refresh(menu)
    return menu


def update_menu(db: Session, identity: Identity, menu_id: str, payload: FoodMenuUpdate) -> FoodMenu:
    menu = _get_owned_menu(db, identity, menu_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(menu, field, value)
    db.commit()
    db.refresh(menu)
    return menu


def _get_owned_menu(db: Session, identity: Identity, menu_id: str) -> FoodMenu:
    menu = db.query(FoodMenu).filter(FoodMenu.id == menu_id, FoodMenu.group_id == identity.group_id).first()
    if not menu:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Menu not found")
    return menu


def get_menu_for_date(db: Session, identity: Identity, menu_date: date) -> FoodMenu | None:
    return (
        db.query(FoodMenu)
        .filter(FoodMenu.group_id == identity.group_id, FoodMenu.menu_date == menu_date)
        .first()
    )


def submit_feedback(db: Session, identity: Identity, menu_id: str, payload: FoodFeedbackCreate) -> FoodFeedback:
    menu = _get_owned_menu(db, identity, menu_id)
    feedback = FoodFeedback(
        menu_id=menu.id,
        user_id=identity.ref_id,
        group_id=identity.group_id,
        rating=payload.rating,
        comment=payload.comment,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback


def list_feedback_for_menu(db: Session, identity: Identity, menu_id: str) -> list[FoodFeedback]:
    _get_owned_menu(db, identity, menu_id)  # ensures group ownership
    return db.query(FoodFeedback).filter(FoodFeedback.menu_id == menu_id).order_by(FoodFeedback.created_at.desc()).all()
