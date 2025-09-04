"""Job execution engine with different job types."""

import json
import time
import asyncio
import random
import requests
from typing import Dict, Any, Optional
import structlog
from src.models import JobStatus

logger = structlog.get_logger()


class JobExecutor:
    """Executes different types of jobs."""
    
    def __init__(self):
        """Initialize the job executor."""
        self.job_handlers = {
            "sleep": self._execute_sleep_job,
            "math": self._execute_math_job,
            "http_request": self._execute_http_job,
            "echo": self._execute_echo_job,
            "random_failure": self._execute_random_failure_job,
        }
    
    async def execute_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a job based on its type."""
        job_type = job_data.get("job_type", "echo")
        payload = job_data.get("payload", "{}")
        
        try:
            # Parse payload
            if isinstance(payload, str):
                try:
                    payload_data = json.loads(payload)
                except json.JSONDecodeError:
                    payload_data = {"data": payload}
            else:
                payload_data = payload
            
            # Get handler for job type
            handler = self.job_handlers.get(job_type, self._execute_echo_job)
            
            # Execute job
            start_time = time.time()
            result = await handler(payload_data)
            execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            logger.info("Job executed successfully", 
                       job_id=job_data.get("id"), 
                       job_type=job_type,
                       execution_time_ms=execution_time)
            
            return {
                "status": JobStatus.COMPLETED,
                "result": json.dumps(result),
                "execution_time_ms": int(execution_time),
                "error_message": None
            }
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error("Job execution failed", 
                        job_id=job_data.get("id"), 
                        job_type=job_type,
                        error=str(e),
                        execution_time_ms=execution_time)
            
            return {
                "status": JobStatus.FAILED,
                "result": None,
                "execution_time_ms": int(execution_time),
                "error_message": str(e)
            }
    
    async def _execute_sleep_job(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a sleep job."""
        duration = payload.get("duration", 1)
        await asyncio.sleep(duration)
        return {"message": f"Slept for {duration} seconds", "duration": duration}
    
    async def _execute_math_job(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a math computation job."""
        operation = payload.get("operation", "add")
        a = payload.get("a", 0)
        b = payload.get("b", 0)
        
        if operation == "add":
            result = a + b
        elif operation == "subtract":
            result = a - b
        elif operation == "multiply":
            result = a * b
        elif operation == "divide":
            if b == 0:
                raise ValueError("Division by zero")
            result = a / b
        else:
            raise ValueError(f"Unknown operation: {operation}")
        
        return {
            "operation": operation,
            "a": a,
            "b": b,
            "result": result
        }
    
    async def _execute_http_job(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an HTTP request job."""
        url = payload.get("url", "https://httpbin.org/get")
        method = payload.get("method", "GET").upper()
        headers = payload.get("headers", {})
        data = payload.get("data", None)
        
        # Simulate async HTTP request
        await asyncio.sleep(0.1)  # Simulate network delay
        
        try:
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=10)
            elif method == "POST":
                response = requests.post(url, json=data, headers=headers, timeout=10)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            return {
                "url": url,
                "method": method,
                "status_code": response.status_code,
                "response": response.text[:1000]  # Limit response size
            }
        except requests.RequestException as e:
            raise Exception(f"HTTP request failed: {str(e)}")
    
    async def _execute_echo_job(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an echo job (returns the payload)."""
        return {
            "message": "Echo job completed",
            "echoed_data": payload
        }
    
    async def _execute_random_failure_job(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a job that randomly fails (for testing)."""
        failure_rate = payload.get("failure_rate", 0.3)
        
        if random.random() < failure_rate:
            raise Exception("Random failure for testing purposes")
        
        return {
            "message": "Random failure job completed successfully",
            "failure_rate": failure_rate
        }
