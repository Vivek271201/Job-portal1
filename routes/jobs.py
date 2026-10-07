"""Job search, job details and applying for a job."""
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import EMPLOYMENT_TYPES, Application, Job
from routes.deps import require_seeker
from services import file_service, job_service
from services.auth_service import flash
from services.validation import clean
from templating import render

router = APIRouter()


def _num(value, cast=float):
    try:
        return cast(value) if value not in (None, "") else None
    except ValueError:
        return None


@router.get("/jobs")
def job_list(request: Request, q: str = "", location: str = "", type: str = "", salary: str = "",
             experience: str = "", posted: str = "", page: int = 1, db: Session = Depends(get_db)):
    data = job_service.search_jobs(
        db, clean(q, 100), clean(location, 100), type if type in EMPLOYMENT_TYPES else "",
        _num(salary), _num(experience, int), _num(posted, int), page, 9)
    f = {"q": q, "location": location, "type": type, "salary": salary, "experience": experience, "posted": posted}
    return render(request, "jobs/index.html", {"page": data, "f": f, "types": EMPLOYMENT_TYPES})


def _get_visible_job(db, job_id, user) -> Job:
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(404, "This job does not exist.")
    owner = bool(user and user.company and user.company.id == job.company_id)
    if job.status != "active" and not owner:
        raise HTTPException(404, "This job is no longer available.")
    return job


@router.get("/jobs/{job_id}")
def job_detail(job_id: int, request: Request, db: Session = Depends(get_db)):
    user = request.state.user
    job = _get_visible_job(db, job_id, user)
    applied = False
    if user and user.role == "seeker" and user.seeker:
        applied = db.scalar(select(Application.id).where(
            Application.job_id == job.id, Application.seeker_id == user.seeker.id)) is not None
    is_owner = bool(user and user.company and user.company.id == job.company_id)
    return render(request, "jobs/details.html", {"job": job, "applied": applied, "is_owner": is_owner})


def _apply_context(job, seeker, errors=None, cover=""):
    return {"job": job, "seeker": seeker, "errors": errors or [], "cover": cover}


@router.get("/jobs/{job_id}/apply")
def apply_page(job_id: int, request: Request, seeker=Depends(require_seeker), db: Session = Depends(get_db)):
    job = _get_visible_job(db, job_id, request.state.user)
    if db.scalar(select(Application.id).where(Application.job_id == job.id, Application.seeker_id == seeker.id)):
        flash(request, "You have already applied for this job.", "info")
        return RedirectResponse(f"/jobs/{job.id}", 303)
    return render(request, "jobs/apply.html", _apply_context(job, seeker))


@router.post("/jobs/{job_id}/apply")
async def apply_submit(job_id: int, request: Request, cover_letter: str = Form(""),
                       resume: UploadFile | None = File(None), seeker=Depends(require_seeker),
                       db: Session = Depends(get_db)):
    job = _get_visible_job(db, job_id, request.state.user)
    if db.scalar(select(Application.id).where(Application.job_id == job.id, Application.seeker_id == seeker.id)):
        flash(request, "You have already applied for this job.", "info")
        return RedirectResponse(f"/jobs/{job.id}", 303)
    cover = clean(cover_letter, 3000)
    errors, resume_rel = [], None
    if not job.is_open:
        errors.append("Applications for this job are closed.")
    if not errors:
        try:
            if file_service.has_file(resume):
                resume_rel = await file_service.save_resume(resume)
            elif seeker.resume_path:
                resume_rel = file_service.copy_file(seeker.resume_path)
            if not resume_rel:
                errors.append("Please upload your resume (PDF) to apply.")
        except file_service.FileValidationError as exc:
            errors.append(str(exc))
    if errors:
        return render(request, "jobs/apply.html", _apply_context(job, seeker, errors, cover), 400)
    try:
        db.add(Application(job_id=job.id, seeker_id=seeker.id, resume_path=resume_rel,
                           cover_letter=cover or None, status="Applied"))
        db.commit()
    except IntegrityError:  # duplicate application (unique constraint)
        db.rollback()
        file_service.delete_file(resume_rel)
        flash(request, "You have already applied for this job.", "info")
        return RedirectResponse(f"/jobs/{job.id}", 303)
    flash(request, f"Application submitted for {job.title} at {job.company.company_name}. Good luck!")
    return RedirectResponse("/seeker/applications", 303)
