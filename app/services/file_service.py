import os
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session
from ..models.models import File, Job
from ..config import settings

class FileService:
    
    @staticmethod
    def save_file(db: Session, file: UploadFile, user_id: int) -> File:
        upload_dir = os.path.join(settings.UPLOAD_DIR, str(user_id))
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, file.filename)
        with open(file_path, "wb") as buffer:
            content = file.file.read()
            buffer.write(content)
        
        db_file = File(
            filename=file.filename,
            path=file_path,
            user_id=user_id
        )
        db.add(db_file)
        db.commit()
        db.refresh(db_file)
        return db_file
    
    @staticmethod
    def get_user_files(db: Session, user_id: int) -> list[File]:
        return db.query(File).filter(File.user_id == user_id).all()
    
    @staticmethod
    def get_file(db: Session, file_id: int, user_id: int) -> File:
        file = db.query(File).filter(File.id == file_id, File.user_id == user_id).first()
        if not file:
            raise HTTPException(status_code=404, detail="File not found")
        return file
    
    @staticmethod
    def delete_file(db: Session, file_id: int, user_id: int):
        file = FileService.get_file(db, file_id, user_id)
        # Nullify references in past jobs so deletion is always allowed
        linked_jobs = db.query(Job).filter(
            (Job.source_file_id == file_id) | (Job.output_file_id == file_id)
        ).all()
        for job in linked_jobs:
            if job.source_file_id == file_id:
                job.source_file_id = None
            if job.output_file_id == file_id:
                job.output_file_id = None
        db.flush()
        # Remove the physical file if it still exists
        if os.path.exists(file.path):
            try:
                os.remove(file.path)
            except Exception:
                pass
        db.delete(file)
        db.commit()

    @staticmethod
    def get_file_for_gateway(db: Session, file_id: int) -> File:
        file = db.query(File).filter(File.id == file_id).first()
        if not file:
            raise HTTPException(status_code=404, detail="File not found")
        return file