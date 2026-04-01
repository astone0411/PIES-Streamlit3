"""
Authentication helpers for the Streamlit app.
Uses bcrypt for password hashing and st.session_state for session management.
"""

import bcrypt
import streamlit as st
from database.models import User, get_session


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def login(username: str, password: str) -> bool:
    """Attempt login. Returns True and sets session state on success."""
    session = get_session()
    user = session.query(User).filter_by(username=username, is_active=True).first()
    session.close()

    if user and verify_password(password, user.password_hash):
        st.session_state["authenticated"] = True
        st.session_state["user_id"]       = user.id
        st.session_state["username"]      = user.username
        st.session_state["display_name"]  = user.display_name
        st.session_state["role"]          = user.role
        return True
    return False


def logout():
    for key in ["authenticated", "user_id", "username", "display_name", "role"]:
        st.session_state.pop(key, None)


def is_authenticated() -> bool:
    return st.session_state.get("authenticated", False)


def require_auth():
    """Call at the top of any page that needs authentication."""
    if not is_authenticated():
        st.warning("Please log in to continue.")
        st.stop()


def current_user_id() -> int | None:
    return st.session_state.get("user_id")


def is_supervisor() -> bool:
    return st.session_state.get("role") == "supervisor"
