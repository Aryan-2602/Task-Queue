#!/usr/bin/env python3
"""Script to run all components of the job scheduler."""

import subprocess
import time
import signal
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import structlog

logger = structlog.get_logger()


def run_command(cmd, name):
    """Run a command in a subprocess."""
    logger.info(f"Starting {name}", command=cmd)
    return subprocess.Popen(cmd, shell=True)


def main():
    """Main function to run all components."""
    processes = []
    
    try:
        # Start REST API
        api_process = run_command("python -m src.api.rest", "REST API")
        processes.append(("REST API", api_process))
        
        # Wait a bit for API to start
        time.sleep(2)
        
        # Start gRPC server
        grpc_process = run_command("python -m src.api.grpc_server", "gRPC Server")
        processes.append(("gRPC Server", grpc_process))
        
        # Wait a bit for gRPC to start
        time.sleep(2)
        
        # Start worker pool
        worker_process = run_command("python -m src.workers.worker_pool", "Worker Pool")
        processes.append(("Worker Pool", worker_process))
        
        logger.info("All components started. Press Ctrl+C to stop.")
        
        # Wait for all processes
        while True:
            time.sleep(1)
            
            # Check if any process died
            for name, process in processes:
                if process.poll() is not None:
                    logger.error(f"{name} process died", returncode=process.returncode)
                    return
    
    except KeyboardInterrupt:
        logger.info("Shutting down all components...")
        
        # Terminate all processes
        for name, process in processes:
            logger.info(f"Stopping {name}")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning(f"Force killing {name}")
                process.kill()
        
        logger.info("All components stopped")


if __name__ == "__main__":
    main()
