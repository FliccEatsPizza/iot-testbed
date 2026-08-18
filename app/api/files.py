from fastapi import APIRouter, Depends, HTTPException, UploadFile, File as FastAPIFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from ..database import get_db
from ..schemas.schemas import FileSchema, UserSchema
from ..services.file_service import FileService
from .auth import get_current_user_dependency

router = APIRouter(
    prefix="/files",
    tags=["files"]
)

@router.post("/upload", response_model=FileSchema)
async def upload_file(
    file: UploadFile = FastAPIFile(...),
    db: Session = Depends(get_db),
    current_user: UserSchema = Depends(get_current_user_dependency)
):
    try:
        return FileService.save_file(db, file, current_user.id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=list[FileSchema])
async def list_files(
    db: Session = Depends(get_db),
    current_user: UserSchema = Depends(get_current_user_dependency)
):
    try:
        return FileService.get_user_files(db, current_user.id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{file_id}/download")
async def download_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: UserSchema = Depends(get_current_user_dependency)
):
    try:
        file = FileService.get_file(db, file_id, current_user.id)
        return FileResponse(file.path, filename=file.filename)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{file_id}")
async def delete_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: UserSchema = Depends(get_current_user_dependency)
):
    try:
        FileService.delete_file(db, file_id, current_user.id)
        return {"message": "File deleted"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))