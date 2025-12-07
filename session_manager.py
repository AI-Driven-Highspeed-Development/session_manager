"""Session management with user authentication and token handling."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session as DBSession, sessionmaker

from managers.auth_manager import AuthManager
from managers.session_manager.models import Base, User, Session


class SessionManager:
    """Manages user sessions with token-based authentication.

    Handles user creation, session token generation, validation, and revocation.
    Uses SQLAlchemy for persistence with configurable database backend.

    Default database: SQLite at project/data/sessions.db
    """

    DEFAULT_DB_URL = "sqlite:///project/data/sessions.db"
    DEFAULT_TOKEN_LENGTH = 32
    DEFAULT_SESSION_DURATION_DAYS = 30

    def __init__(
        self,
        db_url: Optional[str] = None,
        session_duration_days: int = DEFAULT_SESSION_DURATION_DAYS,
    ) -> None:
        """Initialize SessionManager.

        Args:
            db_url: SQLAlchemy database URL. Defaults to SQLite.
            session_duration_days: Session validity period in days.
        """
        self._db_url = db_url or self.DEFAULT_DB_URL
        self._session_duration = timedelta(days=session_duration_days)
        self._auth = AuthManager()

        self._engine = create_engine(self._db_url)
        Base.metadata.create_all(self._engine)
        self._session_factory = sessionmaker(bind=self._engine)

    # ---------------- User Management ----------------

    def create_user(self, username: str, password: str) -> User:
        """Create a new user with hashed password.

        Args:
            username: Unique username.
            password: Plaintext password (will be hashed).

        Returns:
            The created User object.

        Raises:
            ValueError: If username already exists.
        """
        password_hash = self._auth.hash_password(password)

        with self._get_db() as db:
            existing = db.query(User).filter(User.username == username).first()
            if existing:
                raise ValueError(f"User '{username}' already exists")

            user = User(username=username, password_hash=password_hash)
            db.add(user)
            db.commit()
            db.refresh(user)
            return user

    def get_user(self, username: str) -> Optional[User]:
        """Get a user by username.

        Args:
            username: The username to look up.

        Returns:
            The User object or None if not found.
        """
        with self._get_db() as db:
            return db.query(User).filter(User.username == username).first()

    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate a user with username and password.

        Args:
            username: The username.
            password: The plaintext password.

        Returns:
            The User object if credentials are valid, None otherwise.
        """
        with self._get_db() as db:
            user = db.query(User).filter(User.username == username).first()
            if user and self._auth.verify_password(password, user.password_hash):
                return user
            return None

    # ---------------- Session Management ----------------

    def create_session(self, user_id: int) -> str:
        """Create a new session token for a user.

        Args:
            user_id: The user's ID.

        Returns:
            The session token string.

        Raises:
            ValueError: If user does not exist.
        """
        token = secrets.token_hex(self.DEFAULT_TOKEN_LENGTH)
        expires_at = datetime.utcnow() + self._session_duration

        with self._get_db() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError(f"User with id {user_id} not found")

            session = Session(
                user_id=user_id,
                token=token,
                expires_at=expires_at,
            )
            db.add(session)
            db.commit()
            return token

    def validate_session(self, token: str) -> Optional[User]:
        """Validate a session token and return the associated user.

        Args:
            token: The session token to validate.

        Returns:
            The User object if token is valid, None otherwise.
        """
        with self._get_db() as db:
            session = db.query(Session).filter(Session.token == token).first()
            if session and session.is_valid:
                return session.user
            return None

    def revoke_session(self, token: str) -> bool:
        """Revoke a specific session token.

        Args:
            token: The session token to revoke.

        Returns:
            True if session was revoked, False if not found.
        """
        with self._get_db() as db:
            session = db.query(Session).filter(Session.token == token).first()
            if session:
                session.is_revoked = True
                db.commit()
                return True
            return False

    def revoke_sessions(self, user_id: int) -> int:
        """Revoke all sessions for a user.

        Args:
            user_id: The user's ID.

        Returns:
            Number of sessions revoked.
        """
        with self._get_db() as db:
            sessions = db.query(Session).filter(
                Session.user_id == user_id,
                Session.is_revoked == False,
            ).all()
            count = len(sessions)
            for session in sessions:
                session.is_revoked = True
            db.commit()
            return count

    def login(self, username: str, password: str) -> Optional[str]:
        """Authenticate user and create a session in one step.

        Args:
            username: The username.
            password: The plaintext password.

        Returns:
            Session token if login successful, None otherwise.
        """
        user = self.authenticate_user(username, password)
        if user:
            return self.create_session(user.id)
        return None

    def logout(self, token: str) -> bool:
        """Logout by revoking the session token.

        Args:
            token: The session token to revoke.

        Returns:
            True if logged out successfully.
        """
        return self.revoke_session(token)

    # ---------------- Private Methods ----------------

    def _get_db(self) -> DBSession:
        """Get a database session context manager."""
        return self._session_factory()
