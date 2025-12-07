# Session Manager

Token-based session management with user authentication using SQLAlchemy.

## Overview

- Creates and validates session tokens for users
- Manages user accounts with secure password hashing
- Uses SQLAlchemy for flexible database backend
- Integrates with auth_manager for password operations

## Features

- User creation with secure password hashing
- Session token generation and validation
- Session expiration support
- Single and bulk session revocation
- Convenient login/logout methods
- SQLite by default, supports any SQLAlchemy database

## Quickstart

```python
from managers.session_manager import SessionManager

sm = SessionManager()

# Create a user
user = sm.create_user("alice", "secure_password")

# Login (authenticate + create session)
token = sm.login("alice", "secure_password")

# Validate session
user = sm.validate_session(token)
if user:
    print(f"Logged in as {user.username}")

# Logout
sm.logout(token)
```

## API

```python
class SessionManager:
    def __init__(
        self,
        db_url: str | None = None,
        session_duration_days: int = 30,
    ): ...

    # User management
    def create_user(self, username: str, password: str) -> User: ...
    def get_user(self, username: str) -> User | None: ...
    def authenticate_user(self, username: str, password: str) -> User | None: ...

    # Session management
    def create_session(self, user_id: int) -> str: ...
    def validate_session(self, token: str) -> User | None: ...
    def revoke_session(self, token: str) -> bool: ...
    def revoke_sessions(self, user_id: int) -> int: ...

    # Convenience methods
    def login(self, username: str, password: str) -> str | None: ...
    def logout(self, token: str) -> bool: ...
```

## Custom Database

```python
# Use PostgreSQL
sm = SessionManager(db_url="postgresql://user:pass@localhost/mydb")

# Use MySQL
sm = SessionManager(db_url="mysql://user:pass@localhost/mydb")

# Custom session duration
sm = SessionManager(session_duration_days=7)
```

## Requirements

- `sqlalchemy>=2.0.0`

## Module Structure

```
managers/session_manager/
├── __init__.py          # Module exports
├── init.yaml            # Module metadata
├── session_manager.py   # SessionManager class
├── models.py            # User and Session SQLAlchemy models
├── requirements.txt     # SQLAlchemy dependency
└── README.md            # This file
```

## See Also

- Auth Manager - For standalone password operations
- Secret Manager - For storing API keys securely
