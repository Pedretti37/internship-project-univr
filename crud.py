import json
import os
import pandas as pd
from models import User, Organization, Role
from llm import gemini

FILE_INPUT = "data/ISCO-08 EN Structure and definitions.xlsx"

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

def set_target_roles_user(user: User, target_roles: list[str]) -> dict:
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

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
            
        return matched_roles
        
    except Exception as e:
        print(f"Errore nel salvataggio: {e}")
        return {}

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
        df = pd.read_excel(FILE_INPUT, usecols="B,C,D,E", dtype=str)
        
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
    
def get_role_by_id(target_id: str) -> Role | None:
    try:
        
        df = pd.read_excel(
            FILE_INPUT, 
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

def calculate_skill_gap_user(user, role_ids: list[str]) -> dict:
    """
    Confronta le skill dell'utente con quelle richieste dai ruoli specificati.
    """
    gap_report = {}
    
    # Skill dell'utente (normalizzate in minuscolo per confronto facile)
    # Esempio user_skills_norm = {'python': 3, 'english': 8}
    user_skills_norm = {k.lower(): v for k, v in user.current_skills.items()} if user.current_skills else {}

    for rid in role_ids:
        role_data = get_role_skills_data(rid)
        
        if not role_data:
            continue

        role_title = role_data["info"]["title"]
        gap_report[role_title] = [] # Lista dei gap per questo ruolo

        # Calcolo matematico del GAP
        for req in role_data["skills"]:
            req_name = req["Skill"]
            req_level = int(req["Required Level"])
            
            # Cerchiamo se l'utente ha questa skill (case insensitive match basico)
            # Nota: qui stiamo facendo match esatto di stringa. 
            # In futuro si potrebbe usare l'AI per capire che "Coding" == "Python".
            user_level = user_skills_norm.get(req_name.lower(), 0)
            
            gap_val = req_level - user_level
            
            status = ""
            if user_level == 0:
                status = "MISSING" # L'utente non ce l'ha proprio
            elif gap_val > 0:
                status = "GAP"     # L'utente ce l'ha ma livello troppo basso
            elif gap_val == 0:
                status = "MATCH"   # Perfetto
            else:
                status = "OVERSKILLED" # L'utente è più bravo del necessario

            gap_report[role_title].append({
                "skill_name": req_name,
                "required": req_level,
                "user_level": user_level,
                "gap": gap_val,
                "status": status,
                "reason": req["Reason"]
            })

    user.skill_gap = gap_report
    
    path = get_json_path(user.username)
    
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            data["skill_gap"] = gap_report
            
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
                
            print(f"✅ Skill Gap salvato per l'utente {user.username}")
            
        except Exception as e:
            print(f"❌ Errore salvataggio skill gap: {e}")

    return gap_report

def get_role_skills_data(role_id: str):
    # Leggiamo Excel
    try:
        df = pd.read_excel(FILE_INPUT)
        # Assumiamo Colonna B = ID (indice 1), Colonna C = Titolo, Colonna E = Task
        # Filtriamo per ID (convertendo in stringa per sicurezza)
        row = df[df.iloc[:, 1].astype(str) == role_id]
        
        if row.empty:
            print(f"❌ ID {role_id} non trovato nell'Excel.")
            return None
            
        role_title = row.iloc[0, 2] # Colonna C
        tasks = row.iloc[0, 4]      # Colonna E
        
        # --- CHIAMATA GEMINI ---
        skills_generated = gemini.analyse_with_gemini(role_title, tasks)
        
        if not skills_generated:
            return None

        # Creiamo la struttura dati
        new_entry = {
            "info": {"title": role_title, "id": role_id},
            "skills": []
        }
        
        for s in skills_generated:
            new_entry["skills"].append({
                "Skill": s.get('skill'),
                "Required Level": s.get('level'),
                "Reason": s.get('reason')
            })
            
        return new_entry

    except Exception as e:
        print(f"Errore generazione dati: {e}")
        return None