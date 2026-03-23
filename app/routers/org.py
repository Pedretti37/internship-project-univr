import codecs
import csv
from fastapi import APIRouter, File, Query, Request, Form, UploadFile, status, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Optional
import urllib
from app.crud import crud_user, crud_org
from app.service.dependencies import get_current_org
from app.esco import escoAPI 
from datetime import datetime
from app.service.config import templates, pwd_context
from app.models import Organization, Project, Skill, Course, UserLevel
from pydantic import ValidationError
from app.educational_offerings.courses_recommendation import recommend_courses_for_skill_gap

router = APIRouter()

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
async def logout():
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    # Delete current session
    response.set_cookie(key="session_token", value="", path="/", httponly=True, max_age=0)
    return response

### --- Organization Home --- ###
@router.get("/org_home", response_class=HTMLResponse)
async def org_home(
    request: Request, 
    org: Organization = Depends(get_current_org)
):

    if not org:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    return templates.TemplateResponse("org/org_home.html", {
        "request": request, 
        "org": org,
        "projects": org.projects
    })

### --- Organization Registration GET --- ###
@router.get("/org_register", response_class=HTMLResponse)
async def org_register(request: Request):
    return templates.TemplateResponse("org/org_register.html", {"request": request})

### --- Organization Registration POST --- ###
@router.post("/org_register", response_class=HTMLResponse)
async def register_org(
    request: Request, 
    name: str = Form(...),
    orgname: str = Form(...),
    password: str = Form(...)
):
    hashed_pw = pwd_context.hash(password)
    new_org = Organization(name=name, orgname=orgname, hashed_password=hashed_pw)
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
async def org_profile(
    request: Request, 
    org: Organization = Depends(get_current_org),
    course_id: Optional[str] = Query(None),
    skill_search: Optional[str] = Query(None),
    analyze: Optional[bool] = Query(False),
    edit_course_id: Optional[str] = Query(None),
    success: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    warning: Optional[str] = Query(None)
):
    if not org:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    global_gap = {}
    hr_recommendations = []

    if analyze:
        for project in org.projects:
            gaps = project.get("skill_gap", []) if isinstance(project, dict) else project.skill_gap
            for gap_entry in gaps:
                missing = gap_entry.get("missing_skills", [])
                partial = [p["skill"] for p in gap_entry.get("partially_matching_skills", [])]
                all_needed = missing + partial
                
                for skill in all_needed:
                    uri = skill["uri"] if isinstance(skill, dict) else skill.uri
                    name = skill["name"] if isinstance(skill, dict) else skill.name
                    if uri not in global_gap:
                        global_gap[uri] = {"name": name, "count": 0}
                    global_gap[uri]["count"] += 1

        # Sorting for count
        global_gap = dict(sorted(global_gap.items(), key=lambda item: item[1]['count'], reverse=True))

        # Recommendation for orgs
        if global_gap:
            skills_to_recommend = {uri: data["name"] for uri, data in global_gap.items()}
            all_orgs = crud_org.get_all_orgs()
            hr_recommendations = recommend_courses_for_skill_gap(
                skills_to_recommend, "hr", org.orgname, all_orgs
            )

    # Keeping research with ESCO API
    skill_list = None

    if skill_search and skill_search.strip():
        skill_search = skill_search.title().strip()
        skill_list = escoAPI.get_esco_skills_list(skill_search, language="en", limit=10)

    # If course to edit
    course_to_edit = None
    if edit_course_id:
        for c in org.courses:
            if str(c.id) == edit_course_id:
                course_to_edit = c
                break

    toast_msg = success or error or warning
    toast_type = "success" if success else ("error" if error else ("warning" if warning else None))

    return templates.TemplateResponse("org/org_profile.html", {
        "request": request, 
        "org": org,
        "members": crud_user.get_users_by_usernames(org.members.keys()),
        "available_users": crud_user.get_all_users(),
        "skill_list": skill_list,
        "skill_search": skill_search,
        "active_course_id": course_id,
        "global_gap": global_gap,
        "hr_recommendations": hr_recommendations,
        "analysis_active": analyze,
        "course_to_edit": course_to_edit,
        "toast_msg": toast_msg,
        "toast_type": toast_type
    })

### --- Password Change --- ###
@router.post("/change_password_org", response_class=RedirectResponse)
async def change_password(
    org: Organization = Depends(get_current_org), 
    old_pw: str = Form(...), 
    new_pw: str = Form(...)
):
    if not org:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    if not pwd_context.verify(old_pw, org.hashed_password):
        warning = "Your old password is not correct."
        msg = urllib.parse.quote(warning)
        return RedirectResponse(url=f"/org_profile?warning={msg}", status_code=status.HTTP_303_SEE_OTHER)
    
    new_pw_hashed = pwd_context.hash(new_pw)
    success = crud_org.change_password_org(org, new_pw_hashed) # Updates org too

    if success:
        msg = urllib.parse.quote("Password updated successfully!")
        toast_type = "success"
    else:
        msg = urllib.parse.quote("Failed to update your password.")
        toast_type = "error"
    return RedirectResponse(url=f"/org_profile?{toast_type}={msg}", status_code=status.HTTP_303_SEE_OTHER)
    
### --- Invite Member --- ###
@router.post("/invite_member", response_class=RedirectResponse)
async def invite_member(
    org: Organization = Depends(get_current_org), 
    username_to_invite: str = Form(...)
):
    if not org:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    msg = None

    members = org.members
    invited = False
    user_to_invite = crud_user.get_user_by_username(username_to_invite)

    if not user_to_invite:
        msg = "User not found."
        type = "error"
    elif user_to_invite.username in members:
        msg = "This user is already in your team."
        type = "warning"
    else:
        invited = crud_org.create_invitation(org.orgname, user_to_invite.username)
        if invited:
            msg = f"Invitation sent to '{username_to_invite}' successfully!"
            type = "success"
        else:
            msg = "Failed to send invitation. Please try again."
            type = "error"

    return RedirectResponse(url=f"/org_profile?{type}={urllib.parse.quote(msg)}", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/update_user_level", response_class=RedirectResponse)
async def update_user_level(
    target_username: str = Form(...),
    new_level: str = Form(...), 
    org: Organization = Depends(get_current_org)
):
    if not org:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    if target_username not in org.members:
        msg = urllib.parse.quote("This user is not in your organization")
        return RedirectResponse(url=f"/org_profile?error={msg}", status_code=status.HTTP_303_SEE_OTHER)

    user = crud_user.get_user_by_username(target_username)
    if not user:
        msg = urllib.parse.quote("This user is not in your organization")
        return RedirectResponse(url=f"/org_profile?error={msg}", status_code=status.HTTP_303_SEE_OTHER)

    user.level = UserLevel(new_level) 
    
    crud_user.update_user(user)

    if new_level == 'manager':
        msg = urllib.parse.quote(f"{user.name} {user.surname} promoted to Manager!")
    else:
        msg = urllib.parse.quote(f"{user.name} {user.surname} demoted from Manager.")

    return RedirectResponse(url=f"/org_profile?success={msg}", status_code=status.HTTP_303_SEE_OTHER)

### --- View Project GET --- ###
@router.get("/org/project/{project_id}", response_class=HTMLResponse)
async def view_project(
    request: Request, 
    project_id: str, 
    org: Organization = Depends(get_current_org),
    error: Optional[str] = Query(None), 
    success: Optional[str] = Query(None),
    warning: Optional[str] = Query(None),
    role_search: Optional[str] = Query(None)
):
    if not org:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    current_project: Optional[Project] = next((p for p in org.projects if str(p.id) == project_id), None)

    if not current_project:
        return RedirectResponse(url="/org_home", status_code=status.HTTP_303_SEE_OTHER)

    team = crud_user.get_users_by_usernames(current_project.assigned_members)

    role_list = None
    if role_search and role_search.strip():
        role_search = role_search.title().strip()
        role_list = escoAPI.get_esco_occupations_list(role_search, language="en", limit=10)

    toast_msg = success or error or warning
    toast_type = "success" if success else ("error" if error else ("warning" if warning else None))

    return templates.TemplateResponse("project_detail.html", {
        "request": request,
        "org": org,
        "is_manager": False,
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

### --- Upload Skills CSV for Organization --- ###
@router.post("/upload_employee_skills_csv", response_class=HTMLResponse)
async def upload_employee_skills_csv(
    request: Request,
    file: UploadFile = File(...),
    org: Organization = Depends(get_current_org)
):
    if not org:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    if not file.filename.lower().endswith('.csv'):
        msg = urllib.parse.quote("Invalid file type. Please upload a CSV file.")
        return RedirectResponse(url=f"/org_home?error={msg}", status_code=status.HTTP_303_SEE_OTHER)
    
    await file.seek(0)

    csvReader = csv.DictReader(codecs.iterdecode(file.file, 'utf-8'))
    
    skills_to_review = []
    skills_not_found = []
    known_users = {}

    invitated = []
    not_found = []

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
                    invitated.append(username)
            else:
                known_users[username] = False
                not_found.append(username)

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

    msg = "CSV processed successfully."
    msg_type = "success"

    # MSG for warnings
    warnings = []
    if invitated:
        warnings.append(f"Invited: {', '.join(invitated)}")
    if not_found:
        warnings.append(f"Not found in DB: {', '.join(not_found)}")

    if warnings:
        msg = " | ".join(warnings)
        msg_type = "warning" if invitated else "error"

    if not skills_to_review and (invitated or not_found):
        query_params = f"warning={urllib.parse.quote(msg)}"
        return RedirectResponse(url=f"/org_profile?{query_params}", status_code=303)

    return templates.TemplateResponse("org/review_employee_skills.html", {
        "request": request,
        "org": org,
        "skills_to_review": skills_to_review,
        "skills_not_found": skills_not_found,
        "toast_msg": msg,
        "toast_type": msg_type
    })

@router.post("/org/confirm_employee_skills", response_class=RedirectResponse)
async def confirm_employee_skills(
    request: Request,
    org: Organization = Depends(get_current_org)
):
    if not org:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    form_data = await request.form()
    total_rows_str = form_data.get("total_rows")
    
    if not total_rows_str:
        return RedirectResponse(url="/org_profile", status_code=status.HTTP_303_SEE_OTHER)

    total_rows = int(total_rows_str)
    
    if org.members is None: org.members = {}
    if org.pending_members is None: org.pending_members = {}

    total_rows = int(total_rows_str)
    updates: dict[str, list[Skill]] = {}
    
    for i in range(1, total_rows + 1):
        username = form_data.get(f"username_{i}")
        uri_and_name = form_data.get(f"uri_name_{i}")
        level_str = form_data.get(f"level_{i}")
        
        if not username or not uri_and_name or uri_and_name == "SKIP":
            continue
            
        parts = uri_and_name.split("|||")
        if len(parts) != 2: continue

        skill_obj = Skill(uri=parts[0], name=parts[1], level=int(level_str))
        
        if username not in updates:
            updates[username] = []
        updates[username].append(skill_obj)

    for username, new_skills in updates.items():
        if username in org.members:
            org.members[username] = new_skills
            
            if username in org.pending_members:
                del org.pending_members[username]
        else:
            org.pending_members[username] = new_skills
            
            if username in org.members:
                del org.members[username]

    crud_org.update_org(org)

    msg = urllib.parse.quote("Skills processed successfully.")
    return RedirectResponse(url=f"/org_profile?success={msg}", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/org_global_gap")
async def org_global_gap():
    return RedirectResponse(url="/org_profile?analyze=true", status_code=status.HTTP_303_SEE_OTHER)

### --- Create Course --- ###
@router.post("/add_course", response_class=RedirectResponse)
async def add_course(
    title: str = Form(...),
    description: str = Form(...),
    category: str = Form(...),
    moi: Optional[str] = Form(None),
    ects: Optional[int] = Form(None),
    format: Optional[str] = Form(None),
    start_date: Optional[datetime] = Form(None),
    duration_weeks: Optional[int] = Form(0),
    cost: Optional[float] = Form(0.0),
    link: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    is_public: bool = Form(False), 
    
    org: Organization = Depends(get_current_org)
):
    if not org:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    new_course = Course(
        title=title,
        description=description,
        category=category,
        medium_of_instruction=moi,
        ects=ects,
        format=format,
        start_date=start_date,
        duration_weeks=duration_weeks,
        cost=cost,
        link=link,
        location=location,
        is_public=is_public,
        skills_covered=[] # Added later on!
    )

    # List creation if not present
    if not hasattr(org, 'courses') or org.courses is None:
        org.courses = []

    org.courses.append(new_course)
    crud_org.update_org(org)

    msg = urllib.parse.quote("Course created successfully! Now you can add skills.")
    return RedirectResponse(url=f"/org_profile?success={msg}", status_code=status.HTTP_303_SEE_OTHER)

### --- TOGGLE VISIBILITY (Give/Revoke Access) --- ###
@router.post("/toggle_course_visibility/{course_id}")
async def toggle_course_visibility(
    course_id: str, 
    org: Organization = Depends(get_current_org)
):
    if not org:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    for course in org.courses:
        if str(course.id) == course_id:
            # Switch state of visibility
            course.is_public = not course.is_public
            crud_org.update_org(org)
            status_msg = "public" if course.is_public else "private"
            return RedirectResponse(
                url=f"/org_profile?success=Course+is+now+{status_msg}", 
                status_code=status.HTTP_303_SEE_OTHER
            )
            
    return RedirectResponse(url="/org_profile?error=Course+not+found", status_code=status.HTTP_303_SEE_OTHER)

### --- Delete course --- ###
@router.post("/delete_course/{course_id}")
async def delete_course(
    course_id: str, 
    org: Organization = Depends(get_current_org)
):
    if not org:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    original_count = len(org.courses)
    org.courses = [c for c in org.courses if str(c.id) != course_id]
    
    if len(org.courses) < original_count:
        crud_org.update_org(org)
        return RedirectResponse(url="/org_profile?success=Course+deleted+successfully", status_code=status.HTTP_303_SEE_OTHER)
        
    return RedirectResponse(url="/org_profile?error=Course+not+found", status_code=status.HTTP_303_SEE_OTHER)

### --- Update course --- ###
@router.post("/edit_course/{course_id}")
async def edit_course(
    course_id: str,
    title: str = Form(...),
    description: str = Form(...),
    category: str = Form(...),
    format: Optional[str] = Form(None),
    cost: Optional[float] = Form(0.0),
    location: Optional[str] = Form(None),
    link: Optional[str] = Form(None),
    moi: Optional[str] = Form(None),
    org: Organization = Depends(get_current_org)
):
    if not org:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
        
    for course in org.courses:
        if str(course.id) == course_id:
            course.title = title
            course.description = description
            course.category = category
            course.format = format
            course.cost = cost
            course.location = location
            course.link = link
            course.medium_of_instruction = moi
            
            crud_org.update_org(org)
            return RedirectResponse(url="/org_profile?success=Course+updated+successfully", status_code=status.HTTP_303_SEE_OTHER)

    return RedirectResponse(url="/org_profile?error=Course+not+found", status_code=status.HTTP_303_SEE_OTHER)

### --- Add skills to course --- ###
@router.post("/add_skill_course", response_class=RedirectResponse)
async def add_skill_course(
    request: Request,
    course_id: str = Form(...),
    uri: str = Form(...),
    name: str = Form(...),
    skill_search: Optional[str] = Form(None),
    org: Organization = Depends(get_current_org)
):
    if not org:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    form_data = await request.form()
    selected_level = form_data.get(f"level_{uri}")

    search_query = ""
    if skill_search:
        search_query = f"&skill_search={urllib.parse.quote(skill_search)}&"

    if not selected_level:
        msg = urllib.parse.quote("Please select a level first.")
        return RedirectResponse(url=f"/org_profile?{search_query}warning={msg}", status_code=status.HTTP_303_SEE_OTHER)

    level = int(selected_level)

    target_course = next((c for c in org.courses if str(c.id) == course_id), None)
    
    if not target_course:
        msg = urllib.parse.quote("Course not found.")
        return RedirectResponse(url=f"/org_profile?error={msg}", status_code=status.HTTP_303_SEE_OTHER)

    try:
        new_skill = Skill(uri=uri, name=name, level=level)
    except ValidationError as e:
        msg = urllib.parse.quote("Invalid skill data.")
        return RedirectResponse(url=f"/org_profile?course_id={course_id}&error={msg}", status_code=status.HTTP_303_SEE_OTHER)

    existing_skill = next((s for s in target_course.skills_covered if s.uri == uri), None)
    
    if existing_skill:
        existing_skill.level = level
        msg = urllib.parse.quote(f"Skill '{name}' updated to level {level}.")
    else:
        target_course.skills_covered.append(new_skill)
        msg = urllib.parse.quote(f"Skill '{name}' added successfully to the course.")

    crud_org.update_org(org)

    redirect_url = f"/org_profile?course_id={course_id}&success={msg}"
    
    if skill_search:
        redirect_url += f"&skill_search={urllib.parse.quote(skill_search)}"

    return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)