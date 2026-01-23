import pdfplumber
import json
import re

def extract_modules_dhbw_optimized(pdf_path):
    modules = []
    
    print(f"Elaborazione file: {pdf_path}...")
    
    with pdfplumber.open(pdf_path) as pdf:
        # Iteration over pages
        for page in enumerate(pdf.pages):
            text = page.extract_text()
            if not text:
                continue
            
            # Module detection
            if "FORMALE ANGABEN ZUM MODUL" in text:
                module_data = {}
                
                parts = text.split("FORMALE ANGABEN ZUM MODUL")
                header_part = parts[0] # Title
                body_part = parts[1]   # Ects, Skills, etc.
                
                header_lines = [line.strip() for line in header_part.split('\n') if line.strip()]
                
                title_de = "Titolo sconosciuto"
                
                # Searching for ID and Title
                for line in reversed(header_lines):
                    if "(" in line and ")" in line and any(c.isdigit() for c in line):
                        title_match = re.match(r'^(.*?)\s*\(', line)
                        if title_match:
                            title_de = title_match.group(1).strip()
                        else:
                            title_de = line
                        break
                
                if title_de == "Titolo sconosciuto" and len(header_lines) >= 2:
                     title_de = header_lines[-2] 

                module_data['title_de'] = title_de

                # Ects Extraction
                ects_match = re.search(r'\d+\s+\d+\s+\d+\s+(\d+)', body_part)
                if ects_match:
                    module_data['ects'] = int(ects_match.group(1))
                else:
                    module_data['ects'] = None

                # Skills Extraction
                skills_start = body_part.find("QUALIFIKATIONSZIELE UND KOMPETENZEN")
                
                if skills_start != -1:
                    end_markers = ["LERNEINHEITEN UND INHALTE", "LITERATUR", "PRÜFUNGSVORLEISTUNGEN"]
                    skills_end = len(body_part)
                    
                    for marker in end_markers:
                        idx = body_part.find(marker, skills_start)
                        if idx != -1 and idx < skills_end:
                            skills_end = idx
                    
                    # Cleaning skills text
                    raw_skills = body_part[skills_start + len("QUALIFIKATIONSZIELE UND KOMPETENZEN"):skills_end]
                    clean_skills = re.sub(r'(FACHKOMPETENZ|METHODENKOMPETENZ|PERSONALE.*?KOMPETENZ|ÜBERGREIFENDE.*?KOMPETENZ)', '', raw_skills)
                    module_data['learning_outcomes_de'] = " ".join(clean_skills.split())
                else:
                    module_data['learning_outcomes_de'] = ""

                modules.append(module_data)

    return modules

# Example usage
pdf_filename = "M_T_Modulhandbuch.pdf"

try:
    data = extract_modules_dhbw_optimized(pdf_filename)
    print(f"\nRisultato: Trovati {len(data)} moduli.")
    
    if len(data) > 0:
        output_filename = "educational_offerings.json"
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"Database salvato correttamente in: {output_filename}")
    else:
        print("Nessun modulo trovato. Controlla se il PDF è scansionato (immagine) o testo.")

except FileNotFoundError:
    print(f"Errore: File '{pdf_filename}' non trovato.")
except Exception as e:
    print(f"Errore imprevisto: {e}")