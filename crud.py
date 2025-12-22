import json
import os
import pandas as pd
from models import User, Organization, Role

DATA_DIR_USERS = "data/users"
os.makedirs(DATA_DIR_USERS, exist_ok=True)

DATA_DIR_ORGS = "data/organizations"
os.makedirs(DATA_DIR_ORGS, exist_ok=True)

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

def set_target_roles_user(user: User, target_roles: list[str]):
    path = get_json_path(user.username)
    if not os.path.exists(path):
        return None
    
    matched_roles = extracting_target_roles(target_roles)
    user.target_roles = matched_roles

    with open(path, "r") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = {} # Managing empty file

    data["target_roles"] = matched_roles

    with open(path, "w") as f:
        json.dump(data, f, indent=4)

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
    

### --- Organization CRUD operations --- ###
def get_json_path_org(orgname: str) -> str:
    safe_name = orgname.lower().strip()
    return os.path.join(DATA_DIR_ORGS, f"{safe_name}.json")

def get_organization(orgname: str) -> Organization | None:
    path = get_json_path_org(orgname)
    if not os.path.exists(path):
        return None
    
    with open(path, "r") as f:
        data = json.load(f)
        return Organization(**data)

def create_organization(org: Organization):
    path = get_json_path_org(org.orgname)
    if os.path.exists(path):
        raise ValueError("Organization already exists")
    
    with open(path, "w") as f:
        json.dump(org.model_dump(), f, indent=4) # model_dump() transforms the Pydantic model to a dict for JSON file

def change_password_org(org: Organization, new_pw: str) -> bool:
    path = get_json_path_org(org.orgname)
    
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

### --- Extract skill models by user input --- ###
def extracting_skill_models(user_query: str) -> list[Role] | None:
    # reading Excel file, only columns B (id), C (title), D (definition), E (task)
    try: 
        df = pd.read_excel("data/ISCO-08 EN Structure and definitions.xlsx", usecols="B,C,D,E", dtype=str)
        
        df.columns = ["id", "title", "definition", "task"]
        df = df.fillna("") # managing empty strings


        # filtering rows, converting to string, case insensitive search
        filter = df["title"].astype(str).str.contains(user_query, case=False, na=False)
        results = df[filter]

        if results.empty:
            return None
        
        roles_list = []

        for _, row in results.iterrows():
            new_role = Role(
                id=row["id"],
                title=row["title"],
                definition=row["definition"],
                task=row["task"]
            )
            roles_list.append(new_role)
        return roles_list
    
    except Exception as e:
        print(f"Error extracting skill models: {e}")
        return None

### --- Extract target roles for user profile --- ###
def extracting_target_roles(user_inputs: list[str]) -> list[str]:
    excel_path = "data/ISCO-08 EN Structure and definitions.xlsx"
    
    if not user_inputs:
        return []

    try:
        df = pd.read_excel(excel_path, usecols="C")
        col_title = df.columns[0]
        
        all_found_roles = []

        for role_input in user_inputs:
            # na=False avoiding errors caused by empty cells in Excel
            filter_mask = df[col_title].astype(str).str.contains(role_input, case=False, na=False)
            
            matches = df.loc[filter_mask, col_title].tolist()
            all_found_roles.extend(matches)

        unique_roles = sorted(list(set(all_found_roles)))
        
        return unique_roles

    except Exception as e:
        print(f"Error extracting skills: {e}")
        return []
    
def get_role_by_id(target_id: str) -> Role | None:
    try:
        
        df = pd.read_excel(
            "data/ISCO-08 EN Structure and definitions.xlsx", 
            usecols="B,C,D,E", 
            dtype=str
        )
        df.columns = ["id", "title", "definition", "task"]
        df = df.fillna("")

        match = df[df["id"].astype(str) == str(target_id)]

        if match.empty:
            return None

        row = match.iloc[0]

        return Role(
            id=row["id"],
            title=row["title"],
            definition=row["definition"],
            task=row["task"]
        )

    except Exception as e:
        print(f"Error getting role by ID: {e}")
        return None