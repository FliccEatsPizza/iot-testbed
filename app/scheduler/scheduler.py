from sqlalchemy.orm import Session
from datetime import datetime, timezone
import asyncio
import logging
from typing import List

from ..database import SessionLocal
from ..models.models import JobGroup, Job, Device, JobStatus, DeviceStatus
from ..queue.redis_client import redis_client

logger = logging.getLogger(__name__)

class JobScheduler:
    def __init__(self):
        self.running = False
        self.check_interval = 5  # seconds

    async def start(self):
        self.running = True
        while self.running:
            try:
                await self.check_and_dispatch_jobs()
            except Exception as e:
                logger.error(f"Error in job scheduler: {e}")
            await asyncio.sleep(self.check_interval)
    
    async def stop(self):
        self.running = False
    
    async def check_and_dispatch_jobs(self):
        db: Session = SessionLocal()
        try:
            pending_groups = (
                db.query(JobGroup)
                .filter(JobGroup.status == JobStatus.pending)
                .order_by(JobGroup.created_at)
                .all()
            )
            
            for group in pending_groups:
                jobs = db.query(Job).filter(Job.group_id == group.id).all()
                device_ids = [job.device_id for job in jobs]
                devices = db.query(Device).filter(Device.id.in_(device_ids)).all()
                if all(device.status == DeviceStatus.available for device in devices):
                    await self.dispatch_job_group(db, group, jobs, devices)
        finally:
            db.close()
    
    async def dispatch_job_group(self, db: Session, group: JobGroup, jobs: List[Job], devices: List[Device]):
        try:
            for device in devices:
                device.status = DeviceStatus.busy
            group.status = JobStatus.running
            group.started_at = datetime.now(timezone.utc)

            for job in jobs:
                job.status = JobStatus.running
                job.started_at = datetime.now(timezone.utc)
                job_data = {
                    "job_id": job.id,
                    "group_id": job.group_id,
                    "device_id": job.device_id
                }
                matching_device = next(device for device in devices if device.id == job.device_id)
                await redis_client.push_job(matching_device.gateway_id, job_data)

            db.commit()
            logger.info(f"Dispatched job group {group.id}")
        
        except Exception as e:
            db.rollback()
            logger.error(f"Error dispatching job group {group.id}: {e}")
            for device in devices:
                device.status = DeviceStatus.available
            group.status = JobStatus.failed
            group.completed_at = datetime.now(timezone.utc)
            for job in jobs:
                job.status = JobStatus.failed
                job.completed_at = datetime.now(timezone.utc)
            db.commit()

scheduler = JobScheduler()