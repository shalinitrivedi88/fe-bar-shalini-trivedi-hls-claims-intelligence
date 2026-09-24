"""Claims Operations Console — Databricks App (FastAPI + React).

Serves the built React frontend (frontend/dist) and the JSON API:
  /api/summary          KPI row over the governed schema
  /api/triage-queue     ML-prioritized claims needing review
  /api/disposition-gap  the event-blindness metric
  /api/search           hybrid semantic+keyword search over Lakebase case narratives
  /api/chat             claims Q&A via the governed model endpoint
"""
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from server.routes import summary, triage, search, chat

app = FastAPI(title="Claims Operations Console")
app.include_router(summary.router)
app.include_router(triage.router)
app.include_router(search.router)
app.include_router(chat.router)

_DIST = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.isdir(_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(_DIST, "assets")), name="assets")

    @app.get("/")
    def index():
        return FileResponse(os.path.join(_DIST, "index.html"))
