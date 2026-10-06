# Security Notice — Credentials Found in Supplied Archive

The source archive supplied for this implementation contained credentials in `.env`, including AI-provider and Paystack test credentials.

For security:

1. Do not commit or distribute `.env`.
2. Revoke/rotate every credential that appeared in the supplied archive before production use.
3. Generate new production secrets for `SECRET_KEY`, `APP_ENCRYPTION_KEY`, AI provider keys, Paystack credentials and SMTP credentials.
4. Store secrets only in the deployment environment/secret manager.
5. Review Git history and any copies of the original archive because deleting `.env` from the working tree does not invalidate a previously exposed credential.

The production package generated from this work intentionally excludes `.env`, `.git`, `.venv`, local databases, recovery databases, backups and Python bytecode.
