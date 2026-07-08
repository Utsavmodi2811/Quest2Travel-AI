"""
JWT Security

Creates and verifies JWT access tokens.
"""

from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt

# Move these later to config/settings.py
SECRET_KEY = "CHANGE_THIS_TO_A_LONG_RANDOM_SECRET"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours


def create_access_token(
    user_id: str,
    company_id: str,
    role: str,
) -> str:
    """
    Generate a JWT access token.
    """

    expire = datetime.utcnow() + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": user_id,
        "company_id": company_id,
        "role": role,
        "exp": expire,
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def decode_access_token(
    token: str,
) -> Optional[dict]:
    """
    Decode and validate a JWT token.
    """

    try:
        return jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )

    except JWTError:
        return None