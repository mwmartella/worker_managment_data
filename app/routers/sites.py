from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import Business, Site
from app.schemas import SiteCreate, SiteRead, SiteUpdate

router = APIRouter(prefix="/sites", tags=["Sites"])


@router.get("/", response_model=list[SiteRead])
def list_sites(db: Session = Depends(get_db)):
    """Return all sites ordered by name."""
    return db.query(Site).order_by(Site.name).all()


@router.get("/{site_id}", response_model=SiteRead)
def get_site(site_id: UUID, db: Session = Depends(get_db)):
    site = db.query(Site).filter_by(id=site_id).first()
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Site not found.")
    return site


@router.post("/", response_model=SiteRead, status_code=status.HTTP_201_CREATED)
def create_site(payload: SiteCreate, db: Session = Depends(get_db)):
    """Create a new site. created_at and updated_at are set by the database."""
    # Check for duplicate code if provided
    if payload.code:
        existing = db.query(Site).filter_by(code=payload.code).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail=f"A site with code '{payload.code}' already exists.")

    # Validate FK if provided
    if payload.business_id:
        business = db.query(Business).filter_by(id=payload.business_id).first()
        if not business:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Business not found.")

    site = Site(
        name=payload.name,
        code=payload.code,
        business_id=payload.business_id,
        type=payload.type,
        address=payload.address,
        notes=payload.notes,
    )
    db.add(site)
    db.commit()
    db.refresh(site)
    return site


@router.patch("/{site_id}", response_model=SiteRead)
def update_site(site_id: UUID, payload: SiteUpdate, db: Session = Depends(get_db)):
    """Partially update editable fields (name, type, code, notes) on a site."""
    site = db.query(Site).filter_by(id=site_id).first()
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Site not found.")

    updates = payload.model_dump(exclude_none=True)

    # Check for duplicate code if it's being changed
    if "code" in updates and updates["code"] != site.code:
        existing = db.query(Site).filter_by(code=updates["code"]).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail=f"A site with code '{updates['code']}' already exists.")

    for field, value in updates.items():
        setattr(site, field, value)

    db.commit()
    db.refresh(site)
    return site


@router.delete("/{site_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_site(site_id: UUID, db: Session = Depends(get_db)):
    """Delete a site by ID."""
    site = db.query(Site).filter_by(id=site_id).first()
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Site not found.")
    db.delete(site)
    db.commit()


