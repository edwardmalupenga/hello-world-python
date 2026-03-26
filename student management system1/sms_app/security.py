"""Password security utilities for the SMS application."""

import os
import hashlib


def hash_password(password: str) -> tuple[bytes, bytes]:
    """
    Hash a password using PBKDF2-SHA256.
    Returns a tuple of (salt, hash).
    """
    salt = os.urandom(32)
    pwd_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        100000
    )
    return salt, pwd_hash


def verify_password(password: str, salt: bytes, stored_hash: bytes) -> bool:
    """
    Verify a password against a stored hash.
    Returns True if the password matches, False otherwise.
    """
    pwd_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        100000
    )
    return pwd_hash == stored_hash
