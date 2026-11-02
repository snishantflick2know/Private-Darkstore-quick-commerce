"""
Minimal FastAPI server for Shelf Pulse.

    pip install fastapi uvicorn
    uvicorn server_example:app --reload      # open http://localhost:8000

Replace build_dashboard() with queries against your SQLite data.
The returned dict must match SAMPLE in js/data.js (see README "API contract").
"""
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles

HERE = Path(__file__).parent
app = FastAPI(title="Shelf Pulse")


def build_dashboard(platform: str, period: str) -> dict:
    """Return the dashboard payload. Start by copying SAMPLE from js/data.js,
    then replace each block with a real query, one section at a time."""
    raise NotImplementedError("Build the payload from SQLite here")


@app.get("/api/dashboard")
def dashboard(platform: str = Query("Blinkit"), period: str = Query("7D")):
    return build_dashboard(platform, period)


# Serve index.html, css/ and js/ from this folder (mounted last so /api wins)
app.mount("/", StaticFiles(directory=HERE, html=True), name="static")
