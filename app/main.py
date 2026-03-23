import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from app.service.config import templates
from app.routers import user, org, guest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "cedefop"

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
        full_path = DATA_PATH / filename
        try:
            with open(full_path, "r", encoding='utf-8') as f:
                app.state.cedefop[key] = json.load(f)
            #print(f"{filename} uploaded correctly.")
        except FileNotFoundError:
            print(f"Error: {filename} does not exists in {DATA_PATH}")
        except Exception as e:
            print(f"Error while loading {filename}: {e}")

    yield  # App is READY   

    # --- SHUTDOWN ---
    app.state.cedefop.clear()

# --- APP Initialization ---
app = FastAPI(lifespan=lifespan)

# Setting static materials (CSS, images)
STATIC_PATH = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_PATH)), name="static")

# Linking routers
app.include_router(user.router)
app.include_router(org.router)
app.include_router(guest.router)

### --- Root --- ###
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})