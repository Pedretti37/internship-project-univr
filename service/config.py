from fastapi.templating import Jinja2Templates
from passlib.context import CryptContext

# Setting dir for templates
templates = Jinja2Templates(directory="templates")

# password managing
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")