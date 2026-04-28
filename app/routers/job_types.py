from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import JobType
from app.schemas import JobTypeCreate, JobTypeRead, JobTypeUpdate

router = APIRouter(prefix="/job-types", tags=["Job Types"])


@router.get("/", response_model=list[JobTypeRead])
def list_job_types(db: Session = Depends(get_db)):
    return db.query(JobType).order_by(JobType.name).all()


@router.get("/{job_type_id}", response_model=JobTypeRead)
def get_job_type(job_type_id: UUID, db: Session = Depends(get_db)):
    jt = db.query(JobType).filter_by(id=job_type_id).first()
    if not jt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job type not found.")
    return jt


@router.post("/", response_model=JobTypeRead, status_code=status.HTTP_201_CREATED)
def create_job_type(payload: JobTypeCreate, db: Session = Depends(get_db)):
    existing = db.query(JobType).filter_by(name=payload.name).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=f"A job type named '{payload.name}' already exists.")
    jt = JobType(name=payload.name, category=payload.category, notes=payload.notes)
    db.add(jt)
    db.commit()
    db.refresh(jt)
    return jt


@router.patch("/{job_type_id}", response_model=JobTypeRead)
def update_job_type(job_type_id: UUID, payload: JobTypeUpdate,
                    db: Session = Depends(get_db)):
    jt = db.query(JobType).filter_by(id=job_type_id).first()
    if not jt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job type not found.")

    updates = payload.model_dump(exclude_none=True)

    if "name" in updates and updates["name"] != jt.name:
        existing = db.query(JobType).filter_by(name=updates["name"]).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail=f"A job type named '{updates['name']}' already exists.")

    for key, value in updates.items():
        setattr(jt, key, value)

    db.commit()
    db.refresh(jt)
    return jt


@router.delete("/{job_type_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job_type(job_type_id: UUID, db: Session = Depends(get_db)):
    jt = db.query(JobType).filter_by(id=job_type_id).first()
    if not jt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job type not found.")
    db.delete(jt)
    db.commit()

