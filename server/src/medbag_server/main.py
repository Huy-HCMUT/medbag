"""FastAPI app. Run:  uv run uvicorn medbag_server.main:app --reload --host 0.0.0.0 --port 8000

Simulator: http://localhost:8000/sim     Family app: http://<laptop IP>:8000/family
Endpoints follow the table in the Functional Requirements doc; add them one by one.
Each endpoint reads the request, calls one function in pipelines.py, saves to db and replies.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from medbag_common.types import Settings

from . import db
from .config import GEMINI_API_KEY
from .pipelines import Models

WEB = Path(__file__).resolve().parents[2] / "web"


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init()
    # Load YOLO26n, DINOv2 and the Gemini client here, once; pipelines.py passes them on.
    app.state.models = Models(yolo=None, dino=None, gemini=None)  # e.g. gemini=genai.Client(api_key=GEMINI_API_KEY)
    yield


app = FastAPI(title="The Talking Medicine Bag", lifespan=lifespan)


@app.get("/api/health")
def health():
    return {"ok": True, "gemini_key": bool(GEMINI_API_KEY)}


@app.get("/api/settings")
def get_settings() -> Settings:
    return Settings()  # TODO: read from the settings table


app.mount("/sim", StaticFiles(directory=WEB / "sim", html=True), name="sim")
app.mount("/family", StaticFiles(directory=WEB / "family", html=True), name="family")
