from fastapi import APIRouter, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from app.service.config import templates
from app.esco import escoAPI

router = APIRouter()

### --- Guest Home --- ###
@router.get("/guest_home", response_class=HTMLResponse)
async def gust_home(request: Request):
    return templates.TemplateResponse("guest_home.html", {"request": request})

### --- Logout --- ###
@router.get("/guest_logout")
async def logout():
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    return response

### --- Obtain roles from Guest Input --- ###
@router.post("/role_list_guest", response_class=HTMLResponse)
async def role_list_guest(request: Request, search: str = Form(...)):
    role = search.title().strip()

    language = "en"
    role_list = escoAPI.get_esco_occupations_list(role, language=language, limit=10)

    return templates.TemplateResponse("guest_home.html", {
        "request": request,
        "results": role_list,
        "last_search": search
    })