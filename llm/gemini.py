from google import genai
from google.genai import types
import json

# --- SETTING ---
API_KEY = "CURRENT KEY" 

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
            model="gemini-2.5-flash",
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
