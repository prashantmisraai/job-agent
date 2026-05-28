"""Lightweight access control for the Streamlit app.

Users are configured through Streamlit secrets or environment variables. Passwords
are stored as PBKDF2 hashes so the deployed app never needs plaintext passwords.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass
from typing import Dict, Mapping


HASH_PREFIX = "pbkdf2_sha256"
ITERATIONS = 260_000


@dataclass(frozen=True)
class AuthUser:
    """Configured application user."""

    username: str
    password_hash: str
    display_name: str = ""


def hash_password(password: str, *, salt: bytes | None = None) -> str:
    """Return a portable PBKDF2-SHA256 hash for a plaintext password."""

    if not password:
        raise ValueError("Password cannot be empty.")

    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    encoded_salt = base64.urlsafe_b64encode(salt).decode("ascii").rstrip("=")
    encoded_digest = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return f"{HASH_PREFIX}${ITERATIONS}${encoded_salt}${encoded_digest}"


def verify_password(password: str, password_hash: str) -> bool:
    """Validate a plaintext password against a stored PBKDF2 hash."""

    try:
        prefix, iterations, encoded_salt, encoded_digest = password_hash.split("$", 3)
        if prefix != HASH_PREFIX:
            return False
        salt = _decode_urlsafe_b64(encoded_salt)
        expected = _decode_urlsafe_b64(encoded_digest)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
    except (ValueError, TypeError):
        return False

    return hmac.compare_digest(actual, expected)


def require_login() -> AuthUser | None:
    """Render login UI and stop the app until a configured user is authenticated."""

    import streamlit as st

    users = load_users()
    if not users:
        st.error("Authentication is enabled, but no users are configured.")
        st.info("Add users in `.streamlit/secrets.toml` or the `JOB_ASSISTANT_USERS` environment variable.")
        st.stop()

    if st.session_state.get("auth_user") in users:
        return users[st.session_state["auth_user"]]

    st.markdown("## Sign in")
    st.caption("Use the account shared by the app owner.")
    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("Email or username").strip().lower()
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in", type="primary")

    if submitted:
        user = users.get(username)
        if user and verify_password(password, user.password_hash):
            st.session_state["auth_user"] = user.username
            st.rerun()
        st.error("Invalid username or password.")

    st.stop()


def logout_button() -> None:
    """Render a small logout button in the sidebar."""

    import streamlit as st

    username = st.session_state.get("auth_user", "")
    if username:
        st.caption(f"Signed in as {username}")
        if st.button("Sign out", use_container_width=True):
            st.session_state.pop("auth_user", None)
            st.rerun()


def load_users() -> Dict[str, AuthUser]:
    """Load users from Streamlit secrets first, then environment variables.

    Supported Streamlit secrets:

    [auth.users.alice]
    username = "alice@example.com"
    password_hash = "pbkdf2_sha256$..."
    display_name = "Alice"

    Supported environment variable:
    JOB_ASSISTANT_USERS=alice@example.com:pbkdf2_sha256$...,bob@example.com:pbkdf2_sha256$...
    """

    users: Dict[str, AuthUser] = {}
    users.update(_users_from_streamlit_secrets())
    users.update(_users_from_env(os.getenv("JOB_ASSISTANT_USERS", "")))
    return users


def _users_from_streamlit_secrets() -> Dict[str, AuthUser]:
    try:
        import streamlit as st
    except ImportError:
        return {}

    try:
        auth_config = st.secrets.get("auth", {})
    except Exception:
        return {}

    raw_users = auth_config.get("users", {}) if isinstance(auth_config, Mapping) else {}
    users: Dict[str, AuthUser] = {}
    for fallback_username, user_config in raw_users.items():
        if not isinstance(user_config, Mapping):
            continue
        username = str(user_config.get("username", fallback_username)).strip().lower()
        password_hash = str(user_config.get("password_hash", "")).strip()
        display_name = str(user_config.get("display_name", "")).strip()
        if username and password_hash:
            users[username] = AuthUser(username=username, password_hash=password_hash, display_name=display_name)
    return users


def _users_from_env(raw_value: str) -> Dict[str, AuthUser]:
    users: Dict[str, AuthUser] = {}
    for pair in raw_value.split(","):
        if ":" not in pair:
            continue
        username, password_hash = pair.split(":", 1)
        username = username.strip().lower()
        password_hash = password_hash.strip()
        if username and password_hash:
            users[username] = AuthUser(username=username, password_hash=password_hash)
    return users


def _decode_urlsafe_b64(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)
