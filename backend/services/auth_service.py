"""
Authentication Service
"""

import logging
from datetime import datetime
from typing import Optional

from database.connection import get_db

from models.user import User
from models.auth import RegisterRequest
from security.password import (
    hash_password,
    verify_password,
)

logger = logging.getLogger(__name__)


class AuthService:

    async def get_user_by_email(
        self,
        email: str,
    ) -> Optional[User]:

        db = get_db()

        doc = await db.users.find_one(
            {
                "email": email.lower()
            }
        )

        if not doc:
            return None

        doc.pop("_id", None)

        return User(**doc)

    async def register(
        self,
        request: RegisterRequest,
    ) -> User:

        existing = await self.get_user_by_email(
            request.email
        )

        if existing:
            raise ValueError(
                "Email already registered."
            )

        user = User(

            employee_id=request.employee_id,

            first_name=request.first_name,

            last_name=request.last_name,

            email=request.email.lower(),

            password_hash=hash_password(
                request.password
            ),

            company_id=request.company_id,

            phone=request.phone,

            department=request.department,

            designation=request.designation,

            created_at=datetime.utcnow(),

            updated_at=datetime.utcnow(),
        )

        db = get_db()

        await db.users.insert_one(
            user.dict()
        )

        logger.info(
            "User registered: %s",
            user.email,
        )

        return user

    async def authenticate(
        self,
        email: str,
        password: str,
    ) -> Optional[User]:

        user = await self.get_user_by_email(
            email
        )

        if not user:
            return None

        if not verify_password(
            password,
            user.password_hash,
        ):
            return None

        db = get_db()

        await db.users.update_one(
            {
                "user_id": user.user_id
            },
            {
                "$set": {
                    "last_login": datetime.utcnow()
                }
            }
        )

        return user


auth_service = AuthService()