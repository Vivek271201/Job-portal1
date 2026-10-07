"""SQLAlchemy models for the Job Portal.

Tables: users, job_seekers, companies, jobs, applications, skills,
seeker_skills, education, experience.
"""
from datetime import date, datetime, timezone

from sqlalchemy import (Boolean, Date, DateTime, ForeignKey, Index, Integer,
                        String, Text, UniqueConstraint)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

TABLE_OPTS = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}

ROLE_SEEKER = "seeker"
ROLE_EMPLOYER = "employer"
APPLICATION_STATUSES = ["Applied", "Under Review", "Shortlisted", "Rejected", "Selected"]
EMPLOYMENT_TYPES = ["Full Time", "Part Time", "Internship", "Contract", "Remote"]
JOB_STATUSES = ["active", "closed", "draft"]
COMPANY_SIZES = ["1-10", "11-50", "51-200", "201-500", "501-1000", "1000+"]


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    __table_args__ = TABLE_OPTS


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    seeker: Mapped["JobSeeker"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan")
    company: Mapped["Company"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan")

    @property
    def display_name(self) -> str:
        if self.seeker:
            return self.seeker.full_name
        if self.company:
            return self.company.company_name
        return self.email


class JobSeeker(Base):
    __tablename__ = "job_seekers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    full_name: Mapped[str] = mapped_column(String(150))
    profile_image: Mapped[str | None] = mapped_column(String(255), nullable=True)
    headline: Mapped[str | None] = mapped_column(String(200), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    location: Mapped[str | None] = mapped_column(String(150), nullable=True)
    about: Mapped[str | None] = mapped_column(Text, nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    github_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    portfolio_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resume_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    user: Mapped[User] = relationship(back_populates="seeker")
    education: Mapped[list["Education"]] = relationship(
        back_populates="seeker", cascade="all, delete-orphan",
        order_by="Education.end_year.desc()")
    experience: Mapped[list["Experience"]] = relationship(
        back_populates="seeker", cascade="all, delete-orphan",
        order_by="Experience.start_date.desc()")
    skill_links: Mapped[list["SeekerSkill"]] = relationship(
        back_populates="seeker", cascade="all, delete-orphan")
    applications: Mapped[list["Application"]] = relationship(
        back_populates="seeker", cascade="all, delete-orphan")

    @property
    def skill_names(self) -> list[str]:
        return sorted((l.skill.name for l in self.skill_links), key=str.lower)

    @property
    def avatar_url(self) -> str | None:
        return f"/uploads/{self.profile_image}" if self.profile_image else None

    @property
    def initials(self) -> str:
        parts = (self.full_name or "?").split()
        return "".join(p[0] for p in parts[:2]).upper()

    @property
    def email(self) -> str:
        return self.user.email


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(60), unique=True)


class SeekerSkill(Base):
    __tablename__ = "seeker_skills"
    __table_args__ = (UniqueConstraint("seeker_id", "skill_id", name="uq_seeker_skill"), TABLE_OPTS)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    seeker_id: Mapped[int] = mapped_column(ForeignKey("job_seekers.id", ondelete="CASCADE"))
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"))

    seeker: Mapped[JobSeeker] = relationship(back_populates="skill_links")
    skill: Mapped[Skill] = relationship(lazy="joined")


class Education(Base):
    __tablename__ = "education"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    seeker_id: Mapped[int] = mapped_column(
        ForeignKey("job_seekers.id", ondelete="CASCADE"), index=True)
    institution: Mapped[str] = mapped_column(String(200))
    degree: Mapped[str] = mapped_column(String(150))
    field_of_study: Mapped[str | None] = mapped_column(String(150), nullable=True)
    start_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    seeker: Mapped[JobSeeker] = relationship(back_populates="education")


class Experience(Base):
    __tablename__ = "experience"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    seeker_id: Mapped[int] = mapped_column(
        ForeignKey("job_seekers.id", ondelete="CASCADE"), index=True)
    company_name: Mapped[str] = mapped_column(String(200))
    job_title: Mapped[str] = mapped_column(String(150))
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    seeker: Mapped[JobSeeker] = relationship(back_populates="experience")


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    company_name: Mapped[str] = mapped_column(String(200), index=True)
    logo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cover_image: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    industry: Mapped[str | None] = mapped_column(String(120), index=True, nullable=True)
    company_size: Mapped[str | None] = mapped_column(String(30), nullable=True)
    founded_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    user: Mapped[User] = relationship(back_populates="company")
    jobs: Mapped[list["Job"]] = relationship(
        back_populates="company", cascade="all, delete-orphan")

    @property
    def logo_url(self) -> str | None:
        return f"/uploads/{self.logo}" if self.logo else None

    @property
    def cover_url(self) -> str | None:
        return f"/uploads/{self.cover_image}" if self.cover_image else None

    @property
    def initials(self) -> str:
        return (self.company_name or "?")[0].upper()

    @property
    def location_text(self) -> str:
        return ", ".join(p for p in (self.city, self.state) if p)

    @property
    def open_jobs(self) -> list["Job"]:
        return [j for j in self.jobs if j.is_open]


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (Index("ix_jobs_status_created", "status", "created_at"), TABLE_OPTS)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    description: Mapped[str] = mapped_column(Text)
    requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    responsibilities: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str] = mapped_column(String(150))
    employment_type: Mapped[str] = mapped_column(String(30))
    experience_required: Mapped[int] = mapped_column(Integer, default=0)  # minimum years
    salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)  # INR per year
    salary_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    skills: Mapped[str | None] = mapped_column(String(500), nullable=True)  # comma separated
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    company: Mapped[Company] = relationship(back_populates="jobs")
    applications: Mapped[list["Application"]] = relationship(
        back_populates="job", cascade="all, delete-orphan")

    @property
    def skill_list(self) -> list[str]:
        return [s.strip() for s in (self.skills or "").split(",") if s.strip()]

    @property
    def deadline_passed(self) -> bool:
        return bool(self.deadline and self.deadline < date.today())

    @property
    def is_open(self) -> bool:
        return self.status == "active" and not self.deadline_passed

    @property
    def salary_text(self) -> str:
        def fmt(v):
            return f"₹{v / 100000:g} LPA"
        if self.salary_min and self.salary_max:
            return f"{fmt(self.salary_min)} - {fmt(self.salary_max)}"
        if self.salary_max:
            return f"Up to {fmt(self.salary_max)}"
        if self.salary_min:
            return f"From {fmt(self.salary_min)}"
        return "Not disclosed"

    @property
    def experience_text(self) -> str:
        return "Fresher" if not self.experience_required else f"{self.experience_required}+ years"


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("job_id", "seeker_id", name="uq_application_job_seeker"), TABLE_OPTS)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    seeker_id: Mapped[int] = mapped_column(
        ForeignKey("job_seekers.id", ondelete="CASCADE"), index=True)
    resume_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cover_letter: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Applied", index=True)
    applied_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    job: Mapped[Job] = relationship(back_populates="applications")
    seeker: Mapped[JobSeeker] = relationship(back_populates="applications")
