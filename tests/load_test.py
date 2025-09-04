"""Load testing script for the job scheduler using Locust."""

import json
import random
import time
from locust import HttpUser, task, between
import structlog

logger = structlog.get_logger()


class JobSchedulerUser(HttpUser):
    """Locust user class for load testing the job scheduler."""
    
    wait_time = between(0.1, 1.0)  # Wait between 0.1 and 1 second between tasks
    
    def on_start(self):
        """Called when a user starts."""
        logger.info("User started load testing")
    
    @task(3)
    def submit_sleep_job(self):
        """Submit a sleep job (most common)."""
        payload = {
            "job_type": "sleep",
            "payload": json.dumps({"duration": random.uniform(0.1, 2.0)}),
            "priority": random.randint(0, 10),
            "max_retries": 3,
            "timeout_seconds": 30
        }
        
        with self.client.post("/jobs", json=payload, catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    response.success()
                else:
                    response.failure(f"Job submission failed: {data.get('message')}")
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(2)
    def submit_math_job(self):
        """Submit a math computation job."""
        operations = ["add", "subtract", "multiply", "divide"]
        operation = random.choice(operations)
        
        payload = {
            "job_type": "math",
            "payload": json.dumps({
                "operation": operation,
                "a": random.randint(1, 100),
                "b": random.randint(1, 100)
            }),
            "priority": random.randint(0, 5),
            "max_retries": 2,
            "timeout_seconds": 10
        }
        
        with self.client.post("/jobs", json=payload, catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    response.success()
                else:
                    response.failure(f"Job submission failed: {data.get('message')}")
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(1)
    def submit_http_job(self):
        """Submit an HTTP request job."""
        urls = [
            "https://httpbin.org/get",
            "https://httpbin.org/post",
            "https://jsonplaceholder.typicode.com/posts/1"
        ]
        
        payload = {
            "job_type": "http_request",
            "payload": json.dumps({
                "url": random.choice(urls),
                "method": "GET"
            }),
            "priority": random.randint(0, 3),
            "max_retries": 2,
            "timeout_seconds": 15
        }
        
        with self.client.post("/jobs", json=payload, catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    response.success()
                else:
                    response.failure(f"Job submission failed: {data.get('message')}")
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(1)
    def submit_echo_job(self):
        """Submit an echo job."""
        payload = {
            "job_type": "echo",
            "payload": json.dumps({"message": f"Load test message {time.time()}"}),
            "priority": 0,
            "max_retries": 1,
            "timeout_seconds": 5
        }
        
        with self.client.post("/jobs", json=payload, catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    response.success()
                else:
                    response.failure(f"Job submission failed: {data.get('message')}")
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(1)
    def submit_random_failure_job(self):
        """Submit a job that randomly fails (for testing retry logic)."""
        payload = {
            "job_type": "random_failure",
            "payload": json.dumps({"failure_rate": 0.3}),
            "priority": 0,
            "max_retries": 3,
            "timeout_seconds": 10
        }
        
        with self.client.post("/jobs", json=payload, catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    response.success()
                else:
                    response.failure(f"Job submission failed: {data.get('message')}")
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(2)
    def get_job_status(self):
        """Get job status (this will often fail since we don't track job IDs)."""
        # Generate a random job ID - most will not exist
        job_id = f"job-{random.randint(1000, 9999)}"
        
        with self.client.get(f"/jobs/{job_id}", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                response.success()  # Expected for random job IDs
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(1)
    def list_jobs(self):
        """List jobs."""
        with self.client.get("/jobs?limit=10", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(1)
    def get_health(self):
        """Get health status."""
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(1)
    def get_stats(self):
        """Get job statistics."""
        with self.client.get("/stats", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")


class HighLoadUser(HttpUser):
    """High load user for stress testing."""
    
    wait_time = between(0.01, 0.1)  # Very short wait times
    
    @task(10)
    def submit_quick_job(self):
        """Submit quick echo jobs."""
        payload = {
            "job_type": "echo",
            "payload": json.dumps({"message": f"High load test {time.time()}"}),
            "priority": random.randint(0, 10),
            "max_retries": 1,
            "timeout_seconds": 1
        }
        
        with self.client.post("/jobs", json=payload, catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    response.success()
                else:
                    response.failure(f"Job submission failed: {data.get('message')}")
            else:
                response.failure(f"HTTP {response.status_code}")


# Locust configuration
class WebsiteUser(JobSchedulerUser):
    """Main user class for the load test."""
    pass
