import time
from google.api_core.exceptions import ServiceUnavailable, ResourceExhausted
from google import genai
from google.genai import types
import json

# --- SETTING ---
API_KEY = "CURRENT_KEY" 

FILE_INPUT = "data/ISCO-08 EN Structure and definitions.xlsx"

# --- SETTING Gemini
client = genai.Client(api_key=API_KEY)

def analyse_with_gemini(title_role, tasks):
    """
    Sharing data with Gemini and asking for Skill Models.
    """
    prompt = f"""
    Act as a Technical HR Expert and Skills Analyst.
    
    Analyze the following Job Role and the associated list of Tasks.
    Extract the top 3-5 technical Hard Skills and/or Soft Skills required to perform these tasks.
    For each skill, estimate the required proficiency level from 1 to 9 based on the complexity of the tasks.
    
    Proficiency Scale:
    1-3 = Beginner/Knowledge (Assist, Support, Execute basic tasks)
    4-6 = Intermediate/Autonomous (Develop, Manage, Analyze, Solve problems)
    7-9 = Expert/Strategic (Architect, Lead, Define Strategy, Mentor)

    DATA TO ANALYZE:
    Role: {title_role}
    Tasks/Description: {tasks}

    REQUIRED OUTPUT:
    Return ONLY a valid JSON array (no markdown blocks ```json).
    Example format:
    [
        {{"skill": "Python", "level": 4, "reason": "Must create complex backend architectures"}},
        {{"skill": "Project Management", "level": 2, "reason": "Supports the PM in management tasks"}}
    ]
    """

    try:
        # --- API ---
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1
            )
        )
        
        # cleaner response
        if response.text:
            clean_response = response.text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_response)
        else:
            return []
            
    except Exception as e:
        print(f"Fail to analyse {title_role}: {e}")
        return []

def get_gap_gemini(user_skills, role_skills_list):
    """
    Calcola il gap per TUTTE le skill di un ruolo in UNA sola chiamata API.
    Risparmia tempo e token.
    """
    
    # Costruiamo un JSON stringa delle skill richieste per il prompt
    # Esempio: [{"skill": "Python", "level": 4}, {"skill": "Leadership", "level": 7}]
    required_json = json.dumps([
        {"skill": s["Skill"], "level": int(s["Required Level"])} 
        for s in role_skills_list
    ])

    prompt = f"""
    You are a Skill Gap Analyst.
    
    I will provide:
    1. A User's Current Skill Set (Dictionary: Skill Name -> Level).
    2. A List of Required Skills for a specific Role.

    For EACH required skill, compare it with the user's skills.
    - Find the best matching skill in the user's profile.
    - Calculate the GAP = Required Level - User Level.
    - If User Level > Required Level, Gap is negative (Overskilled).
    - If User doesn't have the skill, assume User Level is 0 (Gap = Required Level).

    USER SKILLS:
    {json.dumps(user_skills)}

    REQUIRED SKILLS TO ANALYZE:
    {required_json}

    OUTPUT FORMAT:
    Return ONLY a valid JSON array of objects. Do NOT use markdown.
    Structure:
    [
        {{ "skill_name": "Requested Skill Name", "gap": integer_value, "user_level": integer_value }},
        ...
    ]
    """

    # Logica di Retry (fondamentale per i modelli Flash/Pro)
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash-lite", # Usa 2.0 o 1.5 per stabilità
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.1)
            )
            
            if response.text:
                clean_text = response.text.replace("```json", "").replace("```", "").strip()
                # A volte aggiunge testo prima o dopo, cerchiamo le quadre
                start = clean_text.find('[')
                end = clean_text.rfind(']') + 1
                if start != -1 and end != -1:
                    json_str = clean_text[start:end]
                    return json.loads(json_str)
            
            return [] # Risposta vuota

        except (ResourceExhausted, ServiceUnavailable):
            print(f"API Overload. Attendo {3 * (attempt + 1)}s...")
            time.sleep(3 * (attempt + 1))
        except Exception as e:
            print(f"Errore API Batch: {e}")
            return []
    
    return [] # Fallito dopo i tentativi