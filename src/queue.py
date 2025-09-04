"""Redis-based job queue implementation."""

import json
import time
import redis
from typing import Optional, Dict, Any, List
from src.config import settings
from src.models import Job, JobStatus
import structlog

logger = structlog.get_logger()


class RedisQueue:
    """Redis-based job queue with fault tolerance."""
    
    def __init__(self):
        """Initialize Redis connection."""
        self.redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password,
            decode_responses=True
        )
        self.queue_name = settings.queue_name
        self.dead_letter_queue = settings.dead_letter_queue
        self.retry_queue = settings.retry_queue
        
    def enqueue_job(self, job: Job) -> bool:
        """Enqueue a job to the Redis queue."""
        try:
            job_data = {
                "id": job.id,
                "job_type": job.job_type,
                "payload": job.payload,
                "priority": job.priority,
                "max_retries": job.max_retries,
                "timeout_seconds": job.timeout_seconds,
                "created_at": time.time()
            }
            
            # Use priority-based queuing
            score = job.priority
            self.redis_client.zadd(self.queue_name, {json.dumps(job_data): score})
            
            logger.info("Job enqueued", job_id=job.id, priority=job.priority)
            return True
            
        except Exception as e:
            logger.error("Failed to enqueue job", job_id=job.id, error=str(e))
            return False
    
    def dequeue_job(self, timeout: int = 0) -> Optional[Dict[str, Any]]:
        """Dequeue a job from the Redis queue (highest priority first)."""
        try:
            # Get highest priority job
            result = self.redis_client.bzpopmax(self.queue_name, timeout=timeout)
            if result:
                queue_name, job_data_str, score = result
                job_data = json.loads(job_data_str)
                logger.info("Job dequeued", job_id=job_data["id"], priority=score)
                return job_data
            return None
            
        except Exception as e:
            logger.error("Failed to dequeue job", error=str(e))
            return None
    
    def enqueue_retry(self, job_data: Dict[str, Any], delay_seconds: int = 0) -> bool:
        """Enqueue a job for retry with optional delay."""
        try:
            if delay_seconds > 0:
                # Use delayed execution
                execute_at = time.time() + delay_seconds
                self.redis_client.zadd(self.retry_queue, {json.dumps(job_data): execute_at})
            else:
                # Immediate retry
                self.enqueue_job(Job(**job_data))
            
            logger.info("Job scheduled for retry", job_id=job_data["id"], delay=delay_seconds)
            return True
            
        except Exception as e:
            logger.error("Failed to enqueue retry", job_id=job_data["id"], error=str(e))
            return False
    
    def enqueue_dead_letter(self, job_data: Dict[str, Any], error_message: str) -> bool:
        """Move job to dead letter queue."""
        try:
            job_data["error_message"] = error_message
            job_data["status"] = JobStatus.DEAD_LETTER
            self.redis_client.lpush(self.dead_letter_queue, json.dumps(job_data))
            
            logger.warning("Job moved to dead letter queue", 
                          job_id=job_data["id"], error=error_message)
            return True
            
        except Exception as e:
            logger.error("Failed to enqueue dead letter", job_id=job_data["id"], error=str(e))
            return False
    
    def process_retry_queue(self) -> List[Dict[str, Any]]:
        """Process delayed retry jobs that are ready to execute."""
        try:
            current_time = time.time()
            ready_jobs = []
            
            # Get jobs ready for retry
            retry_jobs = self.redis_client.zrangebyscore(
                self.retry_queue, 0, current_time, withscores=True
            )
            
            for job_data_str, score in retry_jobs:
                job_data = json.loads(job_data_str)
                ready_jobs.append(job_data)
                
                # Remove from retry queue and add to main queue
                self.redis_client.zrem(self.retry_queue, job_data_str)
                self.enqueue_job(Job(**job_data))
            
            if ready_jobs:
                logger.info("Processed retry jobs", count=len(ready_jobs))
            
            return ready_jobs
            
        except Exception as e:
            logger.error("Failed to process retry queue", error=str(e))
            return []
    
    def get_queue_size(self) -> int:
        """Get current queue size."""
        try:
            return self.redis_client.zcard(self.queue_name)
        except Exception as e:
            logger.error("Failed to get queue size", error=str(e))
            return 0
    
    def get_dead_letter_size(self) -> int:
        """Get dead letter queue size."""
        try:
            return self.redis_client.llen(self.dead_letter_queue)
        except Exception as e:
            logger.error("Failed to get dead letter queue size", error=str(e))
            return 0
    
    def health_check(self) -> bool:
        """Check Redis connection health."""
        try:
            self.redis_client.ping()
            return True
        except Exception as e:
            logger.error("Redis health check failed", error=str(e))
            return False
