from pydantic_settings import BaseSettings

class Settings(BaseSettings):

    # will change this stuff later and move them to .env file
    DATABASE_URL: str = "sqlite:///./iot_testbed.db"
    REDIS_URL: str = "redis://localhost:6379/0"
    API_PREFIX: str = "/api/v1"
    JWT_SECRET_KEY: str = "secret" # replace with a strong secret key
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    UPLOAD_DIR: str = "./uploads"
    LOGS_DIR: str = "./logs"
    
    class Config:
        env_file = ".env"

settings = Settings()
