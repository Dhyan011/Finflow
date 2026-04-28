# FinFlow Architecture

## System Overview
FinFlow is a distributed FinTech application built to securely manage user accounts, KYC documents, and transaction workflows. The system leverages an event-driven microservices architecture to decouple the core CRUD API from heavy, asynchronous processing engines.

## Core Components

1. **Account Service (Django/DRF)**
   - **Role:** The primary gateway for user interactions. Handles User/Account/Transaction CRUD, Authentication (JWT), and metadata storage.
   - **Database:** PostgreSQL. All data is soft-deleted to ensure auditability.
   - **File Storage:** Uploads are streamed securely to MinIO; the DB stores metadata.

2. **Processing Service (FastAPI)**
   - **Role:** Handles heavy background tasks (simulated validation, fraud checks, settlement).
   - **Concurrency:** Uses `asyncio` to handle high-throughput concurrent processing requests.

3. **Apache Kafka & Zookeeper**
   - **Role:** The event backbone. Ensures that if the processing service fails, transaction initiation events (`transaction.created`) are retained and retried.

4. **MinIO**
   - **Role:** S3-compatible object storage ensuring documents never bloat the Postgres database.

## Security Architecture
- **JWT**: Secures external endpoints.
- **HMAC-SHA256**: Internal communication (Account -> Processing) is signed using a shared secret. We validate signatures, timestamps (to prevent replay attacks), and nonces (to ensure idempotency).
- **Audit Logging**: A custom `AuditLog` table intercepts all state mutations and scrubs PII (passwords, tokens).

## Future Scalability
- The Airflow DAG stubs in the `processing-service` demonstrate how complex state-machine tasks will be orchestrated without blocking API workers.
