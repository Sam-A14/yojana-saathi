from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


@lru_cache
def get_engine() -> Engine:
    # Created on first use, not at import time, so the app starts without a database configured.
    # pool_pre_ping: Neon pauses idle databases and drops connections; test them before use.
    return create_engine(get_settings().sqlalchemy_database_url, pool_pre_ping=True)


def new_session() -> Session:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)()
