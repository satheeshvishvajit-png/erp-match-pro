"""
Authentication + role-based access control.

Streamlit has no built-in session/auth system, so we roll a small one on
top of `st.session_state`: passwords are bcrypt-hashed in the DB, and once
a user logs in we keep their id/role in session_state for the rest of the
browser session.
"""
import bcrypt
import streamlit as st

from modules.database import get_session
from modules.models import User, UserRole
from modules.utils.audit import log_action


def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_user(full_name: str, email: str, password: str, role: UserRole, avatar_color: str = "#2563EB") -> User:
    session = get_session()
    try:
        user = User(
            full_name=full_name,
            email=email.lower().strip(),
            password_hash=hash_password(password),
            role=role,
            avatar_color=avatar_color,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user
    finally:
        session.close()


def authenticate(email: str, password: str):
    """Returns the User on success, None on failure."""
    session = get_session()
    try:
        user = session.query(User).filter(User.email == email.lower().strip(), User.is_active.is_(True)).first()
        if user and verify_password(password, user.password_hash):
            from datetime import datetime
            user.last_login_at = datetime.utcnow()
            session.commit()
            return {
                "id": user.id,
                "full_name": user.full_name,
                "email": user.email,
                "role": user.role.value if hasattr(user.role, "value") else user.role,
                "avatar_color": user.avatar_color,
            }
        return None
    finally:
        session.close()


def login(email: str, password: str) -> bool:
    user = authenticate(email, password)
    if user is None:
        return False
    st.session_state["auth_user"] = user
    log_action(invoice_id=None, user_id=user["id"], action="LOGIN", details=f"{user['email']} signed in")
    return True


def logout():
    if "auth_user" in st.session_state:
        user = st.session_state["auth_user"]
        log_action(invoice_id=None, user_id=user["id"], action="LOGOUT", details=f"{user['email']} signed out")
    for key in ("auth_user",):
        st.session_state.pop(key, None)


def current_user():
    return st.session_state.get("auth_user")


def is_authenticated() -> bool:
    return "auth_user" in st.session_state


def require_login():
    """Call at the top of every page. Redirects to the login screen if needed."""
    if not is_authenticated():
        st.switch_page("app.py")
        st.stop()


def has_role(*roles) -> bool:
    user = current_user()
    if not user:
        return False
    role_values = [r.value if hasattr(r, "value") else r for r in roles]
    return user["role"] in role_values


def require_role(*roles):
    """Blocks the page with an error message if the current user lacks the role."""
    if not has_role(*roles):
        st.error("You don't have permission to view this page.")
        st.stop()
