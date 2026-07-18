"""
SQLAlchemy engine/session setup.

One engine for the whole app, created lazily so importing this module never
has side effects (important because Streamlit re-imports pages on every
rerun). `get_session()` is what the rest of the code should use.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

import config

Base = declarative_base()

_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        connect_args = {}
        if config.DATABASE_URL.startswith("sqlite"):
            # Needed because Streamlit talks to the DB from multiple threads.
            connect_args = {"check_same_thread": False}
        _engine = create_engine(config.DATABASE_URL, connect_args=connect_args)
    return _engine


def get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)
    return _SessionLocal


def get_session():
    """Return a fresh Session. Caller is responsible for closing it
    (use as a context manager or call .close())."""
    return get_session_factory()()


def init_db():
    """Create all tables if they don't exist yet. Safe to call repeatedly."""
    from modules import models  # noqa: F401  (registers all model classes on Base)
    Base.metadata.create_all(get_engine())
