import math
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session, scoped_session, DeclarativeBase, Query
from config import get_config

config = get_config()

# Database Engine Setup for FastAPI-native operations
engine = create_engine(
    config.SQLALCHEMY_DATABASE_URI,
    **config.SQLALCHEMY_ENGINE_OPTIONS
)

class Pagination:
    def __init__(self, query, page, per_page, total, items):
        self.query = query
        self.page = page
        self.per_page = per_page
        self.total = total
        self.items = items

    @property
    def pages(self):
        if self.per_page == 0 or self.total is None:
            return 0
        return math.ceil(self.total / self.per_page)

class CustomQuery(Query):
    def get_or_404(self, ident, description=None):
        rv = self.get(ident)
        if rv is None:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail=description or "Resource not found")
        return rv

    def paginate(self, page=1, per_page=20, error_out=True, max_per_page=None):
        if page is None:
            page = 1
        if per_page is None:
            per_page = 20
        if max_per_page is not None:
            per_page = min(per_page, max_per_page)

        total = self.count()
        items = self.limit(per_page).offset((page - 1) * per_page).all()
        return Pagination(self, page, per_page, total, items)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, query_cls=CustomQuery)
db_session = scoped_session(SessionLocal)

class QueryProperty:
    def __get__(self, instance, owner):
        return db_session.query(owner)

class Base(DeclarativeBase):
    query = QueryProperty()

# Dependency to get DB session (for native FastAPI routes)
def get_db():
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        yield db
    finally:
        db.close()


# ── Resilient session teardown ────────────────────────────────────────────────
# MySQL drops idle connections during long-running AI calls (60-90s).
# When db_session.remove() tries to ROLLBACK on a dead socket it raises
# OperationalError — which crashes the middleware and returns a 500 even
# though the AI response was already saved successfully.
#
# Pattern adapted from enpiai/backend/extensions.py::resilient_rollback:
# If remove() fails, invalidate the underlying DBAPI connection so the pool
# discards it and issues a fresh connection on the next request.

_original_remove = db_session.remove

def _resilient_remove():
    try:
        _original_remove()
    except Exception as exc:
        import logging as _logging
        _logging.getLogger("database").warning(
            f"db_session.remove() raised (likely MySQL gone away): {exc!r}. "
            "Invalidating connection and clearing registry."
        )
        # Attempt to invalidate the underlying DBAPI connection
        try:
            session = db_session.registry()
            conn = session.connection()
            conn.invalidate()
        except Exception:
            pass
        # Force-clear the thread-local registry so next request gets a fresh session
        try:
            db_session.registry.registry.clear()
        except Exception:
            pass

db_session.remove = _resilient_remove
# ─────────────────────────────────────────────────────────────────────────────
