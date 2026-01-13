import json
import os
import time
from crud import crud_user
from llm import gemini

def calculate_skill_gap_user(user, role_ids: list[str]) -> dict:
    gap_report = {}
    
    for rid in role_ids:
        role_data = next((r for r in user.target_roles if r['id'] == rid), None) 
        
        if not role_data:
            continue

        role_title = role_data["info"]["title"]
        required_skills_list = role_data["skills"] # Lista di dict
        
        gap_report[role_title] = []

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
                
        except Exception as e:
            print(f"❌ Errore salvataggio skill gap: {e}")

    return gap_report