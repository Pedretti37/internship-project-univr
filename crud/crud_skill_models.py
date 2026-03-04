import os
import pandas as pd
from typing import Dict, List
from models import Project, User, Course, Role
from datetime import datetime

EMP_OCCUPATION = "data/cedefop/employees/Employment_occupation.xlsx"
EMP_OCCUPATION_DETAIL = "data/cedefop/employees/Employment_occupation_detail.xlsx"
ED_COURSES_MEC_ENGINEER = "educational_offerings/courses/educational_offerings_esco_tagged.json"

def skill_gap_user(user: User, role_list: List[Role]) -> User:
    user.skill_gap.clear()

    for role in role_list:
        matching = {}
        missing = {}
        
        essential_skills = role.essential_skills
        
        for uri, skill in essential_skills.items():
            if uri in user.current_skills:
                matching[uri] = skill
            else:
                missing[uri] = skill

        # print(f"Matching: {matching.values()}")
        # print(f"Missing: {missing.values()}")

        total_req = len(essential_skills)
        match_pct = int((len(matching) / total_req) * 100) if total_req > 0 else 0
        
        role_gap_info = {
            'role_id': role.id,
            'role_title': role.title,
            'match_score': match_pct,
            'total_required': total_req,
            'matching_skills': matching,
            'missing_skills': missing
        }
        
        user.skill_gap.append(role_gap_info)

    return user

def skill_gap_project(project: Project, members: List[User]) -> Project:
    
    team_skills = {}
    for user in members:
        if user.current_skills:
            for uri, skill in user.current_skills.items():
                team_skills[uri] = skill

    if hasattr(project, 'skill_gap'):
        project.skill_gap.clear()
    else:
        project.skill_gap = []

    for role in project.target_roles:
        required_skills = role.essential_skills

        matching = {}
        missing = {}
        
        for uri, req_skill in required_skills.items():
            if uri in team_skills:
                matching[uri] = req_skill
            else:
                missing[uri] = req_skill

        # Percentage 
        total_req = len(required_skills)
        match_pct = int((len(matching) / total_req) * 100) if total_req > 0 else 0
        
        role_gap_info = {
            'role_id': role.id,
            'role_title': role.title,
            'match_score': match_pct,
            'total_required': total_req,
            'matching_skills': matching,
            'missing_skills': missing
        }
        project.skill_gap.append(role_gap_info)

    return project

# Forecast employment trends for a given ISCO code and country
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
    
# Recommend courses for skill gap
def recommend_courses_for_skill_gap(missing_skills_uri: Dict[str, str]) -> List[Course]:
    recommended_courses = []
    
    # Reading educational offerings file
    if not os.path.exists(ED_COURSES_MEC_ENGINEER):
        print(f"Educational offerings file not found: {ED_COURSES_MEC_ENGINEER}")
        return []
    
    try:
        courses_df = pd.read_json(ED_COURSES_MEC_ENGINEER)
    except Exception as e:
        print(f"Error reading educational offerings file: {e}")
        return []
    
    # print(courses_df.head())  # Debug: Check the structure of the DataFrame

    for row in courses_df.itertuples():
        matched_skills = {
            uri: missing_skills_uri[uri] 
            for uri in row.esco_skills_match.keys() 
            if uri in missing_skills_uri
        }

        if matched_skills:
            new_course = Course(
                title=row.title_de,
                ects=row.ects,
                description=row.learning_outcomes_de,
                skills_covered=matched_skills
            )
            recommended_courses.append(new_course)

    return recommended_courses