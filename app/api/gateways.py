from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.schemas import GatewayCreate, GatewayRegister, GatewayHeartbeat, GatewaySchema, UserSchema, GatewayTokenVerify
from ..services.gateway_service import GatewayService
from ..services.file_service import FileService
from .auth import get_current_user_dependency

router = APIRouter(
    prefix="/gateways",
    tags=["gateways"]
)

@router.post("/", response_model=GatewayRegister)
def create_gateway(
    gateway: GatewayCreate,
    db: Session = Depends(get_db),
    current_user: UserSchema = Depends(get_current_user_dependency)
):
    try:
        return GatewayService.create_gateway_service(gateway, db)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/register", response_model=GatewaySchema)
def register_gateway(verify: GatewayRegister, db: Session = Depends(get_db)):
    try:
        return GatewayService.verify_gateway_service(verify, db)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/verify-token", response_model=GatewaySchema)
def verify_token(token_data: GatewayTokenVerify, db: Session = Depends(get_db)):
    """
    Verify token and automatically register the gateway if token is valid.
    This endpoint is used for automatic registration when Pi boots up.
    """
    try:
        return GatewayService.verify_token_and_register(token_data.token, db)
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

@router.post("/{gateway_id}/heartbeat")
def gateway_heartbeat(gateway_id: int, heartbeat: GatewayHeartbeat, db: Session = Depends(get_db)):
    try:
        return GatewayService.gateway_heartbeat_service(gateway_id, heartbeat.active_device_ids, db)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    
@router.get("/download/{file_id}")
def download_file_for_gateway(
    file_id: int,
    gateway_token: str = Header(..., alias="X-Gateway-Token"),
    db: Session = Depends(get_db)
):
    gateway = GatewayService.get_gateway_by_token(gateway_token, db)
    if not gateway:
        raise HTTPException(status_code=404, detail="Gateway not found")
    
    file = FileService.get_file_for_gateway(db, file_id)
    return FileResponse(file.path, filename=file.filename)
