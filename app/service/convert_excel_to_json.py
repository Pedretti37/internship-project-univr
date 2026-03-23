import pandas as pd
import json

FILE_EXCEL = "None"

def convert_isco_dict_to_json():
    print("Reading excel file...")
    
    df = pd.read_excel(FILE_EXCEL)
    
    # Managing empty fields
    df = df.fillna("")
    
    database_isco = {}
    
    for index, row in df.iterrows():
        codice = str(row['ISCO 08 Code']).strip()
        titolo = str(row['Title EN']).strip()
        descrizione = str(row['Definition']).strip()
        task = str(row['Tasks include']).strip()
        
        if codice:
            database_isco[codice] = {
                "title": titolo,
                "description": descrizione,
                "tasks": task
            }
            
    with open('data/cedefop/db_isco_definitions.json', 'w') as f:
        json.dump(database_isco, f, indent=2)
        
    print(f"JSON created!")

if __name__ == "__main__":
    convert_isco_dict_to_json()