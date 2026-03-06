import requests
import time
from models import Role, Skill

# Configuration
HEADERS = {
    'User-Agent': 'Mozilla/5.0',
    'Accept': 'application/json'
}
BASE_URL = "https://ec.europa.eu/esco/api"

### API function to get details
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
        details_params = {'uri': uri, 'language': language}
        details_resp = requests.get(f"{BASE_URL}/resource/occupation", params=details_params, headers=HEADERS)
        
        if details_resp.status_code != 200:
            print(f"❌ ESCO API Error: {details_resp.status_code} per URI: {uri}")
            return None

        # Obtain main details    
        d_data = details_resp.json()
        
        title = d_data.get('title', 'Unknown Role')
        desc_obj = d_data.get('description', {}) or d_data.get('definition', {})

        definition = "No description available."
        if isinstance(desc_obj, dict):
            lang_data = desc_obj.get(language) or desc_obj.get('en')
            if lang_data:
                definition = lang_data.get('literal', 'No description available.')

        raw_val = d_data.get('code')
        if raw_val:
            s_code = str(raw_val)
            isco_family = s_code.split('.')[0]
            isco_code_raw = s_code
        else:
            isco_family = "N/A"
            isco_code_raw = "N/A"

        # Essential Skill and Knowledge
        essential_skills = []
        
        related_params = {
            'uri': uri,
            'relation': 'hasEssentialSkill',# Both Essential Skills and Essential Knowledge
            'language': language,
            'limit': 500  # Taking all possible related skills/knowledge
        }
        related_resp = requests.get(f"{BASE_URL}/resource/related", params=related_params, headers=HEADERS)
        
        if related_resp.status_code == 200:
            r_data = related_resp.json()
            embedded_related = r_data.get('_embedded', {})
            
            for items_list in embedded_related.values():
                if isinstance(items_list, list):
                    for item in items_list:
                        s = Skill(
                            uri=item.get('uri'),
                            name=item.get('title'),
                            level=5 # ESCO doesn't provide a skill level in this endpoint -> defaulting to 5 for now
                        )
                        if s.uri and s.name:
                            essential_skills.append(s)

        return Role(
            id=str(isco_family),
            title=title,
            description=definition,
            essential_skills=essential_skills,
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

### API function to get skill URI by name 
def get_esco_skill_uri_by_name(skill_name: str, language: str = 'en') -> str | None:
    """
    Cerca una skill per nome sull'API di ESCO e restituisce il suo URI.
    Prende il primo risultato (il più rilevante).
    """
    search_params = {
        'text': skill_name, 
        'type': 'skill',      
        'language': language, 
        'limit': 1            
    }
    
    try:
        search_resp = requests.get(f"{BASE_URL}/search", params=search_params, headers=HEADERS)
        search_resp.raise_for_status()
        
        results = search_resp.json().get('_embedded', {}).get('results', [])
        
        if results:
            return results[0].get('uri')
            
    except Exception as e:
        print(f"Errore durante la ricerca della skill '{skill_name}': {e}")
        
    return None 

### Main function to search for skills based on user input
def get_esco_skills_list(keyword, language, limit=10):
    search_params = {'text': keyword, 'type': 'skill', 'language': language, 'limit': limit}
    
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
        uri = hit.get('uri')
        title = hit.get('title')

        if uri and title:
            skill = Skill(
                uri=uri,
                name=title,
                level=0 # ESCO doesn't provide a skill level in this endpoint -> defaulting to 0 for now
            )
            output_list.append(skill)

    return output_list
