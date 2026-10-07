"""Safe file uploads: validation, unique names, storage and deletion.

Files live in uploads/<folder>/. Only the relative path (e.g.
"resumes/ab12.pdf") is stored in the database.
"""
import os
import shutil
import uuid
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", BASE_DIR / "uploads")).resolve()
FOLDERS = ["profile_images", "company_logos", "company_covers", "resumes"]

MAX_IMAGE_BYTES = 2 * 1024 * 1024   # 2 MB
MAX_RESUME_BYTES = 5 * 1024 * 1024  # 5 MB

IMAGE_EXT = {".jpg": {"image/jpeg", "image/pjpeg"}, ".jpeg": {"image/jpeg", "image/pjpeg"},
             ".png": {"image/png"}}


class FileValidationError(Exception):
    pass


def ensure_dirs():
    for f in FOLDERS:
        (UPLOAD_DIR / f).mkdir(parents=True, exist_ok=True)


def has_file(upload) -> bool:
    return upload is not None and not isinstance(upload, str) and bool(upload.filename)


async def _read_limited(upload, limit: int) -> bytes:
    data = await upload.read(limit + 1)
    if len(data) > limit:
        raise FileValidationError(f"File is too large. Maximum size is {limit // (1024 * 1024)} MB.")
    if not data:
        raise FileValidationError("The uploaded file is empty.")
    return data


async def save_image(upload, folder: str) -> str:
    ext = Path(upload.filename).suffix.lower()
    if ext not in IMAGE_EXT:
        raise FileValidationError("Only JPG, JPEG or PNG images are allowed.")
    if (upload.content_type or "").lower() not in IMAGE_EXT[ext]:
        raise FileValidationError("The file type does not match a JPG/PNG image.")
    data = await _read_limited(upload, MAX_IMAGE_BYTES)
    is_png = data.startswith(b"\x89PNG\r\n\x1a\n")
    is_jpg = data.startswith(b"\xff\xd8\xff")
    if not (is_png or is_jpg) or (ext == ".png") != is_png:
        raise FileValidationError("The file is not a valid JPG or PNG image.")
    return _write(folder, ext, data)


async def save_resume(upload) -> str:
    if Path(upload.filename).suffix.lower() != ".pdf":
        raise FileValidationError("Resume must be a PDF file.")
    if (upload.content_type or "").lower() != "application/pdf":
        raise FileValidationError("Resume must be a PDF file (invalid file type).")
    data = await _read_limited(upload, MAX_RESUME_BYTES)
    if not data.startswith(b"%PDF"):
        raise FileValidationError("The file is not a valid PDF.")
    return _write("resumes", ".pdf", data)


def _write(folder: str, ext: str, data: bytes) -> str:
    assert folder in FOLDERS
    ensure_dirs()
    rel = f"{folder}/{uuid.uuid4().hex}{ext}"
    (UPLOAD_DIR / rel).write_bytes(data)
    return rel


def resolve(rel: str | None) -> Path | None:
    """Return the absolute path of a stored file, only if inside UPLOAD_DIR."""
    if not rel:
        return None
    p = (UPLOAD_DIR / rel).resolve()
    if UPLOAD_DIR not in p.parents or not p.is_file():
        return None
    return p


def copy_file(rel: str, folder: str = "resumes") -> str | None:
    src = resolve(rel)
    if not src:
        return None
    new_rel = f"{folder}/{uuid.uuid4().hex}{src.suffix}"
    shutil.copyfile(src, UPLOAD_DIR / new_rel)
    return new_rel


def delete_file(rel: str | None):
    p = resolve(rel)
    if p:
        try:
            p.unlink()
        except OSError:
            pass


def delete_resume_if_unused(db, rel: str | None):
    """Delete a resume file only when no profile/application still uses it."""
    if not rel:
        return
    from sqlalchemy import func, select
    from database.models import Application, JobSeeker
    used = db.scalar(select(func.count()).select_from(Application).where(Application.resume_path == rel))
    used += db.scalar(select(func.count()).select_from(JobSeeker).where(JobSeeker.resume_path == rel))
    if not used:
        delete_file(rel)
