"""FastAPI dependencies: current user, role checks and CSRF protection."""
import hmac
import time

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import JobSeeker, User


class LoginRequired(Exception):
    def __init__(self, next_url: str = "/"):
        self.next_url = next_url


async def verify_csrf(request: Request):
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        form = await request.form()
        sent = str(form.get("csrf_token") or request.headers.get("x-csrf-token") or "")
        expected = request.session.get("csrf")
        if not expected or not sent or not hmac.compare_digest(sent, expected):
            raise HTTPException(403, "Your session security token is missing or expired. "
                                     "Please go back, refresh the page and try again.")


def load_user(request: Request, db: Session = Depends(get_db)):
    user = None
    uid = request.session.get("user_id")
    if uid:
        if request.session.get("exp", 0) > time.time():
            user = db.get(User, uid)
        if user is None or not user.is_active:
            request.session.clear()
            user = None
    request.state.user = user
    return user


def require_user(request: Request, user=Depends(load_user)) -> User:
    if user is None:
        q = request.url.query
        raise LoginRequired(request.url.path + (f"?{q}" if q else ""))
    return user


def require_seeker(user: User = Depends(require_user), db: Session = Depends(get_db)) -> JobSeeker:
    if user.role != "seeker":
        raise HTTPException(403, "This page is only available to job seekers.")
    return user.seeker


def require_employer(user: User = Depends(require_user)):
    if user.role != "employer":
        raise HTTPException(403, "This page is only available to employers.")
    return user.company
