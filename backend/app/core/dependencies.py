"""
FastAPI dependency injection functions.

CRITICAL: All request-scoped dependencies live here. Import get_db_session
from THIS module — never from app.core.database directly. FastAPI de-duplicates
dependencies by object identity; importing from two different module paths
produces two separate sessions, breaking RLS enforcement.

get_tenant_context and role-checking helpers will be added in Phase 3.
"""

from app.core.database import get_db_session  # noqa: F401 — re-exported as canonical source

__all__ = ["get_db_session"]
