import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.core.database import Base

class CaseStatus(str, enum.Enum):
    OPEN = "OPEN"
    UNDER_INVESTIGATION = "UNDER_INVESTIGATION"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"

class CasePriority(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class InvestigationCase(Base):
    __tablename__ = "investigation_cases"

    id = Column(Integer, primary_key=True, index=True)
    case_number = Column(String(50), unique=True, index=True, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(SQLEnum(CaseStatus), default=CaseStatus.OPEN, nullable=False, index=True)
    priority = Column(SQLEnum(CasePriority), default=CasePriority.MEDIUM, nullable=False, index=True)
    lead_investigator = Column(String(100), default="Lead Investigator", nullable=False)
    hypothesis = Column(Text, nullable=True)
    tags_json = Column(Text, default="[]")
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    closed_at = Column(DateTime(timezone=True), nullable=True)

    findings = relationship("CaseFinding", back_populates="case", cascade="all, delete-orphan", order_by="CaseFinding.timestamp.asc()")

class CaseFinding(Base):
    __tablename__ = "case_findings"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("investigation_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    item_type = Column(String(50), nullable=False)  # "INCIDENT", "DETECTION", "GLOBAL_TRACK", "ANPR", "FACE", "EVIDENCE", "RECORDING", "SNAPSHOT", "NOTE"
    reference_id = Column(String(100), nullable=True)
    camera_id = Column(Integer, nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    notes = Column(Text, nullable=True)
    metadata_json = Column(Text, default="{}")
    thumbnail_url = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    case = relationship("InvestigationCase", back_populates="findings")
