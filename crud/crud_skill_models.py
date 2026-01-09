import json
import os
import pandas as pd
import time
from crud import crud_user
from models import Role
from llm import gemini

FILE_INPUT = "data/ISCO-08 EN Structure and definitions.xlsx"

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

def calculate_skill_gap_user(user, role_ids: list[str]) -> dict:
    gap_report = {}
    
    for rid in role_ids:
        # Recuperiamo i dati del ruolo (Titolo e lista skill richieste)
        role_data = get_role_skills_data(rid) 
        
        if not role_data:
            continue

        role_title = role_data["info"]["title"]
        required_skills_list = role_data["skills"] # Lista di dict
        
        gap_report[role_title] = []

        # print(f"📊 Analisi gap per ruolo: {role_title} (Batch)...")

        # CHIAMATA UNICA A GEMINI
        batch_results = gemini.get_gap_gemini(user.current_skills, required_skills_list)
        
        # Creiamo una mappa per accesso rapido ai risultati: {"SkillName": {gap: 2, user_level: 5}}
        results_map = {r["skill_name"]: r for r in batch_results}

        # Ricostruiamo il report finale
        for req in required_skills_list:
            req_name = req["Skill"]
            req_level = int(req["Required Level"])
            reason = req["Reason"]
            
            # Recuperiamo i dati calcolati da Gemini
            result = results_map.get(req_name)
            
            if result:
                user_val = int(result.get("user_level", 0))
                gap_val = req_level - user_val
            else:
                # Fallback se Gemini si è dimenticato la skill
                user_val = 0
                gap_val = req_level

            # Determina Status
            if user_val == 0:
                 # Opzionale: Se l'utente non ha proprio la skill, è MISSING
                 status = "MISSING"
                 # Nota: gap_val sarà uguale a req_level (positivo)
            elif gap_val == 0:
                status = "MATCH"
            elif gap_val > 0:
                status = "GAP"
            else: # gap negativo (es. gap -2 significa che ho 2 punti in più)
                status = "OVERSKILLED"

            gap_report[role_title].append({
                "skill_name": req_name,
                "required": req_level,
                "user_level": user_val,
                "gap": gap_val,
                "status": status,
                "reason": reason
            })

        # Pausa tra un RUOLO e l'altro
        time.sleep(10) 

    user.skill_gap = gap_report
    path = crud_user.get_json_path(user.username)

    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            data["skill_gap"] = gap_report
            
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
                
            # print(f"✅ Skill Gap salvato per l'utente {user.username}")
            
        except Exception as e:
            print(f"❌ Errore salvataggio skill gap: {e}")

    return gap_report

def get_role_skills_data(role_id: str):
    # Leggiamo Excel
    try:
        df = pd.read_excel(FILE_INPUT)
        # Colonna B = ID (indice 1), Colonna C = Titolo, Colonna E = Task
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