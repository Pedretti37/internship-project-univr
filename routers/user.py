import ast
from datetime import datetime
from fastapi import APIRouter, Query, Request, Form, UploadFile, File, status, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import EmailStr
from typing import Optional

import urllib
from crud import crud_user, crud_org
from dependencies import get_current_user
import csv
import io

from config import templates, pwd_context
import crud.crud_skill_models as crud_skill_models
from esco import escoAPI
from models import Role, Skill, User

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
async def logout():
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    # Delete current session
    response.set_cookie(key="session_token", value="", path="/", httponly=True, max_age=0)
    return response

### --- User Home --- ###
@router.get("/user_home", response_class=HTMLResponse)
async def user_home(
    request: Request, 
    user: User = Depends(get_current_user),
    role_search: Optional[str] = Query(None),
    skill_search: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    success: Optional[str] = Query(None),
    warning: Optional[str] = Query(None)
):

    if not user:
        response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
        return response

    role_list = None
    skill_list = None

    if role_search and role_search.strip():
        role_search = role_search.title().strip()
        role_list = escoAPI.get_esco_occupations_list(role_search, language="en", limit=10)
    
    if skill_search and skill_search.strip():
        skill_search = skill_search.title().strip()
        skill_list = escoAPI.get_esco_skills_list(skill_search, language="en", limit=10)

    toast_msg = success or error or warning
    toast_type = "success" if success else ("error" if error else ("warning" if warning else None))

    return templates.TemplateResponse("user/user_home.html", {
        "request": request,
        "user": user,
        "role_list": role_list,
        "role_search": role_search,
        "skill_list": skill_list,
        "skill_search": skill_search,
        "toast_msg": toast_msg,
        "toast_type": toast_type
    })

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
async def user_profile(
    request: Request, 
    user: User = Depends(get_current_user),
    success: Optional[str] = Query(None), 
    error: Optional[str] = Query(None),
    warning: Optional[str] = Query(None)
):
    
    if not user:
        response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
        return response

    invitations = crud_user.get_pending_invitations_for_user(user.username)
        
    toast_msg = success or error or warning
    toast_type = "success" if success else ("error" if error else ("warning" if warning else None))
    
    return templates.TemplateResponse("user/user_profile.html", {
        "request": request, 
        "user": user, 
        "countries_list": EU_COUNTRIES,
        "invitations": invitations,
        "toast_msg": toast_msg,
        "toast_type": toast_type,
        "current_year": datetime.now().year,
        "forecast_results": None,
        "recommended_courses": None,
        "country": None
    })

### --- Set User Target Roles --- ###
@router.post("/add_to_user_target_roles", response_class=RedirectResponse)
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
    encoded_uri = urllib.parse.quote(uri, safe='')

    # Manual conversion from string to list[Skill]
    if essential_skills:
        try:
            skills_list = ast.literal_eval(essential_skills)
            # Check
            if isinstance(skills_list, list):
                skills_list = skills_list
            else:
                msg = urllib.parse.quote(f"Parsed_data not a valid list. Found type: {type(skills_list)}")
                return RedirectResponse(url=f"/details?uri={encoded_uri}&error={msg}", status_code=status.HTTP_303_SEE_OTHER)
            
        except (ValueError, SyntaxError) as e:
            msg = urllib.parse.quote(f"Error parsing essential_skills: {essential_skills} - Error: {e}")
            return RedirectResponse(url=f"/details?uri={encoded_uri}&error={msg}", status_code=status.HTTP_303_SEE_OTHER)
    else:
        msg = urllib.parse.quote("No essential skills data provided for this role.")
        return RedirectResponse(url=f"/details?uri={encoded_uri}&warning={msg}", status_code=status.HTTP_303_SEE_OTHER)


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

    already_exists = any(r.id == role_id for r in user.target_roles)

    if not already_exists:
        user.target_roles.append(role_object)
        crud_user.update_user(user)
        msg = urllib.parse.quote("Target role added successfully!")
        return RedirectResponse(url=f"/details?uri={encoded_uri}&success={msg}", status_code=status.HTTP_303_SEE_OTHER)
    else:
        msg = urllib.parse.quote("This role is already in your target list.")
        return RedirectResponse(url=f"/details?uri={encoded_uri}&warning={msg}", status_code=status.HTTP_303_SEE_OTHER)

### --- Add User Skills --- ###
@router.post("/add_to_user_skills", response_class=RedirectResponse)
async def add_to_user_skills(
    request: Request,
    user: User = Depends(get_current_user),
    essential_skills: str = Form(...),
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
    
    existing_skills_dict = {s.uri: s for s in user.current_skills}

    for skill_dict in skills_list:
        skill_uri = skill_dict.get("uri")
        selected_level = form_data.get(f"level_{skill_uri}")
        
        if selected_level:
            skill_level = int(selected_level)
            
            if skill_uri in existing_skills_dict:
                existing_skill = existing_skills_dict[skill_uri]
                
                if existing_skill.level != skill_level:
                    existing_skill.level = skill_level
                    updated_skill = True
            
            else:
                skill_dict["level"] = skill_level
                new_skill = Skill(**skill_dict)
                user.current_skills.append(new_skill)
                
                existing_skills_dict[skill_uri] = new_skill
                updated_skill = True

    encoded_uri = urllib.parse.quote(uri, safe='')

    if updated_skill:
        crud_user.update_user(user)
        msg = urllib.parse.quote("Role skills successfully added or updated in your profile!")
        return RedirectResponse(url=f"/details?uri={encoded_uri}&success={msg}", status_code=status.HTTP_303_SEE_OTHER)
    else:
        msg = urllib.parse.quote("No changes were made. Skills are already at the selected levels or no level was selected.")
        return RedirectResponse(url=f"/details?uri={encoded_uri}&warning={msg}", status_code=status.HTTP_303_SEE_OTHER)

### --- Add Single Skill to User --- ###
@router.post("/add_single_skill", response_class=RedirectResponse)
async def add_single_skill(
    request: Request,
    user: User = Depends(get_current_user),
    uri: str = Form(...),
    name: str = Form(...),
    skill_search: Optional[str] = Form(None)
):
    if not user:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    

    form_data = await request.form()
    selected_level = form_data.get(f"level_{uri}")

    search_query = ""
    if skill_search:
        search_query = f"&skill_search={urllib.parse.quote(skill_search)}&"

    if not selected_level:
        msg = urllib.parse.quote("Please select a proficiency level first.")
        return RedirectResponse(url=f"/user_home?{search_query}warning={msg}", status_code=status.HTTP_303_SEE_OTHER)

    skill_level = int(selected_level)
    skill_found = False
    toast_type = "success"

    for existing_skill in user.current_skills:
        if existing_skill.uri == uri:
            skill_found = True
            if existing_skill.level == skill_level:
                message_text = "You already have this skill at this exact level."
                toast_type = "warning"
            else:
                existing_skill.level = skill_level
                message_text = f"Skill \"{existing_skill.name}\" updated to level {skill_level}!"
            break

    if not skill_found:
        new_skill = Skill(uri=uri, name=name, level=skill_level)
        user.current_skills.append(new_skill)
        message_text = f"Skill \"{new_skill.name}\" added to your profile!"

    crud_user.update_user(user)

    msg = urllib.parse.quote(message_text)

    return RedirectResponse(url=f"/user_home?{search_query}{toast_type}={msg}", status_code=status.HTTP_303_SEE_OTHER)

### --- Password Change --- ###
@router.post("/change_password_user", response_class=RedirectResponse)
async def change_password(
    user: User = Depends(get_current_user), 
    old_pw: str = Form(...), 
    new_pw: str = Form(...)
):

    if not user:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    if not pwd_context.verify(old_pw, user.hashed_password):
        warning = "Your old password is not correct."
        msg = urllib.parse.quote(warning)
        return RedirectResponse(url=f"/user_profile?warning={msg}", status_code=status.HTTP_303_SEE_OTHER)

    new_pw_hashed = pwd_context.hash(new_pw)
    success = crud_user.change_password_user(user, new_pw_hashed) # Updates user too
    
    if success:
        msg = urllib.parse.quote("Password updated successfully!")
        toast_type = "success"
    else:
        msg = urllib.parse.quote("Failed to update your password.")
        toast_type = "error"
    return RedirectResponse(url=f"/user_profile?{toast_type}={msg}", status_code=status.HTTP_303_SEE_OTHER)
    
### --- Details for a selected Skill Model --- ###
@router.get("/details", response_class=HTMLResponse)
async def details_page(
    request: Request, 
    uri: str = Query(...),
    user: User = Depends(get_current_user),
    success: Optional[str] = Query(None),
    warning: Optional[str] = Query(None),
    error: Optional[str] = Query(None)
):

    if not user:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    selected_role = escoAPI.get_single_role_details(uri, language="en")

    if not selected_role:
        return RedirectResponse(url="/user_home", status_code=status.HTTP_303_SEE_OTHER)

    toast_msg = success or warning or error
    toast_type = "success" if success else ("warning" if warning else ("error" if error else None))

    return templates.TemplateResponse("details.html", {
        "request": request,
        "is_user": True,
        "role": selected_role,
        "toast_msg": toast_msg,
        "toast_type": toast_type
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
        msg = urllib.parse.quote("You can analyze up to 5 target roles at a time.")
        return RedirectResponse(url=f"/user_profile?error={msg}", status_code=status.HTTP_303_SEE_OTHER)

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

    # Course recommendation
    missing_skills = {}
    for role in updated_user.skill_gap:
        if 0 <= role["match_score"] < 100:
            for result in forecast_results:
                if result["isco_code"] == str(role["role_id"]):
                    data = result["data"]
                    if data["growth_pct"] >= -5:
                        # Role is expected to grow or remain stable --> provide educational courses and training opportunities
                        for skill in role.get("missing_skills", []):
                            missing_skills[skill.uri] = skill.name
                        for skill in role.get("partially_matching_skills", []):
                            skill_obj = skill["skill"]
                            missing_skills[skill_obj.uri] = skill_obj.name
                    break

    # print(len(missing_skills))

    # List of recommended courses for the missing skills
    # Role type will be a factor in course recommendation, for now we will consider just the missing skills, 
    # assuming "Mechanical Engineer" and similar role as default role type
    recommended_courses = crud_skill_models.recommend_courses_for_skill_gap(missing_skills)

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

    inv = crud_org.get_inv_by_id(inv_id)
    if inv:
        inv.status = "accepted"
        crud_org.update_invitation(inv)

    user_skills_updated = False
    existing_skills_dict = {s.uri: s for s in user.current_skills}

    # Checking if user was in pending_members of any project within the organization
    for project in org.projects:
        pending_list = getattr(project, 'pending_members', [])
        
        pending_user_data = next((pm for pm in pending_list if pm["username"] == user.username), None)
        
        if pending_user_data:
            # Unlocking the skills data from the pending member
            for sk in pending_user_data["skills"]:
                if sk["uri"] in existing_skills_dict:
                    if existing_skills_dict[sk["uri"]].level != sk["level"]:
                        existing_skills_dict[sk["uri"]].level = sk["level"]
                        user_skills_updated = True
                else:
                    new_skill = Skill(uri=sk["uri"], name=sk["name"], level=sk["level"])
                    user.current_skills.append(new_skill)
                    existing_skills_dict[sk["uri"]] = new_skill
                    user_skills_updated = True
            
            # Not pending anymore
            project.pending_members = [pm for pm in pending_list if pm["username"] != user.username]
            
            # Promotion to assigned member
            if user.username not in project.assigned_members:
                project.assigned_members.append(user.username)

    # Update user
    if user_skills_updated:
        crud_user.update_user(user)


    # Update org
    crud_org.update_org(org)

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

### --- Upload Skill via CSV ---###
@router.post("/upload_skills_csv", response_class=HTMLResponse)
async def upload_skills_csv(
    request: Request,
    user: User = Depends(get_current_user),
    file: UploadFile = File(...)
):
    if not user:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    if not file.filename.lower().endswith('.csv'):
        msg = urllib.parse.quote("Invalid file type. Please upload a CSV file.")
        return RedirectResponse(url=f"/user_home?error={msg}", status_code=status.HTTP_303_SEE_OTHER)

    content = await file.read()
    try:
        decoded_content = content.decode('utf-8')
    except UnicodeDecodeError:
        msg = urllib.parse.quote("Failed to decode the file. Please ensure it's a valid UTF-8 encoded CSV.")
        return RedirectResponse(url=f"/user_profile?error={msg}", status_code=status.HTTP_303_SEE_OTHER)

    csv_reader = csv.DictReader(io.StringIO(decoded_content))

    skills_to_review = []
    skills_not_found = []

    for row in csv_reader:
        skill_name = row.get("skill_name")
        level_str = row.get("level")

        if not skill_name or not level_str:
            continue # Skipping rows with missing data
            
        try:
            skill_level = int(level_str)
            skill_level = max(1, min(9, skill_level)) # Forcing level to be between 1 and 9
        except ValueError:
            continue # Skipping rows where the level is not a valid integer

        # API search to get the official ESCO skill URI and name based on the provided skill name in the CSV
        search_results = escoAPI.get_esco_skills_list(skill_name, language="en", limit=10)
        
        if search_results:
            skills_to_review.append({
            "raw_name": skill_name.capitalize(),
            "level": skill_level,
            "options": search_results # First 10 results from ESCO, user can choose the most relevant one in the review step
        })
        else:
            skills_not_found.append(skill_name)

    return templates.TemplateResponse("user/review_skills.html", {
        "request": request,
        "user": user,
        "skills_to_review": skills_to_review,
        "skills_not_found": skills_not_found
    })

### --- Confirm and Save CSV Skills --- ###
@router.post("/confirm_skills_csv", response_class=RedirectResponse)
async def confirm_skills_csv(
    request: Request,
    user: User = Depends(get_current_user)
):
    if not user:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    form_data = await request.form()
    
    # Obtain number of rows = number of skills to review, which we had saved in a hidden input in the HTML form
    total_rows_str = form_data.get("total_rows")
    if not total_rows_str:
        return RedirectResponse(url="/user_home", status_code=status.HTTP_303_SEE_OTHER)
        
    total_rows = int(total_rows_str)
    
    existing_skills_dict = {s.uri: s for s in user.current_skills}
    updated = False

    for i in range(1, total_rows + 1):
        uri_and_name = form_data.get(f"uri_name_{i}")
        level_str = form_data.get(f"level_{i}")
        
        # If user decides to skip a skill
        if not uri_and_name or uri_and_name == "SKIP":
            continue
            
        # Splitting URI and offical name, connected by "|||", which we had set in a hidden input in the HTML form for each skill option
        parts = uri_and_name.split("|||")
        if len(parts) != 2:
            continue
            
        skill_uri = parts[0]
        official_name = parts[1]
        skill_level = int(level_str)

        # Update logic
        if skill_uri in existing_skills_dict:
            if existing_skills_dict[skill_uri].level != skill_level:
                existing_skills_dict[skill_uri].level = skill_level
                updated = True
        else:
            new_skill = Skill(uri=skill_uri, name=official_name, level=skill_level)
            user.current_skills.append(new_skill)
            existing_skills_dict[skill_uri] = new_skill
            updated = True

    if updated:
        crud_user.update_user(user)

    return RedirectResponse(url="/user_home", status_code=status.HTTP_303_SEE_OTHER)

