# Papers RAG Web Backend

A FastAPI backend service for a Papers RAG (Retrieval-Augmented Generation) web application. This backend provides user authentication, user management, and agent communication capabilities.

## Features

- JWT-based authentication
- User management with admin privileges
- Integration with Papers RAG agent
- Firestore database for user storage
- Ready for Google Cloud Run deployment

## Project Structure

```
papers-rag-web-backend/
├── main.py                 # Main FastAPI application
├── auth.py                # JWT authentication utilities
├── firestore_db.py        # Firestore database operations
├── agent_service.py       # Agent communication service
├── requirements.txt       # Python dependencies
├── Dockerfile            # Container configuration
├── cloudbuild.yaml       # Cloud Build configuration
└── README.md            # This file
```

## Environment Variables

- `JWT_SECRET_KEY`: Secret key for JWT token signing (default: "papers-rag-app")
- `PORT`: Port for the application (default: 8080)
- Google Cloud credentials are automatically provided in Cloud Run

## Deployment

### Prerequisites
- Google Cloud Project with the following APIs enabled:
  - Cloud Build API
  - Cloud Run API
  - Firestore API
- `gcloud` CLI installed and authenticated

### Deploy to Cloud Run
```bash
gcloud builds submit --config cloudbuild.yaml
```

## API Endpoints

### Base URL
When deployed: `https://[service-name]-[hash]-[region].run.app`
Local development: `http://localhost:8080`

### Authentication
Protected endpoints require a Bearer token in the Authorization header:
```
Authorization: Bearer <jwt_token>
```

---

## Endpoint Documentation for LLM Agents

### 1. POST /login
**Purpose**: Authenticate a user and receive a JWT token for subsequent requests.

**Request Format**:
```json
{
  "user_email": "user@example.com"
}
```

**Response Format**:
```json
{
  "status": "success|fail",
  "message": "Login successful|User not found|Login failed: <error>",
  "user_token": "jwt_token_string_or_null",
  "is_admin": "boolean_or_null"
}
```

**Usage Example**:
```bash
curl -X POST "https://your-api-url/login" \
  -H "Content-Type: application/json" \
  -d '{"user_email": "admin@example.com"}'
```

**Important Notes for LLM Agents**:
- The user must exist in the `rag_users` Firestore collection
- Save the `user_token` from successful responses for use in protected endpoints
- The `is_admin` field indicates whether the user has administrative privileges
- Token expires after 24 hours

---

### 2. POST /add_user
**Purpose**: Add a new user to the system (admin-only operation).

**Authentication**: Required (JWT token in Authorization header)

**Request Format**:
```json
{
  "user_email": "current_admin@example.com",
  "new_user_email": "newuser@example.com", 
  "is_admin": true
}
```

**Response Format**:
```json
{
  "status": "success|fail",
  "message": "User added successfully|Only admin users can add new users|Failed to add user|Error adding user: <error>"
}
```

**Usage Example**:
```bash
curl -X POST "https://your-api-url/add_user" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <jwt_token>" \
  -d '{
    "user_email": "admin@example.com",
    "new_user_email": "newuser@example.com",
    "is_admin": false
  }'
```

**Important Notes for LLM Agents**:
- Only users with `is_admin: true` can add new users
- The `user_email` should match the email from the JWT token
- `is_admin` determines if the new user will have admin privileges

---

### 3. POST /message_to_agent
**Purpose**: Send a message to the Papers RAG agent and receive a response.

**Authentication**: Required (JWT token in Authorization header)

**Request Format**:
```json
{
  "user_email": "user@example.com",
  "session_id": "unique_session_identifier",
  "message_to_agent": "What are the latest developments in kidney transplants?"
}
```

**Response Format**:
```json
{
  "status": "success|fail",
  "message": "agent_response_text|No response from agent|Error communicating with agent: <error>",
  "session_id": "session_identifier_used"
}
```

**Usage Example**:
```bash
curl -X POST "https://your-api-url/message_to_agent" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <jwt_token>" \
  -d '{
    "user_email": "user@example.com",
    "session_id": "session_123",
    "message_to_agent": "Tell me about recent AI research papers"
  }'
```

**Important Notes for LLM Agents**:
- Sessions are automatically created if they don't exist
- The same `session_id` maintains conversation context
- The agent response is extracted from `events[-1]["content"]["parts"][0]["text"]`
- Requires `gcloud` CLI authentication in the deployment environment

---

### 4. GET /health
**Purpose**: Health check endpoint to verify service status.

**Authentication**: Not required

**Response Format**:
```json
{
  "status": "healthy"
}
```

**Usage Example**:
```bash
curl -X GET "https://your-api-url/health"
```

---

## LLM Agent Integration Workflow

For an LLM agent integrating with this API, follow this typical workflow:

1. **Authentication**: Call `/login` with a valid user email to get a JWT token
2. **Save Token**: Store the JWT token for subsequent authenticated requests  
3. **User Management** (if admin): Use `/add_user` to manage users in the system
4. **Agent Communication**: Use `/message_to_agent` to interact with the Papers RAG system
5. **Session Management**: Reuse session IDs to maintain conversation context

### Error Handling
All endpoints return consistent JSON with `status` field:
- `"success"`: Operation completed successfully
- `"fail"`: Operation failed, check `message` field for details

### Rate Limiting
The service is deployed on Cloud Run with auto-scaling. Monitor for 429 responses if rate limits are exceeded.

## Development

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export JWT_SECRET_KEY="your-secret-key"
export GOOGLE_APPLICATION_CREDENTIALS="path/to/service-account.json"

# Run the application
uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

### Testing Endpoints
Use the provided curl examples or tools like Postman to test the endpoints. Ensure you have valid users in your Firestore `rag_users` collection for testing authentication.