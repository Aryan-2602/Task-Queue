"""Pydantic schemas for API request/response models."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from src.models import JobStatus


class JobSubmitRequest(BaseModel):
    """Request schema for job submission."""
    job_type: str = Field(..., description="Type of job to execute")
    payload: str = Field(..., description="Job payload/data")
    priority: int = Field(default=0, description="Job priority (higher = more priority)")
    max_retries: int = Field(default=3, description="Maximum number of retries")
    timeout_seconds: int = Field(default=300, description="Job timeout in seconds")


class JobSubmitResponse(BaseModel):
    """Response schema for job submission."""
    success: bool
    message: str
    job_id: str


class JobStatusResponse(BaseModel):
    """Response schema for job status."""
    id: str
    job_type: str
    payload: str
    status: JobStatus
    priority: int
    max_retries: int
    retry_count: int
    timeout_seconds: int
    created_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    result: Optional[str]
    error_message: Optional[str]
    worker_id: Optional[str]
    execution_time_ms: Optional[int]


class JobListRequest(BaseModel):
    """Request schema for listing jobs."""
    status_filter: Optional[JobStatus] = None
    limit: int = Field(default=100, le=1000)
    offset: int = Field(default=0, ge=0)


class JobListResponse(BaseModel):
    """Response schema for job listing."""
    jobs: List[JobStatusResponse]
    total_count: int


class HealthResponse(BaseModel):
    """Response schema for health check."""
    status: str
    redis_connected: bool
    database_connected: bool
    queue_size: int
    dead_letter_size: int


class MetricsResponse(BaseModel):
    """Response schema for metrics."""
    jobs_queued: int
    jobs_running: int
    jobs_completed: int
    jobs_failed: int
    jobs_dead_letter: int
    average_execution_time_ms: float
    throughput_per_minute: float
