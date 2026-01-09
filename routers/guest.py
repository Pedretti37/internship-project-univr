from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse
from config import templates
import crud.crud_skill_models as crud_skill_models

router = APIRouter()

### --- Guest Home --- ###
@router.get("/guest_home", response_class=HTMLResponse)
async def gust_home(request: Request):
    return templates.TemplateResponse("guest_home.html", {"request": request})

### --- Obtain skills from Guest Input --- ###
@router.post("/extract_general_skill_models", response_class=HTMLResponse)
async def extract_general_skill_models(request: Request, search: str = Form(...)):
    role = search.title().strip()

    extracted_models = {}

    skill_models_list = crud_skill_models.extracting_skill_models(role)
    if skill_models_list:
        extracted_models[role] = skill_models_list
    
    
    return templates.TemplateResponse("guest_home.html", {
        "request": request,
        "results": extracted_models,
        "last_search": search
    })