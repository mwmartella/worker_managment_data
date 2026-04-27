from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import Variety, VarietyClone
from app.schemas import VarietyCloneCreate, VarietyCloneRead, VarietyCloneUpdate

router = APIRouter(prefix="/variety-clones", tags=["Variety Clones"])


@router.get("/", response_model=list[VarietyCloneRead])
def list_variety_clones(db: Session = Depends(get_db)):
    return db.query(VarietyClone).order_by(VarietyClone.name).all()


@router.get("/{clone_id}", response_model=VarietyCloneRead)
def get_variety_clone(clone_id: UUID, db: Session = Depends(get_db)):
    vc = db.query(VarietyClone).filter_by(id=clone_id).first()
    if not vc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Variety clone not found.")
    return vc


@router.post("/", response_model=VarietyCloneRead, status_code=status.HTTP_201_CREATED)
def create_variety_clone(payload: VarietyCloneCreate, db: Session = Depends(get_db)):
    # Validate FK
    variety = db.query(Variety).filter_by(id=payload.variety_id).first()
    if not variety:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Variety not found.")
    # Check unique(name, variety_id)
    existing = db.query(VarietyClone).filter_by(
        name=payload.name, variety_id=payload.variety_id).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=f"Clone '{payload.name}' already exists for this variety.")
    vc = VarietyClone(name=payload.name, variety_id=payload.variety_id, notes=payload.notes)
    db.add(vc)
    db.commit()
    db.refresh(vc)
    return vc


@router.patch("/{clone_id}", response_model=VarietyCloneRead)
def update_variety_clone(clone_id: UUID, payload: VarietyCloneUpdate,
                         db: Session = Depends(get_db)):
    vc = db.query(VarietyClone).filter_by(id=clone_id).first()
    if not vc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Variety clone not found.")

    updates = payload.model_dump(exclude_none=True)

    if "name" in updates and updates["name"] != vc.name:
        existing = db.query(VarietyClone).filter_by(
            name=updates["name"], variety_id=vc.variety_id).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail=f"Clone '{updates['name']}' already exists for this variety.")

    for key, value in updates.items():
        setattr(vc, key, value)

    db.commit()
    db.refresh(vc)
    return vc


@router.delete("/{clone_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_variety_clone(clone_id: UUID, db: Session = Depends(get_db)):
    vc = db.query(VarietyClone).filter_by(id=clone_id).first()
    if not vc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Variety clone not found.")
    db.delete(vc)
    db.commit()

