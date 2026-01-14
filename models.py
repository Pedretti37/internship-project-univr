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
    current_skills: Dict[str, int] = {}
    skill_gap: Dict[str, List[Any]] = {}
    id_organization: Optional[str] = None

class Organization(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    address: str
    phone: str
    email: EmailStr
    orgname: str
    hashed_password: str
    members: List[User] = []

class Role(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    essential_skills: Optional[str] = None
    optional_skills: Optional[str] = None
    task: Optional[str] = None
    id_full: Optional[str] = None
    uri: Optional[str] = None

class Course(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    learning_outcomes: Optional[str] = None
    target_skills: List[str] = []
