import json
import os
from models import Project

# Configuration
DATA_DIR_PROJECTS = "data/projects"
os.makedirs(DATA_DIR_PROJECTS, exist_ok=True)

def get_json_path(project_id: str) -> str:
    return os.path.join(DATA_DIR_PROJECTS, f"{project_id}.json")

def create_project(project: Project):
    file_path = get_json_path(project.id)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(project.model_dump(), indent=4))
    return project

def get_project(project_id: str) -> Project | None:
    path = get_json_path(project_id)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return Project(**data)
    except Exception:
        return None

def get_org_projects(org_id: str) -> list[Project]:
    projects = []
    if not os.path.exists(DATA_DIR_PROJECTS):
        return []

    for filename in os.listdir(DATA_DIR_PROJECTS):
        if filename.endswith(".json"):
            file_path = os.path.join(DATA_DIR_PROJECTS, filename)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get("org_id") == org_id:
                        projects.append(Project(**data))
            except Exception:
                continue
    return projects

### --- Update Project --- ###
def update_project(project: Project):
    path = get_json_path(project.id)
    
    if not os.path.exists(path):
        return

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(project.model_dump(), f, indent=4)
    except Exception as e:
        print(f"Error updating project: {e}") 

def add_target_role(project: Project, role_data: dict):
    # Avoid duplicates based on 'uri'
    if not any(r['uri'] == role_data['uri'] for r in project.target_roles):
        project.target_roles.append(role_data)
        update_project(project)
    return project