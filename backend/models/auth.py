"""
Authentication Models

Request and response models for user authentication.
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional

from models.user import UserRole


# ==========================================================
# Register Request
# ==========================================================

class RegisterRequest(BaseModel):
    """
    Request body for user registration.
    """

    employee_id: str = Field(..., min_length=1)

    first_name: str = Field(..., min_length=1)

    last_name: str = Field(..., min_length=1)

    email: EmailStr

    password: str = Field(..., min_length=8)

    company_id: str

    phone: Optional[str] = None

    department: Optional[str] = None

    designation: Optional[str] = None


# ==========================================================
# Login Request
# ==========================================================

class LoginRequest(BaseModel):
    """
    Request body for user login.
    """

    email: EmailStr

    password: str


# ==========================================================
# Token Response
# ==========================================================

class TokenResponse(BaseModel):
    """
    JWT token returned after successful login.
    """

    access_token: str

    token_type: str = "bearer"


# ==========================================================
# User Response
# ==========================================================

class UserResponse(BaseModel):
    """
    User information returned to the frontend.
    """

    user_id: str

    employee_id: str

    first_name: str

    last_name: str

    email: EmailStr

    company_id: str

    role: UserRole

    department: Optional[str] = None

    designation: Optional[str] = None


# ==========================================================
# Login Response
# ==========================================================

class LoginResponse(BaseModel):
    """
    Response returned after successful login.
    """

    access_token: str

    token_type: str = "bearer"

    user: UserResponse