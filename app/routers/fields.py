from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import Field, Site
from app.schemas import FieldCreate, FieldRead, FieldUpdate

router = APIRouter(prefix="/fields", tags=["Fields"])


@router.get("/", response_model=list[FieldRead])
def list_fields(db: Session = Depends(get_db)):
    """Return all fields ordered by name."""
    return db.query(Field).order_by(Field.name).all()


@router.get("/{field_id}", response_model=FieldRead)
def get_field(field_id: UUID, db: Session = Depends(get_db)):
    field = db.query(Field).filter_by(id=field_id).first()
    if not field:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Field not found.")
    return field


@router.post("/", response_model=FieldRead, status_code=status.HTTP_201_CREATED)
def create_field(payload: FieldCreate, db: Session = Depends(get_db)):
    """Create a new field."""
    if payload.code:
        existing = db.query(Field).filter_by(code=payload.code).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail=f"A field with code '{payload.code}' already exists.")

    if payload.site_id:
        site = db.query(Site).filter_by(id=payload.site_id).first()
        if not site:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Site not found.")

    field = Field(
        name=payload.name,
        code=payload.code,
        site_id=payload.site_id,
        gross_area_ha=payload.gross_area_ha,
        notes=payload.notes,
    )
    db.add(field)
    db.commit()
    db.refresh(field)
    return field


@router.patch("/{field_id}", response_model=FieldRead)
def update_field(field_id: UUID, payload: FieldUpdate, db: Session = Depends(get_db)):
    """Partially update editable fields (name, code, gross_area_ha, notes)."""
    field = db.query(Field).filter_by(id=field_id).first()
    if not field:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Field not found.")

    updates = payload.model_dump(exclude_none=True)

    if "code" in updates and updates["code"] != field.code:
        existing = db.query(Field).filter_by(code=updates["code"]).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail=f"A field with code '{updates['code']}' already exists.")

    for key, value in updates.items():
        setattr(field, key, value)

    db.commit()
    db.refresh(field)
    return field


@router.delete("/{field_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_field(field_id: UUID, db: Session = Depends(get_db)):
    """Delete a field by ID."""
    field = db.query(Field).filter_by(id=field_id).first()
    if not field:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Field not found.")
    db.delete(field)
    db.commit()

