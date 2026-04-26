from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import FruitType
from app.schemas import FruitTypeCreate, FruitTypeRead, FruitTypeUpdate

router = APIRouter(prefix="/fruit-types", tags=["Fruit Types"])


@router.get("/", response_model=list[FruitTypeRead])
def list_fruit_types(db: Session = Depends(get_db)):
    return db.query(FruitType).order_by(FruitType.name).all()


@router.get("/{fruit_type_id}", response_model=FruitTypeRead)
def get_fruit_type(fruit_type_id: UUID, db: Session = Depends(get_db)):
    ft = db.query(FruitType).filter_by(id=fruit_type_id).first()
    if not ft:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Fruit type not found.")
    return ft


@router.post("/", response_model=FruitTypeRead, status_code=status.HTTP_201_CREATED)
def create_fruit_type(payload: FruitTypeCreate, db: Session = Depends(get_db)):
    existing = db.query(FruitType).filter_by(name=payload.name).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=f"A fruit type named '{payload.name}' already exists.")
    ft = FruitType(name=payload.name, notes=payload.notes)
    db.add(ft)
    db.commit()
    db.refresh(ft)
    return ft


@router.patch("/{fruit_type_id}", response_model=FruitTypeRead)
def update_fruit_type(fruit_type_id: UUID, payload: FruitTypeUpdate,
                      db: Session = Depends(get_db)):
    ft = db.query(FruitType).filter_by(id=fruit_type_id).first()
    if not ft:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Fruit type not found.")

    updates = payload.model_dump(exclude_none=True)

    if "name" in updates and updates["name"] != ft.name:
        existing = db.query(FruitType).filter_by(name=updates["name"]).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail=f"A fruit type named '{updates['name']}' already exists.")

    for key, value in updates.items():
        setattr(ft, key, value)

    db.commit()
    db.refresh(ft)
    return ft


@router.delete("/{fruit_type_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_fruit_type(fruit_type_id: UUID, db: Session = Depends(get_db)):
    ft = db.query(FruitType).filter_by(id=fruit_type_id).first()
    if not ft:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Fruit type not found.")
    db.delete(ft)
    db.commit()

