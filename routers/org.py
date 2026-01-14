from fastapi import APIRouter, Request, Form, status, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import EmailStr
from crud import crud_user
from dependencies import get_current_org

from config import templates, pwd_context
import crud.crud_org as crud_org
from models import Organization

router = APIRouter()

### --- Organization Login --- ###
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

@router.post("/org_login", response_class=HTMLResponse)
async def org_login(request: Request, orgname: str = Form(...), password: str = Form(...)):
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
    
    members = crud_user.get_users_by_ids(org.members)

    response = templates.TemplateResponse("org/org_home.html", {
        "request": request, 
        "org": org,
        "members": members
    })

    # No cache storage
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.headers["Vary"] = "Cookie"

    return response

### --- Organization Registration --- ###
@router.get("/org_register", response_class=HTMLResponse)
async def org_register(request: Request):
    return templates.TemplateResponse("org/org_register.html", {"request": request})

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
    
### --- Add Member --- ###
@router.post("/add_member", response_class=HTMLResponse)
async def add_member(
    request: Request, 
    org = Depends(get_current_org), 
    username_to_add: str = Form(...)
):
    if not org:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    error_msg = None
    success_msg = None

    user_to_add = crud_user.get_user_by_username(username_to_add)

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