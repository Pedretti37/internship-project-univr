from typing import Dict, List
from models import Course, Organization

ED_COURSES_MEC_ENGINEER = "educational_offerings/courses/educational_offerings_esco_tagged.json"

# Recommend courses for skill gap
def recommend_courses_for_skill_gap(
    missing_skills_uri: Dict[str, str], 
    level: str, # 'individual', 'manager', o 'hr'
    current_orgname: str,
    all_organizations: List[Organization]
) -> List[Course]:
    
    recommended_courses = []
    
    # Categories
    hr_categories = ["Seminar", "Hands-on Session", "Industrial Training"]
    individual_categories = ["Online Course", "University Course", "Video Tutorial", "Webinar"]

    for org in all_organizations:
        is_own_org = (org.orgname == current_orgname)
        
        for course in org.courses:
            if is_own_org or course.is_public:
                
                should_include = False
                if level == 'hr':
                    if course.category in hr_categories:
                        should_include = True
                else:
                    if course.category in individual_categories:
                        should_include = True
                
                if should_include:
                    if any(s.uri in missing_skills_uri for s in course.skills_covered):
                        recommended_courses.append(course)


    ### --- Here we can add a function to research online courses not present in db --- ###

    return recommended_courses