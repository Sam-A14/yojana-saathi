from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.timing import install_query_timing


@lru_cache
def get_engine() -> Engine:
    # Created on first use, not at import time, so the app starts without a database configured.
    # pool_pre_ping: Neon pauses idle databases and drops connections; test them before use.
    engine = create_engine(get_settings().sqlalchemy_database_url, pool_pre_ping=True)
    install_query_timing(engine)  # per-request timing, see app/timing.py
    return engine


def new_session() -> Session:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)()
