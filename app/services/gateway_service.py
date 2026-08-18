import secrets
import hashlib
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from ..models.models import Gateway, DeviceStatus, VerificationStatus
from ..schemas.schemas import GatewayCreate, GatewayRegister

class GatewayService:

    @staticmethod
    def generate_token():
        return "abcdefgh12345678" # for convenience while testing
        # return secrets.token_urlsafe(16)

    @staticmethod
    def hash_token(token: str):
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    def get_gateway_by_token(token: str, db: Session) -> Gateway:
        token_hash = GatewayService.hash_token(token)
        return db.query(Gateway).filter(Gateway.token_hash == token_hash).first()

    @staticmethod
    def verify_gateway_service(verify: GatewayRegister, db: Session):
        gateway = db.query(Gateway).filter(Gateway.name == verify.name).first()
        if not gateway:
            raise Exception("Gateway not found")
        if gateway.verification_status == VerificationStatus.verified:
            raise Exception("Gateway already verified")
        token_hash = GatewayService.hash_token(verify.token)
        if token_hash != gateway.token_hash:
            raise Exception("Invalid token")
        gateway.verification_status = VerificationStatus.verified
        db.commit()
        db.refresh(gateway)
        return gateway

    @staticmethod
    def create_gateway_service(gateway: GatewayCreate, db: Session):
        if(db.query(Gateway).filter(Gateway.name == gateway.name).first()):
            raise Exception("Gateway name already exists")

        token = GatewayService.generate_token()
        token_hash = GatewayService.hash_token(token)
        
        db_gateway = Gateway(
            name=gateway.name,
            ip_address=gateway.ip_address,
            status=DeviceStatus.available,
            last_seen=datetime.now(timezone.utc),
            verification_status=VerificationStatus.unverified,
            token_hash=token_hash
        )
        db.add(db_gateway)
        try:
            db.commit()
            db.refresh(db_gateway)
        except Exception as e:
            db.rollback()
            raise Exception(str(e))

        return GatewayRegister(name=db_gateway.name, token=token)

    @staticmethod
    def verify_token_and_register(token: str, db: Session):
        """
        Verify token and automatically register the gateway if token is valid.
        Returns the gateway information if successful.
        """
        gateway = GatewayService.get_gateway_by_token(token, db)
        if not gateway:
            raise Exception("Invalid token")
        
        # Update gateway status and last seen
        gateway.last_seen = datetime.now(timezone.utc)
        gateway.status = DeviceStatus.available
        
        # If gateway is not verified yet, verify it
        if gateway.verification_status == VerificationStatus.unverified:
            gateway.verification_status = VerificationStatus.verified
        
        db.commit()
        db.refresh(gateway)
        return gateway

    @staticmethod
    def gateway_heartbeat_service(gateway_id: int, active_device_ids: list[int], db: Session):
        gateway = db.query(Gateway).filter(Gateway.id == gateway_id).first()
        if not gateway:
            raise Exception("Gateway not found")
        gateway.last_seen = datetime.now(timezone.utc)
        if gateway.status == DeviceStatus.offline:
            gateway.status = DeviceStatus.available

        devices = gateway.devices
        for device in devices:
            if device.id in active_device_ids:
                device.last_seen = datetime.now(timezone.utc)
                if device.status == DeviceStatus.offline:
                    device.status = DeviceStatus.available
            else:
                device.status = DeviceStatus.offline
        db.commit()
        return {"message": "Gateway and devices heartbeat updated"}