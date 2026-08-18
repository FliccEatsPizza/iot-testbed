from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..schemas.schemas import DeviceCreate, DeviceSchema
from ..models.models import DeviceStatus
from ..services.device_service import DeviceService

router = APIRouter(
    prefix="/devices",
    tags=["devices"],
)

@router.post("/", response_model=DeviceSchema)
def create_device(device: DeviceCreate, db: Session = Depends(get_db)):
    try:
        return DeviceService.create_device_service(device, db)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=List[DeviceSchema])
def get_devices(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    try:
        return DeviceService.get_devices_service(db, skip, limit)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{device_id}", response_model=DeviceSchema)
def get_device(device_id: int, db: Session = Depends(get_db)):
    try:
        return DeviceService.get_device_service(device_id, db)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.put("/{device_id}", response_model=DeviceSchema)
def update_device_status(device_id: int, status: DeviceStatus, db: Session = Depends(get_db)):
    try:
        return DeviceService.update_device_status_service(device_id, status, db)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/{device_id}")
def delete_device(device_id: int, db: Session = Depends(get_db)):
    try:
        return DeviceService.delete_device_service(device_id, db)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))