from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import SessionLocal
from models import AppSettings
from schemas import AppSettingsRead, AppSettingsUpdate

router = APIRouter(prefix="/api/settings", tags=["settings"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _get_or_create_settings(db: Session) -> AppSettings:
    settings = db.query(AppSettings).first()
    if not settings:
        settings = AppSettings(
            macro_target_protein_pct=20,
            macro_target_fat_pct=30,
            macro_target_carb_pct=50,
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


@router.get("", response_model=AppSettingsRead)
def get_settings(db: Session = Depends(get_db)):
    return _get_or_create_settings(db)


@router.put("", response_model=AppSettingsRead)
def update_settings(data: AppSettingsUpdate, db: Session = Depends(get_db)):
    total = data.macro_target_protein_pct + data.macro_target_fat_pct + data.macro_target_carb_pct
    if abs(total - 100) > 0.1:
        raise HTTPException(
            status_code=422,
            detail=f"Percentages must sum to 100 (got {total})",
        )
    settings = _get_or_create_settings(db)
    settings.macro_target_protein_pct = data.macro_target_protein_pct
    settings.macro_target_fat_pct = data.macro_target_fat_pct
    settings.macro_target_carb_pct = data.macro_target_carb_pct
    db.commit()
    db.refresh(settings)
    return settings
