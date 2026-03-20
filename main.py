import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from service.config import templates
from routers import user, org, guest

BASE_DIR = "data/cedefop/"
FILES_CONFIG = {
    "emp_occupation": "db_occupation.json",
    "emp_occupation_detail": "db_occupation_detail.json",
    "sectors": "db_sector_occupation.json",
    "qualifications": "db_qualifications.json",
    "job_openings": "db_job_openings.json",
    "isco_definitions": "db_isco_definitions.json"
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP: uploading data ---
    app.state.cedefop = {}

    for key, filename in FILES_CONFIG.items():
        try:
            with open(f"{BASE_DIR}{filename}", "r", encoding='utf-8') as f:
                app.state.cedefop[key] = json.load(f)
            #print(f"{filename} uploaded correctly.")
        except FileNotFoundError:
            print(f"Errore: Il file {filename} non esiste in {BASE_DIR}")
        except Exception as e:
            print(f"Errore critico durante il caricamento di {filename}: {e}")

    yield  # App is READY   

    # --- SHUTDOWN ---
    app.state.cedefop.clear()

# --- APP Initialization ---
app = FastAPI(lifespan=lifespan)

# Setting static materials (CSS, images)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Linking routers
app.include_router(user.router)
app.include_router(org.router)
app.include_router(guest.router)

### --- Root --- ###
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})