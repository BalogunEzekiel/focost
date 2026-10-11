"""Encrypt sensitive provider account identifiers before database persistence."""
import base64
import hashlib
from cryptography.fernet import Fernet, InvalidToken
from flask import current_app

class BankSecurityService:
    @staticmethod
    def _fernet():
        secret = (current_app.config.get("APP_ENCRYPTION_KEY") or "").strip()
        if not secret:
            raise RuntimeError("APP_ENCRYPTION_KEY must be configured before connecting bank accounts.")
        # Accept a Fernet key directly; otherwise derive a stable Fernet key from the secret.
        try:
            return Fernet(secret.encode("ascii"))
        except (ValueError, UnicodeEncodeError):
            key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode("utf-8")).digest())
            return Fernet(key)

    @staticmethod
    def encrypt(value):
        if not value:
            raise ValueError("A provider account identifier is required.")
        return BankSecurityService._fernet().encrypt(str(value).encode("utf-8")).decode("ascii")

    @staticmethod
    def decrypt(value):
        if not value:
            raise ValueError("Encrypted bank account identifier is missing.")
        try:
            return BankSecurityService._fernet().decrypt(value.encode("ascii")).decode("utf-8")
        except InvalidToken as exc:
            raise RuntimeError("Unable to decrypt bank account identifier. Verify APP_ENCRYPTION_KEY has not changed.") from exc
