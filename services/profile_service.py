"""Seeker profile helpers: completion percentage and skills handling."""
from sqlalchemy import func, select

from database.models import SeekerSkill, Skill

CHECKS = [
    ("profile_image", "a profile photo"), ("headline", "a professional headline"),
    ("about", "an about summary"), ("phone", "your phone number"),
    ("location", "your location"), ("skills", "your skills"),
    ("education", "your education"), ("experience", "your experience"),
    ("resume_path", "your resume"),
]


def profile_completion(seeker):
    done = {
        "profile_image": bool(seeker.profile_image), "headline": bool(seeker.headline),
        "about": bool(seeker.about), "phone": bool(seeker.phone),
        "location": bool(seeker.location), "skills": bool(seeker.skill_links),
        "education": bool(seeker.education), "experience": bool(seeker.experience),
        "resume_path": bool(seeker.resume_path),
    }
    total = len(CHECKS)
    count = sum(done.values())
    percent = round(count / total * 100)
    suggestions = []
    for key, label in CHECKS:
        if not done[key] and len(suggestions) < 3:
            suggestions.append(f"Add {label} to reach {round((count + len(suggestions) + 1) / total * 100)}%.")
    return {"percent": percent, "suggestions": suggestions, "done": done}


def parse_skills(raw: str) -> list[str]:
    seen, result = set(), []
    for part in (raw or "").replace("\n", ",").split(","):
        name = " ".join(part.split())[:50]
        if name and name.lower() not in seen:
            seen.add(name.lower())
            result.append(name)
    return result[:30]


def set_seeker_skills(db, seeker, names: list[str]):
    wanted = {n.lower(): n for n in names}
    for link in list(seeker.skill_links):
        if link.skill.name.lower() not in wanted:
            seeker.skill_links.remove(link)
    have = {l.skill.name.lower() for l in seeker.skill_links}
    for key, name in wanted.items():
        if key in have:
            continue
        skill = db.scalar(select(Skill).where(func.lower(Skill.name) == key))
        if not skill:
            skill = Skill(name=name)
            db.add(skill)
        seeker.skill_links.append(SeekerSkill(skill=skill))
