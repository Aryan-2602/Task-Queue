"""REST API endpoints for job scheduler."""

from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import structlog
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

from src.database import get_db, create_tables
from src.schemas import (
    JobSubmitRequest, JobSubmitResponse, JobStatusResponse, 
    JobListRequest, JobListResponse, HealthResponse, MetricsResponse
)
from src.models import Job, JobStatus
from src.queue import RedisQueue
from src.config import settings

logger = structlog.get_logger()

# Prometheus metrics
job_submit_counter = Counter('jobs_submitted_total', 'Total jobs submitted', ['job_type'])
job_completion_counter = Counter('jobs_completed_total', 'Total jobs completed', ['status'])
job_execution_time = Histogram('job_execution_seconds', 'Job execution time', ['job_type'])

app = FastAPI(
    title="Distributed Job Scheduler",
    description="A fault-tolerant distributed job scheduling system",
    version="1.0.0"
)

# Initialize Redis queue
redis_queue = RedisQueue()


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    create_tables()
    logger.info("REST API started", port=settings.api_port)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    try:
        redis_connected = redis_queue.health_check()
        queue_size = redis_queue.get_queue_size()
        dead_letter_size = redis_queue.get_dead_letter_size()
        
        return HealthResponse(
            status="healthy" if redis_connected else "unhealthy",
            redis_connected=redis_connected,
            database_connected=True,  # TODO: Add actual DB health check
            queue_size=queue_size,
            dead_letter_size=dead_letter_size
        )
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service unhealthy"
        )


@app.post("/jobs", response_model=JobSubmitResponse)
async def submit_job(
    job_request: JobSubmitRequest,
    db: Session = Depends(get_db)
):
    """Submit a new job for execution."""
    try:
        # Create job record
        job = Job(
            job_type=job_request.job_type,
            payload=job_request.payload,
            priority=job_request.priority,
            max_retries=job_request.max_retries,
            timeout_seconds=job_request.timeout_seconds
        )
        
        # Save to database
        db.add(job)
        db.commit()
        db.refresh(job)
        
        # Enqueue job
        success = redis_queue.enqueue_job(job)
        
        if not success:
            # Update job status to failed
            job.status = JobStatus.FAILED
            job.error_message = "Failed to enqueue job"
            db.commit()
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to enqueue job"
            )
        
        # Update metrics
        job_submit_counter.labels(job_type=job.job_type).inc()
        
        logger.info("Job submitted successfully", job_id=job.id, job_type=job.job_type)
        
        return JobSubmitResponse(
            success=True,
            message="Job submitted successfully",
            job_id=job.id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to submit job", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """Get job status by ID."""
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        return JobStatusResponse(**job.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get job status", job_id=job_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    status_filter: JobStatus = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """List jobs with optional filtering."""
    try:
        query = db.query(Job)
        
        if status_filter:
            query = query.filter(Job.status == status_filter)
        
        total_count = query.count()
        jobs = query.offset(offset).limit(limit).all()
        
        job_responses = [JobStatusResponse(**job.to_dict()) for job in jobs]
        
        return JobListResponse(
            jobs=job_responses,
            total_count=total_count
        )
        
    except Exception as e:
        logger.error("Failed to list jobs", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/stats", response_model=MetricsResponse)
async def get_stats(db: Session = Depends(get_db)):
    """Get job statistics."""
    try:
        # Get job counts by status
        jobs_queued = db.query(Job).filter(Job.status == JobStatus.QUEUED).count()
        jobs_running = db.query(Job).filter(Job.status == JobStatus.RUNNING).count()
        jobs_completed = db.query(Job).filter(Job.status == JobStatus.COMPLETED).count()
        jobs_failed = db.query(Job).filter(Job.status == JobStatus.FAILED).count()
        jobs_dead_letter = db.query(Job).filter(Job.status == JobStatus.DEAD_LETTER).count()
        
        # Calculate average execution time
        completed_jobs = db.query(Job).filter(
            Job.status == JobStatus.COMPLETED,
            Job.execution_time_ms.isnot(None)
        ).all()
        
        avg_execution_time = 0.0
        if completed_jobs:
            total_time = sum(job.execution_time_ms for job in completed_jobs)
            avg_execution_time = total_time / len(completed_jobs)
        
        # TODO: Calculate throughput per minute
        throughput_per_minute = 0.0
        
        return MetricsResponse(
            jobs_queued=jobs_queued,
            jobs_running=jobs_running,
            jobs_completed=jobs_completed,
            jobs_failed=jobs_failed,
            jobs_dead_letter=jobs_dead_letter,
            average_execution_time_ms=avg_execution_time,
            throughput_per_minute=throughput_per_minute
        )
        
    except Exception as e:
        logger.error("Failed to get stats", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)
