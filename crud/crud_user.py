import json
import os

from pydantic_core import ValidationError
from models import User, Invitation

DATA_DIR_USERS = "data/users"
os.makedirs(DATA_DIR_USERS, exist_ok=True)

DATA_INV_DIR = "data/invitations"

### --- User GET path --- ###
def get_json_path(username: str) -> str:
    return os.path.join(DATA_DIR_USERS, f"{username}.json")

### --- Create User --- ###    
def create_user(user: User):
    if os.path.exists(get_json_path(user.username)):
        raise ValueError("Username already exists")

    file_path = os.path.join(DATA_DIR_USERS, f"{user.username}.json")
    with open(file_path, "w") as f:
        f.write(json.dumps(user.model_dump(), indent=4))

    return user

### --- Change Password --- ###
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

### --- Get USER --- ###
def get_user_by_username(username: str) -> User | None:
    """Recupera l'utente direttamente tramite Username (veloce)"""
    path = os.path.join(DATA_DIR_USERS, f"{username}.json")
    if not os.path.exists(path):
        return None
    
    with open(path, "r") as f:
        data = json.load(f)
        return User(**data)

def get_users_by_usernames(usernames_list: list[str]) -> list[User]:
    found_users = []
    for username in usernames_list:
        try:
            user = get_user_by_username(username)
            
            if user is not None:
                found_users.append(user)
            else:
                print(f"File fisico mancante per {username}")
                
        except ValueError as e:
            print(f"❌ Errore di validazione per l'utente {username}: {e}")
            continue
            
    return found_users

### --- Get Pending Invitations for User --- ###
def get_pending_invitations_for_user(username: str) -> list[Invitation]:
    invitations = []
    
    if not os.path.exists(DATA_INV_DIR):
        return invitations
    
    for filename in os.listdir(DATA_INV_DIR):
        if filename.endswith(".json"):
            path = os.path.join(DATA_INV_DIR, filename)
            
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                    if data.get("username") == username and data.get("status") == "pending":
                        invitation_obj = Invitation(**data) 
                        invitations.append(invitation_obj)
                        
            except (json.JSONDecodeError, ValidationError) as e:
                print(f"Errore nella lettura del file {filename}: {e}")
                continue
                
    return invitations