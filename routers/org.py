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

    if org:
        for project in org.projects:
            PROJECT_ROLES_LIST.pop(project.id, None)
            PROJECT_COURSES_LIST.pop(project.id, None)
            PROJECT_FORECAST_RESULTS.pop(project.id, None)
            
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
):
    if not org:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    final_assigned_members = set(assigned_members)

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
    uri: str = Form(...),
    project_id: str = Form(...),
    org: Organization = Depends(get_current_org)):

    if not org:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    current_project: Optional[Project] = next((p for p in org.projects if str(p.id) == project_id), None)
    
    if not current_project:
            return RedirectResponse(url="/org_home", status_code=status.HTTP_303_SEE_OTHER)

    selected_role = escoAPI.get_single_role_details(uri, language="en")

    if not selected_role:
        return RedirectResponse(url="/user_home", status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse("details.html", {
        "request": request,
        "org": org,
        "current_project": current_project,
        "is_user": False,
        "role": selected_role,
        "project_id": project_id
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

    toast_msg = "Error: target role not added."
    toast_type = "error"
    updated_target_role = False
    project_found = False

    for i, project in enumerate(org.projects):
        if str(project.id) == project_id:
            project_found = True
            already_exists = any(r.id == role_id for r in project.target_roles)
            
            if not already_exists:
                project.target_roles.append(role_object)
                
                org.projects[i] = project 
                
                updated_target_role = True
                toast_msg = f"Role '{title}' added to project successfully!"
                toast_type = "success"  # Toast Verde ✅
            else:
                toast_msg = f"The role '{title}' is already in your target list."
                toast_type = "warning"  # Toast Giallo ⚠️
            
            break

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
        "toast_msg": toast_msg,    
        "toast_type": toast_type  
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

### --- Upload Skills CSV for Project --- ###
@router.post("/upload_project_skills_csv", response_class=HTMLResponse)
async def upload_project_skills_csv(
    request: Request,
    project_id: str = Form(...),
    file: UploadFile = File(...),
    org: Organization = Depends(get_current_org)
):
    if not org:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    project = next((p for p in org.projects if str(p.id) == project_id), None)

    if not project:
        return RedirectResponse(url="/org_home", status_code=status.HTTP_303_SEE_OTHER)

    if not file.filename.lower().endswith('.csv'):
        print(f"Errore: Il file {file.filename} non è un CSV.")
        return RedirectResponse(url="/org_home", status_code=status.HTTP_303_SEE_OTHER)
    
    csvReader = csv.DictReader(codecs.iterdecode(file.file, 'utf-8'))
    
    skills_to_review = []
    skills_not_found = []

    known_users = {}

    for row in csvReader:
        username = row.get("username")
        skill_name = row.get("skill_name")
        level_str = row.get("level")
        
        if not username or not skill_name or not level_str:
            continue
            
        try:
            level = int(level_str)
            skill_level = max(1, min(9, level))
        except ValueError:
            continue

        if username not in known_users:
            user = crud_user.get_user_by_username(username)
            if user:
                known_users[username] = True
                if username not in org.members:
                    crud_org.create_invitation(org.orgname, username)
                    print(f"📩 Inviata richiesta di iscrizione a '{username}'.")
            else:
                known_users[username] = False
                print(f"⚠️ Utente {username} non trovato nel database.")

        if not known_users[username]:
            continue

        search_results = escoAPI.get_esco_skills_list(skill_name, language="en", limit=10)
        
        if search_results:
            skills_to_review.append({
                "username": username,
                "raw_name": skill_name.capitalize(),
                "level": skill_level,
                "options": search_results
            })
        else:
            skills_not_found.append({
                "username": username,
                "skill_name": skill_name
            })

    return templates.TemplateResponse("org/review_project_skills.html", {
        "request": request,
        "org": org,
        "project_id": project_id,
        "skills_to_review": skills_to_review,
        "skills_not_found": skills_not_found
    })

@router.post("/org/confirm_project_skills", response_class=RedirectResponse)
async def confirm_project_skills_csv(
    request: Request,
    org: Organization = Depends(get_current_org)
):
    if not org:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    form_data = await request.form()
    
    # Data recovery
    project_id = form_data.get("project_id")
    total_rows_str = form_data.get("total_rows")
    
    if not project_id or not total_rows_str:
        return RedirectResponse(url="/org_home", status_code=status.HTTP_303_SEE_OTHER)

    project = next((p for p in org.projects if str(p.id) == project_id), None)
    if not project:
        return RedirectResponse(url="/org_home", status_code=status.HTTP_303_SEE_OTHER)
        
    total_rows = int(total_rows_str)
    
    # Skill per user
    user_updates = {}
    
    for i in range(1, total_rows + 1):
        username = form_data.get(f"username_{i}")
        uri_and_name = form_data.get(f"uri_name_{i}")
        level_str = form_data.get(f"level_{i}")
        
        if not username or not uri_and_name or uri_and_name == "SKIP":
            continue
            
        parts = uri_and_name.split("|||")
        if len(parts) != 2:
            continue
            
        skill_uri = parts[0]
        official_name = parts[1]
        skill_level = int(level_str)

        if username not in user_updates:
            user_updates[username] = []

        user_updates[username].append({
            "uri": skill_uri,
            "name": official_name,
            "level": skill_level
        })

    members_to_assign = set(project.assigned_members) if project.assigned_members else set()
    pending_members_dict = {pm["username"]: pm for pm in getattr(project, 'pending_members', [])} if getattr(project, 'pending_members', None) else {}

    # Update user skills and project membership based on the confirmed data
    for username, skills in user_updates.items():
        user = crud_user.get_user_by_username(username)
        if not user:
            continue 

        if username in org.members:
            existing_skills_dict = {s.uri: s for s in user.current_skills}
            user_updated = False

            for sk in skills:
                if sk["uri"] in existing_skills_dict:
                    if existing_skills_dict[sk["uri"]].level != sk["level"]:
                        existing_skills_dict[sk["uri"]].level = sk["level"]
                        user_updated = True
                else:
                    new_skill = Skill(uri=sk["uri"], name=sk["name"], level=sk["level"])
                    user.current_skills.append(new_skill)
                    user_updated = True

            if user_updated:
                crud_user.update_user(user)

            members_to_assign.add(username)
            
            if username in pending_members_dict:
                del pending_members_dict[username]

        else:
            pending_members_dict[username] = {
                "username": username,
                "skills": skills 
            }

    # Update lists
    project.assigned_members = list(members_to_assign)
    project.pending_members = list(pending_members_dict.values())

    crud_org.update_org(org)

    return RedirectResponse(url=f"/org/project/{project.id}", status_code=status.HTTP_303_SEE_OTHER)
