from app.crud import crud_user, crud_org
from app.models import Skill, Role, Organization
from unittest.mock import patch
import os
import json

# Helper function
def setup_logged_in_user(client, username="mario_test"):
    form_data = {
        "name": "Mario",
        "surname": "Rossi",
        "username": username,
        "password": "Password123!"
    }
    client.post("/user_register", data=form_data, follow_redirects=False)
    client.cookies.set("session_token", username)
    return username, form_data

def test_register_user_success(client):
    form_data = {
        "name": "Mario",
        "surname": "Rossi",
        "username": "mario_test",
        "password": "a"
    }

    # follow_redirects=False for catching 303 before browser could follow it
    response = client.post("/user_register", data=form_data, follow_redirects=False)

    # Checking if it redirects to login page
    assert response.status_code == 303
    assert response.headers["location"] == "/user_login"

    # Checking if user is in tmp database
    saved_user = crud_user.get_user_by_username("mario_test")
    assert saved_user is not None
    assert saved_user.name == "Mario"

def test_register_duplicate_username(client):
    form_data = {
        "name": "Mario",
        "surname": "Rossi",
        "username": "mario_test",
        "password": "a"
    }

    # First valid user
    client.post("/user_register", data=form_data, follow_redirects=False)

    # Second user, thus duplicate
    response = client.post("/user_register", data=form_data, follow_redirects=False)

    assert response.status_code == 303
    assert "/user_register?error=" in response.headers["location"]

def test_login_user_success(client):
    form_data = {
        "name": "Mario",
        "surname": "Rossi",
        "username": "mario_test",
        "password": "a"
    }

    # First, let's register this user
    client.post("/user_register", data=form_data, follow_redirects=False)

    login_data = {
        "username": "mario_test",
        "password": "a"
    }

    response = client.post("/user_login", data=login_data, follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/user_home"

    assert "session_token" in response.cookies
    assert response.cookies["session_token"] == "mario_test"
    
def test_login_user_error(client):
    form_data = {
        "name": "Mario",
        "surname": "Rossi",
        "username": "mario_test",
        "password": "a"
    }

    # First, let's register this user
    client.post("/user_register", data=form_data, follow_redirects=False)

    login_data = {
        "username": "mario_test",
        "password": "b"
    }

    # Wrong password
    response = client.post("/user_login", data=login_data, follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/user_login"

    assert "flash_error" in response.cookies
    assert response.cookies["flash_error"] == '"Invalid credentials. Please try again."'

def test_logout(client):
    # Already logged in user
    client.cookies.set("session_token", "mario_test_loggato")
    
    response = client.get("/user_logout", follow_redirects=False)
    
    assert response.status_code == 303
    assert response.headers["location"] == "/"
    
    cookie_value = response.cookies.get("session_token", "").strip('"')
    assert cookie_value == ""

def test_user_home_unauthorized(client):
    # without login
    response = client.get("/user_home", follow_redirects=False)
    
    assert response.status_code == 303
    assert response.headers["location"] == "/"

def test_user_profile_filters_invitations_correctly(client):
    username, _ = setup_logged_in_user(client)
    
    invite_1 = {
        "id": "123",
        "orgname": "ORG_1",
        "username": username,  
        "status": "pending",
        "created_at": "2026-03-24T10:29:21.500756Z"
    }
    
    invite_2 = {
        "id": "456",
        "orgname": "ORG_2",
        "username": "luigi_test",  # Another user
        "status": "pending",
        "created_at": "2026-03-24T10:29:21.500756Z"
    }
    
    # writing on fake DB
    with open(os.path.join(crud_user.DATA_INV_DIR, "123.json"), "w") as f:
        json.dump(invite_1, f)
        
    with open(os.path.join(crud_user.DATA_INV_DIR, "456.json"), "w") as f:
        json.dump(invite_2, f)
        
    response = client.get("/user_profile")
    
    assert response.status_code == 200
    assert "ORG_1" in response.text
    assert "ORG_2" not in response.text

def test_add_to_user_target_roles(client):
    username, _ = setup_logged_in_user(client)
    
    fake_skills_str = str([{"uri": "http://skill_1", "name": "Python"}])
    
    # From HTTP
    form_data = {
        "role_search": "Developer",
        "role_id": "isco_123",
        "title": "Software Engineer",
        "description": "...",
        "id_full": "123.4",
        "uri": "http://role_1",
        "essential_skills": fake_skills_str,
        # adding await data
        "level_http://skill_1": "4" 
    }

    response = client.post("/add_to_user_target_roles", data=form_data, follow_redirects=False)
    
    assert response.status_code == 303
    
    location = response.headers["location"]
    assert "/details?uri=" in location
    assert "role_search=Developer" in location
    assert "success=" in location
    
    # Checking database
    user_in_db = crud_user.get_user_by_username(username)
    assert len(user_in_db.target_roles) == 1
    assert user_in_db.target_roles[0].title == "Software Engineer"
    assert user_in_db.target_roles[0].essential_skills[0].level == 4

def test_add_to_user_skills(client):
    username, _ = setup_logged_in_user(client, "luigi_test")
    
    fake_skills_str = str([
        {"uri": "http://skill_A", "name": "Java"},
        {"uri": "http://skill_B", "name": "SQL"}
    ])
    
    form_data = {
        "uri": "http://role_xyz",
        "role_search": "Backend",
        "essential_skills": fake_skills_str,
        # adding await data
        "level_http://skill_A": "5",
        "level_http://skill_B": "3"
    }

    response = client.post("/add_to_user_skills", data=form_data, follow_redirects=False)
    
    assert response.status_code == 303
    assert "success=" in response.headers["location"]
    
    # Check DB
    user_in_db = crud_user.get_user_by_username(username)
    assert len(user_in_db.individual_skills) == 2
    
    # check for level
    java_skill = next(s for s in user_in_db.individual_skills if s.name == "Java")
    assert java_skill.level == 5

def test_add_single_skill(client):
    username, _ = setup_logged_in_user(client, "giulia_test")
    
    form_data = {
        "uri": "http://skill_single",
        "name": "Project Management",
        "skill_search": "Manager",
        # await data
        "level_http://skill_single": "4"
    }

    response = client.post("/add_single_skill", data=form_data, follow_redirects=False)
    
    assert response.status_code == 303
    location = response.headers["location"]
    assert "/user_home?" in location
    assert "skill_search=Manager" in location
    assert "success=" in location
    
    # Check DB
    user_in_db = crud_user.get_user_by_username(username)
    assert len(user_in_db.individual_skills) == 1
    assert user_in_db.individual_skills[0].name == "Project Management"
    assert user_in_db.individual_skills[0].level == 4

def test_upload_skills_csv_invalid_file(client):
    _, _ = setup_logged_in_user(client)
    
    # b for byte
    fake_file = {"file": ("prova.txt", b"testo a caso", "text/plain")}
    
    response = client.post("/upload_skills_csv", files=fake_file, follow_redirects=False)
    
    assert response.status_code == 303
    assert "error=" in response.headers["location"]

@patch("app.routers.user.escoAPI.get_esco_skills_list")
def test_upload_skills_csv_success(mock_esco_api, client):
    _, _ = setup_logged_in_user(client)
    
    csv_content = b"skill_name,level\nPython,5\nfakeSkill,3\n"
    fake_file = {"file": ("skills.csv", csv_content, "text/csv")}
    
    def mock_api_behavior(skill_name, **kwargs):
        if skill_name == "Python":
            return [Skill(uri="http://esco/python", name="Python Programming", level=0)]
        return [] # No result for fakeSkill
        
    mock_esco_api.side_effect = mock_api_behavior
    
    response = client.post("/upload_skills_csv", files=fake_file)
    
    assert response.status_code == 200 
    assert mock_esco_api.call_count == 2
    
    assert "Python Programming" in response.text
    assert "fakeSkill" in response.text 

def test_confirm_skills_csv(client):
    username, _ = setup_logged_in_user(client)
    
    form_data = {
        "total_rows": "2",
        # Skill to save
        "uri_name_1": "http://esco/java|||Java Developer", 
        "level_1": "4",
        # Skill to skip
        "uri_name_2": "SKIP",
        "level_2": "7"
    }
    
    response = client.post("/confirm_skills_csv", data=form_data, follow_redirects=False)
    
    assert response.status_code == 303
    assert response.headers["location"] == "/user_profile"
    
    user_in_db = crud_user.get_user_by_username(username)
    assert len(user_in_db.individual_skills) == 1
    assert user_in_db.individual_skills[0].name == "Java Developer"
    assert user_in_db.individual_skills[0].uri == "http://esco/java"
    assert user_in_db.individual_skills[0].level == 4

def test_forecast_gap_courses_too_many_roles(client):
    username, _ = setup_logged_in_user(client, "too_many_test")
    user_in_db = crud_user.get_user_by_username(username)
    
    # 6 target roles
    for i in range(6):
        user_in_db.target_roles.append(Role(id=str(i), title=f"Role {i}", uri=f"http://role/{i}"))
    crud_user.update_user(user_in_db)
    
    form_data = {"country": "Italy", "sector": "ICT"}
    response = client.post("/forecast_gap_courses", data=form_data, follow_redirects=False)
    
    assert response.status_code == 303
    assert "error=" in response.headers["location"]
    assert "up to 5" in response.headers["location"].replace("%20", " ")

def test_create_project_post(client):
    username, _ = setup_logged_in_user(client, "manager_test")
    
    user = crud_user.get_user_by_username(username)
    user.organization = "a"
    crud_user.update_user(user)
    
    org = Organization(name="TechCorp", orgname="a", hashed_password="fake_password", members={username: [], "dev_luigi": []})
    crud_org.create_organization(org)
    
    form_data = {
        "name": "Project_1",
        "description": "...",
        "members_list": ["dev_luigi", username] 
    }
    
    response = client.post("/manager/create_project", data=form_data, follow_redirects=False)

    assert response.status_code == 303
    location = response.headers["location"]
    assert "/user_home" in location
    assert "success=" in location 
    
    # Check database
    org_in_db = crud_org.get_org_by_orgname(org.orgname)
    
    assert len(org_in_db.projects) == 1
    project = org_in_db.projects[0]
    
    assert project.name == "Project_1"
    assert project.manager == username
    assert "dev_luigi" in project.assigned_members
    assert len(project.assigned_members) == 2
    