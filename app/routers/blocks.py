from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import Block, Field
from app.schemas import BlockCreate, BlockRead, BlockUpdate

router = APIRouter(prefix="/blocks", tags=["Blocks"])


@router.get("/", response_model=list[BlockRead])
def list_blocks(db: Session = Depends(get_db)):
    return db.query(Block).order_by(Block.name).all()


@router.get("/{block_id}", response_model=BlockRead)
def get_block(block_id: UUID, db: Session = Depends(get_db)):
    block = db.query(Block).filter_by(id=block_id).first()
    if not block:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Block not found.")
    return block


@router.post("/", response_model=BlockRead, status_code=status.HTTP_201_CREATED)
def create_block(payload: BlockCreate, db: Session = Depends(get_db)):
    field = db.query(Field).filter_by(id=payload.field_id).first()
    if not field:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Field not found.")
    existing = db.query(Block).filter_by(field_id=payload.field_id, name=payload.name).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=f"Block '{payload.name}' already exists in this field.")
    block = Block(
        field_id=payload.field_id,
        name=payload.name,
        code=payload.code,
        block_type=payload.block_type,
        notes=payload.notes,
    )
    db.add(block)
    db.commit()
    db.refresh(block)
    return block


@router.patch("/{block_id}", response_model=BlockRead)
def update_block(block_id: UUID, payload: BlockUpdate, db: Session = Depends(get_db)):
    block = db.query(Block).filter_by(id=block_id).first()
    if not block:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Block not found.")

    updates = payload.model_dump(exclude_none=True)

    if "name" in updates and updates["name"] != block.name:
        existing = db.query(Block).filter_by(field_id=block.field_id, name=updates["name"]).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail=f"Block '{updates['name']}' already exists in this field.")

    for key, value in updates.items():
        setattr(block, key, value)

    db.commit()
    db.refresh(block)
    return block


@router.delete("/{block_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_block(block_id: UUID, db: Session = Depends(get_db)):
    block = db.query(Block).filter_by(id=block_id).first()
    if not block:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Block not found.")
    db.delete(block)
    db.commit()

