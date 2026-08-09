from passlib.context import CryptContext
from datetime import timedelta, datetime, timezone
import jwt
from src.config import Config
import uuid
import logging

logger = logging.getLogger(__name__)

passwd_context = CryptContext(schemes=["bcrypt"])

ACCESS_TOKEN_EXPIRY = timedelta(minutes=15)
REFRESH_TOKEN_EXPIRY = timedelta(days=7)

# PASSWORD HASHING

def generate_passwd_hash(password: str) -> str:
    return passwd_context.hash(password)


def verify_password(password: str, hash: str) -> bool:
    return passwd_context.verify(password, hash)


# JWT SYSTEM

def create_token(user_data: dict, refresh: bool = False, expiry: timedelta | None = None) -> str:
    if expiry is None:
        expiry = REFRESH_TOKEN_EXPIRY if refresh else ACCESS_TOKEN_EXPIRY

    now = datetime.now(timezone.utc)
    payload = {
        "user": user_data,
        "iat": now,
        "exp": now + expiry,
        "jti": str(uuid.uuid4()),
        "refresh": refresh,
    }
    return jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm=Config.JWT_ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(
            token,
            Config.JWT_SECRET_KEY,
            algorithms=[Config.JWT_ALGORITHM],
            options={"require": ["exp", "iat", "jti", "refresh"]},
        )
    except jwt.ExpiredSignatureError:
        logger.debug("token expired")
        return None
    except jwt.PyJWTError as e:
        logger.warning("token rejected: %s", e)
        return None