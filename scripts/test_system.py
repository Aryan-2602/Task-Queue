#!/usr/bin/env python3
"""Test script to verify the job scheduler system."""

import requests
import time
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import structlog

logger = structlog.get_logger()


def test_rest_api():
    """Test the REST API endpoints."""
    base_url = "http://localhost:8000"
    
    print("🧪 Testing REST API...")
    
    # Test health check
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Health check passed")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False
    
    # Test job submission
    job_payload = {
        "job_type": "echo",
        "payload": json.dumps({"message": "Hello from test!"}),
        "priority": 5,
        "max_retries": 3,
        "timeout_seconds": 30
    }
    
    try:
        response = requests.post(f"{base_url}/jobs", json=job_payload, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                job_id = data.get("job_id")
                print(f"✅ Job submitted successfully: {job_id}")
                
                # Test job status
                time.sleep(1)  # Wait a bit for processing
                status_response = requests.get(f"{base_url}/jobs/{job_id}", timeout=5)
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    print(f"✅ Job status retrieved: {status_data.get('status')}")
                else:
                    print(f"❌ Failed to get job status: {status_response.status_code}")
                
                return True
            else:
                print(f"❌ Job submission failed: {data.get('message')}")
                return False
        else:
            print(f"❌ Job submission failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Job submission failed: {e}")
        return False


def test_different_job_types():
    """Test different job types."""
    base_url = "http://localhost:8000"
    
    print("\n🧪 Testing different job types...")
    
    job_types = [
        {
            "job_type": "sleep",
            "payload": json.dumps({"duration": 1}),
            "name": "Sleep Job"
        },
        {
            "job_type": "math",
            "payload": json.dumps({"operation": "add", "a": 5, "b": 3}),
            "name": "Math Job"
        },
        {
            "job_type": "echo",
            "payload": json.dumps({"message": "Test message"}),
            "name": "Echo Job"
        }
    ]
    
    success_count = 0
    
    for job_config in job_types:
        try:
            payload = {
                "job_type": job_config["job_type"],
                "payload": job_config["payload"],
                "priority": 5,
                "max_retries": 3,
                "timeout_seconds": 30
            }
            
            response = requests.post(f"{base_url}/jobs", json=payload, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    print(f"✅ {job_config['name']} submitted successfully")
                    success_count += 1
                else:
                    print(f"❌ {job_config['name']} failed: {data.get('message')}")
            else:
                print(f"❌ {job_config['name']} failed: {response.status_code}")
        except Exception as e:
            print(f"❌ {job_config['name']} failed: {e}")
    
    print(f"📊 Job type tests: {success_count}/{len(job_types)} passed")
    return success_count == len(job_types)


def test_stats():
    """Test statistics endpoint."""
    base_url = "http://localhost:8000"
    
    print("\n🧪 Testing statistics endpoint...")
    
    try:
        response = requests.get(f"{base_url}/stats", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("✅ Statistics retrieved successfully")
            print(f"   - Jobs queued: {data.get('jobs_queued', 0)}")
            print(f"   - Jobs running: {data.get('jobs_running', 0)}")
            print(f"   - Jobs completed: {data.get('jobs_completed', 0)}")
            print(f"   - Jobs failed: {data.get('jobs_failed', 0)}")
            return True
        else:
            print(f"❌ Statistics failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Statistics failed: {e}")
        return False


def main():
    """Main test function."""
    print("🚀 Starting Job Scheduler System Tests")
    print("=" * 50)
    
    # Wait for services to be ready
    print("⏳ Waiting for services to be ready...")
    time.sleep(3)
    
    # Run tests
    tests = [
        ("REST API", test_rest_api),
        ("Job Types", test_different_job_types),
        ("Statistics", test_stats),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The system is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the logs above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
