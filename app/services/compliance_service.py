from datetime import datetime
import hashlib

from flask import request, g

from app.extensions import db
from app.models.compliance import PolicyDocument, PolicyAcceptance


REQUIRED_REGISTRATION_POLICIES = (
    "terms",
    "privacy",
    "ai-disclosure",
)


class ComplianceService:
    @staticmethod
    def current_policy(slug):
        return PolicyDocument.query.filter_by(
            slug=slug,
            is_current=True,
        ).first()

    @staticmethod
    def _validate_policy_version(version):
        """
        Validate FOCOST policy version format.

        Expected format:
            major.minor

        Examples:
            1.0
            1.1
            1.2
            ...
            1.9
            2.0
            2.1
            ...
            2.9
            3.0
        """
        if not isinstance(version, str):
            raise ValueError(
                "Policy version must be a string in major.minor format."
            )

        version = version.strip()
        parts = version.split(".")

        if len(parts) != 2 or not all(
            part.isascii() and part.isdecimal()
            for part in parts
        ):
            raise ValueError(
                "Invalid policy version. Expected major.minor format "
                "(for example, 1.0, 1.1, 1.9 or 2.0)."
            )

        major, minor = (int(part) for part in parts)

        return major, minor

    @staticmethod
    def publish_policy(
        *,
        slug,
        title,
        version,
        document_type,
        summary,
        content_html,
        effective_at=None,
    ):
        """
        Publish a new immutable policy version.

        Rules:
            - An existing slug/version may never be overwritten.
            - Existing versions must have identical content hashes.
            - A new version must be greater than the current version.
            - A new version creates a new PolicyDocument row.
            - The previous current version is retired.
            - The new version becomes current.
            - Policy content and hashes are immutable after publication.
            - This method does not commit the transaction.
        """
        if not slug:
            raise ValueError("Policy slug is required.")

        if not version:
            raise ValueError("Policy version is required.")

        if not content_html:
            raise ValueError(
                f"Policy '{slug}' version '{version}' cannot have empty content."
            )

        new_version = ComplianceService._validate_policy_version(version)

        content_hash = hashlib.sha256(
            content_html.encode("utf-8")
        ).hexdigest()

        # ---------------------------------------------------------
        # Existing published version
        # ---------------------------------------------------------
        existing = PolicyDocument.query.filter_by(
            slug=slug,
            version=version,
        ).first()

        if existing is not None:
            if existing.content_hash != content_hash:
                raise ValueError(
                    "Immutable policy violation: "
                    f"{slug} version {version} already exists "
                    "with different content. "
                    "Published policy versions cannot be overwritten."
                )

            return existing

        # ---------------------------------------------------------
        # Determine current published version
        # ---------------------------------------------------------
        current = PolicyDocument.query.filter_by(
            slug=slug,
            is_current=True,
        ).first()

        if current is not None:
            current_version = ComplianceService._validate_policy_version(
                current.version
            )

            if new_version <= current_version:
                raise ValueError(
                    f"Policy version {version} must be newer than "
                    f"the current {slug} version {current.version}."
                )

            # Allowed immutable-state transition:
            # historical version -> no longer current.
            current.is_current = False

        # ---------------------------------------------------------
        # Create new immutable version
        # ---------------------------------------------------------
        policy = PolicyDocument(
            slug=slug,
            title=title,
            version=version,
            document_type=document_type,
            summary=summary,
            content_html=content_html,
            effective_at=effective_at or datetime.utcnow(),
            is_current=True,
            content_hash=content_hash,
        )

        db.session.add(policy)

        # Force constraint/event validation immediately.
        db.session.flush()

        return policy

    @staticmethod
    def accept(user, slugs, ip_address=None, user_agent=None):
        """
        Record acceptance of the current versions of the supplied
        policies.

        Published policy documents are immutable. A missing content
        hash is therefore treated as a data-integrity error rather
        than silently modifying the policy during acceptance.
        """
        now = datetime.utcnow()

        for slug in slugs:
            policy = ComplianceService.current_policy(slug)

            if not policy:
                raise ValueError(
                    f"Required policy is unavailable: {slug}"
                )

            if not policy.content_hash:
                raise ValueError(
                    "Policy integrity error: "
                    f"current policy '{slug}' version "
                    f"{policy.version} has no content hash."
                )

            existing = PolicyAcceptance.query.filter_by(
                user_id=user.id,
                policy_id=policy.id,
                policy_version=policy.version,
            ).first()

            if not existing:
                db.session.add(
                    PolicyAcceptance(
                        user_id=user.id,
                        policy_id=policy.id,
                        policy_version=policy.version,
                        accepted_at=now,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        session_id=request.cookies.get("session"),
                        request_id=g.get("request_id"),
                        action="ACCEPTED",
                        source="web",
                        authenticated=True,
                        auth_method="password",
                        content_hash=policy.content_hash,
                    )
                )

    @staticmethod
    def accepted_current(user, slug):
        policy = ComplianceService.current_policy(slug)

        if not policy:
            return False

        return (
            PolicyAcceptance.query.filter_by(
                user_id=user.id,
                policy_id=policy.id,
                policy_version=policy.version,
            ).first()
            is not None
        )