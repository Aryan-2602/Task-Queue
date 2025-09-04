# Distributed Job Scheduler with Fault Tolerance

A high-performance, fault-tolerant distributed job scheduling system that supports REST/gRPC APIs for task submission, leverages a Redis-backed queue for task persistence, and executes jobs using worker pools with horizontal scalability.

## 🚀 Key Features

- **Dual API Support**: REST and gRPC APIs for job submission with better concurrency
- **Fault-Tolerant Queue**: Redis-backed queue with retry & dead-letter support
- **Worker Pools**: Configurable worker pools with concurrency limits & load balancing
- **Job Monitoring**: Comprehensive status tracking (queued, running, completed, failed, retrying, dead_letter)
- **Retry Policies**: Exponential backoff and configurable retry limits
- **Observability**: Prometheus metrics, structured logging, and Grafana dashboards
- **High Throughput**: Designed for 100k+ tasks/day with <100ms scheduling latency
- **Horizontal Scaling**: Docker Compose setup for easy deployment and scaling

## 🏗️ System Architecture

```
                +-----------------+
                |  REST/gRPC API  |
                +-----------------+
                          |
                          v
                +-----------------+
                |   Scheduler     | <-- Responsible for enqueuing jobs
                +-----------------+
                          |
                          v
                +-----------------+
                |  Redis Queue    |
                +-----------------+
                    /         \
                   /           \
        +-----------------+   +-----------------+
        | Worker Pool 1   |   | Worker Pool N   |
        +-----------------+   +-----------------+
               |                        |
        +-----------------+     +-----------------+
        | Job Execution   | ... | Job Execution   |
        +-----------------+     +-----------------+
                          |
                          v
                +-----------------+
                |  Job Status DB  | (Postgres/SQLite)
                +-----------------+

   Monitoring: Prometheus (metrics), Grafana (dashboards), logs
```

## 🛠️ Tech Stack

- **APIs**: FastAPI (REST), gRPC (grpcio)
- **Queue**: Redis with priority-based queuing
- **Workers**: Python asyncio + multiprocessing
- **Persistence**: PostgreSQL/SQLite for job metadata
- **Observability**: Prometheus + Grafana + structured logging
- **Deployment**: Docker Compose
- **Testing**: Pytest + Locust for load testing

## 📦 Installation

### Prerequisites

- Python 3.11+
- Redis
- PostgreSQL (optional, SQLite works for development)
- Docker & Docker Compose (for containerized deployment)

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Task-Queue
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start Redis**
   ```bash
   # Using Docker
   docker run -d -p 6379:6379 redis:7-alpine
   
   # Or install locally
   # brew install redis (macOS)
   # sudo apt-get install redis-server (Ubuntu)
   ```

4. **Start PostgreSQL (optional)**
   ```bash
   # Using Docker
   docker run -d -p 5432:5432 -e POSTGRES_DB=job_scheduler -e POSTGRES_USER=scheduler -e POSTGRES_PASSWORD=scheduler_password postgres:15-alpine
   ```

5. **Run the application**
   ```bash
   # Run all components
   python scripts/run_all.py
   
   # Or run individually:
   # REST API: python -m src.api.rest
   # gRPC Server: python -m src.api.grpc_server
   # Workers: python -m src.workers.worker_pool
   ```

### Docker Deployment

1. **Start all services**
   ```bash
   docker-compose up -d
   ```

2. **Check service status**
   ```bash
   docker-compose ps
   ```

3. **View logs**
   ```bash
   docker-compose logs -f api
   docker-compose logs -f worker
   ```

## 🎯 Usage

### REST API

**Submit a job:**
```bash
curl -X POST "http://localhost:8000/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "job_type": "sleep",
    "payload": "{\"duration\": 2}",
    "priority": 5,
    "max_retries": 3,
    "timeout_seconds": 30
  }'
```

**Get job status:**
```bash
curl "http://localhost:8000/jobs/{job_id}"
```

**List jobs:**
```bash
curl "http://localhost:8000/jobs?status_filter=completed&limit=10"
```

**Health check:**
```bash
curl "http://localhost:8000/health"
```

### gRPC API

**Submit a job:**
```python
import grpc
from src.api import job_scheduler_pb2, job_scheduler_pb2_grpc

channel = grpc.insecure_channel('localhost:50051')
stub = job_scheduler_pb2_grpc.JobSchedulerServiceStub(channel)

request = job_scheduler_pb2.SubmitJobRequest(
    job_type="math",
    payload='{"operation": "add", "a": 5, "b": 3}',
    priority=5,
    max_retries=3,
    timeout_seconds=30
)

response = stub.SubmitJob(request)
print(f"Job submitted: {response.job_id}")
```

### Supported Job Types

1. **sleep**: Sleep for a specified duration
   ```json
   {"duration": 2}
   ```

2. **math**: Perform mathematical operations
   ```json
   {"operation": "add", "a": 5, "b": 3}
   ```

3. **http_request**: Make HTTP requests
   ```json
   {"url": "https://httpbin.org/get", "method": "GET"}
   ```

4. **echo**: Echo back the payload
   ```json
   {"message": "Hello World"}
   ```

5. **random_failure**: Randomly fail for testing retry logic
   ```json
   {"failure_rate": 0.3}
   ```

## 📊 Monitoring

### Prometheus Metrics

Access metrics at: `http://localhost:9090`

Key metrics:
- `jobs_submitted_total`: Total jobs submitted by type
- `jobs_completed_total`: Total jobs completed by type and status
- `job_execution_seconds`: Job execution time histogram
- `queue_size`: Current queue size
- `active_workers`: Number of active workers

### Grafana Dashboards

Access Grafana at: `http://localhost:3000` (admin/admin)

Pre-configured dashboards show:
- Job throughput and latency
- Queue metrics
- Worker performance
- Error rates and retry patterns

### Health Checks

- **REST API**: `GET /health`
- **gRPC**: Health check via gRPC health checking protocol
- **Workers**: Internal health monitoring

## 🧪 Testing

### Unit Tests
```bash
pytest tests/
```

### Load Testing
```bash
# Install locust
pip install locust

# Run load test
locust -f tests/load_test.py --host=http://localhost:8000

# Access web UI at http://localhost:8089
```

### Performance Targets

- **Throughput**: 100k+ jobs/day
- **Latency**: <100ms scheduling latency
- **Concurrency**: Supports high concurrent job submission
- **Fault Tolerance**: Automatic retry with exponential backoff

## ⚙️ Configuration

Environment variables:

```bash
# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# Database Configuration
DATABASE_URL=sqlite:///./job_scheduler.db
# or
DATABASE_URL=postgresql://user:password@localhost:5432/job_scheduler

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
GRPC_PORT=50051

# Worker Configuration
WORKER_CONCURRENCY=4
WORKER_POOL_SIZE=2

# Job Configuration
DEFAULT_MAX_RETRIES=3
DEFAULT_TIMEOUT_SECONDS=300
JOB_TTL_SECONDS=86400

# Monitoring
LOG_LEVEL=INFO
```

## 🔧 Development

### Project Structure

```
Task-Queue/
├── src/
│   ├── api/                 # REST and gRPC APIs
│   ├── workers/             # Worker pool and job execution
│   ├── monitoring/          # Metrics and observability
│   ├── models.py            # Database models
│   ├── queue.py             # Redis queue implementation
│   ├── database.py          # Database connection
│   ├── config.py            # Configuration
│   └── schemas.py           # Pydantic schemas
├── proto/                   # gRPC protocol definitions
├── tests/                   # Test files
├── monitoring/              # Prometheus and Grafana configs
├── scripts/                 # Utility scripts
├── docker-compose.yml       # Docker deployment
├── Dockerfile              # Container definition
└── requirements.txt        # Python dependencies
```

### Adding New Job Types

1. **Implement job handler** in `src/workers/job_executor.py`:
   ```python
   async def _execute_my_job(self, payload: Dict[str, Any]) -> Dict[str, Any]:
       # Your job logic here
       return {"result": "success"}
   ```

2. **Register handler** in `JobExecutor.__init__()`:
   ```python
   self.job_handlers["my_job"] = self._execute_my_job
   ```

3. **Test the job type**:
   ```bash
   curl -X POST "http://localhost:8000/jobs" \
     -H "Content-Type: application/json" \
     -d '{"job_type": "my_job", "payload": "{}"}'
   ```

## 🚀 Deployment

### Production Considerations

1. **Redis Configuration**:
   - Use Redis Cluster for high availability
   - Configure persistence (RDB + AOF)
   - Set appropriate memory limits

2. **Database**:
   - Use PostgreSQL for production
   - Configure connection pooling
   - Set up regular backups

3. **Workers**:
   - Scale horizontally by increasing worker replicas
   - Monitor worker health and restart failed workers
   - Use process managers like systemd or supervisor

4. **Monitoring**:
   - Set up alerting on key metrics
   - Monitor queue depth and processing latency
   - Track error rates and retry patterns

### Kubernetes Deployment

For Kubernetes deployment, see the `k8s/` directory for manifests.

## 📈 Performance Tuning

1. **Redis Optimization**:
   - Use Redis Cluster for horizontal scaling
   - Tune memory settings and eviction policies
   - Monitor Redis performance metrics

2. **Worker Scaling**:
   - Adjust `WORKER_POOL_SIZE` based on CPU cores
   - Monitor worker utilization and queue depth
   - Use auto-scaling based on queue metrics

3. **Database Optimization**:
   - Add indexes on frequently queried columns
   - Use connection pooling
   - Consider read replicas for status queries

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- **Issues**: Report bugs and feature requests via GitHub issues
- **Documentation**: Check the `/docs` directory for detailed documentation
- **Community**: Join our Discord server for discussions

---

**Built with ❤️ for high-performance, fault-tolerant job scheduling**