import redis.asyncio as redis_async
import redis  # Client synchrone pour Celery
import json
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from src.users.schema import UtilisateurRead
import logging
from src.config import Config

logger = logging.getLogger("redis_cache")
logger.setLevel(logging.INFO)

# --- Constantes ---
USER_PREFIX = "user:"
USERS_ALL_KEY = "users:all"
TOKEN_BLOCKLIST_PREFIX = "token:blocklist:"
JTI_EXPIRY = 3600  # 1h
DEFAULT_EXPIRE = 300  # 5 min pour user cache

# --- Redis clients ---
# Client asynchrone pour FastAPI/async code
r = redis_async.from_url(
    Config.REDIS_URL,
    decode_responses=True
)

# Client synchrone pour Celery (important: Celery n'aime pas les coroutines)
r_sync = redis.from_url(
    Config.REDIS_URL,
    decode_responses=True
)

# --- Helper ---
def serialize(obj):
    if isinstance(obj, (UUID, datetime)):
        return str(obj)
    raise TypeError(f"Type {type(obj)} not serializable")

# --- User cache ---
async def get_user_cache(user_id: UUID) -> Optional[dict]:
    try:
        data = await r.get(f"{USER_PREFIX}{user_id}")
        if data:
            return json.loads(data)
    except Exception as e:
        logger.warning(f"Redis get_user_cache failed for {user_id}: {e}")
    return None

async def set_user_cache(user: UtilisateurRead, expire: int = DEFAULT_EXPIRE):
    try:
        await r.set(
            f"{USER_PREFIX}{user.id}",
            json.dumps(user.model_dump(), default=serialize),
            ex=expire
        )
    except Exception as e:
        logger.warning(f"Redis set_user_cache failed for {user.id}: {e}")

# --- All users cache ---
async def get_all_users_cache() -> Optional[List[dict]]:
    try:
        data = await r.get(USERS_ALL_KEY)
        if data:
            return json.loads(data)
    except Exception as e:
        logger.warning(f"Redis get_all_users_cache failed: {e}")
    return None

async def set_all_users_cache(users: List[UtilisateurRead], expire: int = DEFAULT_EXPIRE):
    try:
        users_dict = [u.model_dump() for u in users]
        await r.set(
            USERS_ALL_KEY,
            json.dumps(users_dict, default=serialize),
            ex=expire
        )
    except Exception as e:
        logger.warning(f"Redis set_all_users_cache failed: {e}")

# --- Invalidate cache ---
async def invalidate_user_cache(user_id: Optional[UUID] = None):
    try:
        if user_id:
            await r.delete(f"{USER_PREFIX}{user_id}")
        else:
            await r.delete(USERS_ALL_KEY)
    except Exception as e:
        logger.warning(f"Redis invalidate_user_cache failed for {user_id}: {e}")

async def invalidate_all_users_cache():
    try:
        await r.delete(USERS_ALL_KEY)
    except Exception as e:
        logger.warning(f"Redis invalidate_all_users_cache failed: {e}")

# --- Token blocklist ---
async def add_jti_to_blocklist(jti: str, expiry: int = JTI_EXPIRY) -> bool:
    try:
        # NX=True → ne pas écraser si déjà présent
        await r.set(f"{TOKEN_BLOCKLIST_PREFIX}{jti}", "revoked", ex=expiry, nx=True)
        return True
    except Exception as e:
        logger.warning(f"Redis add_jti_to_blocklist failed for {jti}: {e}")
        return False

async def is_jti_in_blocklist(jti: str) -> bool:
    try:
        exists = await r.exists(f"{TOKEN_BLOCKLIST_PREFIX}{jti}")
        return exists > 0
    except Exception as e:
        logger.debug(f"Redis check failed for {jti}: {e}")
        # fallback : on considère le token comme valide si Redis down
        return False


