# RAG-tester Service

Evaluation service for testing RAG (Retrieval-Augmented Generation) quality using industry-standard information retrieval metrics.

## Features

- ✅ **Test Dataset Management**: Create, read, update, delete ground truth datasets
- ✅ **Async Evaluation Jobs**: Submit evaluation jobs processed by Celery workers
- ✅ **IR Metrics**: Compute NDCG@k, MAP@k, MRR@k at multiple k values
- ✅ **File-Based Storage**: Simple JSON file storage (no database required for MVP)
- ✅ **REST API**: FastAPI with auto-generated OpenAPI docs

## Architecture

```
┌─────────────────────────────────────┐
│   FastAPI Application (Port 8001)  │
│   - Dataset CRUD endpoints          │
│   - Evaluation job submission       │
│   - Results retrieval               │
└────────────┬────────────────────────┘
             │
             │ Submits tasks
             ▼
┌─────────────────────────────────────┐
│   Celery Worker (Redis Queue)      │
│   - Async evaluation processing     │
│   - Calls RAG Service for retrieval │
│   - Computes metrics                │
└─────────────────────────────────────┘
             │
             │ Stores results
             ▼
┌─────────────────────────────────────┐
│   File Storage (./data/)            │
│   - test-datasets/*.json            │
│   - evaluation-results/*.json       │
│   - jobs/*.json                     │
└─────────────────────────────────────┘
```

## Installation

### Prerequisites

- Python 3.11+
- Redis (for Celery task queue)

### Setup

```bash
# Navigate to service directory
cd services/rag-tester

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with your configuration
nano .env
```

## Usage

### Start Redis

```bash
# Using Docker
docker run -d -p 6379:6379 redis:7-alpine

# Or install locally
# macOS: brew install redis && redis-server
# Ubuntu: sudo apt install redis-server && sudo systemctl start redis
```

### Start FastAPI Application

```bash
# Development mode (with auto-reload)
uvicorn src.main:app --reload --port 8001

# Production mode
uvicorn src.main:app --host 0.0.0.0 --port 8001 --workers 4
```

### Start Celery Worker

```bash
# In a separate terminal (same venv)
celery -A src.celery_app worker --loglevel=info
```

### Access API Documentation

- **Interactive Docs**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc
- **OpenAPI JSON**: http://localhost:8001/openapi.json

## API Endpoints

### Datasets

- `POST /test-datasets` - Create dataset
- `GET /test-datasets` - List datasets
- `GET /test-datasets/{id}` - Get dataset
- `PUT /test-datasets/{id}` - Update dataset
- `DELETE /test-datasets/{id}` - Delete dataset

### Evaluations

- `POST /evaluations` - Submit evaluation job
- `GET /evaluations/{job_id}` - Get job status
- `GET /evaluations/{job_id}/results` - Get results (when completed)
- `GET /evaluations` - List all jobs

## Example Usage

### 1. Create Test Dataset

```bash
curl -X POST http://localhost:8001/test-datasets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "RAG Quality Test v1",
    "description": "Basic retrieval quality test",
    "queries": [
      {
        "query": "What is retrieval augmented generation?",
        "expected_docs": [
          {"doc_id": "doc_123", "relevance": 1.0},
          {"doc_id": "doc_456", "relevance": 0.8}
        ]
      }
    ]
  }'
```

### 2. Submit Evaluation

```bash
curl -X POST http://localhost:8001/evaluations \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_id": "abc-123-xyz",
    "retrieval_method": "multi-query",
    "k_values": [1, 3, 5, 10]
  }'
```

### 3. Check Job Status

```bash
curl http://localhost:8001/evaluations/{job_id}
```

### 4. Get Results

```bash
curl http://localhost:8001/evaluations/{job_id}/results
```

## Configuration

Edit `.env` file:

```bash
# RAG Service URL (where to send queries for evaluation)
RAG_SERVICE_URL=http://localhost:8000

# Redis connection
REDIS_URL=redis://localhost:6379/0

# Data storage location
DATA_DIR=./data

# Evaluation settings
RAG_SERVICE_TIMEOUT=30
MAX_QUERIES_PER_DATASET=1000
```

## Docker Deployment

```bash
# Build image
docker build -t rag-tester:latest .

# Run with docker-compose (includes Redis)
docker-compose up -d
```

## Testing

```bash
# Run unit tests
pytest tests/

# Run with coverage
pytest --cov=src tests/

# Run specific test
pytest tests/test_metrics.py
```

## Metrics Explained

### NDCG@k (Normalized Discounted Cumulative Gain)
- Measures ranking quality considering both relevance and position
- Range: 0-1 (1 = perfect ranking)
- Formula: DCG@k / IDCG@k

### MAP@k (Mean Average Precision)
- Average precision across different recall levels
- Range: 0-1
- Emphasizes precision at each recall point

### MRR@k (Mean Reciprocal Rank)
- Focuses on position of first relevant document
- Range: 0-1
- Formula: 1 / rank of first relevant doc

## Troubleshooting

**Celery worker not picking up tasks:**
```bash
# Check Redis connection
redis-cli ping  # Should return PONG

# Check Celery connection
celery -A src.celery_app inspect ping
```

**Job stuck in "queued" status:**
- Ensure Celery worker is running
- Check worker logs for errors
- Verify Redis connectivity

**Evaluation failing:**
- Check RAG Service is running at configured URL
- Verify dataset exists and has valid queries
- Check RAG Service endpoint compatibility

## Development

```bash
# Install dev dependencies
pip install -r requirements.txt pytest pytest-cov black flake8

# Format code
black src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/
```

## File Structure

```
services/rag-tester/
├── src/
│   ├── __init__.py
│   ├── main.py              # FastAPI app
│   ├── config.py            # Configuration
│   ├── storage.py           # File-based storage
│   ├── models.py            # Pydantic models
│   ├── celery_app.py        # Celery configuration
│   ├── tasks.py             # Celery tasks
│   ├── api/
│   │   ├── datasets.py      # Dataset endpoints
│   │   └── evaluations.py   # Evaluation endpoints
│   └── evaluation/
│       ├── metrics.py       # IR metrics (NDCG, MAP, MRR)
│       └── engine.py        # Evaluation orchestration
├── tests/
│   ├── test_storage.py
│   ├── test_metrics.py
│   └── test_api.py
├── data/                    # Created at runtime
├── requirements.txt
├── Dockerfile
├── .env.example
└── README.md
```

## License

MIT License
