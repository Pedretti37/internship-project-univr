import json
import os
import pandas as pd
from models import User

FILE_INPUT = "data/ISCO-08 EN Structure and definitions.xlsx"

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

def extracting_target_roles(user_inputs: list[str]) -> dict[str, str]:
    if not user_inputs:
        return {}

    try:
        df = pd.read_excel(FILE_INPUT, usecols="B,C")
        
        col_id = df.columns[0]
        col_title = df.columns[1]
        
        found_roles = {}

        for role_input in user_inputs:
            # Filtering excel file
            mask = df[col_title].astype(str).str.contains(role_input, case=False, na=False)
            
            matches = df.loc[mask]
            
            for _, row in matches.iterrows():
                role_id = str(row[col_id]) 
                role_title = row[col_title]
                
                found_roles[role_id] = role_title

        return found_roles

    except Exception as e:
        print(f"Error extracting roles: {e}")
        return {}
    
def delete_role_from_user(user: User, role_id_to_delete: str):
    path = get_json_path(user.username)
    
    if not os.path.exists(path):
        return

    if user.target_roles:
        user.target_roles.pop(role_id_to_delete, None)

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        if "target_roles" in data and isinstance(data["target_roles"], dict):
            if role_id_to_delete in data["target_roles"]:
                del data["target_roles"][role_id_to_delete]

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    except Exception as e:
        print(f"Errore durante l'eliminazione del ruolo: {e}")
