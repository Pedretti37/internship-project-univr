from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, List, Any

# Questo modello definisce cosa ci aspettiamo di trovare nel JSON
class User(BaseModel):
    name: str
    surname: str
    username: str
    email: EmailStr
    hashed_password: str
    target_roles: Optional[Dict[str, str]] = None
    current_skills: Optional[Dict[str, int]] = None
    skill_gap: Optional[Dict[str, List[Any]]] = None

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
