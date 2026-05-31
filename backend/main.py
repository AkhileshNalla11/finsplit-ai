"""FinSplit AI — FastAPI backend.

Three endpoints power the app:
  POST /api/split        parse a description into a split (+ store it)
  POST /api/correct      apply a plain English correction (stored under a new id)
  GET  /api/split/{id}   fetch a stored split for the shareable link
"""

import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import claude_service
import supabase_service
from models import CorrectRequest, SplitRequest

# override=True so values in backend/.env win over any empty/stale ambient vars.
# On Railway there is no .env file, so real platform env vars are used unchanged.
load_dotenv(override=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("finsplit")

app = FastAPI(title="FinSplit AI", version="1.0.0")

# CORS: Vite dev server + production Vercel domain (configurable).
_default_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
_frontend_origin = os.environ.get("FRONTEND_ORIGIN")
allow_origins = _default_origins + ([_frontend_origin] if _frontend_origin else [])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
@app.get("/health")
def health():
    return {"status": "ok"}


MAX_DESCRIPTION_CHARS = 2000
MAX_CORRECTION_CHARS = 500


@app.post("/api/split")
def create_split(req: SplitRequest):
    description = (req.description or "").strip()
    if not description:
        raise HTTPException(status_code=400, detail="Description is required.")
    if len(description) > MAX_DESCRIPTION_CHARS:
        raise HTTPException(
            status_code=400,
            detail=f"Description is too long ({len(description)} chars). Please keep it under {MAX_DESCRIPTION_CHARS} characters.",
        )

    try:
        result = claude_service.parse_split(description)
    except claude_service.ClaudeError as exc:
        logger.error("Split parsing failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to parse the description.") from exc

    split_id = supabase_service.store_split(result)
    return {"id": split_id, "result": result}


@app.post("/api/correct")
def correct_split(req: CorrectRequest):
    correction = (req.correction or "").strip()
    if not correction:
        raise HTTPException(status_code=400, detail="Correction is required.")
    if len(correction) > MAX_CORRECTION_CHARS:
        raise HTTPException(
            status_code=400,
            detail=f"Correction is too long ({len(correction)} chars). Please keep it under {MAX_CORRECTION_CHARS} characters.",
        )

    try:
        result = claude_service.apply_correction(
            original_description=req.original_description,
            previous_result=req.previous_result,
            correction=correction,
        )
    except claude_service.ClaudeError as exc:
        logger.error("Correction failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to apply the correction.") from exc

    split_id = supabase_service.store_split(result)
    return {"id": split_id, "result": result}


@app.get("/api/split/{split_id}")
def get_split(split_id: str):
    row = supabase_service.fetch_split(split_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Split not found.")
    return {
        "id": row["id"],
        "result": row["data"],
        "created_at": row.get("created_at"),
    }
