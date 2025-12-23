import pandas as pd
from google import genai
from google.genai import types
import json
import time

# --- SETTING ---
API_KEY = "AIzaSyDcRMGwzpIZzeA1G_7s_dWvaT3NkYmDgj0" 

FILE_INPUT = "data/ISCO-08 EN Structure and definitions.xlsx"
FILE_OUTPUT = "skill_models.json"

# --- SETTING Gemini
client = genai.Client(api_key=API_KEY)

def analyse_with_gemini(title_role, tasks):
    """
    Sharing data with Gemini and asking for Skill Models.
    """
    prompt = f"""
    Act as a Technical HR Expert and Skills Analyst.
    
    Analyze the following Job Role and the associated list of Tasks.
    Extract the top 3-8 technical Hard Skills and/or Soft Skills required to perform these tasks.
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
        # --- CHIAMATA API (NUOVA SINTASSI) ---
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1 # Temperatura bassa per JSON più stabili
            )
        )
        
        # Pulizia della risposta
        if response.text:
            clean_response = response.text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_response)
        else:
            return []
            
    except Exception as e:
        print(f"Fail to analyse {title_role}: {e}")
        return []

# --- EXECUTION ---

print("Caricamento Excel...")
try:
    df = pd.read_excel(FILE_INPUT)
except FileNotFoundError:
    print(f"Errore: Il file {FILE_INPUT} non è stato trovato.")
    exit()

col_titolo = 'Title EN'      # Colonna C
col_tasks = 'Tasks include'  # Colonna E

# Assicuriamoci che i dati siano stringhe e le colonne esistano
if col_titolo in df.columns and col_tasks in df.columns:
    df[col_tasks] = df[col_tasks].astype(str)
    df[col_titolo] = df[col_titolo].astype(str)
else:
    print(f"Errore: Colonne '{col_titolo}' o '{col_tasks}' non trovate.")
    exit()

results = {}

print(f"Inizio analisi di {len(df)} righe totali...")

# --- TEST MODE ---
# Analizza solo le prime 5 righe. Se funziona, commenta questa riga per fare tutto.
# df = df.head(5) 
# print("⚠️ MODALITÀ TEST ATTIVA: Analizzo solo le prime 5 righe.")
# -----------------

# 2. Ciclo su ogni riga
for index, row in df.iterrows():
    # Prendi l'ID dalla Colonna B (indice 1)
    id_excel = row.iloc[1]
    id_key = str(id_excel) # string conversion
    
    role = row[col_titolo]      
    tasks = row[col_tasks]    
    
    print(f" -> Analizzando ID {id_excel}: {role}...")
    
    # Chiamata a Gemini
    skills_estratte = analyse_with_gemini(role, tasks)
    
    if skills_estratte:
        if id_key not in results:
            results[id_key] = []
            
        # Aggiungiamo le skill alla lista di questo ID
        for s in skills_estratte:
            results[id_key].append({
                "Role Title": role,  # Utile tenerlo per contesto
                "Skill": s.get('skill'),
                "Required Level": s.get('level'),
                "Reason": s.get('reason')
            })
    
    time.sleep(1.5)

# 4. Salvataggio risultati
print("Salvataggio risultati...")

if results:
    with open(FILE_OUTPUT, 'w', encoding='utf-8') as f:
        # ensure_ascii=False serve per salvare correttamente accenti e caratteri speciali
        json.dump(results, f, indent=4, ensure_ascii=False)
        
    print(f"✅ Fatto! File salvato come: {FILE_OUTPUT}")
    
    # Esempio di come leggere il primo ID trovato
    first_id = list(results.keys())[0]
    print(f"Esempio struttura per ID {first_id}:")
    print(results[first_id][0])
else:
    print("⚠️ Nessun risultato da salvare.")