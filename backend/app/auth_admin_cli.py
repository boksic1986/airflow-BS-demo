import argparse

from sqlalchemy import select

from app.auth_service import create_user, hash_password
from app.db import get_sessionmaker
from app.models import UserAccount


def main() -> int:
    parser = argparse.ArgumentParser(description="Create or update the initial WGS platform administrator.")
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()
    with get_sessionmaker()() as session:
        account = session.scalar(select(UserAccount).where(UserAccount.username == args.username.strip()))
        if account is None:
            create_user(session=session, username=args.username, password=args.password, role="admin")
        else:
            account.password_hash = hash_password(args.password)
            account.role = "admin"
            account.enabled = True
            session.commit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
