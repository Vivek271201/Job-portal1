# JobPortal – Full-Stack Job Portal (FastAPI + MySQL)

A modern recruitment website with two user types – **Job Seekers** and **Employers (Companies)**.
Companies create profiles, post jobs and manage applicants. Job seekers build a LinkedIn-style profile,
upload a resume and apply for jobs. This is a normal job portal (no AI/ML features).

## 1. Features
- Register / login / logout (session based, bcrypt password hashing, "remember me", show/hide password)
- **Job seeker:** profile photo, headline, about, skills, education, experience, social links, resume (PDF) upload/replace/view/download,
  profile-completion %, dashboard, job search + filters, apply (existing or new resume + cover letter), track status, withdraw
- **Employer:** company profile with logo + cover, post/edit/close/reopen/delete jobs, applications table with filters,
  view applicant profile, view/download resume, change status (Applied → Under Review → Shortlisted → Rejected / Selected)
- Public pages: landing page (live stats), job search with pagination, job details, companies directory, company profile
- Security: CSRF tokens, role-based access, ownership checks, upload validation (extension + MIME + magic bytes + size),
  private resumes (only the owner and employers the seeker applied to can open them), safe filenames, SQLAlchemy (no raw SQL),
  friendly 403/404/500 pages that never show raw errors
- Responsive Tailwind UI: sidebar dashboards, cards, badges, empty states, alerts, loading buttons, mobile hamburger menu

## 2. Technology stack
Python 3.11+ · FastAPI · Uvicorn · SQLAlchemy 2 · PyMySQL · MySQL 8 / MariaDB / XAMPP · Jinja2 · Tailwind CSS (CDN) ·
Font Awesome · Vanilla JavaScript · bcrypt · python-dotenv · pytest

> Tailwind, Font Awesome and the Inter font load from a CDN, so you need an internet connection to see the styling.

## 3. Screenshots
Add your screenshots here (landing page, job list, job details, seeker profile, company profile, dashboards).

## 4. Project structure
```
job_portal/
├── app.py                 FastAPI app, middleware, error handlers
├── templating.py          Jinja2 filters/helpers
├── seed.py                optional: load sample data through SQLAlchemy
├── requirements.txt / requirements-dev.txt
├── .env  /  .env.example  settings (never commit .env)
├── database/              connection.py (engine) · models.py (9 tables)
├── routes/                public · auth · jobs · seeker · employer · deps (login/role/CSRF dependencies)
├── services/              auth_service · file_service · job_service · profile_service · access · validation · seed_data
├── templates/             base, dash_base, components/macros, index, auth/, seeker/, employer/, jobs/, public/, errors/
├── static/                css/style.css · js/main.js · images/
├── uploads/               profile_images · company_logos · company_covers · resumes (private)
├── sql/database.sql       schema + sample data for MySQL Workbench
├── tools/build_sql.py     regenerates database.sql from the models
└── tests/                 pytest suite (29 end-to-end tests)
```

## 5. Installation (Windows 10/11, Python 3.11+)
Open a terminal inside the `job_portal` folder (VS Code → Terminal).

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```
PowerShell says "running scripts is disabled"? Run once:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` and activate again (or use `cmd` instead of PowerShell).

## 6. MySQL Workbench / XAMPP setup
1. Make sure MySQL is running (MySQL Server service, or **XAMPP Control Panel → MySQL → Start**).
2. Open **MySQL Workbench** and connect (`localhost`, port `3306`, user `root`).
3. Menu **File → Open SQL Script…** and choose `sql/database.sql`.
4. Click the **lightning bolt** (Execute). This creates the database `job_portal`, all tables, indexes, foreign keys
   and the sample data. Refresh the *Schemas* panel to see it.
   (Alternative: skip the SQL file – the app creates the empty tables itself on first start, and `python seed.py` adds sample data.)

> ⚠ `database.sql` drops and re-creates the tables, so re-importing resets the data.

## 7. `.env` configuration
Edit `.env` (a copy of `.env.example`):
```
DATABASE_URL=mysql+pymysql://root:YOUR_PASSWORD@localhost:3306/job_portal
SECRET_KEY=change_this_secret_key
```
- XAMPP's root user has **no password** by default → `mysql+pymysql://root:@localhost:3306/job_portal`
- Password contains `@ # : /`? URL-encode it (e.g. `@` → `%40`).
- Use a long random `SECRET_KEY` (`python -c "import secrets; print(secrets.token_hex(32))"`).
- Cloud MySQL with TLS (e.g. TiDB Cloud): put the CA file path in `DB_SSL_CA=` .
- Set `SESSION_HTTPS_ONLY=1` when you deploy behind HTTPS.

## 8. Running the project
```powershell
venv\Scripts\activate
uvicorn app:app --reload
```
Open **http://127.0.0.1:8000**. If MySQL is unreachable the terminal prints a clear "DATABASE CONNECTION FAILED" message with a checklist.

## 9. User roles
| Role | After login | Can |
|---|---|---|
| Job Seeker | `/seeker/dashboard` | profile, resume, search, apply, track applications |
| Employer | `/employer/dashboard` | company profile, jobs, applicants, status changes |

## 10. Sample login credentials
Password for **every** sample account: `Password@123`

| Role | Email |
|---|---|
| Employer | `hr@techvista.example.com` (Pune) · `careers@cloudnine.example.com` · `jobs@finedge.example.com` · `hello@sahyadri.example.com` · `talent@databridge.example.com` |
| Seeker | `aarav.sharma@example.com` · `priya.patil@example.com` · `rohan.deshmukh@example.com` · `sneha.iyer@example.com` · `neha.joshi@example.com` (incomplete profile) … 10 in total |

Sample data: 5 companies, 10 seekers, 15 jobs (13 active, 1 closed, 1 draft), 20 applications, skills, education, experience.
Register your own accounts too – new users have empty profiles.

## 11. File uploads
| What | Allowed | Max | Stored in |
|---|---|---|---|
| Profile photo, company logo/cover | JPG, JPEG, PNG | 2 MB | `uploads/profile_images/`, `company_logos/`, `company_covers/` |
| Resume | PDF only | 5 MB | `uploads/resumes/` |

Files get a random unique name (`uuid4`), the extension, MIME type and file signature are all checked, and only the relative
path (e.g. `resumes/ab12….pdf`) is saved in MySQL. Images are served at `/uploads/...`; **resumes are never public** – they are
streamed by permission-checked routes (`/resumes/<seeker_id>`, `/applications/<id>/resume`). When a seeker applies, the resume is
copied so replacing it later does not change what the employer already received.
Limits can be changed at the top of `services/file_service.py`.

## 12. Testing
```powershell
pip install -r requirements-dev.txt
python -m pytest -q
```
The tests use a temporary SQLite database and a temp upload folder, so they never touch your MySQL data.
To run them against MySQL instead: create an empty database `job_portal_test` and set
`TEST_DATABASE_URL=mysql+pymysql://root:PASSWORD@localhost:3306/job_portal_test` (the tests drop its tables).

Covered: register/login/logout, validation, duplicate email, CSRF, seeker profile/photo/resume/education/experience, company
profile/logo, create/edit/close/delete job, search + filters, apply, duplicate-apply prevention, status changes, withdraw,
role-based access, other-employer/other-seeker access attempts, private resumes, XSS escaping, SQL-injection inputs, inactive accounts,
and every page rendering with the sample data.

Manual checklist (browser): register seeker → complete profile → upload photo + PDF resume → search jobs → apply → see it under
Applications. Register employer → edit company + logo → post job → open Applications → download resume → set status → log in as the seeker and see the new status.

## 13. Troubleshooting
| Problem | Fix |
|---|---|
| `DATABASE CONNECTION FAILED` – *Can't connect* | Start MySQL (XAMPP/Windows service); check port 3306 |
| *Access denied for user 'root'* | Wrong password in `.env`; XAMPP root has an empty password |
| *Unknown database 'job_portal'* | Import `sql/database.sql` (step 6) or run `CREATE DATABASE job_portal;` |
| `cryptography` / `caching_sha2_password` error | `pip install cryptography` (already in requirements.txt) |
| Page has no styling | Needs internet for the Tailwind/Font Awesome CDNs |
| "security token is missing or expired" | Refresh the page (session expired or cookies blocked) |
| Logged out again after restart | Keep the same `SECRET_KEY` in `.env` |
| Port 8000 busy | `uvicorn app:app --reload --port 8001` |
| `ModuleNotFoundError` | Activate the venv (`venv\Scripts\activate`) and re-run `pip install -r requirements.txt` |

## 14. Future improvements
Email notifications, password reset, saved/bookmarked jobs, company reviews, admin panel, interview scheduling,
Alembic migrations, rate limiting on login, Docker deployment.
