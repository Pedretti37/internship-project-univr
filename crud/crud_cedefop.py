import os
import pandas as pd
from datetime import datetime


EMP_OCCUPATION = "data/cedefop/employees/Employment_occupation.xlsx"
EMP_OCCUPATION_DETAIL = "data/cedefop/employees/Employment_occupation_detail.xlsx"
EMP_SECTOR_OCCUPATION_DETAIL = "data/cedefop/employees/Employment_sector_occupation_detail.xlsx"

# Forecast employment occupation trends for a given ISCO code and country
def read_emp_occupation(country: str, isco_id: str) -> dict:
    
    isco_clean = isco_id.strip()
    file_path = ""

    # File and column selection based on ISCO code length
    if len(isco_clean) == 1:
        file_path = EMP_OCCUPATION
        target_isco = isco_clean
        col_idx_isco = 2  
        col_idx_data_start = 3
    else:
        file_path = EMP_OCCUPATION_DETAIL
        target_isco = isco_clean[:2]
        col_idx_isco = 2  
        col_idx_data_start = 4

    if not os.path.exists(file_path):
        return {"error": f"File not found: {file_path}"}

    try:
        df = pd.read_excel(file_path, header=0, sheet_name=1)

        if len(df.columns) <= col_idx_data_start:
            return {
                "error": f"Excel structure error. File has {len(df.columns)} columns, "
                         f"but we tried to read data starting at index {col_idx_data_start}."
            }

        col_country = df.columns[0]         
        col_isco_name = df.columns[col_idx_isco] 

        df[col_country] = df[col_country].astype(str).str.strip()
        df[col_isco_name] = df[col_isco_name].astype(str).str.strip()
        
        row = df[
            (df[col_country].str.lower() == str(country).strip().lower()) & 
            (df[col_isco_name] == str(target_isco))
        ]

        if row.empty:
            return {"error": f"No data found for Country '{country}' and ISCO '{target_isco}' in file {file_path}"}

        results = {
            "history": [], # List of Dicts: [{"year": "2010", "value": 1500}, ...]
            "trend": "Stable",
            "growth_pct": 0
        }

        this_year = datetime.now().year
        
        start_year_file = 2010
        current_col_idx = col_idx_data_start
        current_year = start_year_file

        val_now = None
        val_end = None

        while current_col_idx < len(df.columns):
            val = row.iloc[0, current_col_idx]
            
            if pd.notna(val):
                val_int = int(val)
                
                results["history"].append({
                    "year": str(current_year),
                    "value": val_int
                })

                if current_year == this_year:
                    val_now = val_int
                
                val_end = val_int

            current_col_idx += 1
            current_year += 1
            
        # Trend calculation
        if val_now and val_end and val_now > 0:
            pct_change = ((val_end - val_now) / val_now) * 100
            results["growth_pct"] = round(pct_change, 2)
            
            if pct_change > 5:
                results["trend"] = "Growing"
            elif pct_change < -5:
                results["trend"] = "Declining"
            else:
                results["trend"] = "Stable"
            
        return results

    except Exception as e:
        print(f"Error reading Excel: {e}")
        return {"error": str(e)}
    
# Forecast employment trends for sector
def read_emp_sector_occupation(country: str, sector: str, isco_id: str) -> dict:
    
    if not os.path.exists(EMP_SECTOR_OCCUPATION_DETAIL):
        return {"error": f"File not found: {EMP_SECTOR_OCCUPATION_DETAIL}"}