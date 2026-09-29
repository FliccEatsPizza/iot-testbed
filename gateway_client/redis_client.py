import redis.asyncio as redis
import json
import asyncio
from typing import Dict, Any, Optional
from config import REDIS_URL

class RedisClient:
    def __init__(self):
        self.redis_url = REDIS_URL
        self._redis = None

    async def init(self):
        if self._redis is None:
            self._redis = await redis.from_url(
                self.redis_url,
                max_connections=20,
                decode_responses=True,
                socket_keepalive=True,
                retry_on_timeout=True
            )
    
    async def close(self):
        if self._redis is not None:
            await self._redis.close()
    
    async def push_job(self, gateway_id: int, job_data: Dict[str, Any]):
        queue_key = f"gateway:{gateway_id}:jobs"
        await self._redis.lpush(queue_key, json.dumps(job_data))
    
    async def get_job(self, gateway_id: int) -> Optional[Dict[str, Any]]:
        queue_key = f"gateway:{gateway_id}:jobs"
        try:
            result = await self._redis.brpop(queue_key, timeout=2)
            if result:
                _, job_data = result
                return json.loads(job_data)
        except (redis.TimeoutError, asyncio.TimeoutError, Exception) as e:
            if "timeout" in str(e).lower():
                return None
            raise
        return None

    async def publish_status(self, job_id: int, status: str, message: str):
        channel = f"job:{job_id}:status"
        await self._redis.publish(channel, json.dumps({
            "status": status,
            "message": message
        }))

    async def push_download_notification(self, gateway_id: int, notification: Dict[str, Any]):
        queue_key = f"gateway:{gateway_id}:download_notifications"
        await self._redis.lpush(queue_key, json.dumps(notification))
    
    async def get_download_notification(self, gateway_id: int) -> Optional[Dict[str, Any]]:
        queue_key = f"gateway:{gateway_id}:download_notifications"
        try:
            result = await self._redis.brpop(queue_key, timeout=2)
            if result:
                _, notification_data = result
                return json.loads(notification_data)
        except (redis.TimeoutError, asyncio.TimeoutError, Exception) as e:
            if "timeout" in str(e).lower():
                return None
            raise
        return None

redis_client = RedisClient()
