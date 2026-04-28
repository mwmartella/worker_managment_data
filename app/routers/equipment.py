from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import Equipment
from app.schemas import EquipmentCreate, EquipmentRead, EquipmentUpdate

router = APIRouter(prefix="/equipment", tags=["Equipment"])


@router.get("/", response_model=list[EquipmentRead])
def list_equipment(db: Session = Depends(get_db)):
    return db.query(Equipment).order_by(Equipment.name).all()


@router.get("/{equipment_id}", response_model=EquipmentRead)
def get_equipment(equipment_id: UUID, db: Session = Depends(get_db)):
    eq = db.query(Equipment).filter_by(id=equipment_id).first()
    if not eq:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipment not found.")
    return eq


@router.post("/", response_model=EquipmentRead, status_code=status.HTTP_201_CREATED)
def create_equipment(payload: EquipmentCreate, db: Session = Depends(get_db)):
    eq = Equipment(**payload.model_dump())
    db.add(eq)
    db.commit()
    db.refresh(eq)
    return eq


@router.patch("/{equipment_id}", response_model=EquipmentRead)
def update_equipment(equipment_id: UUID, payload: EquipmentUpdate, db: Session = Depends(get_db)):
    eq = db.query(Equipment).filter_by(id=equipment_id).first()
    if not eq:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipment not found.")
    for key, value in payload.model_dump(exclude_none=True).items():
        setattr(eq, key, value)
    db.commit()
    db.refresh(eq)
    return eq


@router.delete("/{equipment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_equipment(equipment_id: UUID, db: Session = Depends(get_db)):
    eq = db.query(Equipment).filter_by(id=equipment_id).first()
    if not eq:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipment not found.")
    db.delete(eq)
    db.commit()

