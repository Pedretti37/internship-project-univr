import pandas as pd
import json

FILE_EXCEL = "None"

def convert_isco_dict_to_json():
    print("Lettura del file excel...")
    
    df = pd.read_excel(FILE_EXCEL)
    
    # Gestione valori vuoti
    df = df.fillna("")
    
    database_isco = {}
    
    for index, row in df.iterrows():
        codice = str(row['ISCO 08 Code']).strip()
        titolo = str(row['Title EN']).strip()
        descrizione = str(row['Definition']).strip()
        task = str(row['Tasks include']).strip()
        
        # Salviamo solo se c'è un codice valido
        if codice:
            database_isco[codice] = {
                "title": titolo,
                "description": descrizione,
                "tasks": task
            }
            
    # Scrittura su file json
    with open('data/cedefop/db_isco_definitions.json', 'w') as f:
        json.dump(database_isco, f, indent=2)
        
    print(f"JSON creato!")

if __name__ == "__main__":
    convert_isco_dict_to_json()