from datetime import datetime, timedelta, timezone
from typing import Optional, Any
import bcrypt
from jose import jwt
from app.core.config import settings

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def create_access_token(subject: str | Any, role: str, expires_delta: Optional[timedelta] = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "role": role,
        "iat": datetime.now(timezone.utc)
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except Exception:
        return None

def mask_rtsp_url(url: str) -> str:
    """Safely masks user:password credentials in RTSP and HTTP stream URLs."""
    if not url or "@" not in url:
        return url
    import re
    # Match schema://user:pass@host:port/path
    return re.sub(r'(://[^:]+:)([^@]+)(@)', r'\1******\3', url)

def mask_secret(secret: Optional[str]) -> str:
    """Masks authorization secrets/tokens for safe API serialization."""
    if not secret:
        return ""
    if len(secret) <= 6:
        return "******"
    return f"{secret[:3]}******{secret[-3:]}"
