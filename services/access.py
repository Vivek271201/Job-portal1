"""Ownership / permission checks (who may see or change what)."""
from fastapi import HTTPException
from sqlalchemy import select

from database.models import Application, Job


def forbidden(msg="You do not have permission to do that."):
    return HTTPException(status_code=403, detail=msg)


def get_owned_job(db, company, job_id: int) -> Job:
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found.")
    if job.company_id != company.id:
        raise forbidden("You can only manage your own company's jobs.")
    return job


def get_owned_application(db, company, app_id: int) -> Application:
    app = db.get(Application, app_id)
    if not app:
        raise HTTPException(404, "Application not found.")
    if app.job.company_id != company.id:
        raise forbidden("You can only manage applications for your own jobs.")
    return app


def employer_can_see_seeker(db, company, seeker_id: int) -> bool:
    found = db.scalar(
        select(Application.id).join(Job, Job.id == Application.job_id)
        .where(Job.company_id == company.id, Application.seeker_id == seeker_id).limit(1))
    return found is not None


def can_view_seeker(db, user, seeker) -> bool:
    if user is None:
        return False
    if user.role == "seeker":
        return bool(user.seeker and user.seeker.id == seeker.id)
    if user.role == "employer" and user.company:
        return employer_can_see_seeker(db, user.company, seeker.id)
    return False
