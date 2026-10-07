"""Small input-validation helpers shared by the routes."""
import re
from datetime import date

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
PHONE_RE = re.compile(r"^[0-9+\-\s()]{7,20}$")
URL_RE = re.compile(r"^https?://[^\s]+\.[^\s]+$", re.I)


def clean(value, max_len=None) -> str:
    value = (value or "").strip()
    return value[:max_len] if max_len else value


def valid_email(email: str) -> bool:
    return bool(email) and len(email) <= 255 and bool(EMAIL_RE.match(email))


def password_error(pw: str):
    if len(pw) < 8:
        return "Password must be at least 8 characters long."
    if not re.search(r"[A-Za-z]", pw) or not re.search(r"\d", pw):
        return "Password must contain at least one letter and one number."
    if len(pw.encode()) > 72:
        return "Password is too long (max 72 characters)."
    return None


def optional_url(value: str, label: str, errors: list):
    value = clean(value, 255)
    if value and not URL_RE.match(value):
        errors.append(f"{label} must be a valid link starting with http:// or https://")
        return None
    return value or None


def optional_phone(value: str, errors: list):
    value = clean(value, 30)
    if value and not PHONE_RE.match(value):
        errors.append("Phone number is not valid.")
        return None
    return value or None


def optional_int(value, label, errors, low=0, high=100):
    value = clean(value)
    if not value:
        return None
    try:
        n = int(value)
    except ValueError:
        errors.append(f"{label} must be a whole number.")
        return None
    if not low <= n <= high:
        errors.append(f"{label} must be between {low} and {high}.")
        return None
    return n


def optional_date(value, label, errors):
    value = clean(value)
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        errors.append(f"{label} is not a valid date.")
        return None


def lpa_to_rupees(value, label, errors):
    value = clean(value)
    if not value:
        return None
    try:
        n = float(value)
    except ValueError:
        errors.append(f"{label} must be a number (in LPA).")
        return None
    if n < 0 or n > 1000:
        errors.append(f"{label} is out of range.")
        return None
    return int(round(n * 100000))
