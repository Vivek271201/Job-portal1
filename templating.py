"""Jinja2 setup: filters, global helpers and the render() helper."""
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlencode

from markupsafe import Markup, escape
from fastapi.templating import Jinja2Templates

from services.auth_service import get_csrf_token

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
env = templates.env


def timeago(dt):
    if not dt:
        return ""
    days = (datetime.utcnow().date() - (dt.date() if isinstance(dt, datetime) else dt)).days
    if days <= 0:
        return "Today"
    if days == 1:
        return "Yesterday"
    if days < 7:
        return f"{days} days ago"
    if days < 30:
        w = days // 7
        return f"{w} week{'s' if w > 1 else ''} ago"
    return dt.strftime("%d %b %Y")


def date_fmt(d, fmt="%d %b %Y"):
    return d.strftime(fmt) if d else ""


def month_year(d):
    return d.strftime("%b %Y") if d else ""


def lines(text):
    return [l.strip(" -•\t") for l in (text or "").splitlines() if l.strip(" -•\t")]


def get_flashed(request):
    try:
        return request.session.pop("_flash", [])
    except AssertionError:
        return []


def csrf_input(request):
    return Markup(f'<input type="hidden" name="csrf_token" value="{escape(get_csrf_token(request))}">')


def page_url(request, page):
    params = dict(request.query_params)
    params["page"] = page
    return f"{request.url.path}?{urlencode(params)}"


def current_url(request):
    q = request.url.query
    return request.url.path + (f"?{q}" if q else "")


env.filters.update(timeago=timeago, date_fmt=date_fmt, month_year=month_year, lines=lines)
env.globals.update(get_flashed=get_flashed, csrf_token=get_csrf_token, csrf_input=csrf_input,
                   page_url=page_url, current_url=current_url, today=date.today)


def render(request, name, context=None, status_code=200):
    ctx = {"user": getattr(request.state, "user", None)}
    ctx.update(context or {})
    return templates.TemplateResponse(request, name, ctx, status_code=status_code)
