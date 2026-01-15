from models import User

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