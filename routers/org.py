from fastapi import APIRouter, Request, Form, status, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import EmailStr
from crud import crud_project, crud_skill_models, crud_user
from dependencies import get_current_org
from esco import escoAPI 

from config import templates, pwd_context
import crud.crud_org as crud_org
from models import Organization, Project

router = APIRouter()

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

    response.set_cookie(key="session_token", value=org.id, path="/", httponly=True, max_age=1800)  # 30 minutes session
    response.delete_cookie(key="flash_error")

    return response

### --- Organization Home --- ###
@router.get("/org_home", response_class=HTMLResponse)
async def org_home(request: Request, org = Depends(get_current_org)):

    if not org:
        response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie("session_token", value="", path="/", httponly=True, max_age=0)
        return response
    
    # Member list
    members = crud_user.get_users_by_ids(org.members)

    # Project list
    projects = crud_project.get_org_projects(org.id)

    response = templates.TemplateResponse("org/org_home.html", {
        "request": request, 
        "org": org,
        "members": members,
        "projects": projects
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
async def org_profile(request: Request, org = Depends(get_current_org)):
    if not org:
        response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie("session_token", value="", path="/", httponly=True, max_age=0)
        return response

    response = templates.TemplateResponse(
        "org/org_profile.html", 
        {"request": request, "org": org}
    )

    # No cache storage
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.headers["Vary"] = "Cookie"

    return response

### --- Password Change --- ###
@router.post("/change_password_org", response_class=HTMLResponse)
async def change_password(request: Request, org = Depends(get_current_org), old_pw: str = Form(...), new_pw: str = Form(...)):
    if not org:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    if not pwd_context.verify(old_pw, org.hashed_password):
        error = "Your old password is not correct."
        return templates.TemplateResponse("org/org_profile.html", {
            "request": request,
            "org": org,
            "wrong_pw": error
        })
    
    new_pw_hashed = pwd_context.hash(new_pw)

    success = crud_org.change_password_org(org, new_pw_hashed)

    if success:
        msg = "Password updated successfully!"
        return templates.TemplateResponse("org/org_profile.html", {
            "request": request,
            "org": org,
            "success": msg
        })
    else:
        failed = "Failed to update your password."
        return templates.TemplateResponse("org/org_profile.html", {
            "request": request,
            "org": org,
            "failed": failed
        })
    
### --- Invite Member --- ###
@router.post("/invite_member", response_class=HTMLResponse)
async def invite_member(
    request: Request, 
    org = Depends(get_current_org), 
    username_to_invite: str = Form(...)
):
    if not org:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    error_msg = None
    success_msg = None

    user_to_invite = crud_user.get_user_by_username(username_to_invite)
    created = crud_org.create_invitation(org.id, user_to_invite.id)

    if created:
        success_msg = f"Invitation sent to '{username_to_invite}' successfully!"
    else:
        error_msg = "Failed to send invitation. Please try again."

    return templates.TemplateResponse("org/org_home.html", {
        "request": request,
        "org": org,
        "members": crud_user.get_users_by_ids(org.members),
        "error": error_msg,
        "success": success_msg
    })

    if user_to_add:
        if user_to_add.id in org.members:
             error_msg = "User is already in your team."
        else:
             crud_org.add_member_to_org(org, user_to_add.id)
             success_msg = f"User '{user_to_add.name} {user_to_add.surname}' added successfully!"
    else:
        error_msg = "User not found. Please check the username."
    # Refresh member list
    members_objects = crud_user.get_users_by_ids(org.members)

    return templates.TemplateResponse("org/org_home.html", {
        "request": request,
        "org": org,
        "members": members_objects,
        "error": error_msg,
        "success": success_msg
    })

### --- Create Project GET --- ###
@router.get("/org/create_project", response_class=HTMLResponse)
async def create_project_form(request: Request, org = Depends(get_current_org)):
    if not org:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    # member list for assignment with checkboxes
    members = crud_user.get_users_by_ids(org.members)

    return templates.TemplateResponse("org/create_project.html", {
        "request": request,
        "org": org,
        "members": members
    })

### --- Create Project POST --- ###
@router.post("/org/create_project", response_class=HTMLResponse)
async def create_project_submit(
    org = Depends(get_current_org),
    name: str = Form(...),
    description: str = Form(...),
    assigned_members: list[str] = Form(default=[]) 
):
    if not org:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    new_project = Project(
        org_id=org.id,
        name=name,
        description=description,
        assigned_members_ids=assigned_members,
        target_roles=[] # Empty for now
    )

    crud_project.create_project(new_project)

    return RedirectResponse(url="/org_home", status_code=status.HTTP_303_SEE_OTHER)

### --- View Project GET --- ###
@router.get("/org/project/{project_id}", response_class=HTMLResponse)
async def view_project(
    request: Request, 
    project_id: str, 
    org = Depends(get_current_org)
):
    if not org:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    project = crud_project.get_project(project_id)
    
    # Security check: ensure the project belongs to the org
    if not project or project.org_id != org.id:
        return RedirectResponse(url="/org_home", status_code=status.HTTP_303_SEE_OTHER)

    assigned_members = crud_user.get_users_by_ids(project.assigned_members_ids)

    return templates.TemplateResponse("org/project_detail.html", {
        "request": request,
        "org": org,
        "project": project,
        "team": assigned_members,
        "search_results": None 
    })

### --- Project Search Role --- ###
@router.post("/org/project/{project_id}/search", response_class=HTMLResponse)
async def project_search_role(
    request: Request, 
    project_id: str, 
    search: str = Form(...),
    org = Depends(get_current_org)
):
    if not org: return RedirectResponse(url="/", status_code=303)
    
    project = crud_project.get_project(project_id)
    assigned_members = crud_user.get_users_by_ids(project.assigned_members_ids)

    # ESCO API Search
    language = "en"
    results = escoAPI.get_esco_occupations_list(search, language=language, limit=10)

    return templates.TemplateResponse("org/project_detail.html", {
        "request": request,
        "org": org,
        "project": project,
        "team": assigned_members,
        "search_results": results,
        "last_search": search
    })

### --- Project Add Role POST --- ###
@router.post("/org/project/add_role", response_class=RedirectResponse)
async def project_add_role(
    project_id: str = Form(...),
    uri: str = Form(...),
    org = Depends(get_current_org)
):
    if not org: return RedirectResponse(url="/", status_code=303)

    project = crud_project.get_project(project_id)
    
    language = "en"
    if project and project.org_id == org.id:
        role_data = escoAPI.get_single_role_details(uri, language=language)
        
        if role_data:
            crud_project.add_target_role(project, role_data.model_dump())

    # Refresh project detail page
    return RedirectResponse(url=f"/org/project/{project_id}", status_code=status.HTTP_303_SEE_OTHER)

### --- Project Calculate Skill Gap POST --- ###
@router.post("/org/project/calculate_gap", response_class=RedirectResponse)
async def project_calculate_skill_gap(
    project_id: str = Form(...),
    org = Depends(get_current_org)
):
    if not org: return RedirectResponse(url="/", status_code=303)

    project = crud_project.get_project(project_id)
    
    if project and project.org_id == org.id:
        assigned_members = crud_user.get_users_by_ids(project.assigned_members_ids)
        
        updated_project = crud_skill_models.skill_gap_project(project, assigned_members)
        
        crud_project.update_project(updated_project)

    return RedirectResponse(url=f"/org/project/{project_id}", status_code=status.HTTP_303_SEE_OTHER)
