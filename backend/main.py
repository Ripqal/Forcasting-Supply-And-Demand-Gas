from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from backend.routers import upload, dashboard
import os

app = FastAPI(title="Gas Forecasting API", version="1.0.0")

# Setup CORS to allow frontend to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(upload.router, prefix="/api/v1/upload", tags=["Upload"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["Dashboard"])

# Serve the frontend static files at /static/
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="frontend")

@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    """Serve the frontend dashboard"""
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        html = f.read()
    # Rewrite relative paths to /static/ so assets load correctly
    html = html.replace('href="style.css"', 'href="/static/style.css"')
    html = html.replace('src="app.js"', 'src="/static/app.js"')
    return HTMLResponse(content=html)
