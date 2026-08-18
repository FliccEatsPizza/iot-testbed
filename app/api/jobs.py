from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Header
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List
import os

from ..config import settings
from ..database import get_db
from ..schemas.schemas import JobSchema, JobStatusUpdate, UserSchema
from ..api.auth import get_current_user_dependency
from ..services.job_service import JobService
from ..services.gateway_service import GatewayService
from ..models.models import Job, Device

router = APIRouter(
    prefix="/jobs",
    tags=["jobs"]
)

@router.get("/", response_model=List[JobSchema])
def get_jobs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    try:
        return JobService.get_jobs_service(db, skip, limit)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{job_id}", response_model=JobSchema)
def get_job(job_id: int, db: Session = Depends(get_db)):
    try:
        return JobService.get_job_service(job_id, db)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.put("/{job_id}/status")
def update_job_status(job_id: int, status_update: JobStatusUpdate, db: Session = Depends(get_db)):
    try:
        return JobService.update_job_status_service(job_id, status_update, db)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@router.post("/{job_id}/logs")
async def upload_job_logs(
    job_id: int,
    log_file: UploadFile = File(...),
    x_gateway_token: str = Header(...),
    db: Session = Depends(get_db),
):
    # Verify gateway
    gateway = GatewayService.get_gateway_by_token(x_gateway_token, db)
    if not gateway:
        raise HTTPException(status_code=403, detail="Invalid gateway token")
    
    # Verify job exists and belongs to this gateway
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    device = db.query(Device).filter(Device.id == job.device_id).first()
    if not device or device.gateway_id != gateway.id:
        raise HTTPException(status_code=403, detail="Job not associated with this gateway")

    # Save log file
    log_filename = f"{job_id}.txt"
    log_path = os.path.join(settings.LOGS_DIR, log_filename)
    
    try:
        contents = await log_file.read()
        with open(log_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving logs: {str(e)}")
    
    return {"message": "Logs uploaded successfully", "path": log_path}

@router.get("/{job_id}/log")
def check_job_log(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: UserSchema = Depends(get_current_user_dependency),
):
    # fetch job and verify ownership
    job = JobService.get_job_service(job_id, db)
    if job.group.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed to view this log")

    # determine file path
    log_path = os.path.join(settings.LOGS_DIR, f"{job_id}.txt")
    exists = os.path.isfile(log_path)
    return {
        "exists": exists,
        "path": log_path if exists else None
    }


@router.get("/{job_id}/log/download")
def download_job_log(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: UserSchema = Depends(get_current_user_dependency),
):
    # fetch job and verify ownership
    job = JobService.get_job_service(job_id, db)
    if job.group.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed to download this log")

    # locate and stream the file
    log_path = os.path.join(settings.LOGS_DIR, f"{job_id}.txt")
    if not os.path.isfile(log_path):
        raise HTTPException(status_code=404, detail="Log file not found")

    return FileResponse(
        path=log_path,
        media_type="text/plain",
        filename=f"{job_id}.txt"
    )