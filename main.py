from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from config import templates

from routers import user, org, guest

app = FastAPI()

# Setting static materials (CSS, images)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Linking routers to main file
app.include_router(user.router)
app.include_router(org.router)
app.include_router(guest.router)

### --- Root --- ###
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
