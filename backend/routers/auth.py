"""
Authentication Router
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from models.user import User
from models.auth import (
    RegisterRequest,
    LoginRequest,
    LoginResponse,
    UserResponse,
)

from security.dependencies import get_current_user
from security.jwt import create_access_token

from services.auth_service import auth_service
logger = logging.getLogger(__name__)

auth_router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"],
)
@auth_router.post(
    "/register",
    response_model=UserResponse,
)
async def register(
    request: RegisterRequest,
):
    """
    Register a new employee.
    """

    try:

        user = await auth_service.register(request)

        return UserResponse(
            user_id=user.user_id,
            employee_id=user.employee_id,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
            company_id=user.company_id,
            role=user.role,
            department=user.department,
            designation=user.designation,
        )

    except ValueError as e:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    except Exception:

        logger.exception("Registration failed")

        raise HTTPException(
            status_code=500,
            detail="Registration failed.",
        )
@auth_router.post(
    "/login",
    response_model=LoginResponse,
)
async def login(
    request: LoginRequest,
):
    """
    Login user.
    """

    user = await auth_service.authenticate(
        request.email,
        request.password,
    )

    if not user:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    token = create_access_token(
        user_id=user.user_id,
        company_id=user.company_id,
        role=user.role.value,
    )

    return LoginResponse(

        access_token=token,

        user=UserResponse(
            user_id=user.user_id,
            employee_id=user.employee_id,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
            company_id=user.company_id,
            role=user.role,
            department=user.department,
            designation=user.designation,
        ),
    )
# -------------------------
# Current User
# -------------------------

@auth_router.get(
    "/me",
    response_model=UserResponse,
)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    """
    Return the currently logged-in user.
    """

    return UserResponse(
        user_id=current_user.user_id,
        employee_id=current_user.employee_id,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        email=current_user.email,
        company_id=current_user.company_id,
        role=current_user.role,
        department=current_user.department,
        designation=current_user.designation,
    )