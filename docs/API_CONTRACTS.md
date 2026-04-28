# FinFlow API Contracts

Below are the primary internal and external API contracts defining how clients interact with the FinFlow services.

## External API (Account Service)

### 1. User Authentication
- **`POST /api/users/register/`**: Register a new user.
- **`POST /api/users/token/`**: Retrieve access/refresh JWT tokens.
- **`GET /api/users/me/`**: Get authenticated user profile.

### 2. Accounts
- **`GET /api/accounts/`**: List user's accounts.
- **`POST /api/accounts/`**: Create a new account (`currency` required).
- **`PATCH /api/accounts/{id}/`**: Update account status.

### 3. Transactions
- **`GET /api/transactions/`**: List transactions for the authenticated user.
- **`POST /api/transactions/`**: Initiate a transaction.
  - **Payload:** `{"account": "uuid", "amount": "100.00", "currency": "USD", "direction": "CREDIT"}`
  - **Result:** Returns `PENDING` status. Emits Kafka event.

### 4. Documents
- **`POST /api/documents/`**: Multipart upload for KYC documents.
- **`GET /api/documents/{id}/download/`**: Returns a secure, short-lived MinIO presigned URL.

---

## Internal API (Service-to-Service)

### Processing Trigger (Account -> Processing)
- **`POST /api/process/`**
- **Authentication:** HMAC-SHA256 signature in `X-Signature` header.
- **Headers:** `X-Timestamp` (seconds epoch), `X-Nonce` (UUID string).
- **Payload:**
  ```json
  {
    "transaction_id": "uuid",
    "amount": 100.00,
    "currency": "USD",
    "direction": "CREDIT"
  }
  ```

### Status Callback (Processing -> Account)
- **`PATCH /api/internal/transactions/{id}/status/`**
- **Authentication:** Unauthenticated internally (secured via VPC/Docker Network).
- **Payload:**
  ```json
  {
    "status": "COMPLETED",
    "reference": "PROC-12345"
  }
  ```
