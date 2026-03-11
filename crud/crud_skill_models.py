import os
import pandas as pd
from typing import Dict, List
from models import Project, Skill, User, Course, Role

ED_COURSES_MEC_ENGINEER = "educational_offerings/courses/educational_offerings_esco_tagged.json"

# Skill gap analysis for a user
def skill_gap_user(user: User, role_list: List[Role]) -> User:
    user.skill_gap.clear()

    # Create a dictionary for quick lookup of user's current skills by URI
    user_skills_dict = {s.uri: s.level for s in user.current_skills}

    for role in role_list:
        matching = []
        partially_matching = []
        missing = []
        
        essential_skills = role.essential_skills
        total_req = len(essential_skills)

        score = 0.0
        # 1 point for each fully matched skill
        # level_user / level_required for partially matched skills
        # no points for missing skills
        
        for req_skill in essential_skills:
            req_uri = req_skill.uri
            req_level = req_skill.level
            
            if req_skill.uri in user_skills_dict:
                user_level = user_skills_dict[req_uri]
                if user_level >= req_level:
                    matching.append(req_skill)
                    score += 1.0
                else:
                    partial_score = user_level / req_level
                    score += partial_score
                    partially_matching.append({
                        "skill": req_skill,
                        "user_level": user_level
                    })
            else:
                missing.append(req_skill)

        match_pct = int((score / total_req) * 100) if total_req > 0 else 0
        
        role_gap_info = {
            'role_id': role.id,
            'role_title': role.title,
            'match_score': match_pct,
            'total_required': total_req,
            'matching_skills': matching,
            'partially_matching_skills': partially_matching,
            'missing_skills': missing
        }
        
        user.skill_gap.append(role_gap_info)

    return user

# Skill gap analysis for a project team
def skill_gap_project(project: Project, org_members: Dict[str, List[Skill]]) -> Project:
    team_skills_dict = {}
    
    for username in project.assigned_members:
        user_org_skills = org_members.get(username, [])
        
        for s in user_org_skills:
            if s.uri not in team_skills_dict or s.level > team_skills_dict[s.uri]:
                team_skills_dict[s.uri] = s.level

    project.skill_gap = []

    for role in project.target_roles:
        matching = []
        partially_matching = []
        missing = []
        
        essential_skills = role.essential_skills
        if isinstance(essential_skills, dict):
            essential_skills = list(essential_skills.values())
            
        total_req = len(essential_skills)
        score = 0.0

        for req_skill in essential_skills:
            req_uri = req_skill.uri
            req_level = req_skill.level
            
            if req_uri in team_skills_dict:
                best_team_level = team_skills_dict[req_uri]
                
                if best_team_level >= req_level:
                    matching.append(req_skill)
                    score += 1.0
                else:
                    partial_score = best_team_level / req_level
                    score += partial_score
                    partially_matching.append({
                        "skill": req_skill,
                        "team_best_level": best_team_level
                    })
            else:
                missing.append(req_skill)

        match_pct = int((score / total_req) * 100) if total_req > 0 else 0
        
        role_gap_info = {
            'role_id': role.id,
            'role_title': role.title,
            'match_score': match_pct,
            'total_required': total_req,
            'matching_skills': matching,
            'partially_matching_skills': partially_matching,
            'missing_skills': missing
        }
        
        project.skill_gap.append(role_gap_info)

    return project
    
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
        covered_skills_list = []
        
        for uri in row.esco_skills_match.keys():
            if uri in missing_skills_uri:
                skill_name = missing_skills_uri[uri]
                skill_obj = Skill(uri=uri, name=skill_name, level=1) # Level is set to 1 as a placeholder 
                covered_skills_list.append(skill_obj)

        if covered_skills_list:
            new_course = Course(
                title=row.title_de,
                ects=row.ects,
                description=row.learning_outcomes_de,
                skills_covered=covered_skills_list
            )
            recommended_courses.append(new_course)

    return recommended_courses