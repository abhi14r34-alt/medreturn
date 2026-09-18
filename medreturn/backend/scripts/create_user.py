"""Create a privileged account.

Registration through the API only ever creates household users, so admin,
hospital and collector logins are made here by someone with database
access. The password is prompted for, never passed as an argument, so it
does not end up in shell history.

    python -m scripts.create_user --role admin --username admin \
        --email admin@medreturn.in --name "System Administrator"
"""

import argparse
import getpass
import sys

from sqlalchemy import or_, select

from app.core.constants import Role
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import Collector, Credit, Hospital, User


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a MedReturn account.")
    parser.add_argument("--role", required=True,
                        choices=[r.value for r in Role])
    parser.add_argument("--username", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--phone", default=None)
    parser.add_argument("--address", default=None)
    parser.add_argument("--hospital-id", type=int, default=None,
                        help="Required for the hospital role.")
    parser.add_argument("--zone", default=None, help="Collector zone.")
    parser.add_argument("--vehicle", default=None, help="Collector vehicle number.")
    args = parser.parse_args()

    password = getpass.getpass("Password: ")
    if len(password) < 8:
        print("Password must be at least 8 characters.", file=sys.stderr)
        return 1
    if password != getpass.getpass("Confirm password: "):
        print("Passwords do not match.", file=sys.stderr)
        return 1

    db = SessionLocal()
    try:
        username = args.username.strip().lower()
        email = args.email.strip().lower()

        if db.execute(select(User).where(
            or_(User.username == username, User.email == email)
        )).scalar_one_or_none():
            print("That username or email already exists.", file=sys.stderr)
            return 1

        if args.role == Role.HOSPITAL.value:
            if args.hospital_id is None:
                print("--hospital-id is required for the hospital role.", file=sys.stderr)
                return 1
            if db.get(Hospital, args.hospital_id) is None:
                print(f"No hospital with id {args.hospital_id}.", file=sys.stderr)
                return 1

        user = User(
            username=username,
            email=email,
            full_name=args.name,
            phone=args.phone,
            address=args.address,
            password_hash=hash_password(password),
            role=args.role,
            hospital_id=args.hospital_id,
        )
        db.add(user)
        db.flush()

        if args.role == Role.HOUSEHOLD.value:
            db.add(Credit(user_id=user.id))
        elif args.role == Role.COLLECTOR.value:
            db.add(Collector(
                user_id=user.id, name=args.name, phone=args.phone,
                zone=args.zone, vehicle_number=args.vehicle,
            ))

        db.commit()
        print(f"Created {args.role} account '{username}' (id {user.id}).")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
