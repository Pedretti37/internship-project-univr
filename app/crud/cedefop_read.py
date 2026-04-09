# Forecast employment occupation trends for a given ISCO code and country
def read_emp_occupation(db_cedefop: dict, country: str, isco_id: str) -> dict:
    country_clean = country.strip().title()
    isco_clean = isco_id.strip()

    # 1 or 2 digit ISCO code
    if len(isco_clean) == 1:
        source_key = "emp_occupation"
        target_isco = isco_clean
    else:
        source_key = "emp_occupation_detail"
        target_isco = isco_clean[:2]

    # Dict loaded in RAM during startup
    data = db_cedefop.get(source_key, {}).get(country_clean, {}).get(target_isco)

    if not data:
        return {"error": f"Data not found for {country_clean} and ISCO code {target_isco}"}

    return data
    
# Forecast employment trends for sector
def read_emp_sector_occupation(db_cedefop: dict, country: str, sector: str, isco_id: str) -> dict:
    # Optional
    if not sector:
        return {}
    
    country_clean = country.strip().title()
    isco_clean = isco_id.strip()
    
    if len(isco_clean) < 2:
        return {"error": "Sector detail requires at least a 2-digit ISCO code (e.g., '25')"}
    
    isco_2d = isco_clean[:2]

    # Dict loaded in RAM during startup
    data = db_cedefop.get("sectors", {}).get(country_clean, {}).get(isco_2d).get("sectors", {}).get(sector.strip(), {})

    if not data:
        return {"error": f"Data not found for {country_clean}, ISCO code {isco_2d} and sector {sector.strip()}"}

    return data

# Forecast qualifications for a given ISCO code and country
def read_qualifications(db_cedefop: dict, country: str, isco_id: str) -> dict:
    country_clean = country.strip().title()
    isco_clean = isco_id.strip()

    target_isco = isco_clean[:2] if len(isco_clean) >= 2 else isco_clean
    
    data = db_cedefop.get("qualifications", {}).get(country_clean, {}).get(target_isco)

    if not data:
        return {"error": f"Qualification data not found for {country_clean} and ISCO code {target_isco}"}

    return data

# Forecast job openings
def read_job_openings(db_cedefop: dict, country: str, isco_id: str) -> dict:
    country_clean = country.strip().title()
    target_isco = isco_id.strip()[0] # Using 1-digit ISCO for job openings

    data = db_cedefop.get("job_openings", {}).get(country_clean, {}).get(target_isco)

    if not data:
        return {"error": f"Job Openings data not found for {country_clean} and ISCO code {target_isco}"}
    
    return data