"""
FastAPI dependencies.

Both get_engine() and get_session() are injectable.
Tests override get_engine() via app.dependency_overrides — all routes
depending on either automatically receive the test engine.
"""

import os
from collections.abc import Generator

from fastapi import Depends
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session


_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./poker_geeks_lab.db")
_engine = create_engine(_DATABASE_URL)


def get_engine() -> Engine:
    return _engine


def get_session(engine: Engine = Depends(get_engine)) -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
