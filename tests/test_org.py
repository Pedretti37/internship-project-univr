from app.crud import crud_org

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

