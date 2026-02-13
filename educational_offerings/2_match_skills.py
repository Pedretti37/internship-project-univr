import json
import os, sys

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from esco import escoAPI

# Load json module
def load_courses(filename):
    if not os.path.exists(filename):
        print(f"❌ Errore: Il file '{filename}' non esiste.")
        return []
        
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)

# matching logic
def tag_courses_with_esco_role(role_search_term, courses_json_path):
    print(f"🔍 1. Interrogo ESCO per il ruolo: '{role_search_term}'...")
    print(f"   ℹ️  Nota: Richiedo i risultati in TEDESCO (language='de') per il matching con i PDF.")

    results = escoAPI.get_esco_occupations_list(role_search_term, language='de', limit=1)
    
    if not results:
        print("⚠️  Nessun ruolo trovato su ESCO. Prova con un termine diverso (es. 'Maschinenbauingenieur').")
        return
    
    target_role = results[0] # Most relevant result
    print(f"✅ Ruolo Trovato: {target_role.title}")
    print(f"   URI: {target_role.uri}")
    
    # Skill preparation (Parsing the \n string)
    essential_dict = {uri: skill for uri, skill in target_role.essential_skills.items()}
    # optional_dict = target_role.optional_skills.items()
    
    # Remove duplicates while preserving order

    print(f"   -> Scaricate {len(essential_dict)} skills ufficiali in Tedesco.")

    # Courses matching
    courses = load_courses(courses_json_path)
    if not courses:
        return

    print(f"📊 2. Analizzo {len(courses)} moduli didattici dal JSON...")

    matches_found = 0
    total_skills_tagged = 0

    for course in courses:
        # TExt extraction and normalization
        course_text = (course.get('title_de', '') + " " + course.get('learning_outcomes_de', '')).lower()
        
        found_skills = {}
        
        for uri, skill_phrase in essential_dict.items():
            skill_clean = skill_phrase.lower().strip()
            
            if skill_clean in course_text:
                found_skills[uri] = skill_phrase
                continue # FOund direct match, skip to next skill

            # More advanced matching: split into words and check presence
            words = skill_clean.split()
            significant_words = [w for w in words if len(w) > 4]
            
            if not significant_words:
                continue
                
            match_score = 0
            for word in significant_words:
                if word in course_text:
                    match_score += 1
            
            # Euristic decision
            is_match = False
            if len(significant_words) == 1:
                if match_score == 1: is_match = True
            elif match_score >= 1:
                 is_match = True
            
            if is_match:
                found_skills[uri] = skill_phrase

        unique_found = list(found_skills.values())
        
        course['esco_skills_match'] = found_skills
        
        if unique_found:
            matches_found += 1
            total_skills_tagged += len(unique_found)

    # Output saving
    filename_only = "educational_offerings_esco_tagged.json"
    
    output_dir = os.path.join("educational_offerings", "courses")
    
    os.makedirs(output_dir, exist_ok=True)
    
    full_output_path = os.path.join(output_dir, filename_only)

    # 5. Salva il file
    with open(full_output_path, 'w', encoding='utf-8') as f:
        json.dump(courses, f, ensure_ascii=False, indent=4)
        
    print(f"\n🚀 FINE LAVORO!")
    print(f"   - Moduli analizzati: {len(courses)}")
    print(f"   - Moduli con almeno un match: {matches_found}")
    print(f"   - Totale tag assegnati: {total_skills_tagged}")
    print(f"💾 File salvato: {full_output_path}")

# Execution
if __name__ == "__main__":
    tag_courses_with_esco_role("Maschinenbauingenieur", "educational_offerings/educational_offerings.json")