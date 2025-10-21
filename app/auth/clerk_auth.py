# app/auth/clerk_auth.py

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from clerk_sdk.client import Clerk
from clerk_sdk.errors import ClerkAPIException, JWTVerificationError, JWTSignatureExpiredError, JWTSignatureInvalidError
from app.core.config import settings
from typing import Optional

# Initialize Clerk client (uses CLERK_SECRET_KEY automatically if set as env var,
# but explicitly passing is safer if env var name differs or for clarity)
# Make sure CLERK_SECRET_KEY is loaded correctly in settings
if not settings.CLERK_SECRET_KEY:
    raise ValueError("CLERK_SECRET_KEY not found in settings. Cannot initialize Clerk client.")

clerk_client = Clerk(secret_key=settings.CLERK_SECRET_KEY)

# This tells FastAPI to look for an "Authorization: Bearer <token>" header.
# The tokenUrl="token" part isn't actually used for verification here, but FastAPI requires it.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token",
                                     auto_error=False)  # auto_error=False makes token optional initially


async def get_current_user_id(token: Optional[str] = Depends(oauth2_scheme)) -> str:
    """
    Dependency to verify Clerk JWT token and return the user ID ('sub').
    Raises HTTPException 401 if the token is invalid, expired, or missing.
    """
    if token is None:
        # If the token is optional for an endpoint, you might return None here.
        # For required auth, we raise an error.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated: Token is missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Use the Clerk SDK to verify the token
        session_claims = clerk_client.sessions.verify_token(token=token)

        user_id = session_claims.get("sub")  # 'sub' is the standard JWT claim for subject (user ID)

        if user_id is None:
            print("Token verified, but 'sub' (user ID) claim is missing.")
            raise credentials_exception

        print(f"Authenticated user ID: {user_id}")  # Optional: for debugging
        return user_id

    except JWTSignatureExpiredError:
        print("Clerk token expired.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except (JWTVerificationError, JWTSignatureInvalidError, ClerkAPIException) as e:
        # Catch specific Clerk/JWT errors
        print(f"Clerk token verification failed: {e}")
        raise credentials_exception
    except Exception as e:
        # Catch any other unexpected errors during verification
        print(f"An unexpected error occurred during token verification: {e}")
        raise credentials_exception