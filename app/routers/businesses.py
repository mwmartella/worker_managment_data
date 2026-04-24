from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import Business
from app.schemas import BusinessCreate, BusinessRead, BusinessUpdate

router = APIRouter(prefix="/businesses", tags=["Businesses"])


@router.get("/", response_model=list[BusinessRead])
def list_businesses(db: Session = Depends(get_db)):
    """Return all businesses ordered by name."""
    return db.query(Business).order_by(Business.name).all()


@router.get("/{business_id}", response_model=BusinessRead)
def get_business(business_id: UUID, db: Session = Depends(get_db)):
    business = db.query(Business).filter_by(id=business_id).first()
    if not business:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Business not found.")
    return business


@router.post("/", response_model=BusinessRead, status_code=status.HTTP_201_CREATED)
def create_business(payload: BusinessCreate, db: Session = Depends(get_db)):
    """Create a new business. created_at and updated_at are set by the database."""
    # Check for duplicate code if provided
    if payload.code:
        existing = db.query(Business).filter_by(code=payload.code).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail=f"A business with code '{payload.code}' already exists.")

    business = Business(
        name=payload.name,
        code=payload.code,
    )
    db.add(business)
    db.commit()
    db.refresh(business)
    return business


@router.patch("/{business_id}", response_model=BusinessRead)
def update_business(business_id: UUID, payload: BusinessUpdate,
                    db: Session = Depends(get_db)):
    """Partially update editable fields (name, code) on a business."""
    business = db.query(Business).filter_by(id=business_id).first()
    if not business:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Business not found.")

    updates = payload.model_dump(exclude_none=True)

    # Check for duplicate code if it's being changed
    if "code" in updates and updates["code"] != business.code:
        existing = db.query(Business).filter_by(code=updates["code"]).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail=f"A business with code '{updates['code']}' already exists.")

    for field, value in updates.items():
        setattr(business, field, value)

    db.commit()
    db.refresh(business)
    return business


@router.delete("/{business_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_business(business_id: UUID, db: Session = Depends(get_db)):
    """Delete a business by ID."""
    business = db.query(Business).filter_by(id=business_id).first()
    if not business:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Business not found.")
    db.delete(business)
    db.commit()

