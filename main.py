from fastapi import FastAPI, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from passlib.context import CryptContext
from pydantic import EmailStr
from typing import Optional

import crud
from models import User, Organization

app = FastAPI()

# Monta la cartella "static" per servire CSS e immagini
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configura la cartella dei template
templates = Jinja2Templates(directory="templates")

# Sicurezza password
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

### --- Root --- ###
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

### --- User Login --- ###
@app.get("/user_login", response_class=HTMLResponse)
async def user_login(request: Request):
    error_message = request.cookies.get("flash_error")
    response = templates.TemplateResponse("user/user_login.html", {
        "request": request,
        "error": error_message
    })
    if error_message:
        response.delete_cookie("flash_error")
    
    return response

@app.post("/user_login", response_class=HTMLResponse)
async def user_login(request: Request, username: str = Form(...), password: str = Form(...)):
    user = crud.get_user(username)

    if not user or not pwd_context.verify(password, user.hashed_password):
        response = RedirectResponse(url="/user_login", status_code=status.HTTP_303_SEE_OTHER)
        
        response.set_cookie(key="flash_error", value="Invalid credentials. Please try again.")
        return response

    response = RedirectResponse(url="/user_home", status_code=status.HTTP_303_SEE_OTHER)

    response.set_cookie(key="session_token", value=user.username, path="/", httponly=True, max_age=1800)  # 30 minutes session
    response.delete_cookie(key="flash_error")

    return response

### --- User Home --- ###
@app.get("/user_home", response_class=HTMLResponse)
async def user_home(request: Request):
    token = request.cookies.get("session_token")
    
    if not token:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    current_user = crud.get_user(token)

    if not current_user:
        response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie("session_token", value="", path="/", httponly=True, max_age=0)
        return response

    response = templates.TemplateResponse(
        "user/user_home.html", 
        {"request": request, "user": current_user}
    )

    # No cache storage
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.headers["Vary"] = "Cookie"

    return response

### --- Organization Login --- ###
@app.get("/org_login", response_class=HTMLResponse)
async def org_login(request: Request):
    error_message = request.cookies.get("flash_error")
    response = templates.TemplateResponse("org/org_login.html", {
        "request": request,
        "error": error_message
    })
    if error_message:
        response.delete_cookie("flash_error")
    
    return response

@app.post("/org_login", response_class=HTMLResponse)
async def org_login(request: Request, username: str = Form(...), password: str = Form(...)):
    org = crud.get_organization(username)

    if not org or not pwd_context.verify(password, org.hashed_password):
        response = RedirectResponse(url="/org_login", status_code=status.HTTP_303_SEE_OTHER)
        
        response.set_cookie(key="flash_error", value="Invalid credentials. Please try again.")
        return response

    response = RedirectResponse(url="/org_home", status_code=status.HTTP_303_SEE_OTHER)

    response.set_cookie(key="session_token", value=org.username, path="/", httponly=True, max_age=1800)  # 30 minutes session
    response.delete_cookie(key="flash_error")

    return response

### --- Organization Home --- ###
@app.get("/org_home", response_class=HTMLResponse)
async def org_home(request: Request):
    token = request.cookies.get("session_token")
    
    if not token:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    current_org = crud.get_organization(token)

    if not current_org:
        response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie("session_token", value="", path="/", httponly=True, max_age=0)
        return response

    response = templates.TemplateResponse(
        "org/org_home.html", 
        {"request": request, "org": current_org}
    )

    # No cache storage
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.headers["Vary"] = "Cookie"

    return response

### --- Guest Home --- ###
@app.get("/guest_home", response_class=HTMLResponse)
async def gust_home(request: Request):
    return templates.TemplateResponse("guest_home.html", {"request": request})

### --- User Registration --- ###
@app.get("/user_register", response_class=HTMLResponse)
async def register(request: Request):
    return templates.TemplateResponse("user/user_register.html", {"request": request})

@app.post("/user_register", response_class=HTMLResponse)
async def register_user(
    request: Request, 
    name: str = Form(...),
    surname: str = Form(...),
    email: EmailStr = Form(...), 
    username: str = Form(...), 
    password: str = Form(...)
):
    hashed_pw = pwd_context.hash(password)
    new_user = User(name=name, surname=surname, email=email, username=username, hashed_password=hashed_pw)
    try:
        crud.create_user(new_user)
        return RedirectResponse(url="/user_login", status_code=status.HTTP_303_SEE_OTHER)
    except ValueError:
        return templates.TemplateResponse("user/user_register.html", {
            "request": request,
            "error": "Username already exists. Please choose another."
        })
    
### --- Organization Registration --- ###
@app.get("/org_register", response_class=HTMLResponse)
async def org_register(request: Request):
    return templates.TemplateResponse("org/org_register.html", {"request": request})

@app.post("/org_register", response_class=HTMLResponse)
async def register_org(
    request: Request, 
    name: str = Form(...),
    address: str = Form(...),
    phone: str = Form(...),
    email: EmailStr = Form(...), 
    username: str = Form(...),
    password: str = Form(...)
):
    hashed_pw = pwd_context.hash(password)
    new_org = Organization(name=name, address=address, phone=phone, email=email, username=username, hashed_password=hashed_pw)
    try:
        crud.create_organization(new_org)
        return RedirectResponse(url="/org_login", status_code=status.HTTP_303_SEE_OTHER)
    except ValueError:
        return templates.TemplateResponse("org/org_register.html", {
            "request": request,
            "error": "Organization already exists. Please choose another."
        })

### --- Logout --- ###
@app.get("/logout")
async def logout(request: Request):
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    # Delete current session
    response.set_cookie(key="session_token", value="", path="/", httponly=True, max_age=0)
    return response

### --- Obtain skills from User Input --- ###
@app.post("/extract_skill_models", response_class=HTMLResponse)
async def extract_skill_models(request: Request, search: str = Form(...)):
    role = search.title().strip()

    extracted_models = {}

    skill_models_list = crud.extracting_skill_models(role)
    if skill_models_list:
        extracted_models[role] = skill_models_list
    
    user = crud.get_user(request.cookies.get("session_token"))

    return templates.TemplateResponse("user/user_home.html", {
        "request": request,
        "user": user,
        "results": extracted_models,
        "last_search": search
    })

### --- Set Target Roles --- ###
@app.post("/set_target_roles", response_class=HTMLResponse)
async def set_target_roles(
    request: Request, 
    role1: str = Form(...),
    role2: Optional[str] = Form(None),
    role3: Optional[str] = Form(None),
    role4: Optional[str] = Form(None),
    role5: Optional[str] = Form(None)
):
    roles = [role1, role2, role3, role4, role5]
    target_roles = [role.title().strip() for role in roles if role and role.strip() != ""]


    user = crud.get_user(request.cookies.get("session_token"))
    crud.set_target_roles_user(user, target_roles)
    
    return templates.TemplateResponse("user/user_profile.html", {
        "request": request,
        "user": user,
    })

### --- User Profile --- ###
@app.get("/user_profile", response_class=HTMLResponse)
async def user_profile(request: Request):
    token = request.cookies.get("session_token")
    
    if not token:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    current_user = crud.get_user(token)

    if not current_user:
        response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie("session_token", value="", path="/", httponly=True, max_age=0)
        return response

    response = templates.TemplateResponse(
        "user/user_profile.html", 
        {"request": request, "user": current_user}
    )

    # No cache storage
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.headers["Vary"] = "Cookie"

    return response