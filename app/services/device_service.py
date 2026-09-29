from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta

from ..models.models import Device, DeviceStatus, Gateway
from ..schemas.schemas import DeviceCreate

class DeviceService:

    @staticmethod
    def create_device_service(device: DeviceCreate, db: Session):
        gateway = db.query(Gateway).filter(Gateway.id == device.gateway_id).first()
        if not gateway:
            raise Exception("Gateway not found")

        db_device = Device(
            name=device.name,
            gateway_id=device.gateway_id,
            status=DeviceStatus.available,
            device_type=device.device_type,
            last_seen=datetime.now(timezone.utc)
        )
        db.add(db_device)
        try:
            db.commit()
            db.refresh(db_device)
        except Exception as e:
            db.rollback()
            raise Exception(str(e))
        return db_device

    @staticmethod
    def get_devices_service(db: Session, skip: int = 0, limit: int = 100, active_only: bool = True):
        now = datetime.now(timezone.utc)
        # 1. Any device that hasn't reported a heartbeat recently (> 15 seconds) is marked offline
        # unless it is currently busy executing a job
        threshold = now - timedelta(seconds=15)
        stale_devices = db.query(Device).filter(
            Device.last_seen < threshold,
            Device.status != DeviceStatus.busy,
            Device.status != DeviceStatus.offline
        ).all()
        if stale_devices:
            for d in stale_devices:
                d.status = DeviceStatus.offline
            try:
                db.commit()
            except Exception:
                db.rollback()

        query = db.query(Device)
        if active_only:
            query = query.filter(Device.status != DeviceStatus.offline)
        return query.offset(skip).limit(limit).all()

    @staticmethod
    def get_device_service(device_id: int, db: Session):
        device = db.query(Device).filter(Device.id == device_id).first()
        if not device:
            raise Exception("Device not found")
        return device

    @staticmethod
    def update_device_status_service(device_id: int, status: DeviceStatus, db: Session):
        device = db.query(Device).filter(Device.id == device_id).first()
        if not device:
            raise Exception("Device not found")
        device.status = status
        device.last_seen = datetime.now(timezone.utc)
        db.commit()
        db.refresh(device)
        return device

    @staticmethod
    def delete_device_service(device_id: int, db: Session):
        device = db.query(Device).filter(Device.id == device_id).first()
        if not device:
            raise Exception("Device not found")
        db.delete(device)
        db.commit()
        return {"message": "Device deleted"}