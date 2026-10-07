"""Job Portal - FastAPI application entry point.

Run with:  uvicorn app:app --reload
"""
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import quote

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

from database.connection import DATABASE_URL, check_connection, engine  # noqa: E402
from database.models import Base  # noqa: E402
from routes import auth, employer, jobs, public, seeker  # noqa: E402
from routes.deps import LoginRequired, load_user, verify_csrf  # noqa: E402
from services import file_service  # noqa: E402
from templating import render  # noqa: E402

log = logging.getLogger("jobportal")
SECRET_KEY = os.getenv("SECRET_KEY", "change_this_secret_key")


@asynccontextmanager
async def lifespan(app: FastAPI):
    ok, msg = check_connection()
    if not ok:
        banner = (
            "\n" + "=" * 70 + "\n DATABASE CONNECTION FAILED\n"
            f" URL   : {DATABASE_URL.split('@')[-1]}\n Reason: {msg}\n\n"
            " Checklist:\n  1. Is MySQL running (XAMPP / MySQL service)?\n"
            "  2. Does the database 'job_portal' exist? (see README)\n"
            "  3. Are the user/password in .env correct?\n" + "=" * 70)
        print(banner)
        raise RuntimeError("Cannot connect to the database. See the message above.")
    if SECRET_KEY == "change_this_secret_key":
        print("WARNING: SECRET_KEY in .env is still the default. Change it before deploying.")
    Base.metadata.create_all(engine)  # creates missing tables (no-op if database.sql was imported)
    file_service.ensure_dirs()
    yield


app = FastAPI(title="JobPortal", lifespan=lifespan,
              dependencies=[Depends(verify_csrf), Depends(load_user)])
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, same_site="lax",
                   https_only=os.getenv("SESSION_HTTPS_ONLY", "0") == "1",
                   max_age=30 * 24 * 3600)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
file_service.ensure_dirs()
# Only public image folders are served directly. Resumes are NOT public:
# they are served through permission-checked routes.
for folder in ("profile_images", "company_logos", "company_covers"):
    app.mount(f"/uploads/{folder}", StaticFiles(directory=file_service.UPLOAD_DIR / folder), name=folder)

for r in (public.router, auth.router, jobs.router, seeker.router, employer.router):
    app.include_router(r)


# ------------------------------------------------------------------ errors
ERROR_TEXT = {
    400: ("Bad request", "The request could not be understood."),
    403: ("Access denied", "You do not have permission to view this page."),
    404: ("Page not found", "The page you are looking for does not exist or has been moved."),
    405: ("Method not allowed", "That action is not allowed here."),
    422: ("Invalid input", "Some of the information you sent was not valid."),
    500: ("Something went wrong", "An unexpected error occurred. Please try again later."),
}


def error_page(request: Request, code: int, detail: str | None = None):
    title, text = ERROR_TEXT.get(code, ("Error", "Something went wrong."))
    if detail and code in (403, 404):
        text = detail
    try:
        return render(request, "errors/error.html", {"code": code, "title": title, "message": text}, code)
    except Exception:  # noqa: BLE001 - never fail while rendering the error page
        return HTMLResponse(f"<h1>{code} - {title}</h1><p>{text}</p><a href='/'>Home</a>", status_code=code)


@app.exception_handler(LoginRequired)
async def login_required_handler(request: Request, exc: LoginRequired):
    return RedirectResponse(f"/login?next={quote(exc.next_url)}", status_code=303)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return error_page(request, exc.status_code, str(exc.detail))


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    return error_page(request, 422)


@app.exception_handler(SQLAlchemyError)
async def db_error_handler(request: Request, exc: SQLAlchemyError):
    log.exception("Database error: %s", exc)  # details go to the log, never to the user
    return error_page(request, 500)


@app.exception_handler(Exception)
async def unhandled_handler(request: Request, exc: Exception):
    log.exception("Unhandled error: %s", exc)
    return error_page(request, 500)
