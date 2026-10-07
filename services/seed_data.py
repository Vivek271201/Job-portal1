"""Sample data: 5 companies, 10 job seekers, 15 jobs, 20 applications.

Used by seed.py and tools/build_sql.py. All sample accounts use the password
SAMPLE_PASSWORD. Names/emails are fictional (example.com).
"""
from datetime import date, datetime, timedelta

from database.models import (Application, Company, Education, Experience, Job, JobSeeker,
                             SeekerSkill, Skill, User, utcnow)
from services.auth_service import hash_password

SAMPLE_PASSWORD = "Password@123"

COMPANIES = [
    ("TechVista Solutions", "hr@techvista.example.com", "Information Technology", "201-500", 2012, "Pune", "Maharashtra",
     "https://techvista.example.com", "TechVista Solutions builds enterprise web and mobile software for clients across India and Europe. Our 300+ engineers work in agile teams on products used by millions."),
    ("CloudNine Systems", "careers@cloudnine.example.com", "Cloud & SaaS", "51-200", 2017, "Bangalore", "Karnataka",
     "https://cloudnine.example.com", "CloudNine Systems is a SaaS company delivering cloud-based HR and payroll tools to growing businesses. We value ownership, learning and a healthy work-life balance."),
    ("FinEdge Technologies", "jobs@finedge.example.com", "Fintech", "201-500", 2015, "Mumbai", "Maharashtra",
     "https://finedge.example.com", "FinEdge Technologies creates secure payment and lending platforms for banks and NBFCs. Our products process thousands of transactions every minute."),
    ("Sahyadri Infotech", "hello@sahyadri.example.com", "Software Development", "11-50", 2019, "Kolhapur", "Maharashtra",
     "https://sahyadri.example.com", "Sahyadri Infotech is a growing software studio from Kolhapur building websites, ERP systems and mobile apps for local and international clients."),
    ("DataBridge Insights", "talent@databridge.example.com", "Data & Analytics", "51-200", 2016, "Hyderabad", "Telangana",
     "https://databridge.example.com", "DataBridge Insights helps retailers and manufacturers make better decisions with dashboards, reporting and data engineering services."),
]

SEEKERS = [
    ("Aarav Sharma", "aarav.sharma@example.com", "Python Backend Developer", "Pune, Maharashtra", "+91 98765 10001",
     "Backend developer who enjoys building clean REST APIs with Python and FastAPI. Looking for a product company where I can grow.",
     "Python, FastAPI, MySQL, Git, Docker", ("MIT World Peace University", "B.Tech", "Computer Engineering", 2019, 2023),
     ("TechVista Solutions", "Software Engineer", date(2023, 7, 1), None)),
    ("Priya Patil", "priya.patil@example.com", "Full Stack Developer", "Kolhapur, Maharashtra", "+91 98765 10002",
     "BCA graduate with hands-on experience in building full-stack web apps using HTML, CSS, JavaScript and Python.",
     "HTML, CSS, JavaScript, Python, MySQL", ("Shivaji University", "BCA", "Computer Applications", 2020, 2023),
     ("Sahyadri Infotech", "Junior Web Developer", date(2023, 8, 1), None)),
    ("Rohan Deshmukh", "rohan.deshmukh@example.com", "Java Developer", "Mumbai, Maharashtra", "+91 98765 10003",
     "Java developer with experience in Spring Boot, Hibernate and relational databases.",
     "Java, Spring Boot, Hibernate, MySQL, JDBC", ("University of Mumbai", "BSc IT", "Information Technology", 2018, 2021),
     ("FinEdge Technologies", "Java Developer", date(2021, 9, 1), None)),
    ("Sneha Iyer", "sneha.iyer@example.com", "UI/UX Designer", "Bangalore, Karnataka", "+91 98765 10004",
     "Designer focused on clean, accessible interfaces for web and mobile products.",
     "Figma, UI Design, HTML, CSS, Prototyping", ("Christ University", "BDes", "Design", 2018, 2022), None),
    ("Vikram Reddy", "vikram.reddy@example.com", "DevOps Engineer", "Hyderabad, Telangana", "+91 98765 10005",
     "DevOps engineer automating deployments and monitoring on cloud platforms.",
     "Docker, Linux, CI/CD, AWS, Git", ("JNTU Hyderabad", "B.Tech", "Information Technology", 2016, 2020),
     ("DataBridge Insights", "DevOps Engineer", date(2020, 8, 1), None)),
    ("Ananya Gupta", "ananya.gupta@example.com", "Frontend Developer", "Delhi", "+91 98765 10006",
     "Frontend developer who loves responsive layouts and smooth user experiences.",
     "React, JavaScript, Tailwind CSS, HTML, CSS", ("Delhi University", "BCA", "Computer Applications", 2019, 2022),
     ("CloudNine Systems", "Frontend Developer", date(2022, 7, 1), date(2024, 3, 31))),
    ("Karthik Subramanian", "karthik.s@example.com", "QA Engineer", "Chennai, Tamil Nadu", "+91 98765 10007",
     "QA engineer experienced in manual and automation testing for web applications.",
     "Selenium, Java, Test Cases, SQL, Postman", ("Anna University", "B.E.", "Computer Science", 2017, 2021),
     ("TechVista Solutions", "QA Engineer", date(2021, 8, 1), None)),
    ("Neha Joshi", "neha.joshi@example.com", None, "Pune, Maharashtra", None, None, "SQL, Excel", None, None),
    ("Aditya Kulkarni", "aditya.kulkarni@example.com", "Software Intern", "Kolhapur, Maharashtra", "+91 98765 10009",
     "Final-year BCA student looking for an internship in web development.",
     "HTML, CSS, JavaScript, Python", ("Shivaji University", "BCA", "Computer Applications", 2023, 2026), None),
    ("Pooja Nair", "pooja.nair@example.com", "Data Analyst", "Bangalore, Karnataka", "+91 98765 10010",
     "Analyst who turns raw data into clear dashboards and reports.",
     "SQL, Excel, Power BI, Python", ("Bangalore University", "BSc", "Statistics", 2018, 2021),
     ("DataBridge Insights", "Data Analyst", date(2021, 10, 1), None)),
]

# (company_idx, title, location, type, exp_years, min_lpa, max_lpa, skills, status, days_ago)
JOBS = [
    (0, "Python Developer", "Pune, Maharashtra", "Full Time", 1, 5, 8, "Python, FastAPI, MySQL", "active", 2),
    (0, "Full Stack Developer", "Pune, Maharashtra", "Full Time", 2, 8, 14, "Python, JavaScript, HTML, CSS, MySQL", "active", 5),
    (0, "QA Automation Engineer", "Pune, Maharashtra", "Full Time", 2, 6, 10, "Selenium, Java, Postman, SQL", "active", 9),
    (1, "Frontend Developer (React)", "Bangalore, Karnataka", "Full Time", 1, 6, 11, "React, JavaScript, Tailwind CSS", "active", 1),
    (1, "DevOps Engineer", "Bangalore, Karnataka", "Full Time", 3, 12, 20, "Docker, AWS, CI/CD, Linux", "active", 7),
    (1, "Cloud Support Associate", "Remote", "Remote", 0, 3, 5, "Linux, AWS, Communication", "active", 3),
    (2, "Java Backend Developer", "Mumbai, Maharashtra", "Full Time", 3, 10, 18, "Java, Spring Boot, Hibernate, MySQL", "active", 4),
    (2, "Business Analyst", "Mumbai, Maharashtra", "Full Time", 2, 7, 12, "SQL, Excel, Requirement Analysis", "active", 12),
    (2, "Software Engineering Intern", "Mumbai, Maharashtra", "Internship", 0, 1.8, 2.4, "Python, SQL, Git", "active", 6),
    (3, "Web Developer (BCA/BSc IT)", "Kolhapur, Maharashtra", "Full Time", 0, 2.5, 4, "HTML, CSS, JavaScript, PHP", "active", 2),
    (3, "Mobile App Developer (Flutter)", "Kolhapur, Maharashtra", "Contract", 1, 4, 7, "Flutter, Dart, REST API", "active", 15),
    (3, "UI/UX Designer", "Kolhapur, Maharashtra", "Part Time", 0, 2, 3.5, "Figma, UI Design, Prototyping", "closed", 40),
    (4, "Data Analyst", "Hyderabad, Telangana", "Full Time", 1, 5, 9, "SQL, Power BI, Excel, Python", "active", 8),
    (4, "Database Administrator", "Hyderabad, Telangana", "Full Time", 4, 12, 18, "MySQL, Performance Tuning, Backup", "active", 11),
    (4, "Technical Support Engineer", "Chennai, Tamil Nadu", "Full Time", 0, 3, 5, "Troubleshooting, SQL, Communication", "draft", 1),
]

# (seeker_idx, job_idx, status, days_ago)
APPLICATIONS = [
    (0, 0, "Shortlisted", 1), (0, 1, "Under Review", 3), (1, 9, "Selected", 6), (1, 1, "Applied", 2),
    (2, 6, "Under Review", 3), (3, 11, "Rejected", 30), (4, 4, "Shortlisted", 5), (5, 3, "Applied", 1),
    (5, 1, "Under Review", 4), (6, 2, "Rejected", 7), (7, 7, "Applied", 2), (8, 8, "Shortlisted", 4),
    (8, 9, "Applied", 1), (9, 12, "Selected", 6), (9, 7, "Under Review", 5), (0, 5, "Applied", 2),
    (1, 0, "Rejected", 8), (4, 5, "Under Review", 2), (2, 13, "Applied", 3), (6, 8, "Applied", 1),
]


def make_pdf(lines: list[str]) -> bytes:
    """Create a tiny valid one-page PDF (used for sample resumes)."""
    esc = lambda s: s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")  # noqa: E731
    stream = "BT /F1 16 Tf 60 780 Td 22 TL " + " ".join(f"({esc(l)}) Tj T*" for l in lines) + " ET"
    objs = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 5 0 R /Resources << /Font << /F1 4 0 R >> >> >>",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream",
    ]
    out, offsets = b"%PDF-1.4\n", []
    for i, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n{body}\nendobj\n".encode("latin-1")
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 25 n \n".encode().replace(b" 25 n", b" 00000 n")
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return out


def seed(db, upload_dir=None, now: datetime | None = None):
    """Insert sample data. Returns a dict of counts."""
    now = now or utcnow()
    pw = hash_password(SAMPLE_PASSWORD)
    companies, seekers, jobs = [], [], []

    for (name, email, industry, size, year, city, state, site, desc) in COMPANIES:
        u = User(email=email, password_hash=pw, role="employer", created_at=now - timedelta(days=60))
        c = Company(company_name=name, email=email, industry=industry, company_size=size, founded_year=year,
                    city=city, state=state, country="India", website=site, description=desc,
                    phone="+91 20 5550 01" + str(len(companies)) + "0", address=f"{city}, {state}, India",
                    linkedin_url=f"https://linkedin.com/company/{name.split()[0].lower()}")
        u.company = c
        db.add(u)
        companies.append(c)

    skills_cache = {}
    for (name, email, headline, loc, phone, about, skills, edu, exp) in SEEKERS:
        u = User(email=email, password_hash=pw, role="seeker", created_at=now - timedelta(days=45))
        s = JobSeeker(full_name=name, headline=headline, location=loc, phone=phone, about=about)
        u.seeker = s
        for sk in [x.strip() for x in skills.split(",")]:
            skill = skills_cache.get(sk.lower())
            if not skill:
                skill = skills_cache[sk.lower()] = Skill(name=sk)
                db.add(skill)
            s.skill_links.append(SeekerSkill(skill=skill))
        if edu:
            s.education.append(Education(institution=edu[0], degree=edu[1], field_of_study=edu[2],
                                         start_year=edu[3], end_year=edu[4]))
        if exp:
            s.experience.append(Experience(company_name=exp[0], job_title=exp[1], start_date=exp[2], end_date=exp[3],
                                           description="Worked on production features, fixed bugs and collaborated with the team."))
        db.add(u)
        seekers.append(s)
    db.flush()

    # sample resume PDFs (stored in uploads/resumes/)
    if upload_dir is not None:
        (upload_dir / "resumes").mkdir(parents=True, exist_ok=True)
    for i, s in enumerate(seekers):
        if i in (7, 3):  # two seekers have no resume, to demo "profile completion" suggestions
            continue
        rel = f"resumes/sample_resume_{i + 1}.pdf"
        if upload_dir is not None:
            (upload_dir / rel).write_bytes(make_pdf([s.full_name, s.headline or "", s.location or "", "",
                                                     "Sample resume generated for the JobPortal demo."]))
        s.resume_path = rel

    for (ci, title, loc, typ, exp, mn, mx, skills, status, ago) in JOBS:
        company = companies[ci]
        job = Job(company_id=company.id, title=title, location=loc, employment_type=typ, experience_required=exp,
                  salary_min=int(mn * 100000), salary_max=int(mx * 100000), skills=skills, status=status,
                  created_at=now - timedelta(days=ago), deadline=(now + timedelta(days=45)).date() if status == "active" else None,
                  description=(f"{company.company_name} is hiring a {title} to join our {loc.split(',')[0]} team. "
                               f"You will work with {skills.split(',')[0]} and related technologies, collaborate with "
                               "designers and product managers and ship features that matter to our customers."),
                  responsibilities="\n".join([f"Design, build and maintain features using {skills.split(',')[0].strip()}",
                                              "Write clean, tested and well-documented work",
                                              "Collaborate with the team in daily stand-ups and reviews",
                                              "Troubleshoot issues and continuously improve quality"]),
                  requirements="\n".join([f"Working knowledge of {skills}",
                                          "Degree in Computer Science, IT, BCA, MCA or equivalent",
                                          "Good communication and problem-solving skills",
                                          "Eagerness to learn new tools"]))
        db.add(job)
        jobs.append(job)
    db.flush()

    for (si, ji, status, ago) in APPLICATIONS:
        s = seekers[si]
        db.add(Application(job_id=jobs[ji].id, seeker_id=s.id, status=status, resume_path=s.resume_path,
                           applied_at=now - timedelta(days=ago),
                           cover_letter=f"Hello, I am {s.full_name} and I am excited to apply for the {jobs[ji].title} role. "
                                        "I believe my skills and enthusiasm make me a great fit."))
    db.commit()
    return {"companies": len(companies), "seekers": len(seekers), "jobs": len(jobs), "applications": len(APPLICATIONS)}
