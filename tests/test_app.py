"""End-to-end tests following the checklist in the README (auth, seeker, employer, security)."""
import re

import pytest

from conftest import PDF, PNG

JOB = {"title": "Python Developer", "description": "Build APIs with FastAPI and MySQL for our products.",
       "location": "Pune, Maharashtra", "employment_type": "Full Time", "experience_required": "1",
       "salary_min": "5", "salary_max": "8", "skills": "Python, FastAPI, MySQL", "status": "active",
       "requirements": "Python\nSQL", "responsibilities": "Build APIs\nWrite tests", "deadline": ""}


# ---------------------------------------------------------------- fixtures
@pytest.fixture(scope="module")
def world(new_session, app_module):
    """One employer (with a job), a second employer, two seekers - created through the real forms."""
    w = {}
    w["emp"], w["emp2"] = new_session(), new_session()
    w["s1"], w["s2"] = new_session(), new_session()
    w["anon"] = new_session()
    assert w["emp"].register("employer", "ABC Technologies", "hr@abc.test").status_code == 200
    assert w["emp2"].register("employer", "Other Corp", "hr@other.test").status_code == 200
    assert w["s1"].register("seeker", "Vivek Test", "vivek@test.dev").status_code == 200
    assert w["s2"].register("seeker", "Second Seeker", "second@test.dev").status_code == 200
    r = w["emp"].post("/employer/jobs/create", JOB)
    assert r.status_code == 303
    from database.connection import SessionLocal
    from database.models import Job
    with SessionLocal() as db:
        w["job_id"] = db.query(Job).filter_by(title="Python Developer").one().id
    return w


# -------------------------------------------------------------- public pages
def test_public_pages(new_session, world):
    s = new_session()
    for url in ("/", "/jobs", "/companies", "/about", f"/jobs/{world['job_id']}", "/companies/1", "/login", "/register"):
        assert s.get(url).status_code == 200, url
    assert "Find the Right Job" in s.get("/").text


def test_404_page_is_friendly(new_session):
    r = new_session().get("/definitely-missing")
    assert r.status_code == 404 and "Page not found" in r.text and "Traceback" not in r.text
    assert new_session().get("/jobs/99999").status_code == 404
    assert new_session().get("/companies/99999").status_code == 404


# ------------------------------------------------------------- authentication
def test_register_validation(new_session):
    s = new_session()
    r = s.post("/register", {"role": "seeker", "name": "A", "email": "bad", "password": "short", "confirm_password": "x"})
    assert r.status_code == 400 and "valid email" in r.text
    r = s.post("/register", {"role": "seeker", "name": "Dup", "email": "vivek@test.dev", "password": "Secret123",
                             "confirm_password": "Secret123"})
    assert r.status_code == 400 and "already exists" in r.text
    r = s.post("/register", {"role": "seeker", "name": "Mismatch", "email": "m@test.dev", "password": "Secret123",
                             "confirm_password": "Secret124"})
    assert r.status_code == 400 and "do not match" in r.text


def test_password_is_hashed(world):
    from database.connection import SessionLocal
    from database.models import User
    with SessionLocal() as db:
        u = db.query(User).filter_by(email="vivek@test.dev").one()
        assert u.password_hash.startswith("$2") and "Secret123" not in u.password_hash


def test_login_logout(new_session):
    s = new_session()
    r = s.login("vivek@test.dev", "wrongpass1")
    assert r.status_code == 401 and "Invalid email or password" in r.text
    r = s.login("nobody@test.dev")
    assert r.status_code == 401
    r = s.login("vivek@test.dev")
    assert r.status_code == 200 and "Welcome, Vivek Test" in r.text
    r = s.post("/logout", follow_redirects=True)
    assert "logged out" in r.text
    assert s.get("/seeker/dashboard", follow_redirects=False).status_code == 303


def test_employer_login_redirect(new_session):
    s = new_session()
    r = s.login("hr@abc.test")
    assert "Welcome, ABC Technologies" in r.text and str(r.url).endswith("/employer/dashboard")


def test_login_next_is_local_only(new_session):
    s = new_session()
    r = s.post("/login", {"email": "vivek@test.dev", "password": "Secret123", "next": "https://evil.example"})
    assert r.headers["location"] == "/seeker/dashboard"


def test_csrf_required(new_session):
    s = new_session()
    r = s.post("/login", {"email": "vivek@test.dev", "password": "Secret123"}, csrf=False)
    assert r.status_code == 403


# ----------------------------------------------------------------- seeker
def test_seeker_profile_flow(world):
    s = world["s1"]
    s.login("vivek@test.dev")
    r = s.post("/seeker/profile/edit", {
        "full_name": "Vivek Test", "headline": "Full Stack Developer", "phone": "+91 98765 43210",
        "location": "Kolhapur, Maharashtra", "about": "BCA student who loves building web apps.",
        "linkedin_url": "https://linkedin.com/in/vivek", "github_url": "", "portfolio_url": "",
        "skills": "Python, FastAPI, python, MySQL"},
        files={"photo": ("me.png", PNG, "image/png")}, follow_redirects=True)
    assert r.status_code == 200 and "Profile updated" in r.text
    assert "Full Stack Developer" in r.text and "FastAPI" in r.text and "/uploads/profile_images/" in r.text
    assert r.text.count('class="skill-chip">Python<') == 1  # de-duplicated, case-insensitive
    # served image works
    path = re.search(r'src="(/uploads/profile_images/[^"]+)"', r.text).group(1)
    assert s.get(path).status_code == 200


def test_profile_image_validation(world):
    s = world["s1"]
    base = {"full_name": "Vivek Test", "skills": ""}
    r = s.post("/seeker/profile/edit", base, files={"photo": ("x.gif", b"GIF89a", "image/gif")})
    assert r.status_code == 400 and "JPG, JPEG or PNG" in r.text
    r = s.post("/seeker/profile/edit", base, files={"photo": ("x.png", b"not really a png", "image/png")})
    assert r.status_code == 400 and "not a valid" in r.text
    big = PNG + b"\x00" * (2 * 1024 * 1024)
    r = s.post("/seeker/profile/edit", base, files={"photo": ("big.png", big, "image/png")})
    assert r.status_code == 400 and "too large" in r.text
    r = s.post("/seeker/profile/edit", {"full_name": "V", "skills": ""})
    assert r.status_code == 400 and "Full name is required" in r.text
    r = s.post("/seeker/profile/edit", {"full_name": "Vivek Test", "linkedin_url": "javascript:alert(1)"})
    assert r.status_code == 400 and "valid link" in r.text


def test_education_experience(world):
    s = world["s1"]
    r = s.post("/seeker/education/add", {"institution": "Shivaji University", "degree": "BCA", "field_of_study": "Computer Applications",
                                         "start_year": "2023", "end_year": "2026"}, follow_redirects=True)
    assert "Education added" in r.text and "Shivaji University" in r.text
    r = s.post("/seeker/education/add", {"institution": "X", "degree": "Y", "start_year": "2025", "end_year": "2020"}, follow_redirects=True)
    assert "End year cannot be before" in r.text
    r = s.post("/seeker/experience/add", {"company_name": "Sahyadri Infotech", "job_title": "Intern", "start_date": "2025-06-01", "end_date": ""},
               follow_redirects=True)
    assert "Experience added" in r.text and "Present" in s.get("/seeker/profile").text


def test_resume_upload_and_validation(world):
    s = world["s1"]
    r = s.post("/seeker/resume", files={"resume": ("cv.txt", b"hello", "text/plain")}, follow_redirects=True)
    assert "Resume must be a PDF" in r.text
    r = s.post("/seeker/resume", files={"resume": ("cv.pdf", b"not a pdf at all", "application/pdf")}, follow_redirects=True)
    assert "not a valid PDF" in r.text
    big = PDF + b"0" * (5 * 1024 * 1024)
    r = s.post("/seeker/resume", files={"resume": ("cv.pdf", big, "application/pdf")}, follow_redirects=True)
    assert "too large" in r.text
    r = s.post("/seeker/resume", files={"resume": ("cv.pdf", PDF, "application/pdf")}, follow_redirects=True)
    assert "Resume uploaded successfully" in r.text
    r = s.get("/resumes/%d" % _seeker_id("vivek@test.dev"))
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf" and r.content == PDF
    assert "attachment" in s.get("/resumes/%d?download=1" % _seeker_id("vivek@test.dev")).headers["content-disposition"]
    # replace: old file removed
    import os
    from database.connection import SessionLocal
    from database.models import JobSeeker
    from services import file_service
    with SessionLocal() as db:
        old = db.query(JobSeeker).filter_by(id=_seeker_id("vivek@test.dev")).one().resume_path
    s.post("/seeker/resume", files={"resume": ("cv2.pdf", PDF + b"\n%new", "application/pdf")})
    assert not (file_service.UPLOAD_DIR / old).exists()


def _seeker_id(email):
    from database.connection import SessionLocal
    from database.models import User
    with SessionLocal() as db:
        return db.query(User).filter_by(email=email).one().seeker.id


def test_profile_completion_is_100(world):
    html = world["s1"].get("/seeker/dashboard").text
    assert "Profile Completion" in html
    assert re.search(r"<p class=\"text-3xl font-extrabold text-slate-900 mt-1\">(\d+)%</p>", html).group(1) == "100"


# ----------------------------------------------------------------- employer
def test_company_profile_and_logo(world):
    e = world["emp"]
    form = {"company_name": "ABC Technologies", "description": "We build software.", "industry": "Information Technology",
            "company_size": "51-200", "founded_year": "2018", "website": "https://abc.example.com",
            "email": "hr@abc.example.com", "phone": "+91 22 5550 1000", "address": "BKC", "city": "Mumbai",
            "state": "Maharashtra", "country": "India", "linkedin_url": ""}
    r = e.post("/employer/profile/edit", form, files={"logo": ("logo.png", PNG, "image/png")}, follow_redirects=True)
    assert r.status_code == 200 and "Company profile updated" in r.text
    assert "Information Technology" in r.text and "51-200 Employees" in r.text and "/uploads/company_logos/" in r.text
    r = e.post("/employer/profile/edit", form, files={"logo": ("logo.exe", b"MZ", "application/octet-stream")})
    assert r.status_code == 400 and "JPG, JPEG or PNG" in r.text
    r = e.post("/employer/profile/edit", {**form, "website": "not-a-url"})
    assert r.status_code == 400


def test_job_create_validation_and_search(world, new_session):
    e = world["emp"]
    r = e.post("/employer/jobs/create", {**JOB, "title": "x", "salary_min": "9", "salary_max": "3"})
    assert r.status_code == 400 and "Minimum salary cannot be greater" in r.text and "Job title is required" in r.text
    s = new_session()
    assert "Python Developer" in s.get("/jobs?q=fastapi").text
    assert "Python Developer" in s.get("/jobs?q=abc").text           # company name
    assert "Python Developer" in s.get("/jobs?location=pune&type=Full+Time&salary=5&experience=1&posted=7").text
    assert "No jobs match" in s.get("/jobs?q=zzzzzz").text
    assert "No jobs match" in s.get("/jobs?type=Internship").text
    assert "No jobs match" in s.get("/jobs?salary=20").text
    assert "No jobs match" in s.get("/jobs?experience=0").text
    assert s.get("/jobs?page=999&q=%25").status_code == 200       # odd input is safe


def test_job_details_buttons(world, new_session):
    jid = world["job_id"]
    assert "Login to Apply" in new_session().get(f"/jobs/{jid}").text
    world["s2"].login("second@test.dev")
    assert "Apply Now" in world["s2"].get(f"/jobs/{jid}").text
    assert "Edit Job" in world["emp"].get(f"/jobs/{jid}").text


def test_apply_flow_and_duplicates(world):
    jid, s = world["job_id"], world["s1"]
    assert "saved resume will be attached" in s.get(f"/jobs/{jid}/apply").text
    r = s.post(f"/jobs/{jid}/apply", {"cover_letter": "Hello, I'd love to join."}, follow_redirects=True)
    assert "Application submitted" in r.text and "Python Developer" in r.text and "Applied" in r.text
    r = s.post(f"/jobs/{jid}/apply", {"cover_letter": "again"}, follow_redirects=True)
    assert "already applied" in r.text
    assert "Already Applied" in s.get(f"/jobs/{jid}").text
    from database.connection import SessionLocal
    from database.models import Application
    with SessionLocal() as db:
        assert db.query(Application).filter_by(job_id=jid).count() == 1


def test_apply_requires_resume_and_validates(world):
    jid, s = world["job_id"], world["s2"]
    r = s.post(f"/jobs/{jid}/apply", {"cover_letter": ""})
    assert r.status_code == 400 and "upload your resume" in r.text
    r = s.post(f"/jobs/{jid}/apply", {}, files={"resume": ("a.pdf", b"nope", "application/pdf")})
    assert r.status_code == 400 and "not a valid PDF" in r.text
    r = s.post(f"/jobs/{jid}/apply", {"cover_letter": "Hi"}, files={"resume": ("a.pdf", PDF, "application/pdf")}, follow_redirects=True)
    assert "Application submitted" in r.text


def test_employer_manages_applications(world):
    e, jid = world["emp"], world["job_id"]
    html = e.get("/employer/applications").text
    assert "Vivek Test" in html and "Second Seeker" in html and "Python Developer" in html
    from database.connection import SessionLocal
    from database.models import Application
    with SessionLocal() as db:
        apps = {a.seeker.full_name: a.id for a in db.query(Application).filter_by(job_id=jid)}
    r = e.get(f"/applications/{apps['Vivek Test']}/resume")
    assert r.status_code == 200 and r.content.startswith(b"%PDF")
    assert e.get(f"/applications/{apps['Vivek Test']}/resume?download=1").status_code == 200
    assert e.get(f"/seekers/{_seeker_id('vivek@test.dev')}").status_code == 200       # may view applicant profile
    assert e.get(f"/resumes/{_seeker_id('vivek@test.dev')}").status_code == 200
    r = e.post(f"/employer/applications/{apps['Vivek Test']}/status", {"status": "Shortlisted", "back": "/employer/applications?status="},
               follow_redirects=True)
    assert "marked as Shortlisted" in r.text
    r = e.post(f"/employer/applications/{apps['Vivek Test']}/status", {"status": "Hacked"}, follow_redirects=True)
    assert "Invalid application status" in r.text
    assert "Shortlisted" in world["s1"].get("/seeker/applications").text
    assert "Vivek Test" in e.get("/employer/applications?status=Shortlisted").text
    assert "Second Seeker" not in e.get("/employer/applications?status=Shortlisted").text
    # can no longer withdraw once processed
    r = world["s1"].post(f"/seeker/applications/{apps['Vivek Test']}/withdraw", follow_redirects=True)
    assert "can no longer be withdrawn" in r.text
    # but can withdraw while 'Applied'
    r = world["s2"].post(f"/seeker/applications/{apps['Second Seeker']}/withdraw", follow_redirects=True)
    assert "Application withdrawn" in r.text


def test_edit_close_delete_job(world):
    e, jid = world["emp"], world["job_id"]
    r = e.post(f"/employer/jobs/{jid}/edit", {**JOB, "title": "Senior Python Developer"}, follow_redirects=True)
    assert "Job updated" in r.text and "Senior Python Developer" in r.text
    r = e.post(f"/employer/jobs/{jid}/status", {"status": "closed"}, follow_redirects=True)
    assert "Job closed" in r.text
    anon = world["anon"]
    assert anon.get(f"/jobs/{jid}").status_code == 404                  # closed jobs are hidden from the public
    assert "Senior Python Developer" not in anon.get("/jobs").text
    assert e.get(f"/jobs/{jid}").status_code == 200                      # ...but not from the owner
    e.post(f"/employer/jobs/{jid}/status", {"status": "active"})
    # delete a throw-away job together with its application
    e.post("/employer/jobs/create", {**JOB, "title": "Temp Job"})
    from database.connection import SessionLocal
    from database.models import Application, Job
    with SessionLocal() as db:
        tid = db.query(Job).filter_by(title="Temp Job").one().id
    world["s2"].post(f"/jobs/{tid}/apply", {"cover_letter": "x"}, files={"resume": ("a.pdf", PDF, "application/pdf")})
    r = e.post(f"/employer/jobs/{tid}/delete", follow_redirects=True)
    assert "Job deleted" in r.text
    with SessionLocal() as db:
        assert db.get(Job, tid) is None and db.query(Application).filter_by(job_id=tid).count() == 0


# ----------------------------------------------------------------- security
def test_role_based_access(world, new_session):
    assert world["s1"].get("/employer/dashboard").status_code == 403
    assert world["s1"].get("/employer/jobs/create").status_code == 403
    assert world["emp"].get("/seeker/dashboard").status_code == 403
    assert world["emp"].get("/seeker/profile/edit").status_code == 403
    assert world["emp"].get(f"/jobs/{world['job_id']}/apply").status_code == 403
    anon = new_session()
    for url in ("/seeker/dashboard", "/employer/dashboard", "/seeker/applications", "/employer/applications"):
        r = anon.get(url, follow_redirects=False)
        assert r.status_code == 303 and r.headers["location"].startswith("/login?next=")


def test_employer_cannot_touch_other_companys_job(world):
    jid = world["job_id"]
    other = world["emp2"]
    assert other.get(f"/employer/jobs/{jid}/edit").status_code == 403
    assert other.post(f"/employer/jobs/{jid}/edit", JOB).status_code == 403
    assert other.post(f"/employer/jobs/{jid}/delete").status_code == 403
    assert other.post(f"/employer/jobs/{jid}/status", {"status": "closed"}).status_code == 403
    assert "Python Developer" in world["anon"].get("/jobs").text


def test_employer_cannot_touch_other_applications_or_resumes(world):
    from database.connection import SessionLocal
    from database.models import Application
    with SessionLocal() as db:
        app_id = db.query(Application).filter_by(job_id=world["job_id"]).first().id
    other = world["emp2"]
    assert other.post(f"/employer/applications/{app_id}/status", {"status": "Selected"}).status_code == 403
    assert other.get(f"/applications/{app_id}/resume").status_code == 403
    sid = _seeker_id("vivek@test.dev")
    assert other.get(f"/resumes/{sid}").status_code == 403           # not an applicant to emp2
    assert other.get(f"/seekers/{sid}").status_code == 403
    assert world["s2"].get(f"/resumes/{sid}").status_code == 403     # other seekers can't view it either
    assert world["s2"].get(f"/seekers/{sid}").status_code == 403
    assert world["s2"].get(f"/applications/{app_id}/resume").status_code == 403
    assert world["anon"].get(f"/resumes/{sid}", follow_redirects=False).status_code == 303   # anonymous -> login


def test_seeker_cannot_touch_other_seekers_data(world):
    from database.connection import SessionLocal
    from database.models import Application, Education
    with SessionLocal() as db:
        edu_id = db.query(Education).first().id
        app_id = db.query(Application).filter_by(job_id=world["job_id"]).first().id
    assert world["s2"].post(f"/seeker/education/{edu_id}/delete").status_code == 403
    assert world["s2"].post(f"/seeker/applications/{app_id}/withdraw").status_code == 403


def test_resumes_not_publicly_served(world):
    from database.connection import SessionLocal
    from database.models import JobSeeker
    with SessionLocal() as db:
        rel = db.get(JobSeeker, _seeker_id("vivek@test.dev")).resume_path
    assert world["anon"].get("/uploads/" + rel).status_code == 404
    assert world["anon"].get("/uploads/resumes/").status_code == 404


def test_xss_is_escaped(world):
    s = world["s2"]
    s.post("/seeker/profile/edit", {"full_name": "Second Seeker", "headline": "<script>alert(1)</script>", "skills": ""})
    html = s.get("/seeker/profile").text
    assert "<script>alert(1)</script>" not in html and "&lt;script&gt;" in html


def test_sql_injection_attempts(new_session):
    s = new_session()
    assert s.get("/jobs?q=' OR 1=1 --").status_code == 200
    assert "No jobs match" in s.get("/jobs?q=%27%20OR%201%3D1%20--").text
    r = s.login("' OR '1'='1", "x")
    assert r.status_code == 401


def test_inactive_user_cannot_login(world, new_session):
    from database.connection import SessionLocal
    from database.models import User
    w = new_session()
    w.register("seeker", "Blocked User", "blocked@test.dev")
    w.post("/logout")
    with SessionLocal() as db:
        u = db.query(User).filter_by(email="blocked@test.dev").one()
        u.is_active = False
        db.commit()
    r = w.login("blocked@test.dev")
    assert r.status_code == 403 and "deactivated" in r.text


# --------------------------------------------------------- sample data / DB
def test_seed_data_renders_everywhere(tmp_path):
    """Seed a fresh DB and make sure every page renders for every role."""
    import os
    from fastapi.testclient import TestClient
    from database.connection import SessionLocal
    from services.seed_data import SAMPLE_PASSWORD, seed
    from database.models import Base
    from database.connection import engine
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        counts = seed(db, tmp_path)
    assert counts == {"companies": 5, "seekers": 10, "jobs": 15, "applications": 20}
    import app as app_module
    c = TestClient(app_module.app)
    from conftest import Session
    s = Session(c)
    html = c.get("/").text
    assert "TechVista Solutions" in html and "Python Developer" in html
    for url in ("/jobs", "/jobs?page=2", "/companies", "/companies/1", "/jobs/1", "/jobs/15", "/jobs/12"):
        assert c.get(url).status_code in (200, 404), url
    assert c.get("/jobs/15").status_code == 404  # draft hidden
    s.login("aarav.sharma@example.com", SAMPLE_PASSWORD)
    for url in ("/seeker/dashboard", "/seeker/profile", "/seeker/profile/edit", "/seeker/resume", "/seeker/applications", "/jobs/1/apply"):
        assert c.get(url).status_code == 200, url
    s.post("/logout")
    s.login("hr@techvista.example.com", SAMPLE_PASSWORD)
    for url in ("/employer/dashboard", "/employer/jobs", "/employer/jobs/create", "/employer/jobs/1/edit", "/employer/applications",
                "/employer/applications?page=1&status=Shortlisted", "/employer/profile/edit", "/employer/profile"):
        assert c.get(url, follow_redirects=True).status_code == 200, url
