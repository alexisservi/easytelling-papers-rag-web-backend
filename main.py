from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from typing import Optional
import os

from auth import verify_jwt_token, create_jwt_token
from firestore_db import FirestoreDB
from agent_service import AgentService

app = FastAPI(title="Papers RAG Web Backend", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Initialize services
db = FirestoreDB()
agent_service = AgentService()

# Pydantic models
class LoginRequest(BaseModel):
    user_email: str

class AddUserRequest(BaseModel):
    user_email: str
    new_user_email: str
    is_admin: bool

class MessageToAgentRequest(BaseModel):
    user_email: str
    session_id: str
    message_to_agent: str

class DeleteSessionRequest(BaseModel):
    user_email: str
    session_id: str

class StandardResponse(BaseModel):
    status: str
    message: str

class LoginResponse(StandardResponse):
    user_token: Optional[str] = None
    is_admin: Optional[bool] = None

class MessageToAgentResponse(StandardResponse):
    session_id: Optional[str] = None

# Dependency to verify JWT token
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    user_email = verify_jwt_token(token)
    if not user_email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    return user_email

@app.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    try:
        # Get user data from Firestore
        user_data = await db.get_user(request.user_email)

        if not user_data:
            return LoginResponse(
                status="fail",
                message="User not found",
                user_token=None,
                is_admin=None
            )

        # Generate JWT token
        token = create_jwt_token(request.user_email)

        return LoginResponse(
            status="success",
            message="Login successful",
            user_token=token,
            is_admin=user_data.get("is_admin", False)
        )

    except Exception as e:
        return LoginResponse(
            status="fail",
            message=f"Login failed: {str(e)}",
            user_token=None,
            is_admin=None
        )

@app.post("/add_user", response_model=StandardResponse)
async def add_user(request: AddUserRequest, current_user: str = Depends(get_current_user)):
    try:
        # Check if current user is admin
        is_admin = await db.is_user_admin(current_user)
        
        if not is_admin:
            return StandardResponse(
                status="fail",
                message="Only admin users can add new users"
            )
        
        # Add new user to Firestore
        success = await db.add_user(request.new_user_email, request.is_admin)
        
        if success:
            return StandardResponse(
                status="success",
                message="User added successfully"
            )
        else:
            return StandardResponse(
                status="fail",
                message="Failed to add user"
            )
    
    except Exception as e:
        return StandardResponse(
            status="fail",
            message=f"Error adding user: {str(e)}"
        )

@app.post("/message_to_agent", response_model=MessageToAgentResponse)
async def message_to_agent(request: MessageToAgentRequest, current_user: str = Depends(get_current_user)):
    try:
        # Send message to agent using the provided sample code logic
        events, actual_session_id = await agent_service.send_message(
            user_id=request.user_email,
            session_id=request.session_id,
            message=request.message_to_agent
        )
        
        if events and len(events) > 0:
            # Get the response message from the last event
            response_message = events[-1]["content"]["parts"][0]["text"]
            
            return MessageToAgentResponse(
                status="success",
                message=response_message,
                session_id=actual_session_id
            )
        else:
            return MessageToAgentResponse(
                status="fail",
                message="No response from agent",
                session_id=request.session_id
            )
    
    except Exception as e:
        return MessageToAgentResponse(
            status="fail",
            message=f"Error communicating with agent: {str(e)}",
            session_id=request.session_id
        )

@app.delete("/delete_session", response_model=StandardResponse)
async def delete_session(request: DeleteSessionRequest, current_user: str = Depends(get_current_user)):
    try:
        # Verify that the current user matches the user_email in the request
        if current_user != request.user_email:
            return StandardResponse(
                status="fail",
                message="You can only delete your own sessions"
            )

        # Delete the session using agent service
        success = await agent_service.delete_user_session(
            user_id=request.user_email,
            session_id=request.session_id
        )

        if success:
            return StandardResponse(
                status="success",
                message="Session deleted successfully"
            )
        else:
            return StandardResponse(
                status="fail",
                message="Failed to delete session"
            )

    except Exception as e:
        return StandardResponse(
            status="fail",
            message=f"Error deleting session: {str(e)}"
        )

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)