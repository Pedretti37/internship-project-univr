from pydantic import BaseModel, EmailStr
from typing import Optional

# Questo modello definisce cosa ci aspettiamo di trovare nel JSON
class User(BaseModel):
    name: str
    surname: str
    username: str
    email: EmailStr
    hashed_password: str
    target_roles: Optional[list[str]] = None

class Organization(BaseModel):
    name: str
    address: str
    phone: str
    email: EmailStr
    orgname: str
    hashed_password: str

class Role(BaseModel):
    id: int
    title: str
    definition: str
    task: str
