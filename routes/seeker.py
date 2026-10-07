"""Job seeker area: dashboard, profile, education/experience, resume, applications."""
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from database.connection import get_db
from database.models import Application, Education, Experience, JobSeeker
from routes.deps import require_seeker
from services import file_service, job_service
from services.access import can_view_seeker, forbidden
from services.auth_service import flash
from services.profile_service import parse_skills, profile_completion, set_seeker_skills
from services.validation import (clean, optional_date, optional_int, optional_phone, optional_url)
from templating import render

router = APIRouter()


# ---------------------------------------------------------------- dashboard
@router.get("/seeker/dashboard")
def dashboard(request: Request, seeker: JobSeeker = Depends(require_seeker), db: Session = Depends(get_db)):
    apps = list(db.scalars(select(Application).where(Application.seeker_id == seeker.id)
                           .options(joinedload(Application.job)).order_by(Application.applied_at.desc())))
    count = lambda s: sum(1 for a in apps if a.status == s)  # noqa: E731
    latest = job_service.search_jobs(db, page=1, per_page=6)["items"]
    return render(request, "seeker/dashboard.html", {
        "seeker": seeker, "completion": profile_completion(seeker), "recent": apps[:5], "latest_jobs": latest,
        "counts": {"total": len(apps), "review": count("Under Review"),
                   "shortlisted": count("Shortlisted"), "selected": count("Selected")}})


# ------------------------------------------------------------------ profile
def _profile_page(request, db, seeker, is_owner):
    return render(request, "seeker/profile.html", {
        "seeker": seeker, "is_owner": is_owner, "completion": profile_completion(seeker) if is_owner else None,
        "can_resume": is_owner or can_view_seeker(db, request.state.user, seeker)})


@router.get("/seeker/profile")
def my_profile(request: Request, seeker: JobSeeker = Depends(require_seeker), db: Session = Depends(get_db)):
    return _profile_page(request, db, seeker, True)


@router.get("/seekers/{seeker_id}")
def view_profile(seeker_id: int, request: Request, db: Session = Depends(get_db)):
    user = request.state.user
    seeker = db.get(JobSeeker, seeker_id)
    if not seeker:
        raise HTTPException(404, "Profile not found.")
    if not can_view_seeker(db, user, seeker):
        if user is None:
            from routes.deps import LoginRequired
            raise LoginRequired(request.url.path)
        raise forbidden("You can only view profiles of candidates who applied to your jobs.")
    return _profile_page(request, db, seeker, user.role == "seeker")


def _form_from(seeker):
    f = {k: getattr(seeker, k) or "" for k in
         ("full_name", "headline", "phone", "location", "about", "linkedin_url", "github_url", "portfolio_url")}
    f["skills"] = ", ".join(seeker.skill_names)
    return f


@router.get("/seeker/profile/edit")
def edit_profile_page(request: Request, seeker: JobSeeker = Depends(require_seeker)):
    return render(request, "seeker/edit_profile.html",
                  {"seeker": seeker, "form": _form_from(seeker), "errors": [],
                   "completion": profile_completion(seeker)})


@router.post("/seeker/profile/edit")
async def edit_profile(request: Request, full_name: str = Form(""), headline: str = Form(""),
                       phone: str = Form(""), location: str = Form(""), about: str = Form(""),
                       linkedin_url: str = Form(""), github_url: str = Form(""),
                       portfolio_url: str = Form(""), skills: str = Form(""),
                       photo: UploadFile | None = File(None), remove_photo: str = Form(""),
                       seeker: JobSeeker = Depends(require_seeker), db: Session = Depends(get_db)):
    errors = []
    form = dict(full_name=clean(full_name, 150), headline=clean(headline, 200), phone=clean(phone, 30),
                location=clean(location, 150), about=clean(about, 5000), linkedin_url=clean(linkedin_url, 255),
                github_url=clean(github_url, 255), portfolio_url=clean(portfolio_url, 255), skills=skills)
    if len(form["full_name"]) < 2:
        errors.append("Full name is required.")
    phone_v = optional_phone(phone, errors)
    li = optional_url(linkedin_url, "LinkedIn URL", errors)
    gh = optional_url(github_url, "GitHub URL", errors)
    pf = optional_url(portfolio_url, "Portfolio URL", errors)
    new_photo = None
    if not errors and file_service.has_file(photo):
        try:
            new_photo = await file_service.save_image(photo, "profile_images")
        except file_service.FileValidationError as exc:
            errors.append(str(exc))
    if errors:
        return render(request, "seeker/edit_profile.html", {
            "seeker": seeker, "form": form, "errors": errors, "completion": profile_completion(seeker)}, 400)
    old_photo = seeker.profile_image
    seeker.full_name = form["full_name"]
    seeker.headline = form["headline"] or None
    seeker.phone, seeker.location = phone_v, form["location"] or None
    seeker.about = form["about"] or None
    seeker.linkedin_url, seeker.github_url, seeker.portfolio_url = li, gh, pf
    if new_photo:
        seeker.profile_image = new_photo
    elif remove_photo:
        seeker.profile_image = None
    set_seeker_skills(db, seeker, parse_skills(skills))
    db.commit()
    if seeker.profile_image != old_photo:
        file_service.delete_file(old_photo)
    flash(request, "Profile updated successfully.")
    return RedirectResponse("/seeker/profile", 303)


# ------------------------------------------------- education / experience
@router.post("/seeker/education/add")
def add_education(request: Request, institution: str = Form(""), degree: str = Form(""),
                  field_of_study: str = Form(""), start_year: str = Form(""), end_year: str = Form(""),
                  description: str = Form(""), seeker: JobSeeker = Depends(require_seeker),
                  db: Session = Depends(get_db)):
    errors = []
    sy = optional_int(start_year, "Start year", errors, 1950, 2100)
    ey = optional_int(end_year, "End year", errors, 1950, 2100)
    if not clean(institution) or not clean(degree):
        errors.append("Institution and degree are required.")
    if sy and ey and ey < sy:
        errors.append("End year cannot be before start year.")
    if errors:
        flash(request, " ".join(errors), "error")
    else:
        db.add(Education(seeker_id=seeker.id, institution=clean(institution, 200), degree=clean(degree, 150),
                         field_of_study=clean(field_of_study, 150) or None, start_year=sy, end_year=ey,
                         description=clean(description, 2000) or None))
        db.commit()
        flash(request, "Education added.")
    return RedirectResponse("/seeker/profile/edit#education", 303)


@router.post("/seeker/education/{edu_id}/delete")
def delete_education(edu_id: int, request: Request, seeker: JobSeeker = Depends(require_seeker),
                     db: Session = Depends(get_db)):
    edu = db.get(Education, edu_id)
    if not edu or edu.seeker_id != seeker.id:
        raise forbidden("You can only delete your own education entries.")
    db.delete(edu)
    db.commit()
    flash(request, "Education removed.", "info")
    return RedirectResponse("/seeker/profile/edit#education", 303)


@router.post("/seeker/experience/add")
def add_experience(request: Request, company_name: str = Form(""), job_title: str = Form(""),
                   start_date: str = Form(""), end_date: str = Form(""), description: str = Form(""),
                   seeker: JobSeeker = Depends(require_seeker), db: Session = Depends(get_db)):
    errors = []
    sd = optional_date(start_date, "Start date", errors)
    ed = optional_date(end_date, "End date", errors)
    if not clean(company_name) or not clean(job_title):
        errors.append("Company and job title are required.")
    if sd and ed and ed < sd:
        errors.append("End date cannot be before start date.")
    if errors:
        flash(request, " ".join(errors), "error")
    else:
        db.add(Experience(seeker_id=seeker.id, company_name=clean(company_name, 200),
                          job_title=clean(job_title, 150), start_date=sd, end_date=ed,
                          description=clean(description, 2000) or None))
        db.commit()
        flash(request, "Experience added.")
    return RedirectResponse("/seeker/profile/edit#experience", 303)


@router.post("/seeker/experience/{exp_id}/delete")
def delete_experience(exp_id: int, request: Request, seeker: JobSeeker = Depends(require_seeker),
                      db: Session = Depends(get_db)):
    exp = db.get(Experience, exp_id)
    if not exp or exp.seeker_id != seeker.id:
        raise forbidden("You can only delete your own experience entries.")
    db.delete(exp)
    db.commit()
    flash(request, "Experience removed.", "info")
    return RedirectResponse("/seeker/profile/edit#experience", 303)


# ------------------------------------------------------------------- resume
@router.get("/seeker/resume")
def resume_page(request: Request, seeker: JobSeeker = Depends(require_seeker)):
    return render(request, "seeker/edit_resume.html", {"seeker": seeker})


@router.post("/seeker/resume")
async def upload_resume(request: Request, resume: UploadFile | None = File(None),
                        seeker: JobSeeker = Depends(require_seeker), db: Session = Depends(get_db)):
    if not file_service.has_file(resume):
        flash(request, "Please choose a PDF file to upload.", "error")
        return RedirectResponse("/seeker/resume", 303)
    try:
        new_rel = await file_service.save_resume(resume)
    except file_service.FileValidationError as exc:
        flash(request, str(exc), "error")
        return RedirectResponse("/seeker/resume", 303)
    old = seeker.resume_path
    seeker.resume_path = new_rel
    db.commit()
    file_service.delete_resume_if_unused(db, old)
    flash(request, "Resume uploaded successfully.")
    return RedirectResponse("/seeker/profile", 303)


def _send_pdf(rel, name, download):
    path = file_service.resolve(rel)
    if not path:
        raise HTTPException(404, "Resume file not found.")
    safe = "".join(c for c in name if c.isalnum() or c in " _-").strip().replace(" ", "_") or "resume"
    return FileResponse(path, media_type="application/pdf", filename=f"{safe}_Resume.pdf",
                        content_disposition_type="attachment" if download else "inline")


@router.get("/resumes/{seeker_id}")
def serve_profile_resume(seeker_id: int, request: Request, download: int = 0, db: Session = Depends(get_db)):
    from routes.deps import LoginRequired
    user = request.state.user
    if user is None:
        raise LoginRequired(request.url.path)
    seeker = db.get(JobSeeker, seeker_id)
    if not seeker:
        raise HTTPException(404, "Resume not found.")
    if not can_view_seeker(db, user, seeker):
        raise forbidden("You do not have permission to view this resume.")
    return _send_pdf(seeker.resume_path, seeker.full_name, download)


@router.get("/applications/{app_id}/resume")
def serve_application_resume(app_id: int, request: Request, download: int = 0, db: Session = Depends(get_db)):
    from routes.deps import LoginRequired
    user = request.state.user
    if user is None:
        raise LoginRequired(request.url.path)
    app = db.get(Application, app_id)
    if not app:
        raise HTTPException(404, "Application not found.")
    is_applicant = user.role == "seeker" and user.seeker and user.seeker.id == app.seeker_id
    is_employer = user.role == "employer" and user.company and user.company.id == app.job.company_id
    if not (is_applicant or is_employer):
        raise forbidden("You do not have permission to view this resume.")
    return _send_pdf(app.resume_path, app.seeker.full_name, download)


# ------------------------------------------------------------- applications
@router.get("/seeker/applications")
def my_applications(request: Request, seeker: JobSeeker = Depends(require_seeker), db: Session = Depends(get_db)):
    apps = list(db.scalars(select(Application).where(Application.seeker_id == seeker.id)
                           .options(joinedload(Application.job)).order_by(Application.applied_at.desc())))
    return render(request, "seeker/applications.html", {"applications": apps})


@router.post("/seeker/applications/{app_id}/withdraw")
def withdraw(app_id: int, request: Request, seeker: JobSeeker = Depends(require_seeker),
             db: Session = Depends(get_db)):
    app = db.get(Application, app_id)
    if not app or app.seeker_id != seeker.id:
        raise forbidden("You can only withdraw your own applications.")
    if app.status != "Applied":
        flash(request, "This application is already being processed and can no longer be withdrawn.", "error")
        return RedirectResponse("/seeker/applications", 303)
    path = app.resume_path
    db.delete(app)
    db.commit()
    file_service.delete_resume_if_unused(db, path)
    flash(request, "Application withdrawn.", "info")
    return RedirectResponse("/seeker/applications", 303)
