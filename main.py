from fastapi import FastAPI, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()

# Monta la cartella "static" per servire CSS e immagini
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configura la cartella dei template
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("authentication.html", {"request": request})

@app.post("/login", response_class=HTMLResponse)
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == "admin" and password == "1234":
        return RedirectResponse(url=f"/home?user={username}", status_code=status.HTTP_303_SEE_OTHER)
    else:
        return templates.TemplateResponse("authentication.html", {
            "request": request, 
            "error": "Invalid credentials. Please try again."
        })
    
@app.get("/home", response_class=HTMLResponse)
async def home(request: Request, user: str):
    return templates.TemplateResponse("home.html", {"request": request, "user": user})