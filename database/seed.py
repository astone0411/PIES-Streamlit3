"""
Seed initial users so the app is usable on first run.
Default credentials should be changed immediately in production.
"""

import bcrypt
from database.models import User


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def seed_default_users(session):
    """Create default users only if the users table is empty."""
    if session.query(User).count() > 0:
        return

    defaults = [
        User(
            username="admin",
            display_name="Lab Administrator",
            password_hash=hash_password("admin123"),
            role="supervisor",
        ),
        User(
            username="tech1",
            display_name="Lab Technician 1",
            password_hash=hash_password("tech123"),
            role="technician",
        ),
        User(
            username="amy",
            display_name="Amy",
            password_hash=hash_password("tech123"),
            role="technician",
        ),
        User(
            username="jessa",
            display_name="Jessa",
            password_hash=hash_password("admin123"),
            role="supervisor",
        ),
        User(
            username="trista",
            display_name="Trista",
            password_hash=hash_password("admin123"),
            role="supervisor",
        ),
        User(
            username="joseph",
            display_name="Joseph",
            password_hash=hash_password("tech123"),
            role="technician",
        )
    ]

    for user in defaults:
        session.add(user)
    session.commit()
    print("✅ Default users seeded (admin / tech1)")
