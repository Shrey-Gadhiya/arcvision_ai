import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_password_hash
from app.models.user import User, UserRole

logger = logging.getLogger("arc_vision.demo")
router = APIRouter(prefix="/demo", tags=["SIH26187 Demo Orchestration"])


@router.post("/init-sih26187")
async def initialize_sih_demo(db: AsyncSession = Depends(get_db)):
    """
    Creates the four default user accounts only.
    No cameras, zones, rules, or watchlists are seeded —
    everything is added manually by the operator.
    """
    users_to_seed = [
        ("admin",       "admin@ssb.gov.in",        "admin123",       "Administrator",                  UserRole.ADMIN),
        ("commander",   "commander@ssb.gov.in",    "command123",     "Sector Commander",               UserRole.COMMANDER),
        ("operator",    "operator@ssb.gov.in",     "operator123",    "Surveillance Operator",          UserRole.OPERATOR),
        ("investigator","investigator@ssb.gov.in", "investigate123", "Forensic Investigator",          UserRole.INVESTIGATOR),
    ]

    created = []
    for uname, email, pwd, fname, role in users_to_seed:
        existing = await db.execute(select(User).where(User.username == uname))
        if not existing.scalars().first():
            user = User(
                username=uname,
                email=email,
                hashed_password=get_password_hash(pwd),
                full_name=fname,
                role=role,
            )
            db.add(user)
            created.append(uname)

    await db.commit()

    return {
        "status": "SUCCESS",
        "message": "User accounts ready. System is clean — add cameras and data manually.",
        "users_created": created,
    }
