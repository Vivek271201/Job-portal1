"""Queries for jobs/companies: search, pagination and site statistics."""
from datetime import date, datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import joinedload

from database.models import Application, Company, Job, JobSeeker


def paginate(db, stmt, page: int, per_page: int, options=()):
    page = max(page, 1)
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    pages = max((total + per_page - 1) // per_page, 1)
    page = min(page, pages)
    q = stmt.options(*options).offset((page - 1) * per_page).limit(per_page)
    items = list(db.scalars(q).unique())
    return {"items": items, "total": total, "pages": pages, "page": page, "per_page": per_page}


def open_jobs_stmt():
    return (select(Job).join(Job.company)
            .where(Job.status == "active", or_(Job.deadline.is_(None), Job.deadline >= date.today())))


def _like(col, text):
    return func.lower(col).contains(text.lower(), autoescape=True)


def search_jobs(db, q="", location="", employment_type="", min_salary=None,
                max_experience=None, posted_days=None, page=1, per_page=9):
    stmt = open_jobs_stmt()
    if q:
        stmt = stmt.where(or_(_like(Job.title, q), _like(Job.skills, q), _like(Company.company_name, q)))
    if location:
        stmt = stmt.where(_like(Job.location, location))
    if employment_type:
        stmt = stmt.where(Job.employment_type == employment_type)
    if min_salary:
        stmt = stmt.where(Job.salary_max >= int(min_salary * 100000))
    if max_experience is not None:
        stmt = stmt.where(Job.experience_required <= max_experience)
    if posted_days:
        stmt = stmt.where(Job.created_at >= datetime.utcnow() - timedelta(days=posted_days))
    stmt = stmt.order_by(Job.created_at.desc(), Job.id.desc())
    return paginate(db, stmt, page, per_page, options=(joinedload(Job.company),))


def _job_counts():
    return (select(Job.company_id.label("cid"), func.count(Job.id).label("n"))
            .where(Job.status == "active").group_by(Job.company_id).subquery())


def search_companies(db, name="", industry="", location="", page=1, per_page=9, popular_first=False):
    cnt = _job_counts()
    stmt = select(Company).outerjoin(cnt, cnt.c.cid == Company.id)
    if name:
        stmt = stmt.where(_like(Company.company_name, name))
    if industry:
        stmt = stmt.where(_like(Company.industry, industry))
    if location:
        stmt = stmt.where(or_(_like(Company.city, location), _like(Company.state, location)))
    if popular_first:
        stmt = stmt.order_by(func.coalesce(cnt.c.n, 0).desc(), Company.id)
    else:
        stmt = stmt.order_by(Company.company_name)
    return paginate(db, stmt, page, per_page, options=(joinedload(Company.jobs),))


def industries(db):
    rows = db.scalars(select(Company.industry).where(Company.industry.is_not(None)).distinct())
    return sorted(r for r in rows if r)


def site_stats(db):
    return {
        "jobs": db.scalar(select(func.count()).select_from(Job).where(Job.status == "active")) or 0,
        "companies": db.scalar(select(func.count()).select_from(Company)) or 0,
        "seekers": db.scalar(select(func.count()).select_from(JobSeeker)) or 0,
        "applications": db.scalar(select(func.count()).select_from(Application)) or 0,
    }
