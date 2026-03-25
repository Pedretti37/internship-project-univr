from app.crud import crud_org
from app.models import Organization, Course, Skill, Project
from unittest.mock import patch
from datetime import datetime

def test_register_org_success(client):
    form_data = {
        "name": "Università di Verona",
        "orgname": "org_test",
        "password": "a"
    }

    # follow_redirects=False for catching 303 before browser could follow it
    response = client.post("/org_register", data=form_data, follow_redirects=False)

    # Checking if it redirects to login page
    assert response.status_code == 303
    assert response.headers["location"] == "/org_login"

    # Checking if org is in tmp database
    saved_org = crud_org.get_org_by_orgname("org_test")
    assert saved_org is not None
    assert saved_org.name == "Università di Verona"

def test_register_duplicate_orgname(client):
    form_data = {
        "name": "Università di Verona",
        "orgname": "org_test",
        "password": "a"
    }

    # First valid org
    client.post("/org_register", data=form_data, follow_redirects=False)

    # Second org, thus duplicate
    response = client.post("/org_register", data=form_data, follow_redirects=False)

    assert response.status_code == 303
    assert "/org_register?error=" in response.headers["location"]

def test_login_prg_success(client):
    form_data = {
        "name": "Università di Verona",
        "orgname": "org_test",
        "password": "a"
    }

    # First, let's register this org
    client.post("/org_register", data=form_data, follow_redirects=False)

    login_data = {
        "orgname": "org_test",
        "password": "a"
    }

    response = client.post("/org_login", data=login_data, follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/org_home"

    assert "session_token" in response.cookies
    assert response.cookies["session_token"] == "org_test"
    
def test_login_user_error(client):
    form_data = {
        "name": "Università di Verona",
        "orgname": "org_test",
        "password": "a"
    }

    # First, let's register this org
    client.post("/org_register", data=form_data, follow_redirects=False)

    login_data = {
        "orgname": "org_test",
        "password": "b"
    }

    # Wrong password
    response = client.post("/org_login", data=login_data, follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/org_login"

    assert "flash_error" in response.cookies
    assert response.cookies["flash_error"] == '"Invalid credentials. Please try again."'

# Helper
def setup_logged_in_org(client, orgname="techcorp"):
    org = Organization(
        name="TechCorp SPA",
        orgname=orgname,
        hashed_password="password",
        members={},
        projects=[],
        courses=[]
    )
    crud_org.create_organization(org)
    
    client.cookies.set("session_token", orgname) 
    return orgname

def test_org_profile_unauthorized(client):
    # Access to profile without login
    response = client.get("/org_profile", follow_redirects=False)
    
    assert response.status_code == 303
    assert response.headers["location"] == "/"

@patch("app.routers.org.escoAPI.get_esco_skills_list")
def test_org_profile_search_and_edit(mock_esco_api, client):
    orgname = setup_logged_in_org(client)
    
    # Add course to org
    org_in_db = crud_org.get_org_by_orgname(orgname)
    org_in_db.courses.append(Course(id="course_123", title="Basic JAVA", description="..."))
    crud_org.update_org(org_in_db)
    
    # Telling mock what to response
    mock_esco_api.return_value = [Skill(uri="http://java", name="Java Programming", level=0)]
    
    # Route
    response = client.get("/org_profile?skill_search=Java&edit_course_id=corso_123")
    
    # Final check
    assert response.status_code == 200
    mock_esco_api.assert_called_once_with("Java", language="en", limit=10)
    
    html_text = response.text
    assert "Java Programming" in html_text
    assert "Basic JAVA" in html_text

@patch("app.routers.org.recommend_courses_for_skill_gap")
def test_org_profile_analyze_mode(mock_recommend, client):
    orgname = setup_logged_in_org(client)
    
    org_in_db = crud_org.get_org_by_orgname(orgname)

    # Fake project with skill gap
    fake_project = Project(
        name="Project Test",
        description="...",
        manager="boss",
        skill_gap=[
            {
                "missing_skills": [{"uri": "http://python", "name": "Python"}],
                "partially_matching_skills": [{"skill": {"uri": "http://sql", "name": "SQL"}}]
            }
        ],
        created_at="2026-03-24T10:29:21.500756Z"
    )
    org_in_db.projects.append(fake_project)
    crud_org.update_org(org_in_db)
    
    # Recommendation
    mock_recommend.return_value = [{"course_name": "Python", "provider": "TechCorp"}]
    
    # Route
    response = client.get("/org_profile", params={"analyze": True})
    
    # Check
    assert response.status_code == 200
    
    # Called at least once?
    mock_recommend.assert_called_once()
    
    chiamata_args = mock_recommend.call_args[0]
    skills_passate = chiamata_args[0] 
    assert "http://python" in skills_passate
    assert "http://sql" in skills_passate
    
    assert "Python" in response.text

def test_add_course(client):
    orgname = setup_logged_in_org(client, "uni_test")
    
    form_data = {
        "title": "Python Course",
        "description": "Machine Learning and API",
        "category": "IT",
        "ects": "5",
        "cost": "299.99",
        "duration_weeks": "10",
        "is_public": "true", 
        "start_date": "2026-09-01T09:00:00" 
    }
    
    response = client.post("/add_course", data=form_data, follow_redirects=False)
    
    # Check
    assert response.status_code == 303
    assert "/org_profile" in response.headers["location"]
    assert "success=" in response.headers["location"]
    
    # Check DB
    org_in_db = crud_org.get_org_by_orgname(orgname)
    assert len(org_in_db.courses) == 1
    nuovo_corso = org_in_db.courses[0]
    
    assert nuovo_corso.title == "Python Course"
    assert nuovo_corso.cost == 299.99           
    assert nuovo_corso.ects == 5               
    assert nuovo_corso.is_public is True       
    assert isinstance(nuovo_corso.start_date, datetime) 

def test_add_skill_course(client):
    orgname = setup_logged_in_org(client, "uni_test_2")
    
    org_in_db = crud_org.get_org_by_orgname(orgname)
    corso_finto = Course(id="course_999", title="java_course", description="...", category="...")
    org_in_db.courses.append(corso_finto)
    crud_org.update_org(org_in_db)
    
    form_data = {
        "course_id": "course_999",
        "uri": "http://esco/java",
        "name": "Java Programming",
        # await data
        "level_http://esco/java": "4" 
    }
    
    response = client.post("/add_skill_course", data=form_data, follow_redirects=False)
    
    # Check
    assert response.status_code == 303
    location = response.headers["location"]
    assert "course_id=course_999" in location 
    
    # Check DB
    org_aggiornata = crud_org.get_org_by_orgname(orgname)
    corso_aggiornato = next(c for c in org_aggiornata.courses if str(c.id) == "course_999")
    
    assert len(corso_aggiornato.skills_covered) == 1
    assert corso_aggiornato.skills_covered[0].name == "Java Programming"
    assert corso_aggiornato.skills_covered[0].level == 4

def test_delete_course_success(client):
    orgname = setup_logged_in_org(client, "del_org")
    
    org_in_db = crud_org.get_org_by_orgname(orgname)
    org_in_db.courses = [
        Course(id="course_1", title="Python 101", description="...", category="IT"),
        Course(id="course_2", title="Java 101", description="...", category="IT")
    ]
    crud_org.update_org(org_in_db)
    
    # route
    response = client.post("/delete_course/course_1", follow_redirects=False)
    
    # Check
    assert response.status_code == 303
    assert "/org_profile" in response.headers["location"]
    assert "success=" in response.headers["location"]
    
    # Check DB
    org_aggiornata = crud_org.get_org_by_orgname(orgname)
    assert len(org_aggiornata.courses) == 1
    assert str(org_aggiornata.courses[0].id) == "course_2"

