from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from ..database import get_db
from ..schemas.schemas import JobGroupSchema, UserSchema
from ..services.preset_service import PresetService
from .auth import get_current_user_dependency

router = APIRouter(
    prefix="/presets",
    tags=["educational presets"]
)

@router.get("/")
def list_presets(
    current_user: UserSchema = Depends(get_current_user_dependency)
):
    """List all available pre-configured educational experiments"""
    try:
        return PresetService.list_presets()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{preset_id}")
def get_preset_details(
    preset_id: str,
    current_user: UserSchema = Depends(get_current_user_dependency)
):
    """Get complete details, theory, instructions, and source code for a preset"""
    try:
        return PresetService.get_preset_details(preset_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{preset_id}/launch", response_model=JobGroupSchema)
def launch_preset_experiment(
    preset_id: str,
    payload: Dict[str, Any],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: UserSchema = Depends(get_current_user_dependency)
):
    """One-click launch for an educational experiment"""
    try:
        return PresetService.launch_preset(
            preset_id=preset_id,
            user_id=current_user.id,
            payload=payload,
            db=db,
            background_tasks=background_tasks
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
