import ast
from datetime import datetime
from fastapi import APIRouter, Query, Request, Form, UploadFile, File, status, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Optional
import urllib
from crud import crud_user, crud_org, crud_skill_models
from service import cedefop_service
from service.dependencies import get_current_user
import csv
import io
from service.config import templates, pwd_context
from esco import escoAPI
from models import Role, Skill, User, Project
from educational_offerings.courses_recommendation import recommend_courses_for_skill_gap

EU_COUNTRIES = [
    "Austria", "Belgium", "Bulgaria", "Croatia", "Cyprus", "Czech Republic", 
    "Denmark", "EU-27", "Estonia", "Finland", "France", "Germany", "Greece", 
    "Hungary", "Iceland", "Ireland", "Italy", "Latvia", "Lithuania", 
    "Luxembourg", "Malta", "Netherlands", "Norway", "Poland", "Portugal", 
    "Republic of North Macedonia", "Romania", "Slovakia", "Slovenia", 
    "Spain", "Sweden", "Switzerland", "Turkey"
]
CEDEFOP_SECTORS = [
    "Agriculture, Forestry and Fishing",                                        # A
    "Mining and quarrying",                                                     # B
    "Manufacturing",                                                            # C
    "Electricity, Gas, Steam and Air Conditioning Supply",                      # D
    "Water Supply, Sewerage, Waste Management and Remediation Activities",      # E
    "Construction",                                                             # F
    "Wholesale and Retail Trade, Repair of Motor Vehicles and Motorcycles",     # G
    "Transportation and Storage",                                               # H
    "Accommodation and Food Service Activities",                                # I
    "Information and Communication",                                            # J
    "Financial and Insurance Activities",                                       # K
    "Real estate",                                                              # L
    "Professional, Scientific and Technical Activities",                        # M
    "Administrative and Support Service Activities",                            # N
    "Public Administration and Defence, Compulsory Social Security",            # O
    "Education",                                                                # P
    "Human Health and Social Work Activities",                                  # Q
    "Arts and entertainment",                                                   # R
    "Other service activities",                                                 # S
    "Activities of Households as Employers"                                     # T
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

    managed_projects = []
    if user.level == 'manager' and user.organization:
        org = crud_org.get_org_by_orgname(user.organization)
        
        if org and hasattr(org, 'projects'):
            managed_projects = [
                proj for proj in org.projects 
                if proj.manager == user.username
            ]

    toast_msg = success or error or warning
    toast_type = "success" if success else ("error" if error else ("warning" if warning else None))

    return templates.TemplateResponse("user/user_home.html", {
        "request": request,
        "user": user,
        "role_list": role_list,
        "role_search": role_search,
        "skill_list": skill_list,
        "skill_search": skill_search,
        "managed_projects": managed_projects,
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
    username: str = Form(...), 
    password: str = Form(...)
):
    hashed_pw = pwd_context.hash(password)
    new_user = User(name=name, surname=surname, username=username, hashed_password=hashed_pw)
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
    org = crud_org.get_org_by_orgname(user.organization)
        
    toast_msg = success or error or warning
    toast_type = "success" if success else ("error" if error else ("warning" if warning else None))
    
    return templates.TemplateResponse("user/user_profile.html", {
        "request": request, 
        "user": user, 
        "countries_list": EU_COUNTRIES,
        "sectors_list": CEDEFOP_SECTORS,
        "invitations": invitations,
        "org": org,
        "toast_msg": toast_msg,
        "toast_type": toast_type,
        "current_year": datetime.now().year,
        "forecast_results": None,
        "recommended_courses": None,
        "country": None,
        "sector": None
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

    already_exists = any(r.uri == uri for r in user.target_roles)

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
    
    existing_skills_dict = {s.uri: s for s in user.individual_skills}

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
                user.individual_skills.append(new_skill)
                
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

    for existing_skill in user.individual_skills:
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
        user.individual_skills.append(new_skill)
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
    role_uri: str = Form(...)
):
    if not user:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    # new list excluding the role to be deleted
    new_target_list = [
        role for role in user.target_roles 
        if role.uri != role_uri
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
        skill for skill in user.individual_skills 
        if skill.uri != skill_uri
    ]
    
    user.individual_skills = new_skills_list

    crud_user.update_user(user)

    return RedirectResponse(url="/user_profile", status_code=status.HTTP_303_SEE_OTHER)

### --- Occupation Forecast and Gap --- ###
@router.post("/forecast_gap_courses", response_class=HTMLResponse)
async def forecast_gap_courses(
    request: Request,
    user: User = Depends(get_current_user),
    country: str = Form(...),
    sector: Optional[str] = Form(None)
):
    if not user:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    if len(user.target_roles) > 5:
        msg = urllib.parse.quote("You can analyze up to 5 target roles at a time.")
        return RedirectResponse(url=f"/user_profile?error={msg}", status_code=status.HTTP_303_SEE_OTHER)

    db = request.app.state.cedefop

    forecast_results = []
    for role in user.target_roles:
        # String conversion and cleanup
        role_id_str = str(role.id).strip()
            
        # CEDEFOP
        occ_data = cedefop_service.read_emp_occupation(db, country, role_id_str)
        sec_data = cedefop_service.read_emp_sector_occupation(db, country, sector, role_id_str)
        qual_data = cedefop_service.read_qualifications(db, country, role_id_str)
        job_data = cedefop_service.read_job_openings(db, country, role_id_str)
        
        forecast_results.append({
            "title": role.title,  
            "isco_code": role_id_str,
            "uri": role.uri,
            "occupation_data": occ_data,
            "sector_data": sec_data,
            "qualifications_data": qual_data,
            "job_openings_data": job_data
        })
    
    updated_user = crud_skill_models.skill_gap_user(user, user.target_roles)
    crud_user.update_user(updated_user)

    # Course recommendation
    all_missing_skills = {}
    for role_gap in updated_user.skill_gap:
        for skill in role_gap.get("missing_skills", []):
            all_missing_skills[skill.uri] = skill.name
        for skill_entry in role_gap.get("partially_matching_skills", []):
            s_obj = skill_entry["skill"]
            all_missing_skills[s_obj.uri] = s_obj.name

    # print(len(missing_skills))

    # List of recommended courses for the missing skills
    recommended_courses = recommend_courses_for_skill_gap(all_missing_skills, 'individual', user.organization, crud_org.get_all_orgs())

    return templates.TemplateResponse("user/user_profile.html", {
        "request": request,
        "user": updated_user,
        "forecast_results": forecast_results, 
        "recommended_courses": recommended_courses,
        "country": country,
        "sector": sector,
        "countries_list": EU_COUNTRIES,
        "sectors_list": CEDEFOP_SECTORS,
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
    if not org:
        return RedirectResponse(url="/user_profile?error=Organization+not+found", status_code=303)

    if org.members is None: 
        org.members = {}
    if getattr(org, 'pending_members', None) is None:
        org.pending_members = {}

    pending_skills = []
    if hasattr(org, 'pending_members') and user.username in org.pending_members:
        pending_skills = org.pending_members[user.username]
        del org.pending_members[user.username]

    org.members[user.username] = pending_skills

    inv = crud_org.get_inv_by_id(inv_id)
    if inv:
        inv.status = "accepted"
        crud_org.update_invitation(inv)

    crud_org.update_org(org)

    msg = urllib.parse.quote(f"Welcome to {orgname}!")
    return RedirectResponse(url=f"/user_profile?success={msg}", status_code=status.HTTP_303_SEE_OTHER)

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
        return RedirectResponse(url=f"/user_profile?error={msg}", status_code=status.HTTP_303_SEE_OTHER)

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
        return RedirectResponse(url="/user_profile", status_code=status.HTTP_303_SEE_OTHER)
        
    total_rows = int(total_rows_str)
    
    existing_skills_dict = {s.uri: s for s in user.individual_skills}
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
            user.individual_skills.append(new_skill)
            existing_skills_dict[skill_uri] = new_skill
            updated = True

    if updated:
        crud_user.update_user(user)

    return RedirectResponse(url="/user_profile", status_code=status.HTTP_303_SEE_OTHER)

### --------------------------------
### ----------- MANAGER ------------
### --------------------------------

### --- Create Project GET --- ###
@router.get("/manager/create_project", response_class=HTMLResponse)
async def create_project_form(
    request: Request, 
    user: User = Depends(get_current_user)
):
    if not user:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    orgname = user.organization
    org = crud_org.get_org_by_orgname(orgname)

    # member list for assignment with checkboxes
    members = crud_user.get_users_by_usernames(org.members)

    return templates.TemplateResponse("user/create_project.html", {
        "request": request,
        "user": user,
        "members": members
    })

### --- Create Project POST --- ###
@router.post("/manager/create_project", response_class=RedirectResponse)
async def create_project_submit(
    user: User = Depends(get_current_user),
    name: str = Form(...),
    description: str = Form(...),
    members_list: list[str] = Form(default=[]), 
):
    if not user:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    orgname = user.organization
    org = crud_org.get_org_by_orgname(orgname)

    new_project = Project(
        name=name,
        description=description,
        manager=user.username,
        assigned_members=members_list,
        target_roles=[], 
        skill_gap=[]
    )

    org.projects.append(new_project)
    crud_org.update_org(org)

    if new_project in org.projects:
        success = f"Project '{name}' created successfully!"
        msg = urllib.parse.quote(success)
        return RedirectResponse(url=f"/user_home?success={msg}", status_code=status.HTTP_303_SEE_OTHER)
    else:
        error = f"Failed to create project '{name}'."
        msg = urllib.parse.quote(error)
        return RedirectResponse(url=f"/user_home?error={msg}", status_code=status.HTTP_303_SEE_OTHER)
    
### --- View Project GET --- ###
@router.get("/manager/project/{project_id}", response_class=HTMLResponse)
async def view_project(
    request: Request, 
    project_id: str, 
    user: User = Depends(get_current_user),
    error: Optional[str] = Query(None), 
    success: Optional[str] = Query(None),
    warning: Optional[str] = Query(None),
    role_search: Optional[str] = Query(None)
):
    if not user:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    orgname = user.organization
    org = crud_org.get_org_by_orgname(orgname)

    current_project: Optional[Project] = next((p for p in org.projects if str(p.id) == project_id), None)

    if not current_project:
        return RedirectResponse(url="/user_home", status_code=status.HTTP_303_SEE_OTHER)

    team = crud_user.get_users_by_usernames(current_project.assigned_members)

    role_list = None
    if role_search and role_search.strip():
        role_search = role_search.title().strip()
        role_list = escoAPI.get_esco_occupations_list(role_search, language="en", limit=10)

    toast_msg = success or error or warning
    toast_type = "success" if success else ("error" if error else ("warning" if warning else None))

    return templates.TemplateResponse("project_detail.html", {
        "request": request,
        "user": user,
        "org": org,
        "is_manager": True,
        "current_project": current_project,
        "role_list": role_list,
        "role_search": role_search,
        "team": team,
        "countries_list": EU_COUNTRIES,
        "sectors_list": CEDEFOP_SECTORS,
        "recommended_courses": None,
        "forecast_results": None,
        "country": None,
        "sector": None,
        "current_year": datetime.now().year,
        "toast_msg": toast_msg,
        "toast_type": toast_type
    })

### --- Role details for projects --- ###
@router.get("/role_details_for_project", response_class=HTMLResponse)
async def details_page(
    request: Request, 
    uri: str = Query(...),
    project_id: str = Query(...),
    user: User = Depends(get_current_user),
    success: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    warning: Optional[str] = Query(None)
):

    if not user:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    orgname = user.organization
    org = crud_org.get_org_by_orgname(orgname)
    
    current_project: Optional[Project] = next((p for p in org.projects if str(p.id) == project_id), None)
    if not current_project:
            return RedirectResponse(url="/user_home", status_code=status.HTTP_303_SEE_OTHER)

    selected_role = escoAPI.get_single_role_details(uri, language="en")

    if not selected_role:
        return RedirectResponse(url="/user_home", status_code=status.HTTP_303_SEE_OTHER)

    toast_msg = success or warning or error
    toast_type = "success" if success else ("warning" if warning else ("error" if error else None))

    return templates.TemplateResponse("details.html", {
        "request": request,
        "is_user": False,
        "role": selected_role,
        "project_id": project_id,
        "toast_msg": toast_msg,
        "toast_type": toast_type
    })

### --- Project Add Role POST --- ###
@router.post("/add_to_project_target_roles", response_class=RedirectResponse) 
async def project_add_role(
    request: Request,
    project_id: str = Form(...),
    role_id: str = Form(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    essential_skills: Optional[str] = Form(None),
    id_full: str = Form(...),
    uri: str = Form(...),
    user: User = Depends(get_current_user)
):
    if not user: 
        return RedirectResponse(url="/", status_code=303)

    orgname = user.organization
    org = crud_org.get_org_by_orgname(orgname)

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
                return RedirectResponse(url=f"/role_details_for_project?uri={encoded_uri}&error={msg}", status_code=status.HTTP_303_SEE_OTHER)
            
        except (ValueError, SyntaxError) as e:
            msg = urllib.parse.quote(f"Error parsing essential_skills: {essential_skills} - Error: {e}")
            return RedirectResponse(url=f"/role_details_for_project?uri={encoded_uri}&error={msg}", status_code=status.HTTP_303_SEE_OTHER)
    else:
        msg = urllib.parse.quote("No essential skills data provided for this role.")
        return RedirectResponse(url=f"/role_details_for_project?uri={encoded_uri}&warning={msg}", status_code=status.HTTP_303_SEE_OTHER)


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
    toast_type = "error" # Toast Rosso 
    updated_target_role = False
    project_found = False

    for i, project in enumerate(org.projects):
        if str(project.id) == project_id:
            project_found = True
            already_exists = any(r.uri == uri for r in project.target_roles)
            
            if not already_exists:
                project.target_roles.append(role_object)
                
                org.projects[i] = project 
                
                updated_target_role = True
                toast_msg = f"Role '{title}' added to project successfully!"
                toast_type = "success"  # Toast Verde 
            else:
                toast_msg = f"The role '{title}' is already in your target list."
                toast_type = "warning"  # Toast Giallo
            
            break

    if not project_found:
        return RedirectResponse(url="/user_home", status_code=status.HTTP_303_SEE_OTHER)
    
    if updated_target_role:
        crud_org.update_org(org)

    encoded_msg = urllib.parse.quote(toast_msg)
    return RedirectResponse(url=f"/manager/project/{project_id}?{toast_type}={encoded_msg}", status_code=status.HTTP_303_SEE_OTHER)

### --- Delete Target Role from Project --- ###    
@router.post("/delete_project_target_role", response_class=RedirectResponse)
async def delete_project_target_role(
    user: User = Depends(get_current_user),
    uri: str = Form(...),
    project_id: str = Form(...)
):
    if not user:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    orgname = user.organization
    org = crud_org.get_org_by_orgname(orgname)

    role_removed = False
    for project in org.projects:
        if str(project.id) == project_id:
            for role in project.target_roles:
                if role.uri == uri:
                    project.target_roles.remove(role)
                    role_removed = True
                    break

    if role_removed:
        crud_org.update_org(org)

    return RedirectResponse(url=f"/manager/project/{project_id}", status_code=status.HTTP_303_SEE_OTHER)

### --- Add Member to Project POST --- ###
@router.post("/manager/project/{project_id}/add_member", response_class=RedirectResponse)
async def add_member_to_project(
    project_id: str,
    username_to_add: str = Form(...),
    user: User = Depends(get_current_user)
):
    if not user: 
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    orgname = user.organization
    org = crud_org.get_org_by_orgname(orgname)

    project = next((p for p in org.projects if str(p.id) == project_id), None)
    if project is None:
        return RedirectResponse(url="/user_home", status_code=status.HTTP_303_SEE_OTHER)
    
    user_in_org = next((u for u in org.members if u == username_to_add), None)
    if not user_in_org:
        msg = f"User '{username_to_add}' is not a member of your organization."
        type_msg = "warning"
    
    elif username_to_add in project.assigned_members:
        msg = f"User '{username_to_add}' is already assigned to this project."
        type_msg = "warning"
    
    else:
        project.assigned_members.append(username_to_add)
        crud_org.update_org(org)
        msg = f"User '{username_to_add}' added to the project successfully!"
        type_msg = "success"

    encoded_msg = urllib.parse.quote(msg)
    msg_type = "success" if type_msg == "success" else ("warning" if type_msg == "warning" else "error")
    return RedirectResponse(url=f"/manager/project/{project_id}?{msg_type}={encoded_msg}", status_code=status.HTTP_303_SEE_OTHER)

### --- Project Calculate Skill Gap POST --- ###
@router.post("/manager/project/forecast_gap_courses", response_class=HTMLResponse)
async def project_forecast_gap_courses(
    request: Request,
    project_id: str = Form(...),
    user: User = Depends(get_current_user),
    country: str = Form(...),
    sector: Optional[str] = Form(None)
):
    if not user: 
        return RedirectResponse(url="/", status_code=303)

    orgname = user.organization
    org = crud_org.get_org_by_orgname(orgname)

    project_index = next((i for i, p in enumerate(org.projects) if str(p.id) == project_id), None)
    if project_index is None:
        return RedirectResponse(url="/user_home", status_code=status.HTTP_303_SEE_OTHER)
    
    project = org.projects[project_index]

    if len(project.target_roles) > 5:
        msg = urllib.parse.quote("You can analyze up to 5 target roles at a time.")
        return RedirectResponse(url=f"/manager/project/{project_id}?error={msg}", status_code=status.HTTP_303_SEE_OTHER)
    
    db = request.app.state.cedefop

    forecast_results = []
    for role in project.target_roles:
        # String conversion and cleanup
        role_id_str = str(role.id).strip()
            
        # CEDEFOP
        occ_data = cedefop_service.read_emp_occupation(db, country, role_id_str)
        sec_data = cedefop_service.read_emp_sector_occupation(db, country, sector, role_id_str)
        qual_data = cedefop_service.read_qualifications(db, country, role_id_str)
        job_data = cedefop_service.read_job_openings(db, country, role_id_str)

        forecast_results.append({
            "title": role.title,  
            "isco_code": role_id_str,
            "uri": role.uri,
            "occupation_data": occ_data,
            "sector_data": sec_data,
            "qualifications_data": qual_data,
            "job_openings_data": job_data             
        })

    assigned_members = crud_user.get_users_by_usernames(project.assigned_members)
    updated_project = crud_skill_models.skill_gap_project(project, org.members)
    org.projects[project_index] = updated_project
    crud_org.update_org(org)

    # Course recommendation
    all_missing_skills = {}
    for role_gap in updated_project.skill_gap:
        for skill in role_gap.get("missing_skills", []):
            all_missing_skills[skill.uri] = skill.name
        for skill_entry in role_gap.get("partially_matching_skills", []):
            s_obj = skill_entry["skill"]
            all_missing_skills[s_obj.uri] = s_obj.name

    # List of recommended courses for the missing skills
    recommended_courses = recommend_courses_for_skill_gap(all_missing_skills, "manager", user.organization, crud_org.get_all_orgs())

    return templates.TemplateResponse("project_detail.html", {
        "request": request,
        "user": user,
        "org": org,
        "is_manager": True,
        "forecast_results": forecast_results, 
        "recommended_courses": recommended_courses,
        "country": country,
        "sector": sector,
        "countries_list": EU_COUNTRIES,
        "sectors_list": CEDEFOP_SECTORS,
        "current_project": updated_project,
        "team": assigned_members,
        "current_year": datetime.now().year
    })
