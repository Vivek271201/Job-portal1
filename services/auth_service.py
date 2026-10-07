"""Passwords, sessions, flash messages and CSRF tokens."""
import secrets
import time

import bcrypt

SESSION_SHORT = 12 * 3600          # normal login: 12 hours
SESSION_LONG = 30 * 24 * 3600      # "remember me": 30 days


def _prep(pw: str) -> bytes:
    return pw.encode("utf-8")[:72]  # bcrypt only uses the first 72 bytes


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(_prep(pw), bcrypt.gensalt(rounds=12)).decode()


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_prep(pw), hashed.encode())
    except (ValueError, TypeError):
        return False


DUMMY_HASH = hash_password("not-a-real-password-1")  # used to equalise login timing


def login_user(request, user, remember: bool = False):
    request.session.clear()  # new session id data -> prevents session fixation
    request.session["user_id"] = user.id
    request.session["exp"] = time.time() + (SESSION_LONG if remember else SESSION_SHORT)
    request.session["csrf"] = secrets.token_hex(16)


def logout_user(request):
    request.session.clear()


def dashboard_url(user) -> str:
    return "/employer/dashboard" if user.role == "employer" else "/seeker/dashboard"


def flash(request, message: str, category: str = "success"):
    request.session.setdefault("_flash", []).append([category, message])


def get_csrf_token(request) -> str:
    try:
        session = request.session
    except AssertionError:
        return ""
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    return session["csrf"]


def safe_next(url: str, default: str) -> str:
    """Only allow redirects to local paths (prevents open redirects)."""
    if url and url.startswith("/") and not url.startswith("//") and "\\" not in url:
        return url
    return default
