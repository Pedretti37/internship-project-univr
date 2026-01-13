from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse
from config import templates
from esco import escoAPI

router = APIRouter()

### --- Guest Home --- ###
@router.get("/guest_home", response_class=HTMLResponse)
async def gust_home(request: Request):
    return templates.TemplateResponse("guest_home.html", {"request": request})

### --- Obtain roles from Guest Input --- ###
@router.post("/role_list_guest", response_class=HTMLResponse)
async def role_list_guest(request: Request, search: str = Form(...)):
    role = search.title().strip()

    role_list = escoAPI.get_esco_occupations_list(role, limit=5)

    return templates.TemplateResponse("guest_home.html", {
        "request": request,
        "results": role_list,
        "last_search": search
    })