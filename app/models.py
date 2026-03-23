from datetime import datetime, timezone
import uuid
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from enum import Enum

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

class UserLevel(str, Enum):
    EMPLOYEE = "individual"
    MANAGER = "manager"

class User(BaseModel):
    name: str
    surname: str
    username: str
    hashed_password: str
    level: UserLevel = UserLevel.EMPLOYEE # employee default
    target_roles: List[Role] = []
    individual_skills: List[Skill] = []
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
    manager: str
    assigned_members: List[str] = []
    target_roles: List[Role] = []
    skill_gap: List[Dict[str, Any]] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Course(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    ects: Optional[int] = None
    format: Optional[str] = None
    link: Optional[str] = None
    duration_weeks: Optional[int] = None
    start_date: Optional[datetime] = None
    medium_of_instruction: Optional[str] = None
    cost: Optional[float] = None
    location: Optional[str] = None
    category: Optional[str] = None
    is_public: bool = False
    skills_covered: Optional[List[Skill]] = []

class Organization(BaseModel):
    name: str
    orgname: str
    hashed_password: str
    members: Dict[str, List[Skill]] = {}
    pending_members: Dict[str, List[Skill]] = {}
    projects: List[Project] = []
    courses: List[Course] = []

