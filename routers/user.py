from datetime import datetime
from fastapi import APIRouter, Request, Form, status, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import EmailStr
from typing import Optional
from crud import crud_user
from dependencies import get_current_user

from config import templates, pwd_context
import crud.crud_skill_models as crud_skill_models
from esco import escoAPI
from models import Role, User

USER_ROLES_LIST = {}

EU_COUNTRIES = [
    "Austria", "Belgium", "Bulgaria", "Croatia", "Cyprus", "Czech Republic", 
    "Denmark", "EU-27", "Estonia", "Finland", "France", "Germany", "Greece", 
    "Hungary", "Iceland", "Ireland", "Italy", "Latvia", "Lithuania", 
    "Luxembourg", "Malta", "Netherlands", "Norway", "Poland", "Portugal", 
    "Republic of North Macedonia", "Romania", "Slovakia", "Slovenia", 
    "Spain", "Sweden", "Switzerland", "Turkey"
]

router = APIRouter()

### --- User GET Login --- ###
@router.get("/user_login", response_class=HTMLResponse)
async def user_login(request: Request):
    error_message = request.cookies.get("flash_error")
    response = templates.TemplateResponse("user/user_login.html", {
        "request": request,
        "error": error_message
    })
    if error_message:
        response.delete_cookie("flash_error")
    
    return response

### --- User POST Login --- ###
@router.post("/user_login", response_class=HTMLResponse)
async def user_login(username: str = Form(...), password: str = Form(...)):
    user = crud_user.get_user_by_username(username)

    if not user or not pwd_context.verify(password, user.hashed_password):
        response = RedirectResponse(url="/user_login", status_code=status.HTTP_303_SEE_OTHER)
        
        response.set_cookie(key="flash_error", value="Invalid credentials. Please try again.")
        return response

    response = RedirectResponse(url="/user_home", status_code=status.HTTP_303_SEE_OTHER)

    response.set_cookie(key="session_token", value=user.id, path="/", httponly=True, max_age=1800)  # 30 minutes session
    response.delete_cookie(key="flash_error")

    return response

### --- User Home --- ###
@router.get("/user_home", response_class=HTMLResponse)
async def user_home(request: Request, user = Depends(get_current_user)):

    if not user:
        response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie("session_token", value="", path="/", httponly=True, max_age=0)
        return response

    context_results = None
    context_search = ""

    if user.id in USER_ROLES_LIST:
        session_data = USER_ROLES_LIST[user.id]
        context_results = session_data["results"]
        context_search = session_data["last_search"]

    response = templates.TemplateResponse(
        "user/user_home.html", 
        {"request": request, "user": user, "results": context_results, "last_search": context_search}
    )

    # No cache storage
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.headers["Vary"] = "Cookie"

    return response

### --- User GET Registration --- ###
@router.get("/user_register", response_class=HTMLResponse)
async def register(request: Request):
    return templates.TemplateResponse("user/user_register.html", {"request": request})

### --- User POST Registration --- ###
@router.post("/user_register", response_class=HTMLResponse)
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
        crud_user.create_user(new_user)
        return RedirectResponse(url="/user_login", status_code=status.HTTP_303_SEE_OTHER)
    except ValueError:
        return templates.TemplateResponse("user/user_register.html", {
            "request": request,
            "error": "Username already exists. Please choose another."
        })
    
### --- User Profile --- ###
@router.get("/user_profile", response_class=HTMLResponse)
async def user_profile(request: Request, user = Depends(get_current_user)):
    
    if not user:
        response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie("session_token", value="", path="/", httponly=True, max_age=0)
        return response

    response = templates.TemplateResponse(
        "user/user_profile.html", {
            "request": request, 
            "user": user, 
            "countries_list": EU_COUNTRIES, 
            "emp_data": None,    
            "country": None,     
            "isco_id": None,
            "current_year": datetime.now().year
        }
    )

    # No cache storage
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.headers["Vary"] = "Cookie"

    return response

### --- Obtain roles from User Input --- ###
@router.post("/role_list", response_class=HTMLResponse)
async def role_list(request: Request, search: str = Form(...), user = Depends(get_current_user)):
    role = search.title().strip()

    role_list = escoAPI.get_esco_occupations_list(role, limit=5)
    
    if user:
        USER_ROLES_LIST[user.id] = {
            "last_search": search,
            "results": role_list
        }
        return templates.TemplateResponse("user/user_home.html", {
            "request": request,
            "user": user,
            "results": role_list,
            "last_search": search
        })
    else:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
### --- Set User Target Roles --- ###
@router.post("/add_to_user_target_roles", response_class=HTMLResponse)
async def add_to_user_target_roles(
    request: Request,
    user = Depends(get_current_user),
    role_id: str = Form(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    essential_skills: Optional[str] = Form(None),
    optional_skills: Optional[str] = Form(None),
    id_full: str = Form(...),
    uri: str = Form(...)
):
    if not user:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    role_object = Role(
        id=role_id,
        title=title,
        description=description if description else "No description available.",
        essential_skills=essential_skills if essential_skills else "",
        optional_skills=optional_skills if optional_skills else "",
        id_full=id_full,
        uri=uri
    )

    message_text = "Error: target role not added."
    updated_target_role = False

    already_exists = any(r['id'] == role_id for r in user.target_roles)

    if not already_exists:
        user.target_roles.append(role_object.model_dump())
        updated_target_role = True
        message_text = "Target role added successfully!"
    else:
        updated_target_role = True
        message_text = "This role is already in your target list."

    if updated_target_role:
        crud_user.update_user(user)

    return templates.TemplateResponse("user/details.html", {
        "request": request,
        "user": user,
        "role": role_object,
        "updated_target_role": updated_target_role,
        "message": message_text
    })

### --- Add User Skills --- ###
@router.post("/add_to_user_skills", response_class=HTMLResponse)
async def add_to_user_skills(
    request: Request,
    user = Depends(get_current_user),
    role_id: str = Form(...),
    title: str = Form(...),
    description: str = Form(...),
    essential_skills: str = Form(...),
    optional_skills: str = Form(...),
    id_full: str = Form(...),
    uri: str = Form(...)
):
    if not user:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    role_object = Role(
        id=role_id,
        title=title,
        description=description,
        essential_skills=essential_skills,
        optional_skills=optional_skills,
        id_full=id_full,
        uri=uri
    )

    message_text = "Error: No skills were added."
    updated_skill = False

    if essential_skills:
        skills_list = essential_skills.split('\n') 
        for skill in skills_list:
            skill_clean = skill.strip()
            if skill_clean and len(skill_clean) > 1:
                user.current_skills.append(skill_clean)
                updated_skill = True

    if updated_skill:
        crud_user.update_user(user)
        message_text = "Skills updated successfully!"

    return templates.TemplateResponse("user/details.html", {
        "request": request,
        "user": user,
        "role": role_object,
        "updated_skill": updated_skill,
        "message": message_text
    })

### --- Password Change --- ###
@router.post("/change_password_user", response_class=HTMLResponse)
async def change_password(request: Request, user = Depends(get_current_user), old_pw: str = Form(...), new_pw: str = Form(...)):
    if not user:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    if not pwd_context.verify(old_pw, user.hashed_password):
        error = "Your old password is not correct."
        return templates.TemplateResponse("user/user_profile.html", {
            "request": request,
            "user": user,
            "wrong_pw": error
        })
    
    new_pw_hashed = pwd_context.hash(new_pw)

    success = crud_user.change_password_user(user, new_pw_hashed)

    if success:
        msg = "Password updated successfully!"
        return templates.TemplateResponse("user/user_profile.html", {
            "request": request,
            "user": user,
            "success": msg
        })
    else:
        failed = "Failed to update your password."
        return templates.TemplateResponse("user/user_profile.html", {
            "request": request,
            "user": user,
            "failed": failed
        })
    
### --- Details for a selected Skill Model --- ###
@router.post("/details", response_class=HTMLResponse)
async def details_page(
    request: Request, 
    role_id: str = Form(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    essential_skills: Optional[str] = Form(None),
    optional_skills: Optional[str] = Form(None),
    id_full: str = Form(...),
    uri: str = Form(...),
    user = Depends(get_current_user)):

    if not user:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    role_object = Role(
        id=role_id,
        title=title,
        description=description if description else "No description available.",
        essential_skills=essential_skills if essential_skills else "",
        optional_skills=optional_skills if optional_skills else "",
        id_full=id_full,
        uri=uri
    )

    return templates.TemplateResponse("user/details.html", {
        "request": request,
        "user": user,
        "role": role_object
    })
    
### --- Delete Target Role from User --- ###    
@router.post("/delete_target_role", response_class=RedirectResponse)
async def delete_target_role(
    user = Depends(get_current_user),
    role_id: str = Form(...)
):
    if not user:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    new_target_list = [
        role for role in user.target_roles 
        if role.get('id') != role_id
    ]
    
    user.target_roles = new_target_list

    crud_user.update_user(user)

    return RedirectResponse(url="/user_profile", status_code=status.HTTP_303_SEE_OTHER)

### --- Calculating Skill Gap --- ###
@router.post("/calculate_skill_gap", response_class=HTMLResponse)
async def calculate_skill_gap(request: Request, user = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    if len(user.target_roles) > 5:
        error = "You can analyze up to 5 target roles at a time."
        return templates.TemplateResponse("user/user_profile.html", {
            "request": request,
            "user": user,
            "error": error
        })

    updated_user = crud_skill_models.skill_gap_user(user)
    crud_user.update_user(updated_user)

    return templates.TemplateResponse("user/user_profile.html", {
        "request": request,
        "user": updated_user,
        "countries_list": EU_COUNTRIES, 
        "emp_data": None,
        "country": None
    })

### --- Read CEDEFOP Employment Data --- ###
@router.post("/read_emp_occupation", response_class=HTMLResponse)
async def read_emp_occupation(
    request: Request,
    user = Depends(get_current_user),
    country: str = Form(...),
    isco_id: str = Form(...),
):
    if not user:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    emp_data = crud_skill_models.read_emp_occupation(country=country, isco_id=isco_id)

    return templates.TemplateResponse("user/user_profile.html", {
        "request": request,
        "user": user,
        "emp_data": emp_data,
        "country": country,
        "countries_list": EU_COUNTRIES,
        "isco_id": isco_id,
        "current_year": datetime.now().year
    })
