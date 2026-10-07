"""Public pages: home, about, company directory and company profile."""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import Company
from services import job_service
from templating import render

router = APIRouter()


@router.get("/")
def index(request: Request, db: Session = Depends(get_db)):
    featured = job_service.search_jobs(db, page=1, per_page=6)["items"]
    companies = job_service.search_companies(db, per_page=6, popular_first=True)["items"]
    return render(request, "index.html", {
        "featured_jobs": featured, "popular_companies": companies,
        "stats": job_service.site_stats(db)})


@router.get("/about")
def about(request: Request):
    return render(request, "public/about.html")


@router.get("/companies")
def companies(request: Request, name: str = "", industry: str = "", location: str = "",
              page: int = 1, db: Session = Depends(get_db)):
    data = job_service.search_companies(db, name.strip(), industry.strip(), location.strip(), page, 9)
    return render(request, "public/companies.html", {
        "page": data, "industries": job_service.industries(db),
        "f": {"name": name, "industry": industry, "location": location}})


@router.get("/companies/{company_id}")
def company_detail(company_id: int, request: Request, db: Session = Depends(get_db)):
    company = db.get(Company, company_id)
    if not company:
        raise HTTPException(404, "Company not found.")
    user = request.state.user
    is_owner = bool(user and user.company and user.company.id == company.id)
    jobs = sorted(company.open_jobs, key=lambda j: j.created_at, reverse=True)
    return render(request, "public/company.html", {"company": company, "jobs": jobs, "is_owner": is_owner})
