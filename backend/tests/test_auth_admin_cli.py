import sys

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import auth_admin_cli
from app.auth_service import hash_password
from app.models import Base, UserAccount


def test_admin_bootstrap_does_not_reset_an_existing_account(monkeypatch) -> None:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    original_hash = hash_password("operator-selected-password")
    with sessions.begin() as session:
        session.add(
            UserAccount(
                username="admin",
                password_hash=original_hash,
                role="viewer",
                enabled=False,
            )
        )
    monkeypatch.setattr(auth_admin_cli, "get_sessionmaker", lambda: sessions)
    monkeypatch.setattr(
        sys,
        "argv",
        ["auth_admin_cli", "--username", "admin", "--password", "bootstrap-only"],
    )

    assert auth_admin_cli.main() == 0

    with sessions() as session:
        account = session.scalar(
            select(UserAccount).where(UserAccount.username == "admin")
        )
        assert account is not None
        assert account.password_hash == original_hash
        assert account.role == "viewer"
        assert account.enabled is False

