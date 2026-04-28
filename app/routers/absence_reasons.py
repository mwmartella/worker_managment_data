from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import AbsenceReason
from app.schemas import AbsenceReasonCreate, AbsenceReasonRead, AbsenceReasonUpdate

router = APIRouter(prefix="/absence-reasons", tags=["Absence Reasons"])


@router.get("/", response_model=list[AbsenceReasonRead])
def list_absence_reasons(db: Session = Depends(get_db)):
    return db.query(AbsenceReason).order_by(AbsenceReason.name).all()


@router.get("/{absence_reason_id}", response_model=AbsenceReasonRead)
def get_absence_reason(absence_reason_id: UUID, db: Session = Depends(get_db)):
    ar = db.query(AbsenceReason).filter_by(id=absence_reason_id).first()
    if not ar:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Absence reason not found.")
    return ar


@router.post("/", response_model=AbsenceReasonRead, status_code=status.HTTP_201_CREATED)
def create_absence_reason(payload: AbsenceReasonCreate, db: Session = Depends(get_db)):
    existing = db.query(AbsenceReason).filter_by(name=payload.name).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=f"An absence reason named '{payload.name}' already exists.")
    ar = AbsenceReason(name=payload.name, notes=payload.notes)
    db.add(ar)
    db.commit()
    db.refresh(ar)
    return ar


@router.patch("/{absence_reason_id}", response_model=AbsenceReasonRead)
def update_absence_reason(absence_reason_id: UUID, payload: AbsenceReasonUpdate,
                          db: Session = Depends(get_db)):
    ar = db.query(AbsenceReason).filter_by(id=absence_reason_id).first()
    if not ar:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Absence reason not found.")

    updates = payload.model_dump(exclude_none=True)

    if "name" in updates and updates["name"] != ar.name:
        existing = db.query(AbsenceReason).filter_by(name=updates["name"]).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail=f"An absence reason named '{updates['name']}' already exists.")

    for key, value in updates.items():
        setattr(ar, key, value)

    db.commit()
    db.refresh(ar)
    return ar


@router.delete("/{absence_reason_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_absence_reason(absence_reason_id: UUID, db: Session = Depends(get_db)):
    ar = db.query(AbsenceReason).filter_by(id=absence_reason_id).first()
    if not ar:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Absence reason not found.")
    db.delete(ar)
    db.commit()

