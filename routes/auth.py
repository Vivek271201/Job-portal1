"""Registration, login and logout."""
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import Company, JobSeeker, User
from services.auth_service import (DUMMY_HASH, dashboard_url, flash, hash_password, login_user,
                                   logout_user, safe_next, verify_password)
from services.validation import clean, password_error, valid_email
from templating import render

router = APIRouter()


@router.get("/register")
def register_page(request: Request, role: str = "seeker"):
    if request.state.user:
        return RedirectResponse(dashboard_url(request.state.user), 303)
    return render(request, "auth/register.html", {"form": {"role": role if role in ("seeker", "employer") else "seeker"}, "errors": []})


@router.post("/register")
def register(request: Request, role: str = Form("seeker"), name: str = Form(""), email: str = Form(""),
             password: str = Form(""), confirm_password: str = Form(""), db: Session = Depends(get_db)):
    name, email = clean(name, 200), clean(email, 255).lower()
    errors = []
    if role not in ("seeker", "employer"):
        errors.append("Please choose a valid account type.")
        role = "seeker"
    if len(name) < 2:
        errors.append("Full name is required." if role == "seeker" else "Company name is required.")
    if not valid_email(email):
        errors.append("Please enter a valid email address.")
    elif db.scalar(select(User.id).where(func.lower(User.email) == email)):
        errors.append("An account with this email already exists.")
    pw_err = password_error(password)
    if pw_err:
        errors.append(pw_err)
    elif password != confirm_password:
        errors.append("Passwords do not match.")
    if not errors:
        try:
            user = User(email=email, password_hash=hash_password(password), role=role)
            if role == "seeker":
                user.seeker = JobSeeker(full_name=name[:150])
            else:
                user.company = Company(company_name=name, email=email)
            db.add(user)
            db.commit()
        except IntegrityError:
            db.rollback()
            errors.append("An account with this email already exists.")
        else:
            login_user(request, user)
            flash(request, "Welcome to JobPortal! Your account has been created.")
            if role == "seeker":
                flash(request, "Complete your profile to get noticed by employers.", "info")
            else:
                flash(request, "Complete your company profile to attract candidates.", "info")
            return RedirectResponse(dashboard_url(user), 303)
    return render(request, "auth/register.html",
                  {"form": {"role": role, "name": name, "email": email}, "errors": errors}, 400)


@router.get("/login")
def login_page(request: Request, next: str = ""):
    if request.state.user:
        return RedirectResponse(dashboard_url(request.state.user), 303)
    return render(request, "auth/login.html", {"form": {}, "errors": [], "next": next})


@router.post("/login")
def login(request: Request, email: str = Form(""), password: str = Form(""), remember: str = Form(""),
          next: str = Form(""), db: Session = Depends(get_db)):
    email = clean(email, 255).lower()
    user = db.scalar(select(User).where(func.lower(User.email) == email))
    ok = verify_password(password, user.password_hash if user else DUMMY_HASH)
    if not user or not ok:
        return render(request, "auth/login.html", {
            "form": {"email": email}, "errors": ["Invalid email or password."], "next": next}, 401)
    if not user.is_active:
        return render(request, "auth/login.html", {
            "form": {"email": email}, "errors": ["This account has been deactivated."], "next": next}, 403)
    login_user(request, user, remember=bool(remember))
    flash(request, f"Welcome back, {user.display_name}!")
    return RedirectResponse(safe_next(next, dashboard_url(user)), 303)


@router.post("/logout")
def logout(request: Request):
    logout_user(request)
    flash(request, "You have been logged out.", "info")
    return RedirectResponse("/", 303)
