from redis.asyncio import Redis
from config import settings


redis_instance = Redis(host=settings.redis.REDIS_HOST, decode_responses=True)
