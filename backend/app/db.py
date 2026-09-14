from functools import lru_cache

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


@lru_cache
def get_engine() -> Engine:
    return create_engine(get_settings().database_url, pool_pre_ping=True)


@lru_cache
def get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)


@lru_cache
def get_reference_sessionmaker() -> sessionmaker[Session]:
    """Dedicated bounded pool for best-effort projection, not request traffic."""
    url = get_settings().database_url
    if make_url(url).get_backend_name() == "postgresql":
        engine = create_engine(
            url, pool_pre_ping=True, pool_timeout=5,
            connect_args={"connect_timeout": 5,
                          "options": "-c statement_timeout=15000 -c lock_timeout=500"},
        )
    else:
        engine = create_engine(url, connect_args={"timeout": 0.5})
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def check_database() -> None:
    with get_engine().connect() as connection:
        connection.execute(text("select 1"))
