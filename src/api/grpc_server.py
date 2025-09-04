"""gRPC server implementation for job scheduler."""

import grpc
from concurrent import futures
import structlog
from sqlalchemy.orm import Session

from src.database import get_db_session
from src.models import Job, JobStatus
from src.queue import RedisQueue
from src.config import settings
from . import job_scheduler_pb2
from . import job_scheduler_pb2_grpc

logger = structlog.get_logger()


class JobSchedulerServicer(job_scheduler_pb2_grpc.JobSchedulerServiceServicer):
    """gRPC servicer for job scheduler operations."""
    
    def __init__(self):
        """Initialize the servicer."""
        self.redis_queue = RedisQueue()
    
    def SubmitJob(self, request, context):
        """Submit a new job for execution."""
        try:
            # Create job record
            job = Job(
                id=request.job_id or None,  # Use provided ID or generate new one
                job_type=request.job_type,
                payload=request.payload,
                priority=request.priority,
                max_retries=request.max_retries,
                timeout_seconds=request.timeout_seconds
            )
            
            # Save to database
            db = get_db_session()
            try:
                db.add(job)
                db.commit()
                db.refresh(job)
                
                # Enqueue job
                success = self.redis_queue.enqueue_job(job)
                
                if not success:
                    # Update job status to failed
                    job.status = JobStatus.FAILED
                    job.error_message = "Failed to enqueue job"
                    db.commit()
                    
                    return job_scheduler_pb2.SubmitJobResponse(
                        success=False,
                        message="Failed to enqueue job",
                        job_id=job.id
                    )
                
                logger.info("Job submitted via gRPC", job_id=job.id, job_type=job.job_type)
                
                return job_scheduler_pb2.SubmitJobResponse(
                    success=True,
                    message="Job submitted successfully",
                    job_id=job.id
                )
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error("Failed to submit job via gRPC", error=str(e))
            return job_scheduler_pb2.SubmitJobResponse(
                success=False,
                message=f"Internal server error: {str(e)}",
                job_id=""
            )
    
    def GetJobStatus(self, request, context):
        """Get job status by ID."""
        try:
            db = get_db_session()
            try:
                job = db.query(Job).filter(Job.id == request.job_id).first()
                
                if not job:
                    context.set_code(grpc.StatusCode.NOT_FOUND)
                    context.set_details("Job not found")
                    return job_scheduler_pb2.GetJobStatusResponse()
                
                return job_scheduler_pb2.GetJobStatusResponse(
                    job_id=job.id,
                    status=job.status,
                    result=job.result or "",
                    error_message=job.error_message or "",
                    created_at=int(job.created_at.timestamp()) if job.created_at else 0,
                    started_at=int(job.started_at.timestamp()) if job.started_at else 0,
                    completed_at=int(job.completed_at.timestamp()) if job.completed_at else 0,
                    retry_count=job.retry_count
                )
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error("Failed to get job status via gRPC", job_id=request.job_id, error=str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal server error: {str(e)}")
            return job_scheduler_pb2.GetJobStatusResponse()
    
    def ListJobs(self, request, context):
        """List jobs with optional filtering."""
        try:
            db = get_db_session()
            try:
                query = db.query(Job)
                
                if request.status_filter:
                    query = query.filter(Job.status == request.status_filter)
                
                total_count = query.count()
                jobs = query.offset(request.offset).limit(request.limit).all()
                
                job_responses = []
                for job in jobs:
                    job_responses.append(job_scheduler_pb2.GetJobStatusResponse(
                        job_id=job.id,
                        status=job.status,
                        result=job.result or "",
                        error_message=job.error_message or "",
                        created_at=int(job.created_at.timestamp()) if job.created_at else 0,
                        started_at=int(job.started_at.timestamp()) if job.started_at else 0,
                        completed_at=int(job.completed_at.timestamp()) if job.completed_at else 0,
                        retry_count=job.retry_count
                    ))
                
                return job_scheduler_pb2.ListJobsResponse(
                    jobs=job_responses,
                    total_count=total_count
                )
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error("Failed to list jobs via gRPC", error=str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal server error: {str(e)}")
            return job_scheduler_pb2.ListJobsResponse()


def serve():
    """Start the gRPC server."""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    
    # Add the servicer
    job_scheduler_pb2_grpc.add_JobSchedulerServiceServicer_to_server(
        JobSchedulerServicer(), server
    )
    
    # Start server
    listen_addr = f'[::]:{settings.grpc_port}'
    server.add_insecure_port(listen_addr)
    
    logger.info("Starting gRPC server", port=settings.grpc_port)
    server.start()
    
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down gRPC server")
        server.stop(0)


if __name__ == "__main__":
    serve()
