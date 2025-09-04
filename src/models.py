"""Database models for job tracking."""

from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime
from enum import Enum
import uuid

Base = declarative_base()


class JobStatus(str, Enum):
    """Job status enumeration."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    DEAD_LETTER = "dead_letter"


class Job(Base):
    """Job model for tracking job execution."""
    
    __tablename__ = "jobs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_type = Column(String, nullable=False)
    payload = Column(Text, nullable=False)
    status = Column(String, nullable=False, default=JobStatus.QUEUED)
    priority = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    retry_count = Column(Integer, default=0)
    timeout_seconds = Column(Integer, default=300)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Results
    result = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Metadata
    worker_id = Column(String, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)
    
    def to_dict(self):
        """Convert job to dictionary."""
        return {
            "id": self.id,
            "job_type": self.job_type,
            "payload": self.payload,
            "status": self.status,
            "priority": self.priority,
            "max_retries": self.max_retries,
            "retry_count": self.retry_count,
            "timeout_seconds": self.timeout_seconds,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
            "error_message": self.error_message,
            "worker_id": self.worker_id,
            "execution_time_ms": self.execution_time_ms,
        }
