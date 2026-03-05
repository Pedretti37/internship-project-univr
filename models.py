from datetime import datetime, timezone
import uuid
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, List, Any

class Skill(BaseModel):
    uri: str
    name: str
    level: int

class Role(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    essential_skills: List[Skill] = []
    id_full: Optional[str] = None
    uri: Optional[str] = None

class User(BaseModel):
    name: str
    surname: str
    username: str
    email: EmailStr
    hashed_password: str
    target_roles: List[Role] = []
    current_skills: List[Skill] = []
    skill_gap: List[Dict[str, Any]] = []
    organization: Optional[str] = None

class Invitation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    orgname: str
    username: str
    status: str  # e.g., "pending", "accepted", "declined"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Project(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    assigned_members: List[str] = []
    target_roles: List[Role] = []
    skill_gap: List[Dict[str, Any]] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Organization(BaseModel):
    name: str
    address: str
    phone: str
    email: EmailStr
    orgname: str
    hashed_password: str
    members: List[str] = []
    projects: List[Project] = []

class Course(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    ects: int
    description: Optional[str] = None
    skills_covered: List[Skill] = []
