from redis.asyncio import from_url
from src.config import Config

JTI_EXPIRY = 3600

redis_client = from_url(Config.REDIS_URL)

async def add_jti_to_blocklist(jti: str) -> None:
    await redis_client.set(
        name=jti,
        value="",
        ex=JTI_EXPIRY
    )
 
async def token_in_blocklist(jti: str) -> bool:
    jti = await redis_client.get(jti)
    return jti is not None