from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional
from ..models.models import DeviceStatus, JobStatus

# User Schemas
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)

class UserSchema(BaseModel):
    id: int
    username: str
    created_at: datetime

    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    username: str
    password: str

# Gateway Schemas
class GatewayCreate(BaseModel):
    name: str = Field(..., max_length=100)
    ip_address: Optional[str] = None

class GatewaySchema(BaseModel):
    id: int
    name: str
    ip_address: Optional[str]
    status: DeviceStatus
    last_seen: datetime

    class Config:
        from_attributes = True

class GatewayRegister(BaseModel):
    name: str = Field(..., max_length=100)
    token: str

class GatewayHeartbeat(BaseModel):
    active_device_ids: List[int]

class GatewayTokenVerify(BaseModel):
    token: str

# Device Schemas
class DeviceCreate(BaseModel):
    name: str = Field(..., max_length=100)
    gateway_id: int

class DeviceSchema(BaseModel):
    id: int
    name: str
    gateway_id: int
    status: DeviceStatus
    last_seen: datetime

    class Config:
        from_attributes = True

# Job Schemas
class JobCreate(BaseModel):
    device_id: int
    source_file_id: int

class JobStatusUpdate(BaseModel):
    status: JobStatus
    output_file_id: Optional[int] = None

class JobSchema(BaseModel):
    id: int
    source_file_id: int
    group_id: int
    device_id: int
    status: JobStatus
    output_file_id: Optional[int] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Job Group Schemas
class JobGroupCreate(BaseModel):
    name: str
    jobs: List[JobCreate]

class JobGroupSchema(BaseModel):
    id: int
    name: str
    user_id: int
    status: JobStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    jobs: List[JobSchema]

    class Config:
        from_attributes = True

# File Schemas
class FileSchema(BaseModel):
    id: int
    filename: str
    created_at: datetime

    class Config:
        from_attributes = True