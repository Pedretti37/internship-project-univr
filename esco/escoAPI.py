import requests
import time
from models import Role

# Configurazione Comune
HEADERS = {
    'User-Agent': 'Mozilla/5.0',
    'Accept': 'application/json'
}
BASE_URL = "https://ec.europa.eu/esco/api"

def get_single_role_details(uri: str) -> Role | None:
    """
    Recupera i dettagli completi di un ruolo specifico usando il suo URI univoco.
    Questa è la nostra 'Fonte di Verità'.
    """
    if not uri:
        return None

    try:
        # Chiamata specifica alla risorsa
        details_params = {'uri': uri, 'language': 'en'}
        details_resp = requests.get(f"{BASE_URL}/resource/occupation", params=details_params, headers=HEADERS)
        
        if details_resp.status_code != 200:
            print(f"❌ ESCO API Error: {details_resp.status_code} per URI: {uri}")
            return None
            
        d_data = details_resp.json()
        
        # 1. Estrazione Titolo e Descrizione
        title = d_data.get('title', 'Unknown Role')
        desc_obj = d_data.get('description', {}) or d_data.get('definition', {})
        # A volte la descrizione è un oggetto con 'en', a volte è stringa, gestiamo il caso standard ESCO
        if isinstance(desc_obj, dict):
            definition = desc_obj.get('en', {}).get('literal', 'No description available.')
        else:
            definition = "No description format recognized."

        # 2. Estrazione Codici ISCO
        raw_val = d_data.get('code')
        if raw_val:
            s_code = str(raw_val)
            isco_family = s_code.split('.')[0]
            isco_code_raw = s_code
        else:
            isco_family = "N/A"
            isco_code_raw = "N/A"

        # 3. Estrazione Skills (Strategia Ibrida _embedded + _links)
        embedded = d_data.get('_embedded', {})
        links = d_data.get('_links', {})

        def extract_titles(key_name):
            # Prima proviamo embedded (dati completi)
            source = embedded.get(key_name, [])
            if not source:
                # Fallback su links (solo riferimenti)
                source = links.get(key_name, [])
            
            # Estraiamo i titoli
            titles = []
            for item in source:
                t = item.get('title')
                if t:
                    titles.append(t)
            return titles

        essential_titles = extract_titles('hasEssentialSkill')
        optional_titles = extract_titles('hasOptionalSkill')

        # Limitiamo per evitare testi giganti nel DB (opzionale)
        str_essential = "\n".join(essential_titles[:40]) 
        str_optional = "\n".join(optional_titles[:40])

        # Creiamo l'oggetto Role
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
        print(f"❌ Exception fetching single details for {uri}: {e}")
        return None

def get_esco_occupations_list(keyword, limit=10):
    """
    Cerca i ruoli per parola chiave e usa get_single_role_details per popolare i dati.
    """
    search_params = {'text': keyword, 'type': 'occupation', 'language': 'en', 'limit': limit}
    
    try:
        print(f"🔍 Searching ESCO for: {keyword}...")
        search_resp = requests.get(f"{BASE_URL}/search", params=search_params, headers=HEADERS)
        search_resp.raise_for_status()
        
        # I risultati della ricerca sono spesso parziali, contengono solo titolo e uri
        results = search_resp.json().get('_embedded', {}).get('results', [])
    except Exception as e:
        print(f"❌ Connection error during search: {e}")
        return []

    if not results:
        return []

    output_list = []

    for hit in results:
        uri = hit['uri']
        # Usiamo la funzione sopra per ottenere i dettagli puliti e completi
        role_data = get_single_role_details(uri)
        
        if role_data:
            output_list.append(role_data)
        
        # Piccolo ritardo per non bombardare l'API
        time.sleep(0.05) 

    return output_list