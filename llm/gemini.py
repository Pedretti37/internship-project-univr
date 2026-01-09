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
    Identifica il livello dell'utente per ogni skill richiesta usando matching semantico.
    NON calcola il gap matematico (lo fa Python).
    """
    
    # Costruiamo il JSON delle skill richieste
    # Nota: Passiamo solo il nome della skill, il livello richiesto serve a poco a Gemini ora,
    # ma possiamo lasciarlo per contesto.
    required_json = json.dumps([
        {"skill": s["Skill"]} 
        for s in role_skills_list
    ])

    prompt = f"""
    You are an expert HR Skill Matcher.
    
    I will provide:
    1. A User's Current Skill Set (Dictionary: Skill Name -> Level).
    2. A List of Required Skills for a target Role.

    YOUR TASK:
    For EACH required skill, look at the User's Skills and find the best semantic match.
    
    RULES:
    - If the user has the exact skill or a highly similar equivalent (e.g., "Ms Excel" matches "Excel"), return the User's Level.
    - If the user has a related but broader/narrower skill, estimate the applicable level conservatively.
    - If the user strictly DOES NOT have the skill or anything similar, return 0.
    - Do NOT calculate the gap. I only need the User's current level.

    USER SKILLS:
    {json.dumps(user_skills)}

    REQUIRED SKILLS TO FIND:
    {required_json}

    OUTPUT FORMAT:
    Return ONLY a valid JSON array of objects.
    [
        {{ "skill_name": "The Required Skill Name", "user_level": integer_value }},
        ...
    ]
    """

    # Logica di Retry
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash-lite", # O il modello che stai usando
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.0, # Temperature a 0 per massima precisione
                    response_mime_type="application/json" # Forza output JSON (se supportato dal modello)
                )
            )
            
            if response.text:
                # Pulizia standard del markdown
                clean_text = response.text.replace("```json", "").replace("```", "").strip()
                
                start = clean_text.find('[')
                end = clean_text.rfind(']') + 1
                
                if start != -1 and end != -1:
                    json_str = clean_text[start:end]
                    return json.loads(json_str)
            
            return [] # Risposta vuota o malformata

        except (ResourceExhausted, ServiceUnavailable):
            print(f"⚠️ API Overload. Attendo {2 * (attempt + 1)}s...")
            time.sleep(2 * (attempt + 1))
        except Exception as e:
            print(f"❌ Errore API Gemini: {e}")
            return []
    
    return [] # Fallito dopo i tentativi