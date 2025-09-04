"""Prometheus metrics collection for job scheduler."""

from prometheus_client import Counter, Histogram, Gauge, Info, CollectorRegistry, generate_latest
from typing import Dict, Any
import structlog

logger = structlog.get_logger()


class MetricsCollector:
    """Collects and exposes Prometheus metrics for the job scheduler."""
    
    def __init__(self):
        """Initialize metrics collector."""
        self.registry = CollectorRegistry()
        
        # Job metrics
        self.jobs_submitted = Counter(
            'jobs_submitted_total',
            'Total number of jobs submitted',
            ['job_type'],
            registry=self.registry
        )
        
        self.jobs_completed = Counter(
            'jobs_completed_total',
            'Total number of jobs completed',
            ['job_type', 'status'],
            registry=self.registry
        )
        
        self.job_execution_time = Histogram(
            'job_execution_seconds',
            'Job execution time in seconds',
            ['job_type'],
            buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, float('inf')],
            registry=self.registry
        )
        
        self.job_retries = Counter(
            'job_retries_total',
            'Total number of job retries',
            ['job_type'],
            registry=self.registry
        )
        
        # Queue metrics
        self.queue_size = Gauge(
            'queue_size',
            'Current number of jobs in queue',
            registry=self.registry
        )
        
        self.dead_letter_size = Gauge(
            'dead_letter_queue_size',
            'Current number of jobs in dead letter queue',
            registry=self.registry
        )
        
        # Worker metrics
        self.active_workers = Gauge(
            'active_workers',
            'Number of active workers',
            registry=self.registry
        )
        
        self.worker_jobs_processed = Counter(
            'worker_jobs_processed_total',
            'Total jobs processed by workers',
            ['worker_id'],
            registry=self.registry
        )
        
        # System metrics
        self.system_info = Info(
            'system_info',
            'System information',
            registry=self.registry
        )
        
        # Initialize system info
        self.system_info.info({
            'version': '1.0.0',
            'component': 'job_scheduler'
        })
    
    def record_job_submitted(self, job_type: str):
        """Record a job submission."""
        self.jobs_submitted.labels(job_type=job_type).inc()
        logger.debug("Job submission recorded", job_type=job_type)
    
    def record_job_completed(self, job_type: str, status: str, execution_time: float):
        """Record a job completion."""
        self.jobs_completed.labels(job_type=job_type, status=status).inc()
        self.job_execution_time.labels(job_type=job_type).observe(execution_time)
        logger.debug("Job completion recorded", 
                    job_type=job_type, 
                    status=status, 
                    execution_time=execution_time)
    
    def record_job_retry(self, job_type: str):
        """Record a job retry."""
        self.job_retries.labels(job_type=job_type).inc()
        logger.debug("Job retry recorded", job_type=job_type)
    
    def update_queue_size(self, size: int):
        """Update queue size metric."""
        self.queue_size.set(size)
    
    def update_dead_letter_size(self, size: int):
        """Update dead letter queue size metric."""
        self.dead_letter_size.set(size)
    
    def update_active_workers(self, count: int):
        """Update active workers count."""
        self.active_workers.set(count)
    
    def record_worker_job_processed(self, worker_id: str):
        """Record a job processed by a worker."""
        self.worker_jobs_processed.labels(worker_id=worker_id).inc()
    
    def get_metrics(self) -> str:
        """Get metrics in Prometheus format."""
        return generate_latest(self.registry).decode('utf-8')
    
    def get_metrics_dict(self) -> Dict[str, Any]:
        """Get metrics as a dictionary for JSON responses."""
        # This is a simplified version - in production you might want to
        # parse the Prometheus format or use a different approach
        return {
            "jobs_submitted": dict(self.jobs_submitted._metrics),
            "jobs_completed": dict(self.jobs_completed._metrics),
            "queue_size": self.queue_size._value._value,
            "dead_letter_size": self.dead_letter_size._value._value,
            "active_workers": self.active_workers._value._value,
        }


# Global metrics collector instance
metrics = MetricsCollector()
