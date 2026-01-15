import requests
import time
from models import Role

# Configuration
HEADERS = {
    'User-Agent': 'Mozilla/5.0',
    'Accept': 'application/json'
}
BASE_URL = "https://ec.europa.eu/esco/api"

def get_single_role_details(uri: str) -> Role | None:
    if not uri:
        return None

    try:
        # Fetch role details from ESCO API
        details_params = {'uri': uri, 'language': 'en'}
        details_resp = requests.get(f"{BASE_URL}/resource/occupation", params=details_params, headers=HEADERS)
        
        if details_resp.status_code != 200:
            print(f"❌ ESCO API Error: {details_resp.status_code} per URI: {uri}")
            return None
            
        d_data = details_resp.json()
        
        # Title and Description
        title = d_data.get('title', 'Unknown Role')
        desc_obj = d_data.get('description', {}) or d_data.get('definition', {})
        if isinstance(desc_obj, dict):
            definition = desc_obj.get('en', {}).get('literal', 'No description available.')
        else:
            definition = "No description format recognized."

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

def get_esco_occupations_list(keyword, limit=10):
    search_params = {'text': keyword, 'type': 'occupation', 'language': 'en', 'limit': limit}
    
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
        role_data = get_single_role_details(uri)
        
        if role_data:
            output_list.append(role_data)
        
        # Sleep to avoid rate limiting
        time.sleep(0.05) 

    return output_list