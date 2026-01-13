import requests
import time
from models import Role

def get_esco_occupations_list(keyword, limit):
    base_url = "https://ec.europa.eu/esco/api"
    
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'application/json'
    }
    
    # Research occupations matching the keyword
    search_params = {'text': keyword, 'type': 'occupation', 'language': 'en', 'limit': limit}
    
    try:
        search_resp = requests.get(f"{base_url}/search", params=search_params, headers=headers)
        search_resp.raise_for_status()
        results = search_resp.json().get('_embedded', {}).get('results', [])
    except Exception as e:
        print(f"Connection error during search: {e}")
        return []

    if not results:
        print("No results found.")
        return []

    output_list = []

    for hit in results:
        title = hit['title']
        uri = hit['uri']
        
        # ISCO Code extraction
        raw_val = hit.get('code')
        if raw_val:
            s_code = str(raw_val) 
            isco_family = s_code.split('.')[0] 
            isco_code_raw = s_code 
        else:
            isco_family = "N/A"
            isco_code_raw = "N/A"

        definition = "N/A"
        str_essential = ""
        str_optional = ""
        
        try:
            details_params = {'uri': uri, 'language': 'en'} 
            
            details_resp = requests.get(f"{base_url}/resource/occupation", params=details_params, headers=headers)
            
            if details_resp.status_code == 200:
                d_data = details_resp.json()
                
                # Description extraction
                desc_obj = d_data.get('description', {}) or d_data.get('definition', {})
                definition = desc_obj.get('en', {}).get('literal', 'N/A')

                # Hybrid extraction for skills
                embedded = d_data.get('_embedded', {})
                links = d_data.get('_links', {})

                def extract_titles(key_name):
                    # Try _embedded
                    source = embedded.get(key_name, [])
                    if not source:
                        # Fallback on _links
                        source = links.get(key_name, [])
                    
                    return [item.get('title', 'Unknown Skill') for item in source]

                # Extract
                essential_titles = extract_titles('hasEssentialSkill')
                optional_titles = extract_titles('hasOptionalSkill')
                
                # Max 20 skills for now
                str_essential = "\n".join(essential_titles[:20])
                str_optional = "\n".join(optional_titles[:20])
                

        except Exception as e:
            print(f"Error fetching details for {title}: {e}")

        role_data = Role(
            id=str(isco_family),
            title=title,
            description=definition,
            essential_skills=str_essential,
            optional_skills=str_optional,
            id_full=str(isco_code_raw),
            uri=uri
        )
        
        output_list.append(role_data)
        time.sleep(0.1)

    return output_list