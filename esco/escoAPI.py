import requests
import time
from models import Role

def get_esco_occupations_list(keyword, limit):
    base_url = "https://ec.europa.eu/esco/api"
    
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'application/json'
    }
    
    # 1. CERCA I RUOLI
    search_params = {'text': keyword, 'type': 'occupation', 'language': 'en', 'limit': limit}
    
    try:
        search_resp = requests.get(f"{base_url}/search", params=search_params, headers=headers)
        search_resp.raise_for_status()
        results = search_resp.json().get('_embedded', {}).get('results', [])
    except Exception as e:
        print(f"Connection error: {e}")
        return []

    if not results:
        return []

    output_list = []

    # 2. PER OGNI RUOLO, SCARICA I DETTAGLI (E I TASK/SKILL)
    for hit in results:
        title = hit['title']
        uri = hit['uri']
        
        # Gestione Codice ISCO
        raw_val = hit.get('code')
        
        if raw_val:
            s_code = str(raw_val) # Forza stringa "2512.3"
            isco_family = s_code.split('.')[0] # Diventa "2512"
            isco_code_raw = s_code # Manteniamo l'originale come stringa
        else:
            isco_family = "N/A"
            isco_code_raw = "N/A"

        definition = "N/A"
        tasks_string = "" # <--- Qui metteremo i tasks

        try:
            details_params = {'uri': uri, 'language': 'en'}
            details_resp = requests.get(f"{base_url}/resource/occupation", params=details_params, headers=headers)
            
            if details_resp.status_code == 200:
                d_data = details_resp.json()
                
                # A. Estrazione Descrizione
                desc_obj = d_data.get('description', {}) or d_data.get('definition', {})
                definition = desc_obj.get('en', {}).get('literal', 'N/A')

                # B. Estrazione TASKS (Essential Skills)
                links = d_data.get('_links', {})
                skills_list = links.get('hasEssentialSkill', [])
                
                # Prendiamo i titoli delle skill e li uniamo in una stringa
                # Esempio: "write code, debug software, work in teams"
                extracted_tasks = [skill['title'] for skill in skills_list]
                
                # Limitiamo a 10 task per non intasare il DB
                tasks_string = ", ".join(extracted_tasks[:10]) 

        except Exception as e:
            print(f"Error fetching details for {title}: {e}")

        # Creazione Oggetto Role
        role_data = Role(
            id=str(isco_family),
            title=title,
            description=definition,
            task=tasks_string,
            id_full=str(isco_code_raw),
            uri=uri
        )
        
        output_list.append(role_data)
        time.sleep(0.1) 

    return output_list