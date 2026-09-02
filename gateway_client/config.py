import os

# Base server host defaults to your laptop's mDNS hostname (LAPTOP-TTI3F4FK.local)
# Can be overridden via SERVER_HOST or SERVER_URL environment variable if needed.
SERVER_HOST = os.getenv("SERVER_HOST", "LAPTOP-TTI3F4FK.local")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

SERVER_URL = os.getenv("SERVER_URL", f"http://{SERVER_HOST}:{SERVER_PORT}")
API_BASE_URL = os.getenv("API_BASE_URL", f"{SERVER_URL}/api/v1")
REDIS_URL = os.getenv("REDIS_URL", f"redis://{SERVER_HOST}:{REDIS_PORT}/0")

GATEWAY_ID = int(os.getenv("GATEWAY_ID", "1"))
GATEWAY_TOKEN = os.getenv("GATEWAY_TOKEN", "abcdefgh12345678")
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "./downloads")
