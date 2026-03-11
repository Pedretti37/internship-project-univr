import os
import pandas as pd
from typing import Dict, List
from models import Course, Skill

ED_COURSES_MEC_ENGINEER = "educational_offerings/courses/educational_offerings_esco_tagged.json"

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