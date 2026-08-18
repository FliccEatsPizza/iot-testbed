from sqlalchemy.orm import Session
from datetime import datetime, timezone
from fastapi import BackgroundTasks

from ..models.models import JobGroup, Job, Device, JobStatus, DeviceStatus
from ..schemas.schemas import JobGroupCreate
from ..queue.redis_client import redis_client

class JobGroupService:

    @staticmethod
    def create_job_group_service(job_group: JobGroupCreate, user_id: int, db: Session, background_tasks: BackgroundTasks):
        if not job_group.jobs or len(job_group.jobs) == 0:
            raise Exception("No jobs provided")

        device_ids = [job.device_id for job in job_group.jobs]
        devices = db.query(Device).filter(Device.id.in_(device_ids)).all()
        if len(devices) != len(device_ids):
            raise Exception("One or more devices not found")
        
        device_map = {device.id: device for device in devices}
        
        db_job_group = JobGroup(
            name=job_group.name,
            user_id=user_id,
            status=JobStatus.preparing,
            created_at=datetime.now(timezone.utc)
        )
        db.add(db_job_group)
        db.flush()

        for job_data in job_group.jobs:
            job = Job(
                group_id=db_job_group.id,
                device_id=job_data.device_id,
                source_file_id=job_data.source_file_id,
                status=JobStatus.preparing,
                created_at=datetime.now(timezone.utc)
            )
            db.add(job)
        
        try:
            db.commit()
            db.refresh(db_job_group)
        except Exception as e:
            db.rollback()
            raise Exception(str(e))
        
        for job in db_job_group.jobs:
            device = device_map[job.device_id]
            gateway_id = device.gateway_id
            notification = {
                "job_id": job.id,
                "source_file_id": job.source_file_id
            }
            background_tasks.add_task(redis_client.push_download_notification, gateway_id, notification)
        
        return db_job_group

    @staticmethod
    def get_queue_status_service(user_id: int, db: Session):
        pending_groups = db.query(JobGroup).filter(
            JobGroup.status == JobStatus.pending,
            JobGroup.user_id == user_id
        ).all()
        
        queue_status = []
        for group in pending_groups:
            jobs = db.query(Job).filter(Job.group_id == group.id).all()
            device_ids = [job.device_id for job in jobs]
            devices = db.query(Device).filter(Device.id.in_(device_ids)).all()
            
            queue_status.append({
                "group_id": group.id,
                "name": group.name,
                "created_at": group.created_at,
                "devices": [
                    {
                        "device_id": device.id,
                        "name": device.name,
                        "status": device.status.value
                    }
                    for device in devices
                ],
                "ready_to_run": all(device.status == DeviceStatus.available for device in devices)
            })
        return queue_status

    @staticmethod
    def get_job_groups_service(user_id: int, db: Session, skip: int = 0, limit: int = 100):
        return db.query(JobGroup).filter(JobGroup.user_id == user_id).offset(skip).limit(limit).all()

    @staticmethod
    def get_job_group_service(group_id: int, user_id: int, db: Session):
        job_group = db.query(JobGroup).filter(
            JobGroup.id == group_id,
            JobGroup.user_id == user_id
        ).first()
        if not job_group:
            raise Exception("Job group not found")
        return job_group

    @staticmethod
    def cancel_job_group_service(group_id: int, user_id: int, db: Session):
        job_group = db.query(JobGroup).filter(
            JobGroup.id == group_id,
            JobGroup.user_id == user_id
        ).first()
        if not job_group:
            raise Exception("Job group not found")
        
        if job_group.status == JobStatus.completed:
            raise Exception("Cannot cancel completed job group")
        
        job_group.status = JobStatus.cancelled
        job_group.completed_at = datetime.now(timezone.utc)
        
        db.query(Job).filter(
            Job.group_id == group_id,
            Job.status.in_([JobStatus.pending, JobStatus.running])
        ).update({"status": JobStatus.cancelled, "completed_at": datetime.now(timezone.utc)})
        
        db.commit()
        return {"message": "Job group cancelled"}

    @staticmethod
    def get_job_group_status_service(group_id: int, user_id: int, db: Session):
        job_group = db.query(JobGroup).filter(
            JobGroup.id == group_id,
            JobGroup.user_id == user_id
        ).first()
        if not job_group:
            raise Exception("Job group not found")
        
        jobs = db.query(Job).filter(Job.group_id == group_id).all()
        status_counts = {
            "total": len(jobs),
            "pending": sum(1 for job in jobs if job.status == JobStatus.pending),
            "running": sum(1 for job in jobs if job.status == JobStatus.running),
            "completed": sum(1 for job in jobs if job.status == JobStatus.completed),
            "cancelled": sum(1 for job in jobs if job.status == JobStatus.cancelled),
            "failed": sum(1 for job in jobs if job.status == JobStatus.failed)
        }
        
        device_ids = [job.device_id for job in jobs]
        devices = db.query(Device).filter(Device.id.in_(device_ids)).all()
        
        return {
            "group_status": job_group.status.value,
            "job_stats": status_counts,
            "created_at": job_group.created_at,
            "started_at": job_group.started_at,
            "completed_at": job_group.completed_at,
            "devices": [
                {
                    "device_id": device.id,
                    "name": device.name,
                    "status": device.status.value
                }
                for device in devices
            ]
        }