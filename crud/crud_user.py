import json
import os
from models import User

DATA_DIR_USERS = "data/users"
os.makedirs(DATA_DIR_USERS, exist_ok=True)

INDEX_FILE = "data/users/user_index.json"
os.makedirs(os.path.dirname(INDEX_FILE), exist_ok=True)

### --- User GET path --- ###
def get_json_path(id: str) -> str:
    return os.path.join(DATA_DIR_USERS, f"{id}.json")

### --- Create User --- ###    
def create_user(user: User):
    index = _load_index()
    if user.username in index:
        raise ValueError("Username already exists")

    file_path = os.path.join(DATA_DIR_USERS, f"{user.id}.json")
    with open(file_path, "w") as f:
        f.write(json.dumps(user.model_dump(), indent=4))

    index[user.username] = user.id
    _save_index(index)
    
    return user

### --- Change Password --- ###
def change_password_user(user: User, new_pw: str) -> bool:
    path = get_json_path(user.id)
    
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
    path = get_json_path(user.id)
    
    if not os.path.exists(path):
        return

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(user.model_dump(), f, indent=4)
    except Exception as e:
        print(f"Error updating user: {e}")

### --- Users Index Management --- ###
def _load_index():
    if not os.path.exists(INDEX_FILE):
        return {}
    with open(INDEX_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def _save_index(index_data):
    with open(INDEX_FILE, "w") as f:
        json.dump(index_data, f, indent=4)

# --- Get USER --- #
def get_user_by_id(user_id: str) -> User | None:
    """Recupera l'utente direttamente tramite ID (veloce)"""
    path = os.path.join(DATA_DIR_USERS, f"{user_id}.json")
    if not os.path.exists(path):
        return None
    
    with open(path, "r") as f:
        data = json.load(f)
        return User(**data)

def get_users_by_ids(user_ids: list[str]) -> list[User]:
    found_users = []
    for uid in user_ids:
        user = get_user_by_id(uid)
        if user:
            found_users.append(user)
    return found_users

def get_user_by_username(username: str) -> User | None:
    """
    Recupera l'utente tramite Username.
    Usa l'indice per trovare l'ID corrispondente.
    """
    index = _load_index()
    
    # Cerchiamo l'ID associato allo username
    user_id = index.get(username)
    
    if not user_id:
        return None # Utente non trovato nell'indice
        
    # Ora che abbiamo l'ID, carichiamo il file vero
    return get_user_by_id(user_id)