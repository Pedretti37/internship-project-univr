from app.crud import crud_user

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