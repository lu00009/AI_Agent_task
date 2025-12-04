from typing import TypedDict

class ExperienceItem(TypedDict):
    company: str
    role: str
    duration: str
    description: str

class EducationItem(TypedDict):
    institution: str
    degree: str
    year: str

class ResumeData(TypedDict):
    name: str
    skills: list[str]
    experience: list[ExperienceItem]
    education: list[EducationItem]
