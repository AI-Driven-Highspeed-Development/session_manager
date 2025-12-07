"""Session management with user authentication and token handling."""

from __future__ import annotations

import secrets
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Iterator, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session as DBSession, sessionmaker

from managers.auth_manager import AuthManager
from managers.config_manager import ConfigManager
from managers.session_manager.models import Base, User, Session
from utils.logger_util import Logger


class SessionManager:
    """Manages user sessions with token-based authentication."""

    def __init__(
        self,
        db_url: Optional[str] = None,
        session_duration_days: Optional[int] = None,
    ) -> None:
        self.logger = Logger(name=__class__.__name__)
        self.config = ConfigManager().config.session_manager

        self._db_url = db_url or self.config.database.url
        duration = session_duration_days or self.config.session.duration_days
        self._session_duration = timedelta(days=duration)

        self._auth = AuthManager()

        self._engine = create_engine(self._db_url)
        Base.metadata.create_all(self._engine)
        self._session_factory = sessionmaker(bind=self._engine, expire_on_commit=False)

    # ---------------- User Management ----------------

    def create_user(self, username: str, password: str) -> User:
        """Create a new user with hashed password."""
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
        """Get a user by username."""
        with self._get_db() as db:
            return db.query(User).filter(User.username == username).first()

    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate a user with username and password."""
        with self._get_db() as db:
            user = db.query(User).filter(User.username == username).first()
            if user and self._auth.verify_password(password, user.password_hash):
                return user
            return None

    # ---------------- Session Management ----------------

    def create_session(self, user_id: int) -> str:
        """Create a new session token for a user."""
        token = secrets.token_hex(self.config.session.token_length)
        expires_at = datetime.now(timezone.utc) + self._session_duration

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
        """Validate a session token and return the associated user."""
        with self._get_db() as db:
            session = db.query(Session).filter(Session.token == token).first()
            if session and session.is_valid:
                return session.user
            return None

    def revoke_session(self, token: str) -> bool:
        """Revoke a specific session token."""
        with self._get_db() as db:
            session = db.query(Session).filter(Session.token == token).first()
            if session:
                session.is_revoked = True
                db.commit()
                return True
            return False

    def revoke_sessions(self, user_id: int) -> int:
        """Revoke all sessions for a user."""
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
        """Authenticate user and create a session in one step."""
        user = self.authenticate_user(username, password)
        if user:
            return self.create_session(user.id)
        return None

    def logout(self, token: str) -> bool:
        """Logout by revoking the session token."""
        return self.revoke_session(token)

    # ---------------- Private Methods ----------------

    @contextmanager
    def _get_db(self) -> Iterator[DBSession]:
        """Get a database session context manager."""
        session = self._session_factory()
        try:
            yield session
        finally:
            session.close()
