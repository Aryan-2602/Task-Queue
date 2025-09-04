"""Worker pool implementation for distributed job execution."""

import asyncio
import signal
import time
import uuid
from typing import List, Optional
import structlog
from sqlalchemy.orm import Session

from src.database import get_db_session
from src.models import Job, JobStatus
from src.queue import RedisQueue
from src.config import settings
from .job_executor import JobExecutor

logger = structlog.get_logger()


class Worker:
    """Individual worker that processes jobs from the queue."""
    
    def __init__(self, worker_id: str, queue: RedisQueue):
        """Initialize worker."""
        self.worker_id = worker_id
        self.queue = queue
        self.executor = JobExecutor()
        self.running = False
        self.current_job: Optional[Job] = None
        
    async def start(self):
        """Start the worker."""
        self.running = True
        logger.info("Worker started", worker_id=self.worker_id)
        
        while self.running:
            try:
                # Poll for jobs with timeout
                job_data = self.queue.dequeue_job(timeout=5)
                
                if job_data:
                    await self._process_job(job_data)
                else:
                    # No jobs available, continue polling
                    await asyncio.sleep(0.1)
                    
            except Exception as e:
                logger.error("Worker error", worker_id=self.worker_id, error=str(e))
                await asyncio.sleep(1)  # Brief pause before retrying
    
    async def stop(self):
        """Stop the worker gracefully."""
        self.running = False
        logger.info("Worker stopped", worker_id=self.worker_id)
    
    async def _process_job(self, job_data: dict):
        """Process a single job."""
        job_id = job_data.get("id")
        logger.info("Processing job", worker_id=self.worker_id, job_id=job_id)
        
        # Update job status to running
        db = get_db_session()
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                logger.error("Job not found in database", job_id=job_id)
                return
            
            # Update job status
            job.status = JobStatus.RUNNING
            from datetime import datetime
            job.started_at = datetime.now()
            job.worker_id = self.worker_id
            db.commit()
            
            self.current_job = job
            
            # Execute job
            result = await self.executor.execute_job(job_data)
            
            # Update job with result
            job.status = result["status"]
            job.result = result["result"]
            job.error_message = result["error_message"]
            job.execution_time_ms = result["execution_time_ms"]
            
            if result["status"] == JobStatus.COMPLETED:
                from datetime import datetime
                job.completed_at = datetime.now()
                logger.info("Job completed successfully", 
                           worker_id=self.worker_id, 
                           job_id=job_id,
                           execution_time_ms=result["execution_time_ms"])
            else:
                # Handle failed job
                await self._handle_failed_job(job, job_data)
            
            db.commit()
            
        except Exception as e:
            logger.error("Error processing job", 
                        worker_id=self.worker_id, 
                        job_id=job_id, 
                        error=str(e))
            
            # Mark job as failed
            if job:
                job.status = JobStatus.FAILED
                job.error_message = str(e)
                from datetime import datetime
                job.completed_at = datetime.now()
                db.commit()
                
                # Handle failed job
                await self._handle_failed_job(job, job_data)
        
        finally:
            self.current_job = None
            db.close()
    
    async def _handle_failed_job(self, job: Job, job_data: dict):
        """Handle a failed job with retry logic."""
        retry_count = job.retry_count + 1
        max_retries = job.max_retries
        
        if retry_count < max_retries:
            # Schedule retry with exponential backoff
            delay_seconds = min(2 ** retry_count, 300)  # Max 5 minutes
            job.status = JobStatus.RETRYING
            job.retry_count = retry_count
            
            logger.info("Scheduling job retry", 
                       job_id=job.id, 
                       retry_count=retry_count,
                       delay_seconds=delay_seconds)
            
            # Enqueue for retry
            self.queue.enqueue_retry(job_data, delay_seconds)
        else:
            # Move to dead letter queue
            logger.warning("Job moved to dead letter queue", 
                          job_id=job.id, 
                          retry_count=retry_count)
            
            job.status = JobStatus.DEAD_LETTER
            self.queue.enqueue_dead_letter(job_data, job.error_message)


class WorkerPool:
    """Pool of workers for distributed job processing."""
    
    def __init__(self, pool_size: int = None):
        """Initialize worker pool."""
        self.pool_size = pool_size or settings.worker_pool_size
        self.workers: List[Worker] = []
        self.queue = RedisQueue()
        self.running = False
        
    async def start(self):
        """Start the worker pool."""
        self.running = True
        logger.info("Starting worker pool", pool_size=self.pool_size)
        
        # Create workers
        for i in range(self.pool_size):
            worker_id = f"worker-{uuid.uuid4().hex[:8]}"
            worker = Worker(worker_id, self.queue)
            self.workers.append(worker)
        
        # Start all workers
        tasks = [worker.start() for worker in self.workers]
        
        # Start retry queue processor
        retry_task = asyncio.create_task(self._process_retry_queue())
        
        try:
            await asyncio.gather(*tasks, retry_task)
        except asyncio.CancelledError:
            logger.info("Worker pool tasks cancelled")
    
    async def stop(self):
        """Stop the worker pool gracefully."""
        self.running = False
        logger.info("Stopping worker pool")
        
        # Stop all workers
        for worker in self.workers:
            await worker.stop()
        
        logger.info("Worker pool stopped")
    
    async def _process_retry_queue(self):
        """Process delayed retry jobs."""
        while self.running:
            try:
                # Process retry queue every 10 seconds
                self.queue.process_retry_queue()
                await asyncio.sleep(10)
            except Exception as e:
                logger.error("Error processing retry queue", error=str(e))
                await asyncio.sleep(5)


async def main():
    """Main function to run the worker pool."""
    # Configure logging
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Create and start worker pool
    pool = WorkerPool()
    
    # Handle shutdown signals
    def signal_handler(signum, frame):
        logger.info("Received shutdown signal", signal=signum)
        asyncio.create_task(pool.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await pool.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    finally:
        await pool.stop()


if __name__ == "__main__":
    asyncio.run(main())
