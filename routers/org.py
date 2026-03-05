import codecs
import csv

from fastapi import APIRouter, File, Query, Request, Form, UploadFile, status, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import EmailStr
from typing import Optional

import urllib
from crud import crud_skill_models, crud_user
from dependencies import get_current_org
from esco import escoAPI 
import ast
from datetime import datetime
from time import sleep
from config import templates, pwd_context
import crud.crud_org as crud_org
from models import Organization, Project, Role, Skill

router = APIRouter()

PROJECT_ROLES_LIST = {}
PROJECT_COURSES_LIST = {}
PROJECT_FORECAST_RESULTS = {}

EU_COUNTRIES = [
    "Austria", "Belgium", "Bulgaria", "Croatia", "Cyprus", "Czech Republic", 
    "Denmark", "EU-27", "Estonia", "Finland", "France", "Germany", "Greece", 
    "Hungary", "Iceland", "Ireland", "Italy", "Latvia", "Lithuania", 
    "Luxembourg", "Malta", "Netherlands", "Norway", "Poland", "Portugal", 
    "Republic of North Macedonia", "Romania", "Slovakia", "Slovenia", 
    "Spain", "Sweden", "Switzerland", "Turkey"
]

### --- Organization Login GET --- ###
@router.get("/org_login", response_class=HTMLResponse)
async def org_login(request: Request):
    error_message = request.cookies.get("flash_error")
    response = templates.TemplateResponse("org/org_login.html", {
        "request": request,
        "error": error_message
    })
    if error_message:
        response.delete_cookie("flash_error")
    
    return response

### --- Organization Login POST --- ###
@router.post("/org_login", response_class=HTMLResponse)
async def org_login(orgname: str = Form(...), password: str = Form(...)):
    org = crud_org.get_org_by_orgname(orgname)

    if not org or not pwd_context.verify(password, org.hashed_password):
        response = RedirectResponse(url="/org_login", status_code=status.HTTP_303_SEE_OTHER)
        
        response.set_cookie(key="flash_error", value="Invalid credentials. Please try again.")
        return response

    response = RedirectResponse(url="/org_home", status_code=status.HTTP_303_SEE_OTHER)

    response.set_cookie(key="session_token", value=org.orgname, path="/", httponly=True, max_age=1800)  # 30 minutes session
    response.delete_cookie(key="flash_error")

    return response

### --- Logout --- ###
@router.get("/org_logout")
async def logout(org: Organization = Depends(get_current_org)):
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    # Delete current session
    response.set_cookie(key="session_token", value="", path="/", httponly=True, max_age=0)

    for project in org.projects:
        if project.id in PROJECT_ROLES_LIST:
            del PROJECT_ROLES_LIST[project.id]
        if project.id in PROJECT_COURSES_LIST:
            del PROJECT_COURSES_LIST[project.id]
        if project.id in PROJECT_FORECAST_RESULTS:
            del PROJECT_FORECAST_RESULTS[project.id]
    return response

### --- Organization Home --- ###
@router.get("/org_home", response_class=HTMLResponse)
async def org_home(request: Request, org: Organization = Depends(get_current_org)):

    if not org:
        response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie("session_token", value="", path="/", httponly=True, max_age=0)
        return response
    
    # Member list
    members = crud_user.get_users_by_usernames(org.members)

    response = templates.TemplateResponse("org/org_home.html", {
        "request": request, 
        "org": org,
        "members": members,
        "projects": org.projects
    })

    # No cache storage headers
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.headers["Vary"] = "Cookie"

    return response

### --- Organization Registration GET --- ###
@router.get("/org_register", response_class=HTMLResponse)
async def org_register(request: Request):
    return templates.TemplateResponse("org/org_register.html", {"request": request})

### --- Organization Registration POST --- ###
@router.post("/org_register", response_class=HTMLResponse)
async def register_org(
    request: Request, 
    name: str = Form(...),
    address: str = Form(...),
    phone: str = Form(...),
    email: EmailStr = Form(...), 
    orgname: str = Form(...),
    password: str = Form(...)
):
    hashed_pw = pwd_context.hash(password)
    new_org = Organization(name=name, address=address, phone=phone, email=email, orgname=orgname, hashed_password=hashed_pw)
    try:
        crud_org.create_organization(new_org)
        return RedirectResponse(url="/org_login", status_code=status.HTTP_303_SEE_OTHER)
    except ValueError:
        return templates.TemplateResponse("org/org_register.html", {
            "request": request,
            "error": "Organization already exists. Please choose another."
        })
    
### --- Organization Profile --- ###
@router.get("/org_profile", response_class=HTMLResponse)
async def org_profile(request: Request, org: Organization = Depends(get_current_org)):
    if not org:
        response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie("session_token", value="", path="/", httponly=True, max_age=0)
        return response

    response = templates.TemplateResponse("org/org_profile.html", {
        "request": request, 
        "org": org,
        "members": crud_user.get_users_by_usernames(org.members)
    })

    # No cache storage
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.headers["Vary"] = "Cookie"

    return response

### --- Password Change --- ###
@router.post("/change_password_org", response_class=HTMLResponse)
async def change_password(request: Request, org: Organization = Depends(get_current_org), old_pw: str = Form(...), new_pw: str = Form(...)):
    if not org:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    if not pwd_context.verify(old_pw, org.hashed_password):
        error = "Your old password is not correct."
        return templates.TemplateResponse("org/org_profile.html", {
            "request": request,
            "org": org,
            "wrong_pw": error,
            "countries_list": EU_COUNTRIES
        })
    
    new_pw_hashed = pwd_context.hash(new_pw)

    success = crud_org.change_password_org(org, new_pw_hashed)

    if success:
        msg = "Password updated successfully!"
        return templates.TemplateResponse("org/org_profile.html", {
            "request": request,
            "org": org,
            "success": msg,
            "countries_list": EU_COUNTRIES
        })
    else:
        failed = "Failed to update your password."
        return templates.TemplateResponse("org/org_profile.html", {
            "request": request,
            "org": org,
            "failed": failed,
            "countries_list": EU_COUNTRIES
        })
    
### --- Invite Member --- ###
@router.post("/invite_member", response_class=HTMLResponse)
async def invite_member(
    request: Request, 
    org: Organization = Depends(get_current_org), 
    username_to_invite: str = Form(...)
):
    if not org:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    error_msg = None
    success_msg = None

    members = org.members
    invited = False
    user_to_invite = crud_user.get_user_by_username(username_to_invite)

    if not user_to_invite:
        error_msg = "User not found."
    elif user_to_invite.username in members:
        error_msg = "This user is already in your team."
    else:
        invited = crud_org.create_invitation(org.orgname, user_to_invite.username)
        if invited:
            success_msg = f"Invitation sent to '{username_to_invite}' successfully!"
        else:
            error_msg = "Failed to send invitation. Please try again."

    return templates.TemplateResponse("org/org_profile.html", {
        "request": request,
        "org": org,
        "members": crud_user.get_users_by_usernames(org.members),
        "invite_error": error_msg,
        "invite_success": success_msg
    })

### --- Create Project GET --- ###
@router.get("/org/create_project", response_class=HTMLResponse)
async def create_project_form(request: Request, org: Organization = Depends(get_current_org)):
    if not org:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    # member list for assignment with checkboxes
    members = crud_user.get_users_by_usernames(org.members)

    return templates.TemplateResponse("org/create_project.html", {
        "request": request,
        "org": org,
        "members": members
    })

### --- Create Project POST --- ###
@router.post("/org/create_project", response_class=HTMLResponse)
async def create_project_submit(
    request: Request,
    org: Organization = Depends(get_current_org),
    name: str = Form(...),
    description: str = Form(...),
    assigned_members: list[str] = Form(default=[]), 
    file: UploadFile = File(None)
):
    if not org:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    final_assigned_members = set(assigned_members)

    if file and file.filename and file.filename.endswith('.csv'):
        csvReader = csv.DictReader(codecs.iterdecode(file.file, 'utf-8'))
        extracted_skills = {}
        
        for row in csvReader:
            username = row.get("Username")
            skill_name = row.get("Skill_Name")
            level_str = row.get("Proficiency_Level")
            
            if not username or not skill_name:
                continue
                
            try:
                level = int(level_str)
            except ValueError:
                level = 1

            skill_uri = escoAPI.get_esco_skill_uri_by_name(skill_name, language="en")
            
            if not skill_uri:
                print(f"⚠️ Skill ignorata: ESCO non ha trovato '{skill_name}'")
                continue 
                
            sleep(0.05) # Rate limiting
            
            if username not in extracted_skills:
                extracted_skills[username] = []
                
            extracted_skills[username].append({
                "name": skill_name,
                "uri": skill_uri, 
                "level": level
            })

        for username, skills in extracted_skills.items():
            user = crud_user.get_user_by_username(username)

            if user:
                if username in org.members:
                    validated_skills = [Skill(**skill_dict) for skill_dict in skills]
                    user.current_skills = validated_skills
                    crud_user.update_user(user) 
                    
                    final_assigned_members.add(username)
                
                else:
                    crud_org.create_invitation(org.orgname, username)
                    print(f"📩 Inviata richiesta di iscrizione all'utente '{username}'.")
                    
            else:
                print(f"⚠️ Utente {username} dal CSV non trovato nel database.")

    new_project = Project(
        name=name,
        description=description,
        assigned_members=list(final_assigned_members),
        target_roles=[], 
        skill_gap=[]
    )

    org.projects.append(new_project)
    crud_org.update_org(org)

    return RedirectResponse(url="/org_home", status_code=status.HTTP_303_SEE_OTHER)

### --- View Project GET --- ###
@router.get("/org/project/{project_id}", response_class=HTMLResponse)
async def view_project(
    request: Request, 
    project_id: str, 
    org: Organization = Depends(get_current_org),
    error: str = Query(None), 
    success: str = Query(None)
):
    if not org:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    current_project: Optional[Project] = next((p for p in org.projects if str(p.id) == project_id), None)

    if not current_project:
        return RedirectResponse(url="/org_home", status_code=status.HTTP_303_SEE_OTHER)

    team = crud_user.get_users_by_usernames(current_project.assigned_members)

    context_results = None
    context_search = ""

    if current_project.id in PROJECT_ROLES_LIST:
        session_data = PROJECT_ROLES_LIST[current_project.id]
        context_results = session_data["results"]
        context_search = session_data["last_search"]

    if current_project.id in PROJECT_COURSES_LIST:
        session_data = PROJECT_COURSES_LIST[current_project.id]
        recommended_courses = session_data["results"]
    else:
        recommended_courses = None

    if current_project.id in PROJECT_FORECAST_RESULTS:
        session_data = PROJECT_FORECAST_RESULTS[current_project.id]
        forecast_results = session_data["results"]
        country = session_data["country"]
    else:
        forecast_results = None
        country = None

    return templates.TemplateResponse("org/project_detail.html", {
        "request": request,
        "org": org,
        "current_project": current_project,
        "results": context_results,
        "last_search": context_search,
        "team": team,
        "countries_list": EU_COUNTRIES,
        "recommended_courses": recommended_courses,
        "forecast_results": forecast_results,
        "country": country,
        "member_error": error,    
        "member_success": success
    })

### --- Project Search Role --- ###
@router.post("/org/project/{project_id}/search", response_class=HTMLResponse)
async def project_search_role(
    request: Request, 
    project_id: str, 
    search: str = Form(...),
    org: Organization = Depends(get_current_org)
):
    if not org:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    current_project: Optional[Project] = next((p for p in org.projects if str(p.id) == project_id), None)
    
    if not current_project:
            return RedirectResponse(url="/org_home", status_code=status.HTTP_303_SEE_OTHER)
    
    role = search.title().strip()
    language = "en"
    role_list = escoAPI.get_esco_occupations_list(role, language=language, limit=10)

    team = crud_user.get_users_by_usernames(current_project.assigned_members)

    PROJECT_ROLES_LIST[current_project.id] = {
        "last_search": search,
        "results": role_list
    }
    return templates.TemplateResponse("org/project_detail.html", {
        "request": request,
        "org": org,
        "current_project": current_project,
        "results": role_list,
        "last_search": search,
        "team": team
    })
    
### --- Role details for Org. projects --- ###
@router.post("/role_details_for_project", response_class=HTMLResponse)
async def details_page(
    request: Request, 
    role_id: str = Form(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    essential_skills: Optional[str] = Form(None),
    id_full: str = Form(...),
    uri: str = Form(...),
    project_id: str = Form(...),
    org: Organization = Depends(get_current_org)):

    if not org:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    # Manual conversion from string to dict
    if essential_skills:
        try:
            # ast.literal_eval manages {'key': 'value'}
            e_skills_dict = ast.literal_eval(essential_skills)
            
            # Controllo extra: assicuriamoci che sia davvero un dict
            if not isinstance(e_skills_dict, dict):
                e_skills_dict = {}
        except (ValueError, SyntaxError):
            print(f"Errore nel parsing di essential_skills: {essential_skills}")
            e_skills_dict = {}
    else:
        e_skills_dict = {}
    
    role_object = Role(
        id=role_id,
        title=title,
        description=description if description else "No description available.",
        essential_skills=e_skills_dict,
        id_full=id_full,
        uri=uri
    )

    return templates.TemplateResponse("details.html", {
        "request": request,
        "org": org,
        "is_user": False,
        "role": role_object,
        "project_id": project_id,
        "updated_target_role": False
    })

### --- Project Add Role POST --- ###
@router.post("/add_to_project_target_roles", response_class=HTMLResponse) 
async def project_add_role(
    request: Request,
    project_id: str = Form(...),
    role_id: str = Form(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    essential_skills: Optional[str] = Form(None),
    id_full: str = Form(...),
    uri: str = Form(...),
    org: Organization = Depends(get_current_org)
):
    if not org: return RedirectResponse(url="/", status_code=303)

    # Manual conversion from string to dict
    if essential_skills:
        try:
            # ast.literal_eval manages {'key': 'value'}
            e_skills_dict = ast.literal_eval(essential_skills)
            
            # Controllo extra: assicuriamoci che sia davvero un dict
            if not isinstance(e_skills_dict, dict):
                e_skills_dict = {}
        except (ValueError, SyntaxError):
            print(f"Errore nel parsing di essential_skills: {essential_skills}")
            e_skills_dict = {}
    else:
        e_skills_dict = {}

    role_object = Role(
        id=role_id,
        title=title,
        description=description if description else "No description available.",
        essential_skills=e_skills_dict,
        id_full=id_full,
        uri=uri
    )

    message_text = "Error: target role not added."
    updated_target_role = False

    project_found = False
    for project in org.projects:
        if str(project.id) == project_id:
            project_found = True
            already_exists = any(r.id == role_id for r in project.target_roles)
            if not already_exists:
                project.target_roles.append(role_object)
                updated_target_role = True
                message_text = "Target role added successfully!"
                break
            else:
                updated_target_role = True
                message_text = "This role is already in your target list."

    if not project_found:
        return RedirectResponse(url="/org_home", status_code=status.HTTP_303_SEE_OTHER)
    
    if updated_target_role:
        crud_org.update_org(org)

    return templates.TemplateResponse("details.html", {
        "request": request,
        "org": org,
        "is_user": False,
        "role": role_object,
        "project_id": project_id,
        "updated_target_role": updated_target_role,
        "message": message_text
    })

### --- Delete Target Role from Project --- ###    
@router.post("/delete_project_target_role", response_class=RedirectResponse)
async def delete_project_target_role(
    org: Organization = Depends(get_current_org),
    role_id: str = Form(...),
    project_id: str = Form(...)
):
    if not org:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    role_removed = False
    for project in org.projects:
        if str(project.id) == project_id:
            for role in project.target_roles:
                if role.id == role_id:
                    project.target_roles.remove(role)
                    role_removed = True
                    break

    if role_removed:
        crud_org.update_org(org)

    return RedirectResponse(url=f"/org/project/{project_id}", status_code=status.HTTP_303_SEE_OTHER)

### --- Add Member to Project POST --- ###
@router.post("/org/project/{project_id}/add_member", response_class=HTMLResponse)
async def add_member_to_project(
    request: Request,
    project_id: str,
    username_to_add: str = Form(...),
    org: Organization = Depends(get_current_org)
):
    if not org: return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    project = next((p for p in org.projects if str(p.id) == project_id), None)

    if project is None:
        return RedirectResponse(url="/org_home", status_code=status.HTTP_303_SEE_OTHER)
    
    user_in_org = next((u for u in org.members if u == username_to_add), None)
    redirect_url = f"/org/project/{project_id}"

    if not user_in_org:
        error_msg = urllib.parse.quote(f"User '{username_to_add}' is not a member of your organization.")
        return RedirectResponse(url=f"{redirect_url}?error={error_msg}", status_code=status.HTTP_303_SEE_OTHER)
    
    if username_to_add in project.assigned_members:
        error_msg = urllib.parse.quote(f"User '{username_to_add}' is already assigned to this project.")
        return RedirectResponse(url=f"{redirect_url}?error={error_msg}", status_code=status.HTTP_303_SEE_OTHER)
    
    project.assigned_members.append(username_to_add)
    crud_org.update_org(org)
       
    success_msg = urllib.parse.quote(f"User '{username_to_add}' added to the project successfully!")
    return RedirectResponse(url=f"{redirect_url}?success={success_msg}", status_code=status.HTTP_303_SEE_OTHER)

### --- Project Calculate Skill Gap POST --- ###
@router.post("/org/project/calculate_forecast_and_gap")
async def project_calculate_skill_gap(
    request: Request,
    project_id: str = Form(...),
    org: Organization = Depends(get_current_org),
    country: str = Form(...)
):
    if not org: return RedirectResponse(url="/", status_code=303)

    project_index = next((i for i, p in enumerate(org.projects) if str(p.id) == project_id), None)
    
    if project_index is None:
        return RedirectResponse(url="/org_home", status_code=status.HTTP_303_SEE_OTHER)
    
    project = org.projects[project_index]

    if len(project.target_roles) > 5:
        error = "You can analyze up to 5 target roles at a time."
        return templates.TemplateResponse("org/project_detail.html", {
            "request": request,
            "org": org,
            "error": error,
            "countries_list": EU_COUNTRIES,
            "current_project": project,
            "team": crud_user.get_users_by_usernames(project.assigned_members),  
            "current_year": datetime.now().year,
            "forecast_results": None,
            "recommended_courses": None
        })
    
    forecast_results = []
    role_list = []
    for role in project.target_roles:
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


    assigned_members = crud_user.get_users_by_usernames(project.assigned_members)
    updated_project = crud_skill_models.skill_gap_project(project, assigned_members)
    
    org.projects[project_index] = updated_project
    crud_org.update_org(org)

    PROJECT_FORECAST_RESULTS[updated_project.id] = {
        "country": country,
        "results": forecast_results
    }

    # Course recommendation
    missing_skills = {}
    for role in updated_project.skill_gap:
        if 0 <= role["match_score"] < 100:
            for result in forecast_results:
                data = result["data"]
                if data["growth_pct"] >= -5:
                    # Role is expected to grow or remain stable --> provide educational courses and training opportunities
                    for skill_uri, skill_name in role["missing_skills"].items():
                        missing_skills[skill_uri] = skill_name

    # List of recommended courses for the missing skills
    # Role type will be a factor in course recommendation, for now we will consider just the missing skills, 
    # assuming "Mechanical Engineer" and similar role as default role type
    recommended_courses = crud_skill_models.recommend_courses_for_skill_gap(missing_skills)

    PROJECT_COURSES_LIST[updated_project.id] = {
        "results": recommended_courses
    }

    return templates.TemplateResponse("org/project_detail.html", {
        "request": request,
        "org": org,
        "forecast_results": forecast_results, 
        "recommended_courses": recommended_courses,
        "country": country,
        "countries_list": EU_COUNTRIES,
        "current_project": updated_project,
        "team": assigned_members,
        "error": None,
        "current_year": datetime.now().year
    })

