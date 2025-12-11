"""CLI commands and registration for session_manager."""

import argparse
import getpass
import sys

from managers.session_manager.session_manager import SessionManager
from managers.cli_manager import CLIManager, ModuleRegistration, Command, CommandArg


# ─────────────────────────────────────────────────────────────────────────────
# Handler Functions
# ─────────────────────────────────────────────────────────────────────────────

def create_user(args: argparse.Namespace) -> int:
    """Create a new user account."""
    sm = SessionManager()

    # Prompt for password if not provided
    password = getpass.getpass(f"Enter password for '{args.username}': ")
    if not password:
        print("Aborted: Empty password.", file=sys.stderr)
        return 1

    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("Aborted: Passwords do not match.", file=sys.stderr)
        return 1

    try:
        user = sm.create_user(args.username, password)
        print(f"User '{user.username}' created successfully (ID: {user.id}).")
        return 0
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def list_users(args: argparse.Namespace) -> int:
    """List all user accounts."""
    sm = SessionManager()

    with sm._get_db() as db:
        from managers.session_manager.models import User
        users = db.query(User).all()

        if not users:
            print("No users found.")
            return 0

        print("Users:")
        print(f"  {'ID':<6} {'Username':<20} {'Active':<8} {'Created'}")
        print(f"  {'-'*6} {'-'*20} {'-'*8} {'-'*20}")
        for user in users:
            created = user.created_at.strftime("%Y-%m-%d %H:%M") if user.created_at else "N/A"
            active = "Yes" if user.is_active else "No"
            print(f"  {user.id:<6} {user.username:<20} {active:<8} {created}")

    return 0


def revoke_sessions(args: argparse.Namespace) -> int:
    """Revoke all sessions for a user."""
    sm = SessionManager()

    user = sm.get_user(args.username)
    if not user:
        print(f"Error: User '{args.username}' not found.", file=sys.stderr)
        return 1

    count = sm.revoke_sessions(user.id)
    if count > 0:
        print(f"Revoked {count} session(s) for user '{args.username}'.")
    else:
        print(f"No active sessions found for user '{args.username}'.")
    return 0


def delete_user(args: argparse.Namespace) -> int:
    """Delete a user account."""
    sm = SessionManager()

    user = sm.get_user(args.username)
    if not user:
        print(f"Error: User '{args.username}' not found.", file=sys.stderr)
        return 1

    # Confirm deletion
    if not args.force:
        confirm = input(f"Delete user '{args.username}'? This cannot be undone. [y/N]: ")
        if confirm.lower() != "y":
            print("Aborted.")
            return 0

    with sm._get_db() as db:
        from managers.session_manager.models import User
        db_user = db.query(User).filter(User.id == user.id).first()
        if db_user:
            db.delete(db_user)
            db.commit()
            print(f"User '{args.username}' deleted.")
            return 0

    print(f"Error: Failed to delete user.", file=sys.stderr)
    return 1


def session_list(args: argparse.Namespace) -> int:
    """List all sessions (optionally for a specific user)."""
    from datetime import datetime, timezone

    sm = SessionManager()

    with sm._get_db() as db:
        from managers.session_manager.models import Session, User

        query = db.query(Session).join(User)
        if args.username:
            query = query.filter(User.username == args.username)

        sessions = query.all()

        if not sessions:
            print("No sessions found.")
            return 0

        print("Sessions:")
        print(f"  {'ID':<6} {'User':<15} {'Created':<17} {'Expires':<17} {'Status'}")
        print(f"  {'-'*6} {'-'*15} {'-'*17} {'-'*17} {'-'*10}")
        for s in sessions:
            created = s.created_at.strftime("%Y-%m-%d %H:%M") if s.created_at else "N/A"
            expires = s.expires_at.strftime("%Y-%m-%d %H:%M") if s.expires_at else "Never"

            # Determine status safely (handle timezone-naive datetimes from SQLite)
            if s.is_revoked:
                status = "Revoked"
            elif s.expires_at:
                now = datetime.now(timezone.utc)
                expires_at = s.expires_at
                # Make timezone-aware if naive
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                status = "Active" if now < expires_at else "Expired"
            else:
                status = "Active"

            print(f"  {s.id:<6} {s.user.username:<15} {created:<17} {expires:<17} {status}")

    return 0


# ─────────────────────────────────────────────────────────────────────────────
# CLI Registration
# ─────────────────────────────────────────────────────────────────────────────

def register_cli() -> None:
    """Register session_manager commands with CLIManager."""
    cli = CLIManager()
    cli.register_module(ModuleRegistration(
        module_name="session_manager",
        short_name="ssm",
        description="User and session management",
        commands=[
            Command(
                name="create-user",
                help="Create a new user account",
                handler="managers.session_manager.session_manager_cli:create_user",
                args=[
                    CommandArg(name="username", help="Username for the new account"),
                ],
            ),
            Command(
                name="list-users",
                help="List all user accounts",
                handler="managers.session_manager.session_manager_cli:list_users",
            ),
            Command(
                name="revoke",
                help="Revoke all sessions for a user",
                handler="managers.session_manager.session_manager_cli:revoke_sessions",
                args=[
                    CommandArg(name="username", help="Username to revoke sessions for"),
                ],
            ),
            Command(
                name="delete-user",
                help="Delete a user account",
                handler="managers.session_manager.session_manager_cli:delete_user",
                args=[
                    CommandArg(name="username", help="Username to delete"),
                    CommandArg(
                        name="--force",
                        short="-f",
                        help="Skip confirmation prompt",
                        action="store_true",
                    ),
                ],
            ),
            Command(
                name="session-list",
                help="List all sessions",
                handler="managers.session_manager.session_manager_cli:session_list",
                args=[
                    CommandArg(
                        name="--username",
                        short="-u",
                        help="Filter by username",
                    ),
                ],
            ),
        ],
    ))
