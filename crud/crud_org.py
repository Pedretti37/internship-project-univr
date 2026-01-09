import json
import os
from models import Organization

FILE_INPUT = "data/ISCO-08 EN Structure and definitions.xlsx"

DATA_DIR_ORGS = "data/organizations"
os.makedirs(DATA_DIR_ORGS, exist_ok=True)

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
