from fastapi import APIRouter, Request, Form, status, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import EmailStr
from typing import Optional, List
from crud import crud_user
from dependencies import get_current_user

from config import templates, pwd_context
import crud.crud_skill_models as crud_skill_models
from models import User

router = APIRouter()

### --- User Login --- ###
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

@router.post("/user_login", response_class=HTMLResponse)
async def user_login(request: Request, username: str = Form(...), password: str = Form(...)):
    user = crud_user.get_user(username)

    if not user or not pwd_context.verify(password, user.hashed_password):
        response = RedirectResponse(url="/user_login", status_code=status.HTTP_303_SEE_OTHER)
        
        response.set_cookie(key="flash_error", value="Invalid credentials. Please try again.")
        return response

    response = RedirectResponse(url="/user_home", status_code=status.HTTP_303_SEE_OTHER)

    response.set_cookie(key="session_token", value=user.username, path="/", httponly=True, max_age=1800)  # 30 minutes session
    response.delete_cookie(key="flash_error")

    return response

### --- User Home --- ###
@router.get("/user_home", response_class=HTMLResponse)
async def user_home(request: Request, user = Depends(get_current_user)):

    if not user:
        response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie("session_token", value="", path="/", httponly=True, max_age=0)
        return response

    response = templates.TemplateResponse(
        "user/user_home.html", 
        {"request": request, "user": user}
    )

    # No cache storage
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.headers["Vary"] = "Cookie"

    return response

### --- User Registration --- ###
@router.get("/user_register", response_class=HTMLResponse)
async def register(request: Request):
    return templates.TemplateResponse("user/user_register.html", {"request": request})

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
        "user/user_profile.html", 
        {"request": request, "user": user}
    )

    # No cache storage
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.headers["Vary"] = "Cookie"

    return response

### --- Obtain skills from User Input --- ###
@router.post("/extract_skill_models", response_class=HTMLResponse)
async def extract_skill_models(request: Request, search: str = Form(...), user = Depends(get_current_user)):
    role = search.title().strip()

    extracted_models = {}

    skill_models_list = crud_skill_models.extracting_skill_models(role)
    if skill_models_list:
        extracted_models[role] = skill_models_list
    
    if user:
        return templates.TemplateResponse("user/user_home.html", {
            "request": request,
            "user": user,
            "results": extracted_models,
            "last_search": search
        })
    else:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
### --- Set Target Roles --- ###
@router.post("/set_target_roles", response_class=HTMLResponse)
async def set_target_roles(
    request: Request,
    user = Depends(get_current_user),
    role1: str = Form(...), # Usa ... se il campo è obbligatorio, o None se opzionale
    role2: Optional[str] = Form(None),
    role3: Optional[str] = Form(None),
    role4: Optional[str] = Form(None),
    role5: Optional[str] = Form(None)
):
    if not user:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    roles_input = [role1, role2, role3, role4, role5]
    clean_inputs = [r.strip() for r in roles_input if r and r.strip() != ""]

    found_roles_dict = crud_user.set_target_roles_user(user, clean_inputs)
    
    msg = ""
    msg_type = "success"

    if not clean_inputs:
        msg = "Hai rimosso tutti i ruoli target."
        msg_type = "warning"
    elif not found_roles_dict:
        msg = "Nessun ruolo trovato nel database corrispondente alla tua ricerca. Riprova con termini diversi."
        msg_type = "danger"
    else:
        msg = f"Profilo aggiornato! Trovati {len(found_roles_dict)} ruoli su {len(clean_inputs)} cercati."

    return templates.TemplateResponse("user/user_profile.html", {
        "request": request,
        "user": user,
        "message": msg,
        "message_type": msg_type
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
@router.get("/details/{role_id}")
async def details_page(request: Request, role_id: str, user = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    role_object = crud_skill_models.get_role_by_id(role_id)

    if not role_object:
        error = "Skill Model not found"
        return templates.TemplateResponse("user/user_home.html", {
            "request": request,
            "user": user,
            "error": error
        })
    
    return templates.TemplateResponse("user/details.html", {
        "request": request,
        "user": user,
        "role": role_object
    })
    
### --- Delete Target Role --- ###
@router.post("/delete_target_role", response_class=HTMLResponse)
async def delete_target_role(
    user = Depends(get_current_user),
    role_id: str = Form(...)
):
    if not user:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    crud_user.delete_role_from_user(user, role_id)

    return RedirectResponse(url="/user_profile", status_code=status.HTTP_303_SEE_OTHER)
    # return Response(status_code=200)

### --- Calculating Skill Gap --- ###
@router.post("/calculate_skill_gap", response_class=HTMLResponse)
async def calculate_skill_gap(request: Request, user = Depends(get_current_user), role_ids: List[str] = Form(...)):
    if not user:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    if len(role_ids) > 5:
        error = "You can analyze up to 5 roles at a time."
        return templates.TemplateResponse("user/user_profile.html", {
            "request": request,
            "user": user,
            "error": error
        })

    gap_analysis_result = crud_skill_models.calculate_skill_gap_user(user, role_ids)

    # 2. Mostriamo i risultati
    return templates.TemplateResponse("user/user_profile.html", {
        "request": request,
        "user": user,
        "gap_report": gap_analysis_result
    })