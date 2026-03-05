import ast
from datetime import datetime
from fastapi import APIRouter, Request, Form, status, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import EmailStr
from typing import Optional
from crud import crud_user, crud_org
from dependencies import get_current_user

from config import templates, pwd_context
import crud.crud_skill_models as crud_skill_models
from esco import escoAPI
from models import Role, Skill, User

USER_ROLES_LIST = {}
USER_COURSES_LIST = {}
USER_FORECAST_RESULTS = {}

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

    response.set_cookie(key="session_token", value=user.username, path="/", httponly=True, max_age=1800)  # 30 minutes session
    response.delete_cookie(key="flash_error")

    return response

### --- Logout --- ###
@router.get("/user_logout")
async def logout(user: User = Depends(get_current_user)):
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    # Delete current session
    response.set_cookie(key="session_token", value="", path="/", httponly=True, max_age=0)

    if user.username in USER_ROLES_LIST:
        del USER_ROLES_LIST[user.username]
    if user.username in USER_COURSES_LIST:
        del USER_COURSES_LIST[user.username]
    if user.username in USER_FORECAST_RESULTS:
        del USER_FORECAST_RESULTS[user.username]
    return response

### --- User Home --- ###
@router.get("/user_home", response_class=HTMLResponse)
async def user_home(request: Request, user: User = Depends(get_current_user)):

    if not user:
        response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie("session_token", value="", path="/", httponly=True, max_age=0)
        return response

    context_results = None
    context_search = ""

    if user.username in USER_ROLES_LIST:
        session_data = USER_ROLES_LIST[user.username]
        context_results = session_data["results"]
        context_search = session_data["last_search"]

    response = templates.TemplateResponse("user/user_home.html", {
        "request": request, 
        "user": user, 
        "results": context_results, 
        "last_search": context_search
    })

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
async def user_profile(request: Request, user: User = Depends(get_current_user)):
    
    if not user:
        response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie("session_token", value="", path="/", httponly=True, max_age=0)
        return response

    invitations = crud_user.get_pending_invitations_for_user(user.username)
        
    if user.username in USER_COURSES_LIST:
        session_data = USER_COURSES_LIST[user.username]
        recommended_courses = session_data["results"]
    else:
        recommended_courses = None

    if user.username in USER_FORECAST_RESULTS:
        session_data = USER_FORECAST_RESULTS[user.username]
        forecast_results = session_data["results"]
        country = session_data["country"]
    else:
        forecast_results = None
        country = None

    response = templates.TemplateResponse(
        "user/user_profile.html", {
            "request": request, 
            "user": user, 
            "countries_list": EU_COUNTRIES,
            "invitations": invitations,
            "recommended_courses": recommended_courses,
            "forecast_results": forecast_results,
            "country": country,
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
async def role_list(request: Request, search: str = Form(...), user: User = Depends(get_current_user)):
    role = search.title().strip()

    language = "en"
    role_list = escoAPI.get_esco_occupations_list(role, language=language, limit=10)
    
    if user:
        USER_ROLES_LIST[user.username] = {
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
    user: User = Depends(get_current_user),
    role_id: str = Form(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    essential_skills: Optional[str] = Form(None),
    id_full: str = Form(...),
    uri: str = Form(...)
):
    if not user:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    form_data = await request.form()

    skills_list = []

    # Manual conversion from string to list[Skill]
    if essential_skills:
        try:
            skills_list = ast.literal_eval(essential_skills)
            
            # Check
            if isinstance(skills_list, list):
                skills_list = skills_list
            else:
                print(f"Parsed_data not a valid list. Found type: {type(skills_list)}")
                skills_list = []

        except (ValueError, SyntaxError) as e:
            print(f"Error parsing essential_skills: {essential_skills} - Error: {e}")
            skills_list = []
    else:
        skills_list = []


    final_skills_list = []

    for skill_dict in skills_list:
        skill_uri = skill_dict.get("uri")
        
        selected_level = form_data.get(f"level_{skill_uri}")
        
        if selected_level:
            skill_dict["level"] = int(selected_level)
        else:
            skill_dict["level"] = 5  # Default level if not selected, can be adjusted as needed
            
        final_skills_list.append(Skill(**skill_dict))

    role_object = Role(
        id=role_id,
        title=title,
        description=description if description else "No description available.",
        essential_skills=final_skills_list,
        id_full=id_full,
        uri=uri
    )

    updated_target_role = False
    already_exists = any(r.id == role_id for r in user.target_roles)


    if not already_exists:
        user.target_roles.append(role_object)
        updated_target_role = True
        message_text = "Target role added successfully!"
    else:
        updated_target_role = True
        message_text = "This role is already in your target list."

    if updated_target_role:
        crud_user.update_user(user)

    return templates.TemplateResponse("details.html", {
        "request": request,
        "user": user,
        "role": role_object,
        "updated_target_role": updated_target_role,
        "message": message_text,
        "is_user": True
    })

### --- Add User Skills --- ###
@router.post("/add_to_user_skills", response_class=HTMLResponse)
async def add_to_user_skills(
    request: Request,
    user: User = Depends(get_current_user),
    role_id: str = Form(...),
    title: str = Form(...),
    description: str = Form(...),
    essential_skills: str = Form(...),
    id_full: str = Form(...),
    uri: str = Form(...)
):
    if not user:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    form_data = await request.form()

    skills_list = []

    # Manual conversion from string to list[Skill]
    try:
        skills_list = ast.literal_eval(essential_skills)
        # Check
        if isinstance(skills_list, list):
            skills_list = skills_list
        else:
            print(f"Parsed_data not a valid list. Found type: {type(skills_list)}")
            skills_list = []
    except (ValueError, SyntaxError):
        skills_list = []

    updated_skill = False
    existing_uris = {s.uri for s in user.current_skills}

    for skill_dict in skills_list:
        skill_uri = skill_dict.get("uri")
        
        selected_level = form_data.get(f"level_{skill_uri}")
        
        if selected_level and skill_uri not in existing_uris:
            skill_dict["level"] = int(selected_level)
            
            user.current_skills.append(Skill(**skill_dict))
            existing_uris.add(skill_uri)
            updated_skill = True

    if updated_skill:
        crud_user.update_user(user)
        message_text = "Role skills added to your profile!"
    else:
        message_text = "No new skills were added. They might already be in your profile or no level was selected."

    return templates.TemplateResponse("details.html", {
        "request": request,
        "user": user,
        "role": Role(
            id=role_id,
            title=title,
            description=description if description else "No description available.",
            essential_skills=skills_list,
            id_full=id_full,
            uri=uri
        ),
        "updated_skill": updated_skill,
        "message": message_text,
        "is_user": True
    })

### --- Password Change --- ###
@router.post("/change_password_user", response_class=HTMLResponse)
async def change_password(
    request: Request, 
    user: User = Depends(get_current_user), 
    old_pw: str = Form(...), 
    new_pw: str = Form(...)
):

    if not user:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    if not pwd_context.verify(old_pw, user.hashed_password):
        error = "Your old password is not correct."
        return templates.TemplateResponse("user/user_profile.html", {
            "request": request,
            "user": user,
            "wrong_pw": error,
            "countries_list": EU_COUNTRIES
        })
    
    new_pw_hashed = pwd_context.hash(new_pw)

    success = crud_user.change_password_user(user, new_pw_hashed)

    if success:
        msg = "Password updated successfully!"
        return templates.TemplateResponse("user/user_profile.html", {
            "request": request,
            "user": user,
            "success": msg,
            "countries_list": EU_COUNTRIES
        })
    else:
        failed = "Failed to update your password."
        return templates.TemplateResponse("user/user_profile.html", {
            "request": request,
            "user": user,
            "failed": failed,
            "countries_list": EU_COUNTRIES,
        })
    
### --- Details for a selected Skill Model --- ###
@router.post("/details", response_class=HTMLResponse)
async def details_page(
    request: Request, 
    role_id: str = Form(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    essential_skills: Optional[str] = Form(None),
    id_full: str = Form(...),
    uri: str = Form(...),
    user: User = Depends(get_current_user)):

    if not user:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    e_skills_list = []

    # Manual conversion from string to list[Skill]
    if essential_skills:
        try:
            parsed_data = ast.literal_eval(essential_skills)
            
            # Check
            if isinstance(parsed_data, list):
                e_skills_list = parsed_data
            else:
                print(f"Parsed_data not a valid list. Found type: {type(parsed_data)}")
                e_skills_list = []

        except (ValueError, SyntaxError) as e:
            print(f"Error parsing essential_skills: {essential_skills} - Error: {e}")
            e_skills_list = []
    else:
        e_skills_list = []

    role_object = Role(
        id=role_id,
        title=title,
        description=description if description else "No description available.",
        essential_skills=e_skills_list,
        id_full=id_full,
        uri=uri
    )

    return templates.TemplateResponse("details.html", {
        "request": request,
        "user": user,
        "is_user": True,
        "role": role_object
    })
    
### --- Delete Target Role from User --- ###    
@router.post("/delete_target_role", response_class=RedirectResponse)
async def delete_target_role(
    user: User = Depends(get_current_user),
    role_id: str = Form(...)
):
    if not user:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    # new list excluding the role to be deleted
    new_target_list = [
        role for role in user.target_roles 
        if role.id != role_id
    ]
    
    user.target_roles = new_target_list

    crud_user.update_user(user)

    return RedirectResponse(url="/user_profile", status_code=status.HTTP_303_SEE_OTHER)

### --- Delete Skill from User --- ###
@router.post("/delete_user_skill", response_class=RedirectResponse)
async def delete_user_skill(
    user: User = Depends(get_current_user),
    skill_uri: str = Form(...)
):
    if not user:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    # new list excluding the skill to be deleted
    new_skills_list = [
        skill for skill in user.current_skills 
        if skill.uri != skill_uri
    ]
    
    user.current_skills = new_skills_list

    crud_user.update_user(user)

    return RedirectResponse(url="/user_profile", status_code=status.HTTP_303_SEE_OTHER)

### --- Occupation Forecast and Gap --- ###
@router.post("/occupation_forecast_and_gap", response_class=HTMLResponse)
async def occupation_forecast_and_gap(
    request: Request,
    user: User = Depends(get_current_user),
    country: str = Form(...),
):
    if not user:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    if len(user.target_roles) > 5:
        error = "You can analyze up to 5 target roles at a time."
        return templates.TemplateResponse("user/user_profile.html", {
            "request": request,
            "user": user,
            "error": error,
            "countries_list": EU_COUNTRIES
        })

    forecast_results = []
    role_list = []
    for role in user.target_roles:
        # String conversion and cleanup
        role_id_str = str(role.id).strip()
            
        # CEDEFOP
        data = crud_skill_models.read_emp_occupation(country=country, isco_id=role_id_str)
        
        forecast_results.append({
            "title": role.title,  
            "isco_code": role_id_str,
            "uri": role.uri,
            "data": data              
        })

        if data['growth_pct'] >= -5:
            role_list.append(role)
    
    updated_user = crud_skill_models.skill_gap_user(user, role_list)
    crud_user.update_user(updated_user)

    USER_FORECAST_RESULTS[updated_user.username] = {
        "country": country,
        "results": forecast_results
    }

    # Course recommendation
    missing_skills = {}
    for role in updated_user.skill_gap:
        if 0 <= role["match_score"] < 100:
            for result in forecast_results:
                data = result["data"]
                if data["growth_pct"] >= -5:
                    # Role is expected to grow or remain stable --> provide educational courses and training opportunities
                    for skill_uri, skill_name in role["missing_skills"].items():
                        missing_skills[skill_uri] = skill_name

    # print(len(missing_skills))

    # List of recommended courses for the missing skills
    # Role type will be a factor in course recommendation, for now we will consider just the missing skills, 
    # assuming "Mechanical Engineer" and similar role as default role type
    recommended_courses = crud_skill_models.recommend_courses_for_skill_gap(missing_skills)

    USER_COURSES_LIST[updated_user.username] = {
        "results": recommended_courses
    }

    return templates.TemplateResponse("user/user_profile.html", {
        "request": request,
        "user": updated_user,
        "forecast_results": forecast_results, 
        "recommended_courses": recommended_courses,
        "country": country,
        "countries_list": EU_COUNTRIES,
        "current_year": datetime.now().year
    })

### --- Accept Invitation --- ###
@router.post("/accept_invitation", response_class=RedirectResponse)
async def accept_invitation(
    user: User = Depends(get_current_user),
    orgname: str = Form(...),
    inv_id: str = Form(...)
):
    if not user:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    user.organization = orgname
    crud_user.update_user(user)

    org = crud_org.get_org_by_orgname(orgname)
    if org:
        org.members.append(user.username)
        crud_org.update_org(org)

    inv = crud_org.get_inv_by_id(inv_id)
    if inv:
        inv.status = "accepted"
        crud_org.update_invitation(inv)

    return RedirectResponse(url="/user_profile", status_code=status.HTTP_303_SEE_OTHER)

### --- Decline Invitation --- ###
@router.post("/decline_invitation", response_class=RedirectResponse)
async def decline_invitation(
    user: User = Depends(get_current_user),
    inv_id: str = Form(...)
):
    if not user:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    inv = crud_org.get_inv_by_id(inv_id)
    if inv:
        inv.status = "declined"
        crud_org.update_invitation(inv)

    return RedirectResponse(url="/user_profile", status_code=status.HTTP_303_SEE_OTHER)




