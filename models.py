from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, List, Any

# Questo modello definisce cosa ci aspettiamo di trovare nel JSON
class User(BaseModel):
    name: str
    surname: str
    username: str
    email: EmailStr
    hashed_password: str
    target_roles: List[Dict[str, Any]] = []
    current_skills: Dict[str, int] = {}
    skill_gap: Dict[str, List[Any]] = {}

class Organization(BaseModel):
    name: str
    address: str
    phone: str
    email: EmailStr
    orgname: str
    hashed_password: str

class Role(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    task: Optional[str] = None
    id_full: Optional[str] = None
    uri: Optional[str] = None

class Course(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    learning_outcomes: Optional[str] = None
    target_skills: List[str] = []
