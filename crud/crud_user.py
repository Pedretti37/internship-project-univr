import json
import os
from models import User

DATA_DIR_USERS = "data/users"
os.makedirs(DATA_DIR_USERS, exist_ok=True)

### --- User CRUD operations --- ###
def get_json_path(username: str) -> str:
    safe_name = username.lower().strip()
    return os.path.join(DATA_DIR_USERS, f"{safe_name}.json")

def get_user(username: str) -> User | None:
    path = get_json_path(username)
    if not os.path.exists(path):
        return None
    
    with open(path, "r") as f:
        data = json.load(f)
        return User(**data)
    
def create_user(user: User):
    path = get_json_path(user.username)
    if os.path.exists(path):
        raise ValueError("User already exists")
    
    with open(path, "w") as f:
        json.dump(user.model_dump(), f, indent=4) # model_dump() transforms the Pydantic model to a dict for JSON file

def change_password_user(user: User, new_pw: str) -> bool:
    path = get_json_path(user.username)
    
    if not os.path.exists(path):
        return False
    
    try:
        with open(path, "r") as f:
            data = json.load(f)

        data["hashed_password"] = new_pw

        with open(path, "w") as f:
            json.dump(data, f, indent=4)
        
        return True

    except Exception as e:
        return False

### --- Update User Profile --- ###
def update_user(user: User):
    path = get_json_path(user.username)
    
    if not os.path.exists(path):
        return

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(user.model_dump(), f, indent=4)
    except Exception as e:
        print(f"Error updating user: {e}")
