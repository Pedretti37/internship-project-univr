import json
import os
from models import Organization, Invitation

DATA_DIR_ORGS = "data/organizations"
os.makedirs(DATA_DIR_ORGS, exist_ok=True)

DATA_INV_DIR = "data//invitations"
os.makedirs(DATA_INV_DIR, exist_ok=True)

### --- Helper: Path --- ###
def get_json_path(orgname: str) -> str:
    return os.path.join(DATA_DIR_ORGS, f"{orgname}.json")

def get_inv_json_path(id: str) -> str:
    return os.path.join(DATA_INV_DIR, f"{id}.json")

### --- CRUD: Create --- ###
def create_organization(org: Organization):
    if os.path.exists(get_json_path(org.orgname)):
        raise ValueError("Organization identifier already exists")

    file_path = get_json_path(org.orgname)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(org.model_dump(), indent=4))
    
    return org

### --- CRUD: Update & Manage --- ###
def update_org(org: Organization):
    path = get_json_path(org.orgname)
    
    if not os.path.exists(path):
        return

    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(org.model_dump_json(indent=4))
    except Exception as e:
        print(f"Error updating organization: {e}")

def add_member_to_org(org: Organization, username: str):
    if username not in org.members:
        org.members.append(username)

    update_org(org)
    return org

def change_password_org(org: Organization, new_pw: str) -> bool:
    path = get_json_path(org.orgname)
    
    if not os.path.exists(path):
        return False
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        data["hashed_password"] = new_pw

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        
        return True
    except Exception:
        return False

### --- CRUD: Getters --- ###
def get_org_by_orgname(orgname: str) -> Organization | None:
    path = get_json_path(orgname)
    if not os.path.exists(path):
        return None
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return Organization(**data)
    except Exception:
        return None

### --- Create Invitation --- ###
def create_invitation(orgname: str, username: str) -> bool:
    invitation = Invitation(
        orgname=orgname,
        username=username,
        status="pending"
    )

    inv_path = os.path.join(DATA_INV_DIR, f"{invitation.id}.json")
    with open(inv_path, "w", encoding="utf-8") as f:
        f.write(invitation.model_dump_json(indent=4))
        return True 
    
    return False

### --- Get Invitation By ID --- ###
def get_inv_by_id(id: str) -> Invitation | None:
    path = get_inv_json_path(id)
    if not os.path.exists(path):
        return None
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return Invitation(**data)
    except Exception:
        return None

### --- Update Invitation --- ###
def update_invitation(inv: Invitation):
    path = get_inv_json_path(inv.id)
    
    if not os.path.exists(path):
        return

    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(inv.model_dump_json(indent=4))
    except Exception as e:
        print(f"Error updating invitation: {e}")
