"""Employer area: dashboard, company profile, job management, applications."""
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from database.connection import get_db
from database.models import (APPLICATION_STATUSES, COMPANY_SIZES, EMPLOYMENT_TYPES, JOB_STATUSES,
                             Application, Company, Job)
from routes.deps import require_employer
from services import file_service, job_service
from services.access import get_owned_application, get_owned_job
from services.auth_service import flash
from services.validation import (clean, lpa_to_rupees, optional_date, optional_int, optional_phone,
                                 optional_url, valid_email)
from templating import render

router = APIRouter()


# ---------------------------------------------------------------- dashboard
@router.get("/employer/dashboard")
def dashboard(request: Request, company: Company = Depends(require_employer), db: Session = Depends(get_db)):
    jobs = list(db.scalars(select(Job).where(Job.company_id == company.id)
                           .options(joinedload(Job.applications)).order_by(Job.created_at.desc())).unique())
    app_stmt = (select(Application).join(Job).where(Job.company_id == company.id)
                .options(joinedload(Application.job), joinedload(Application.seeker)))
    apps = list(db.scalars(app_stmt.order_by(Application.applied_at.desc()).limit(8)).unique())
    total_apps = db.scalar(select(func.count()).select_from(Application).join(Job).where(Job.company_id == company.id))
    shortlisted = db.scalar(select(func.count()).select_from(Application).join(Job).where(
        Job.company_id == company.id, Application.status == "Shortlisted"))
    return render(request, "employer/dashboard.html", {
        "company": company, "recent_jobs": jobs[:5], "recent_apps": apps,
        "stats": {"jobs": len(jobs), "active": sum(1 for j in jobs if j.status == "active"),
                  "applications": total_apps, "shortlisted": shortlisted}})


# ---------------------------------------------------------- company profile
@router.get("/employer/profile")
def my_profile(company: Company = Depends(require_employer)):
    return RedirectResponse(f"/companies/{company.id}", 303)


COMPANY_FIELDS = ("company_name", "description", "industry", "company_size", "founded_year", "website",
                  "email", "phone", "address", "city", "state", "country", "linkedin_url")


@router.get("/employer/profile/edit")
def edit_profile_page(request: Request, company: Company = Depends(require_employer)):
    form = {k: ("" if getattr(company, k) is None else getattr(company, k)) for k in COMPANY_FIELDS}
    return render(request, "employer/edit_profile.html",
                  {"company": company, "form": form, "errors": [], "sizes": COMPANY_SIZES})


@router.post("/employer/profile/edit")
async def edit_profile(request: Request, company_name: str = Form(""), description: str = Form(""),
                       industry: str = Form(""), company_size: str = Form(""), founded_year: str = Form(""),
                       website: str = Form(""), email: str = Form(""), phone: str = Form(""),
                       address: str = Form(""), city: str = Form(""), state: str = Form(""),
                       country: str = Form(""), linkedin_url: str = Form(""),
                       logo: UploadFile | None = File(None), cover: UploadFile | None = File(None),
                       company: Company = Depends(require_employer), db: Session = Depends(get_db)):
    errors = []
    form = dict(company_name=clean(company_name, 200), description=clean(description, 5000),
                industry=clean(industry, 120), company_size=company_size, founded_year=clean(founded_year),
                website=clean(website, 255), email=clean(email, 255), phone=clean(phone, 30),
                address=clean(address, 255), city=clean(city, 100), state=clean(state, 100),
                country=clean(country, 100), linkedin_url=clean(linkedin_url, 255))
    if len(form["company_name"]) < 2:
        errors.append("Company name is required.")
    if form["email"] and not valid_email(form["email"]):
        errors.append("Company email is not valid.")
    if company_size and company_size not in COMPANY_SIZES:
        errors.append("Please choose a valid company size.")
    year = optional_int(founded_year, "Founded year", errors, 1800, 2100)
    site = optional_url(website, "Website", errors)
    li = optional_url(linkedin_url, "LinkedIn URL", errors)
    ph = optional_phone(phone, errors)
    new_logo = new_cover = None
    if not errors:
        try:
            if file_service.has_file(logo):
                new_logo = await file_service.save_image(logo, "company_logos")
            if file_service.has_file(cover):
                new_cover = await file_service.save_image(cover, "company_covers")
        except file_service.FileValidationError as exc:
            errors.append(str(exc))
            file_service.delete_file(new_logo)
    if errors:
        return render(request, "employer/edit_profile.html",
                      {"company": company, "form": form, "errors": errors, "sizes": COMPANY_SIZES}, 400)
    old_logo, old_cover = company.logo, company.cover_image
    company.company_name = form["company_name"]
    company.description = form["description"] or None
    company.industry = form["industry"] or None
    company.company_size = company_size or None
    company.founded_year = year
    company.website, company.linkedin_url, company.phone = site, li, ph
    company.email = form["email"] or None
    company.address = form["address"] or None
    company.city, company.state = form["city"] or None, form["state"] or None
    company.country = form["country"] or None
    if new_logo:
        company.logo = new_logo
    if new_cover:
        company.cover_image = new_cover
    db.commit()
    if new_logo:
        file_service.delete_file(old_logo)
    if new_cover:
        file_service.delete_file(old_cover)
    flash(request, "Company profile updated successfully.")
    return RedirectResponse(f"/companies/{company.id}", 303)


# --------------------------------------------------------------------- jobs
JOB_FIELDS = ("title", "description", "responsibilities", "requirements", "location", "employment_type",
              "experience_required", "salary_min", "salary_max", "skills", "deadline", "status")


def _job_form_from(job=None):
    if not job:
        return {"employment_type": "Full Time", "status": "active", "experience_required": "0"}
    f = {k: getattr(job, k) for k in ("title", "description", "responsibilities", "requirements", "location",
                                      "employment_type", "skills", "status")}
    f = {k: (v or "") for k, v in f.items()}
    f["experience_required"] = str(job.experience_required or 0)
    f["salary_min"] = f"{job.salary_min / 100000:g}" if job.salary_min else ""
    f["salary_max"] = f"{job.salary_max / 100000:g}" if job.salary_max else ""
    f["deadline"] = job.deadline.isoformat() if job.deadline else ""
    return f


def _parse_job(form: dict):
    errors = []
    if len(form["title"]) < 3:
        errors.append("Job title is required (at least 3 characters).")
    if len(form["description"]) < 20:
        errors.append("Please write a job description (at least 20 characters).")
    if not form["location"]:
        errors.append("Location is required.")
    if form["employment_type"] not in EMPLOYMENT_TYPES:
        errors.append("Please choose a valid employment type.")
    if form["status"] not in JOB_STATUSES:
        errors.append("Please choose a valid status.")
    exp = optional_int(form["experience_required"], "Experience", errors, 0, 40) or 0
    smin = lpa_to_rupees(form["salary_min"], "Minimum salary", errors)
    smax = lpa_to_rupees(form["salary_max"], "Maximum salary", errors)
    if smin and smax and smin > smax:
        errors.append("Minimum salary cannot be greater than maximum salary.")
    deadline = optional_date(form["deadline"], "Deadline", errors)
    skills = ", ".join(dict.fromkeys(s.strip() for s in form["skills"].split(",") if s.strip()))[:500]
    values = dict(title=form["title"], description=form["description"],
                  responsibilities=form["responsibilities"] or None, requirements=form["requirements"] or None,
                  location=form["location"], employment_type=form["employment_type"],
                  experience_required=exp, salary_min=smin, salary_max=smax, skills=skills or None,
                  deadline=deadline, status=form["status"])
    return values, errors


def _collect(title, description, responsibilities, requirements, location, employment_type,
             experience_required, salary_min, salary_max, skills, deadline, status):
    return dict(title=clean(title, 200), description=clean(description, 10000),
                responsibilities=clean(responsibilities, 10000), requirements=clean(requirements, 10000),
                location=clean(location, 150), employment_type=employment_type,
                experience_required=experience_required, salary_min=salary_min, salary_max=salary_max,
                skills=skills, deadline=deadline, status=status)


@router.get("/employer/jobs")
def my_jobs(request: Request, company: Company = Depends(require_employer), db: Session = Depends(get_db)):
    jobs = list(db.scalars(select(Job).where(Job.company_id == company.id)
                           .options(joinedload(Job.applications)).order_by(Job.created_at.desc())).unique())
    return render(request, "employer/jobs.html", {"company": company, "jobs": jobs})


@router.get("/employer/jobs/create")
def create_job_page(request: Request, company: Company = Depends(require_employer)):
    return render(request, "employer/create_job.html", {
        "form": _job_form_from(), "errors": [], "types": EMPLOYMENT_TYPES, "statuses": JOB_STATUSES})


@router.post("/employer/jobs/create")
def create_job(request: Request, title: str = Form(""), description: str = Form(""),
               responsibilities: str = Form(""), requirements: str = Form(""), location: str = Form(""),
               employment_type: str = Form("Full Time"), experience_required: str = Form("0"),
               salary_min: str = Form(""), salary_max: str = Form(""), skills: str = Form(""),
               deadline: str = Form(""), status: str = Form("active"),
               company: Company = Depends(require_employer), db: Session = Depends(get_db)):
    form = _collect(title, description, responsibilities, requirements, location, employment_type,
                    experience_required, salary_min, salary_max, skills, deadline, status)
    values, errors = _parse_job(form)
    if errors:
        return render(request, "employer/create_job.html", {
            "form": form, "errors": errors, "types": EMPLOYMENT_TYPES, "statuses": JOB_STATUSES}, 400)
    job = Job(company_id=company.id, **values)
    db.add(job)
    db.commit()
    flash(request, "Job posted successfully." if job.status == "active" else "Job saved.")
    return RedirectResponse("/employer/jobs", 303)


@router.get("/employer/jobs/{job_id}/edit")
def edit_job_page(job_id: int, request: Request, company: Company = Depends(require_employer),
                  db: Session = Depends(get_db)):
    job = get_owned_job(db, company, job_id)
    return render(request, "employer/edit_job.html", {
        "job": job, "form": _job_form_from(job), "errors": [], "types": EMPLOYMENT_TYPES, "statuses": JOB_STATUSES})


@router.post("/employer/jobs/{job_id}/edit")
def edit_job(job_id: int, request: Request, title: str = Form(""), description: str = Form(""),
             responsibilities: str = Form(""), requirements: str = Form(""), location: str = Form(""),
             employment_type: str = Form("Full Time"), experience_required: str = Form("0"),
             salary_min: str = Form(""), salary_max: str = Form(""), skills: str = Form(""),
             deadline: str = Form(""), status: str = Form("active"),
             company: Company = Depends(require_employer), db: Session = Depends(get_db)):
    job = get_owned_job(db, company, job_id)
    form = _collect(title, description, responsibilities, requirements, location, employment_type,
                    experience_required, salary_min, salary_max, skills, deadline, status)
    values, errors = _parse_job(form)
    if errors:
        return render(request, "employer/edit_job.html", {
            "job": job, "form": form, "errors": errors, "types": EMPLOYMENT_TYPES, "statuses": JOB_STATUSES}, 400)
    for k, v in values.items():
        setattr(job, k, v)
    db.commit()
    flash(request, "Job updated successfully.")
    return RedirectResponse("/employer/jobs", 303)


@router.post("/employer/jobs/{job_id}/status")
def set_job_status(job_id: int, request: Request, status: str = Form(""),
                   company: Company = Depends(require_employer), db: Session = Depends(get_db)):
    job = get_owned_job(db, company, job_id)
    if status not in JOB_STATUSES:
        flash(request, "Invalid job status.", "error")
    else:
        job.status = status
        db.commit()
        flash(request, "Job closed." if status == "closed" else "Job status updated.", "info")
    return RedirectResponse("/employer/jobs", 303)


@router.post("/employer/jobs/{job_id}/delete")
def delete_job(job_id: int, request: Request, company: Company = Depends(require_employer),
               db: Session = Depends(get_db)):
    job = get_owned_job(db, company, job_id)
    paths = [a.resume_path for a in job.applications]
    db.delete(job)
    db.commit()
    for p in paths:
        file_service.delete_resume_if_unused(db, p)
    flash(request, "Job deleted.", "info")
    return RedirectResponse("/employer/jobs", 303)


# ------------------------------------------------------------- applications
@router.get("/employer/applications")
def applications(request: Request, job_id: str = "", status: str = "", page: int = 1,
                 company: Company = Depends(require_employer), db: Session = Depends(get_db)):
    stmt = select(Application).join(Job).where(Job.company_id == company.id)
    if job_id.isdigit():
        stmt = stmt.where(Application.job_id == int(job_id))
    if status in APPLICATION_STATUSES:
        stmt = stmt.where(Application.status == status)
    stmt = stmt.order_by(Application.applied_at.desc(), Application.id.desc())
    data = job_service.paginate(db, stmt, page, 10,
                                options=(joinedload(Application.job), joinedload(Application.seeker)))
    my_jobs_list = list(db.scalars(select(Job).where(Job.company_id == company.id).order_by(Job.title)))
    return render(request, "employer/applications.html", {
        "page": data, "jobs": my_jobs_list, "statuses": APPLICATION_STATUSES,
        "f": {"job_id": job_id, "status": status}})


@router.post("/employer/applications/{app_id}/status")
def change_status(app_id: int, request: Request, status: str = Form(""), back: str = Form(""),
                  company: Company = Depends(require_employer), db: Session = Depends(get_db)):
    app = get_owned_application(db, company, app_id)
    if status not in APPLICATION_STATUSES:
        flash(request, "Invalid application status.", "error")
    else:
        app.status = status
        db.commit()
        flash(request, f"{app.seeker.full_name}'s application marked as {status}.")
    target = back if back.startswith("/employer/") else "/employer/applications"
    return RedirectResponse(target, 303)
