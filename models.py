from datetime import datetime
import uuid
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, List, Any

class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    surname: str
    username: str
    email: EmailStr
    hashed_password: str
    target_roles: List[Dict[str, Any]] = []
    current_skills: Dict[str, str] = {}
    skill_gap: List[Dict[str, Any]] = []
    id_organization: Optional[str] = None

class Invitation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    org_id: str
    user_id: str
    status: str  # e.g., "pending", "accepted", "declined"
    created_at: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))

class Organization(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    address: str
    phone: str
    email: EmailStr
    orgname: str
    hashed_password: str
    members: List[str] = []

class Role(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    essential_skills: Dict[str, str] = {}
    optional_skills: Dict[str, str] = {}
    id_full: Optional[str] = None
    uri: Optional[str] = None

class Project(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    org_id: str
    name: str
    description: str
    assigned_members_ids: List[str] = []
    target_roles: List[Dict[str, Any]] = []
    skill_gap: List[Dict[str, Any]] = []
    created_at: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))

class Course(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    ects: int
    description: Optional[str] = None
    skills_covered: List[str] = []
