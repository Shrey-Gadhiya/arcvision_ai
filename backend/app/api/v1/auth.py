from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token, decode_access_token
from app.models.user import User, UserRole
from app.models.audit import AuditLog
from app.schemas.all_schemas import Token, LoginRequest, UserResponse, UserCreate

router = APIRouter(prefix="/auth", tags=["Authentication"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed credentials")
    
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalars().first()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account inactive or not found")
    return user

def require_roles(allowed_roles: list[UserRole]):
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required roles: {[r.value for r in allowed_roles]}"
            )
        return current_user
    return role_checker

@router.post("/login", response_model=Token)
async def login(credentials: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == credentials.username.strip()))
    user = result.scalars().first()

    if not user or not verify_password(credentials.password, user.hashed_password):
        # Security audit log for failed login attempts
        try:
            audit = AuditLog(
                username=credentials.username.strip(),
                user_role="UNKNOWN",
                action="LOGIN_FAILED",
                resource_type="USER",
                resource_id="0",
                details_json='{"status": "FAILED", "reason": "Incorrect username or password"}'
            )
            db.add(audit)
            await db.commit()
        except Exception:
            await db.rollback()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    
    if not user.is_active:
        try:
            audit = AuditLog(
                username=user.username,
                user_role=user.role.value,
                action="LOGIN_BLOCKED",
                resource_type="USER",
                resource_id=str(user.id),
                details_json='{"status": "BLOCKED", "reason": "Account is deactivated"}'
            )
            db.add(audit)
            await db.commit()
        except Exception:
            await db.rollback()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account is deactivated. Contact Tactical Administrator.")

    try:
        user.last_login = datetime.now(timezone.utc)
        audit = AuditLog(
            username=user.username,
            user_role=user.role.value,
            action="USER_LOGIN",
            resource_type="USER",
            resource_id=str(user.id),
            details_json='{"status": "SUCCESS"}'
        )
        db.add(audit)
        await db.commit()
    except Exception:
        await db.rollback()

    token = create_access_token(subject=user.username, role=user.role.value)
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role.value,
        "username": user.username
    }

@router.post("/token", response_model=Token)
async def token_login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == form_data.username.strip()))
    user = result.scalars().first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        try:
            audit = AuditLog(
                username=form_data.username.strip(),
                user_role="UNKNOWN",
                action="LOGIN_FAILED",
                resource_type="USER",
                resource_id="0",
                details_json='{"status": "FAILED", "reason": "Incorrect username or password via OAuth2 form"}'
            )
            db.add(audit)
            await db.commit()
        except Exception:
            await db.rollback()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account is deactivated")

    token = create_access_token(subject=user.username, role=user.role.value)
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role.value,
        "username": user.username
    }

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Returns validated tactical profile of the currently authenticated operator."""
    return current_user

@router.get("/verify")
async def verify_auth_token(current_user: User = Depends(get_current_user)):
    """Validates session token integrity and returns current operator authorization tier."""
    return {
        "authenticated": True,
        "username": current_user.username,
        "role": current_user.role.value,
        "full_name": current_user.full_name
    }

@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Logs tactical session termination."""
    try:
        audit = AuditLog(
            username=current_user.username,
            user_role=current_user.role.value,
            action="USER_LOGOUT",
            resource_type="USER",
            resource_id=str(current_user.id),
            details_json='{"status": "SESSION_TERMINATED"}'
        )
        db.add(audit)
        await db.commit()
    except Exception:
        await db.rollback()
    return {"status": "SUCCESS", "message": "Tactical session terminated securely."}

