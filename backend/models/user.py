"""
User Model

Represents an employee of a client company.
Each user belongs to exactly one company and inherits the
company's travel policies and enabled services.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field, EmailStr


# ==========================================================
# Enums
# ==========================================================

class UserRole(str, Enum):
    EMPLOYEE = "employee"
    MANAGER = "manager"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    BLOCKED = "blocked"


# ==========================================================
# User Preferences
# ==========================================================

class UserPreferences(BaseModel):
    """
    User-specific travel preferences.
    """

    preferred_airline: Optional[str] = None

    preferred_hotel_chain: Optional[str] = None

    preferred_car_type: Optional[str] = None

    preferred_seat: Optional[str] = None

    meal_preference: Optional[str] = None

    special_assistance: bool = False


# ==========================================================
# User Model
# ==========================================================

class User(BaseModel):
    """
    Employee/User of a client company.
    """

    user_id: str = Field(
        default_factory=lambda: f"USR-{uuid4().hex[:8].upper()}"
    )

    employee_id: str

    first_name: str

    last_name: str

    email: EmailStr

    phone: Optional[str] = None

    company_id: str

    department: Optional[str] = None

    designation: Optional[str] = None

    role: UserRole = UserRole.EMPLOYEE

    status: UserStatus = UserStatus.ACTIVE

    preferences: UserPreferences = Field(
        default_factory=UserPreferences
    )

    active: bool = True

    created_at: datetime = Field(
        default_factory=datetime.utcnow
    )

    updated_at: datetime = Field(
        default_factory=datetime.utcnow
    )