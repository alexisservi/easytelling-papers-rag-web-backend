import jwt
import os
from datetime import datetime, timedelta
from typing import Optional

# JWT configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "papers-rag-app")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

def create_jwt_token(user_email: str) -> str:
    """
    Create a JWT token for the given user email.
    
    Args:
        user_email: The email of the user to create the token for
        
    Returns:
        JWT token string
    """
    payload = {
        "user_email": user_email,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.utcnow()
    }
    
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token

def verify_jwt_token(token: str) -> Optional[str]:
    """
    Verify and decode a JWT token.
    
    Args:
        token: The JWT token to verify
        
    Returns:
        User email if token is valid, None otherwise
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_email = payload.get("user_email")
        return user_email
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None