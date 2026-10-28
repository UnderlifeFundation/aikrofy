"""
Database Manager Utility
Provides robust anti-disconnect mechanisms for MySQL connections.

Usage:
    from utils.db_manager import ensure_db_fresh

    # Before any DB operation after a long pause (e.g., post-LLM call):
    ensure_db_fresh()
    db.session.add(message)
    db.session.commit()
"""
from extensions import db


def ensure_db_fresh():
    """
    Clear any pending/failed transaction state so the next DB operation
    gets a clean connection from the pool.
    
    Uses ONLY rollback() — this resets the transaction state without
    detaching existing SQLAlchemy objects from the session. Combined with
    pool_pre_ping=True in config.py, the pool will automatically verify
    the MySQL connection is alive before the next query.
    
    IMPORTANT: We intentionally do NOT call db.session.remove() here
    because that would detach all loaded objects (Agent, Conversation, etc.)
    causing DetachedInstanceError in the middle of request flows.
    
    Safe to call multiple times — it's a no-op if the session is already clean.
    """
    try:
        db.session.rollback()
    except Exception:
        pass
