import redis.asyncio as redis
import json
import logging
from typing import Dict, Any, Optional
from ..config import settings

logger = logging.getLogger(__name__)

class RedisClient:
    def __init__(self):
        self.redis_url = settings.REDIS_URL
        self._redis: Optional[redis.Redis] = None
        self.is_connected: bool = False

    async def init(self):
        if self._redis is None:
            try:
                self._redis = await redis.from_url(
                    self.redis_url,
                    max_connections=20,
                    decode_responses=True,
                    health_check_interval=10,
                    socket_keepalive=True,
                    retry_on_timeout=True
                )
                await self.ping()
            except Exception as e:
                self._redis = None
                self.is_connected = False
                logger.warning(f"Redis connection failed: {e}")

    async def ping(self):
        if self._redis is None:
            self.is_connected = False
            return False
        try:
            res = await self._redis.ping()
            self.is_connected = True
            return res
        except Exception as e:
            self.is_connected = False
            logger.warning(f"Redis ping error: {e}")
            return False
    
    async def close(self):
        if self._redis is not None:
            try:
                await self._redis.close()
            except Exception:
                pass
            self.is_connected = False
    
    async def push_job(self, gateway_id: int, job_data: Dict[str, Any]):
        if not self._redis: return
        try:
            queue_key = f"gateway:{gateway_id}:jobs"
            await self._redis.lpush(queue_key, json.dumps(job_data))
        except Exception as e:
            logger.error(f"Error pushing job to Redis: {e}")
    
    async def get_job(self, gateway_id: int) -> Optional[Dict[str, Any]]:
        if not self._redis: return None
        try:
            queue_key = f"gateway:{gateway_id}:jobs"
            result = await self._redis.brpop(queue_key, timeout=5)
            if result:
                _, job_data = result
                return json.loads(job_data)
        except Exception as e:
            logger.error(f"Error getting job from Redis: {e}")
        return None

    async def publish_status(self, job_id: int, status: str, message: str):
        if not self._redis: return
        try:
            channel = f"job:{job_id}:status"
            await self._redis.publish(channel, json.dumps({
                "status": status,
                "message": message
            }))
        except Exception as e:
            logger.error(f"Error publishing status to Redis: {e}")

    async def push_download_notification(self, gateway_id: int, notification: Dict[str, Any]):
        if not self._redis: return
        try:
            queue_key = f"gateway:{gateway_id}:download_notifications"
            await self._redis.lpush(queue_key, json.dumps(notification))
        except Exception as e:
            logger.error(f"Error pushing download notification to Redis: {e}")
    
    async def get_download_notification(self, gateway_id: int) -> Optional[Dict[str, Any]]:
        if not self._redis: return None
        try:
            queue_key = f"gateway:{gateway_id}:download_notifications"
            result = await self._redis.brpop(queue_key, timeout=5)
            if result:
                _, notification_data = result
                return json.loads(notification_data)
        except Exception as e:
            logger.error(f"Error getting download notification from Redis: {e}")
        return None

redis_client = RedisClient()
