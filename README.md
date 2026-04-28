# FinFlow Microservices Project

Welcome to FinFlow! This is the complete, production-ready backend infrastructure designed for the 5-Day Internship Challenge. The project demonstrates an advanced, scalable backend architecture utilizing Django, FastAPI, PostgreSQL, Kafka, and MinIO.

## Project Architecture

The platform consists of two main microservices that communicate asynchronously via Kafka and synchronously via HMAC-authenticated HTTP APIs:

1. **Account Service (`:8000`)**: A Django REST Framework (DRF) application responsible for user management, account operations, document uploads, and transaction initiation.
2. **Processing Service (`:8001`)**: A FastAPI application that securely processes initiated transactions. It listens to Kafka events and also exposes an HMAC-authenticated endpoint to simulate complex processing workflows (like fraud-checking and settlement) before calling back to the Account Service.

### Technologies Used
- **Django 4.2 & DRF**: Core business logic and primary API.
- **FastAPI**: High-performance asynchronous processing service.
- **PostgreSQL**: Relational data store for the Account Service.
- **Apache Kafka & Zookeeper**: Event streaming platform for asynchronous communication.
- **MinIO**: S3-compatible object storage for secure document management.
- **Docker & Docker Compose**: Full infrastructure orchestration.

---

## Getting Started

### Prerequisites
Make sure you have Docker and Docker Compose installed on your local machine.

### Running the Full Infrastructure
To spin up the entire FinFlow infrastructure (PostgreSQL, MinIO, Kafka, Account Service, and Processing Service) in a single command, run from the root of the project:

```bash
docker-compose up --build
```

Docker Compose will automatically:
1. Spin up Postgres, MinIO, Zookeeper, and Kafka.
2. Build the Docker image for the `account-service`, run database migrations automatically, and start the Django server on `http://localhost:8000`.
3. Build the Docker image for the `processing-service` and start the FastAPI server on `http://localhost:8001`.

### Useful Endpoints
- **Account Service Swagger UI**: `http://localhost:8000/api/schema/swagger-ui/`
- **Processing Service Swagger UI**: `http://localhost:8001/docs`
- **Processing Service Health**: `http://localhost:8001/health`
- **MinIO Console**: `http://localhost:9001` (Credentials: `minioadmin` / `minioadmin`)

### Running Tests Locally (Without Docker)

**Account Service**
```bash
cd account-service
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -v tests/ --cov=apps
```

**Processing Service**
```bash
cd processing-service
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -v tests/ --cov=app
```
