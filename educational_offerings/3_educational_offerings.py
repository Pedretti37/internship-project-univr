import json
import os
import time
import re
from deep_translator import GoogleTranslator

# File paths
PROJECT_FILE = 'data\\projects\\5f6cd065-289e-46f4-908c-73a5074a7a21.json'
COURSES_FILE = 'educational_offerings_esco_tagged.json'
OUTPUT_FILE = 'skill_matching_results_v2.json'

# Words to ignore during matching (common words that don't add value)
STOP_WORDS = {
    # Deutsch
    'und', 'oder', 'die', 'der', 'das', 'den', 'dem', 'des', 'ein', 'eine', 'einer', 
    'einem', 'eines', 'für', 'mit', 'von', 'im', 'in', 'zu', 'auf', 'aus', 'an', 
    'bei', 'als', 'um', 'sie', 'er', 'es', 'wir', 'ihr', 'ist', 'sind', 'war', 
    'wird', 'werden', 'wenden', 'führen', 'durch', 'stellen', 'sicher', 'erstellen', 
    'bewerten', 'verwalten', 'verwenden', 'überwachen', 'dass', 'wie', 'können',
    # English
    'and', 'or', 'the', 'a', 'an', 'for', 'with', 'from', 'in', 'on', 'at', 'to', 
    'by', 'as', 'is', 'are', 'was', 'were', 'be', 'use', 'apply', 'create', 
    'manage', 'ensure', 'monitor', 'execute', 'develop', 'system', 'systems'
}

def load_json(filename):
    if not os.path.exists(filename):
        print(f"ERRORE: File non trovato: {filename}")
        return None
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"ERRORE lettura {filename}: {e}")
        return None

def find_missing_skills(project_data, role_title="software manager"):
    if 'skill_gap' not in project_data:
        return []
    for gap in project_data['skill_gap']:
        if gap.get('role_title', '').lower() == role_title.lower():
            return gap.get('missing_skills', [])
    return []

def translate_skills_to_german(skills_list):
    print(f"\n--- Inizio traduzione e analisi di {len(skills_list)} skill ---")
    translator = GoogleTranslator(source='en', target='de')
    processed_skills = {}
    
    for i, skill in enumerate(skills_list, 1):
        try:
            translated = translator.translate(skill)
            
            # Keyword extraction: Combine original and translated, clean punctuation, lowercase
            full_text = f"{skill} {translated}".lower()
            words = re.findall(r'\b\w+\b', full_text)
            
            # Filtering out stop words
            keywords = [w for w in words if w not in STOP_WORDS and len(w) > 2]
            
            # Set to remove duplicates
            keywords = list(set(keywords))
            
            processed_skills[skill] = {
                "translation": translated,
                "keywords": keywords
            }
            
            print(f"[{i}] '{skill}' -> Keywords: {keywords}")
            time.sleep(0.2)
        except Exception as e:
            print(f"Errore su '{skill}': {e}")
            
    return processed_skills

def find_matching_courses(processed_skills_map, courses_data):
    matches = {}

    for original_skill, data in processed_skills_map.items():
        translation = data['translation']
        keywords = data['keywords']
        
        found_courses = []

        for course in courses_data:
            # Course title and outcomes combined
            title = course.get('title_de', '')
            outcomes = course.get('learning_outcomes_de', '')
            course_text = (title + " " + outcomes).lower()
            
            matched_keywords = []
            
            for kw in keywords:
                if kw in course_text:
                    matched_keywords.append(kw)
            
            # Match score based on number of matched keywords
            if matched_keywords:
                score = len(matched_keywords)
                found_courses.append({
                    "title": title,
                    "ects": course.get('ects', 'N/A'),
                    "matched_keywords": matched_keywords,
                    "score": score
                })
        
        found_courses.sort(key=lambda x: x['score'], reverse=True)
        
        if found_courses:
            matches[original_skill] = {
                "german_translation": translation,
                "top_matches": found_courses[:5] # Keep top 5 matches
            }

    return matches

def main():
    print("--- MATCHING SKILL INTELLIGENTE ---")
    
    project = load_json(PROJECT_FILE)
    courses = load_json(COURSES_FILE)
    
    if not project or not courses:
        return

    target_role = "software manager"
    missing_skills = find_missing_skills(project, target_role)
    
    if not missing_skills:
        print(f"Nessuna skill mancante per {target_role}.")
        return

    processed_skills = translate_skills_to_german(missing_skills)

    results = find_matching_courses(processed_skills, courses)
    
    print(f"\n--- RISULTATO ---")
    print(f"Trovate corrispondenze per {len(results)} skill su {len(missing_skills)}.")

    for skill, data in results.items():
        print(f"\nSkill: {skill} (DE: {data['german_translation']})")
        for match in data['top_matches'][:2]:
            print(f"   -> Corso: {match['title']} (Keywords: {match['matched_keywords']})")

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    print(f"\nSalvati risultati dettagliati in '{OUTPUT_FILE}'")

if __name__ == "__main__":
    main()