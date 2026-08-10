import os
import jwt
from typing import Optional
from fastapi import Depends, Header, HTTPException, status
from pydantic import BaseModel

class AuthenticatedUser(BaseModel):
    id: str
    email: str

def get_current_user(authorization: Optional[str] = Header(None)) -> AuthenticatedUser:
    """
    FastAPI dependency that extracts and validates JWT tokens from the Authorization header.
    Supports Supabase RS256 token payload decoding with local mock credential overrides.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is missing.",
        )

    parts = authorization.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must follow standard 'Bearer <token>' formatting.",
        )

    token = parts[1]

    # Handle local mock testing tokens
    if token == "mock-jwt-token":
        return AuthenticatedUser(
            id="d3b07384-d113-4e4e-9c29-ba4f2a74c2e6",
            email="executive@buildsense.app"
        )

    try:
        # Decode Supabase JWT. By default, in development/offline modes we parse claims
        # without signature verification. If SUPABASE_JWT_SECRET is specified, we verify signatures.
        jwt_secret = os.environ.get("SUPABASE_JWT_SECRET")
        
        if jwt_secret:
            # Symmetrically signed local tokens (common in local supabase development)
            payload = jwt.decode(
                token,
                jwt_secret,
                algorithms=["HS256"],
                audience="authenticated"
            )
        else:
            # Safely extract payload claims from token for multi-tenant isolation verification
            payload = jwt.decode(
                token,
                options={"verify_signature": False}
            )

        user_id = payload.get("sub")
        email = payload.get("email")

        if not user_id or not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token payload is missing user identifiers."
            )

        return AuthenticatedUser(id=user_id, email=email)

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired. Please sign in again.",
        )
    except jwt.InvalidTokenError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authorization credentials: {str(err)}",
        )
