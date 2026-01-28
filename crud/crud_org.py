import json
import os
from models import Organization, Invitation

DATA_DIR_ORGS = "data/organizations"
os.makedirs(DATA_DIR_ORGS, exist_ok=True)

INDEX_FILE = "data/organizations/org_index.json"
os.makedirs(os.path.dirname(INDEX_FILE), exist_ok=True)

DATA_INV_DIR = "data/organizations/invitations"
os.makedirs(DATA_INV_DIR, exist_ok=True)

### --- Helper: Path --- ###
def get_json_path(id: str) -> str:
    return os.path.join(DATA_DIR_ORGS, f"{id}.json")

def get_inv_json_path(id: str) -> str:
    return os.path.join(DATA_INV_DIR, f"{id}.json")

### --- Internal Index Management --- ###
def _load_index() -> dict:
    if not os.path.exists(INDEX_FILE):
        return {}
    try:
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def _save_index(index_data: dict):
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index_data, f, indent=4)

### --- CRUD: Create --- ###
def create_organization(org: Organization):
    index = _load_index()
    
    if org.orgname in index:
        raise ValueError("Organization identifier already exists")

    file_path = get_json_path(org.id)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(org.model_dump(), indent=4))

    index[org.orgname] = org.id
    _save_index(index)
    
    return org

### --- CRUD: Update & Manage --- ###
def update_org(org: Organization):
    path = get_json_path(org.id)
    
    if not os.path.exists(path):
        return

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(org.model_dump(), f, indent=4)
    except Exception as e:
        print(f"Error updating organization: {e}")

def add_member_to_org(org: Organization, user_id: str):
    if user_id not in org.members:
        org.members.append(user_id)

    update_org(org)
    return org

def change_password_org(org: Organization, new_pw: str) -> bool:
    path = get_json_path(org.id)
    
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
def get_org_by_id(org_id: str) -> Organization | None:
    path = get_json_path(org_id)
    if not os.path.exists(path):
        return None
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return Organization(**data)
    except Exception:
        return None

def get_org_by_orgname(orgname: str) -> Organization | None:
    index = _load_index()

    org_id = index.get(orgname)
    
    if not org_id:
        return None
        
    return get_org_by_id(org_id)

### --- Create Invitation --- ###
def create_invitation(org_id: str, user_id: str) -> bool:
    invitation = Invitation(
        org_id=org_id,
        user_id=user_id,
        status="pending"
    )

    inv_path = os.path.join(DATA_INV_DIR, f"{invitation.id}.json")
    with open(inv_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(invitation.model_dump(), indent=4))
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
            json.dump(inv.model_dump(), f, indent=4)
    except Exception as e:
        print(f"Error updating organization: {e}")
