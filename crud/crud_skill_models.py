import os
import pandas as pd
from typing import List
from models import Project, User

EMP_OCCUPATION = "data/cedefop/employees/Employment_occupation.xlsx"
EMP_OCCUPATION_DETAIL = "data/cedefop/employees/Employment_occupation_detail.xlsx"

def skill_gap_user(user: User) -> User:
    
    # User skills in a set    
    user_skills_set = set()
    
    if user.current_skills:
        for skill in user.current_skills:
            user_skills_set.add(skill.lower().strip())
            
    user.skill_gap.clear()
    
    # Target roles iteration
    for role in user.target_roles:
        
        ess_str = role.get('essential_skills', '') or ""
        
        required_skills_list = [s.strip() for s in ess_str.split('\n') if s.strip()]
        
        matching = []
        missing = []
        
        for req_skill in required_skills_list:
            if req_skill.lower().strip() in user_skills_set:
                matching.append(req_skill)
            else:
                missing.append(req_skill)

        # Percentage
        total_req = len(required_skills_list)
        match_pct = int((len(matching) / total_req) * 100) if total_req > 0 else 0

        
        role_gap_info = {
            'role_id': role.get('id', ''),
            'role_title': role.get('title', ''),
            'match_score': match_pct,
            'total_required': total_req,
            'matching_skills': matching,
            'missing_skills': missing
        }
        user.skill_gap.append(role_gap_info)

    return user

def skill_gap_project(project: Project, members: List[User]) -> Project:
    
    team_skills_set = set()
    for user in members:
        if user.current_skills:
            for skill in user.current_skills:
                team_skills_set.add(skill.lower().strip())

    project.skill_gap.clear()

    for role in project.target_roles:
        
        ess_str = role.get('essential_skills', '') or ""
        required_skills_list = [s.strip() for s in ess_str.split('\n') if s.strip()]
        
        matching = []
        missing = []
        
        for req_skill in required_skills_list:
            if req_skill.lower().strip() in team_skills_set:
                matching.append(req_skill)
            else:
                missing.append(req_skill)

        # Percentage 
        total_req = len(required_skills_list)
        match_pct = int((len(matching) / total_req) * 100) if total_req > 0 else 0
        
        role_gap_info = {
            'role_id': role.get('id', ''),
            'role_title': role.get('title', ''),
            'match_score': match_pct,
            'total_required': total_req,
            'matching_skills': matching,
            'missing_skills': missing
        }
        project.skill_gap.append(role_gap_info)

    return project

def read_emp_occupation(country: str, isco_id: str, target_year: int) -> dict:
    
    isco_clean = isco_id.strip()
    file_path = ""

    if len(isco_clean) == 1:
        file_path = EMP_OCCUPATION
        target_isco = isco_clean
        
        col_idx_isco = 2  
        col_idx_data_start = 3
        
    else:
        file_path = EMP_OCCUPATION_DETAIL
        target_isco = isco_clean[:2] # First two characters
        
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

        results = {}
        start_year_file = 2010
        
        target_offset = target_year - start_year_file
        
        for i in range(target_offset + 1):
            year = start_year_file + i
            col_idx = col_idx_data_start + i
            
            if col_idx < len(df.columns):
                val = row.iloc[0, col_idx]
                
                if pd.notna(val):
                    results[str(year)] = int(val)
                else:
                    results[str(year)] = 0
            
        return results

    except Exception as e:
        print(f"Error reading Excel: {e}")
        return {"error": str(e)}