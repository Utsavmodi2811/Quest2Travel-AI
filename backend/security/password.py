"""
Password Security

Provides password hashing and verification using bcrypt.
"""

from passlib.context import CryptContext

# bcrypt configuration
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


def hash_password(password: str) -> str:
    """
    Convert a plain-text password into a secure hash.
    """

    return pwd_context.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    """
    Verify a user's password against the stored hash.
    """

    return pwd_context.verify(
        plain_password,
        hashed_password,
    )