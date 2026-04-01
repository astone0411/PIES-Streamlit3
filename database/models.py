"""
SQLAlchemy models for the LIMS application.
"""

from sqlalchemy import (
    create_engine, Column, Integer, String, DateTime,
    Boolean, Text, ForeignKey, Enum
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime
import enum
import os

Base = declarative_base()

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TestResult(str, enum.Enum):
    DETECTED = "Detected"
    NOT_DETECTED = "Not Detected"
    INCONCLUSIVE = "Inconclusive"
    PENDING = "Pending"

class Sex(str, enum.Enum):
    MALE = "Male"
    FEMALE = "Female"
    UNKNOWN = "Unknown"

class QCStatus(str, enum.Enum):
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class User(Base):
    """Lab staff who can enter data and sign off on QC."""
    __tablename__ = "users"

    id           = Column(Integer, primary_key=True)
    username     = Column(String(64), unique=True, nullable=False)
    display_name = Column(String(128), nullable=False)
    password_hash = Column(String(256), nullable=False)
    role         = Column(String(32), default="technician")   # technician | supervisor
    is_active    = Column(Boolean, default=True)
    created_at   = Column(DateTime, default=datetime.utcnow)

    # Relationships
    audit_logs   = relationship("AuditLog", back_populates="user")
    qc_signoffs  = relationship("QCRecord", back_populates="signed_by_user")


class Patient(Base):
    """Demographic data pulled from the source system."""
    __tablename__ = "patients"

    id              = Column(Integer, primary_key=True)
    external_id     = Column(String(64), unique=True, nullable=False)   # ID from source system
    first_name      = Column(String(128), nullable=False)
    last_name       = Column(String(128), nullable=False)
    date_of_birth   = Column(String(10), nullable=False)                # ISO: YYYY-MM-DD
    sex             = Column(Enum(Sex), default=Sex.UNKNOWN)
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    specimens       = relationship("Specimen", back_populates="patient")


class Specimen(Base):
    """
    A single test encounter for a patient.
    Combines the imported result with supplemental lab data.
    """
    __tablename__ = "specimens"

    id                   = Column(Integer, primary_key=True)
    accession_number     = Column(String(64), unique=True, nullable=False)
    patient_id           = Column(Integer, ForeignKey("patients.id"), nullable=False)

    # --- Data from source system ---
    source_result        = Column(Enum(TestResult), default=TestResult.PENDING)
    collected_at         = Column(DateTime, nullable=True)
    received_at          = Column(DateTime, nullable=True)

    # --- Supplemental data (entered in this app) ---
    diagnosis            = Column(String(256), nullable=True)
    indication_for_test  = Column(Text, nullable=True)
    supplemental_result  = Column(Enum(TestResult), default=TestResult.PENDING)
    supplemental_notes   = Column(Text, nullable=True)
    entered_by_id        = Column(Integer, ForeignKey("users.id"), nullable=True)
    entered_at           = Column(DateTime, nullable=True)

    # --- Status ---
    is_verified          = Column(Boolean, default=False)
    created_at           = Column(DateTime, default=datetime.utcnow)
    updated_at           = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    patient              = relationship("Patient", back_populates="specimens")
    entered_by           = relationship("User", foreign_keys=[entered_by_id])
    qc_records           = relationship("QCRecord", back_populates="specimen")
    audit_logs           = relationship("AuditLog", back_populates="specimen")


class QCRecord(Base):
    """QC sign-off record for a specimen."""
    __tablename__ = "qc_records"

    id              = Column(Integer, primary_key=True)
    specimen_id     = Column(Integer, ForeignKey("specimens.id"), nullable=False)
    signed_by_id    = Column(Integer, ForeignKey("users.id"), nullable=False)
    status          = Column(Enum(QCStatus), default=QCStatus.PENDING)
    notes           = Column(Text, nullable=True)
    signed_at       = Column(DateTime, default=datetime.utcnow)

    # Relationships
    specimen        = relationship("Specimen", back_populates="qc_records")
    signed_by_user  = relationship("User", back_populates="qc_signoffs")


class AuditLog(Base):
    """Immutable record of every data change."""
    __tablename__ = "audit_logs"

    id          = Column(Integer, primary_key=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=False)
    specimen_id = Column(Integer, ForeignKey("specimens.id"), nullable=True)
    action      = Column(String(128), nullable=False)   # e.g. "specimen.create", "qc.approve"
    detail      = Column(Text, nullable=True)            # JSON-serialised diff
    timestamp   = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user        = relationship("User", back_populates="audit_logs")
    specimen    = relationship("Specimen", back_populates="audit_logs")


# ---------------------------------------------------------------------------
# DB initialisation helper
# ---------------------------------------------------------------------------

def get_engine(db_url: str | None = None):
    url = db_url or os.environ.get("DATABASE_URL", "sqlite:///lims.db")
    # SQLite needs check_same_thread=False for Streamlit
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)


def init_db(engine=None):
    """Create all tables and seed a default admin user if none exist."""
    from database.seed import seed_default_users
    if engine is None:
        engine = get_engine()
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with Session() as session:
        seed_default_users(session)
    return engine


def get_session(engine=None):
    if engine is None:
        engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()
