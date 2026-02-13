import requests
import time
from models import Role

# Configuration
HEADERS = {
    'User-Agent': 'Mozilla/5.0',
    'Accept': 'application/json'
}
BASE_URL = "https://ec.europa.eu/esco/api"

### API function to get details
def get_single_role_details(uri: str, language: str) -> Role | None:
    if not uri:
        return None

    try:
        # Fetch role details from ESCO API
        details_params = {'uri': uri, 'language': language}
        details_resp = requests.get(f"{BASE_URL}/resource/occupation", params=details_params, headers=HEADERS)
        
        if details_resp.status_code != 200:
            print(f"❌ ESCO API Error: {details_resp.status_code} per URI: {uri}")
            return None
            
        d_data = details_resp.json()
        
        # Title and Description
        title = d_data.get('title', 'Unknown Role')
        desc_obj = d_data.get('description', {}) or d_data.get('definition', {})

        definition = "No description available."
        if isinstance(desc_obj, dict):
            lang_data = desc_obj.get(language) or desc_obj.get('en')
            if lang_data:
                definition = lang_data.get('literal', 'No description available.')

        # ISCO Code Extraction
        raw_val = d_data.get('code')
        if raw_val:
            s_code = str(raw_val)
            isco_family = s_code.split('.')[0]
            isco_code_raw = s_code
        else:
            isco_family = "N/A"
            isco_code_raw = "N/A"

        # Skills Extraction
        embedded = d_data.get('_embedded', {})
        links = d_data.get('_links', {})

        def extract_titles(key_name):
            # Embedded skills (detailed info)
            source = embedded.get(key_name, [])
            if not source:
                # Links only 
                source = links.get(key_name, [])
            
            titles = []
            for item in source:
                t = item.get('title')
                if t:
                    titles.append(t)
            return titles

        essential_titles = extract_titles('hasEssentialSkill')
        optional_titles = extract_titles('hasOptionalSkill')

        # Up to 40 skills each for now
        str_essential = "\n".join([t.capitalize() for t in essential_titles[:40]])
        str_optional = "\n".join([t.capitalize() for t in optional_titles[:40]])

        return Role(
            id=str(isco_family),
            title=title,
            description=definition,
            essential_skills=str_essential,
            optional_skills=str_optional,
            id_full=str(isco_code_raw),
            uri=uri
        )

    except Exception as e:
        print(f"Exception fetching single details for {uri}: {e}")
        return None

### Main function to search and get details for occupations
def get_esco_occupations_list(keyword, language, limit=10):
    search_params = {'text': keyword, 'type': 'occupation', 'language': language, 'limit': limit}
    
    try:
        # print(f"🔍 Searching ESCO for: {keyword}...")
        search_resp = requests.get(f"{BASE_URL}/search", params=search_params, headers=HEADERS)
        search_resp.raise_for_status()
        
        results = search_resp.json().get('_embedded', {}).get('results', [])
    except Exception as e:
        print(f"Connection error during search: {e}")
        return []

    if not results:
        return []

    output_list = []

    for hit in results:
        uri = hit['uri']

        # Calling the single details function
        role_data = get_single_role_details(uri, language=language)
        
        if role_data:
            output_list.append(role_data)
        
        # Sleep to avoid rate limiting
        time.sleep(0.05) 

    return output_list

### Skill translation function (EN -> DE)
def translate_skill_esco(roles: list[dict]) -> list[str]:
    results = []  
    not_found = []

    for role in roles:
        # print("--- Processing role ---")
        try:
            # URI extraction
            role_uri = role.get("role_uri")
            if not role_uri:
                not_found.append(role["role_title"])
                continue
            # print(f"Role URI found: {role_uri}")
            
            # English Skills
            resp_en = requests.get(f"{BASE_URL}/resource/occupation", params={'uri': role_uri, 'language': 'en', 'viewMode': 'FULL'}).json()
            # print(f"URL: {BASE_URL}/resource/occupation?uri={role_uri}&language=en&viewMode=FULL")
            links = resp_en.get('_links', {})
            all_skills_en = links.get('hasEssentialSkill', [])

            en_skill_map = {}
            for item in all_skills_en:
                en_skill_map[item['title'].lower()] = item['uri']
            # print(f"English skills mapped: {en_skill_map.keys()}")

            # German Skills
            resp_de = requests.get(f"{BASE_URL}/resource/occupation", params={'uri': role_uri, 'language': 'de', 'viewMode': 'FULL'}).json()
            # print(f"URL: {BASE_URL}/resource/occupation?uri={role_uri}&language=de&viewMode=FULL")
            links = resp_de.get('_links', {})
            all_skills_de = links.get('hasEssentialSkill', [])

            de_skill_map = {}
            for item in all_skills_de:
                de_skill_map[item['uri']] = item['title']
            # print(f"German skills mapped: {de_skill_map.values()}")

            for skill_en in role["missing_skills"]:
                uri = en_skill_map.get(skill_en.lower())
                # print(f"Processing skill: '{skill_en}' -> URI: {uri}")
                if uri:
                    translation = de_skill_map.get(uri)
                    # print(f"Translation found: '{skill_en}' -> '{translation}'")
                    if translation:
                        results.append(translation)
                    else:
                        not_found.append(skill_en) # URI is found but no German translation available
                else:
                    # ESCO definition not found for this skill
                    not_found.append(skill_en)
        
        except Exception as e:
            return f"Error during API call: {str(e)}"
        # print("--------------------------")
    
    # print(results)
    return results #, not_found