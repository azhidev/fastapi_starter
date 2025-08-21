from fastapi import APIRouter, Depends, HTTPException, status
from tortoise.exceptions import DoesNotExist

from app.core.security import require_active_user
from app.repositories.task import TaskRepository
from app.schemas.task import TaskRead, TaskCreate

router = APIRouter(prefix="/calendar", tags=["calendar"])
repo = TaskRepository()

# app.py
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from datetime import date, timedelta
from typing import Dict, Any, List, Tuple
import os, json

# app = FastAPI(title="Baghdad Lunar Calendar API", version="1.0")

# You can override these via environment variables if your files live elsewhere.
DATA_FILES = [
    os.getenv("BAGHDAD_2025_PATH") or "app/data/calendar/astrology/lunar_calendar_baghdad_2025.json",
    os.getenv("BAGHDAD_2026_PATH") or "app/data/calendar/astrology/lunar_calendar_baghdad_2026.json",
]


def _first_existing_path(path: str) -> str | None:
    """Return a real file path, trying with and without .json."""
    candidates = [path]
    if not path.endswith(".json"):
        candidates.append(path + ".json")
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


def _read_json(path: str) -> Dict[str, Any]:
    """Read a JSON file, handling optional UTF-8 BOM."""
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read().lstrip("\ufeff").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse JSON in {path}: {e}") from e


def _load_data() -> Tuple[Dict[str, Dict[str, Any]], str, str, List[str]]:
    """
    Load 'days' from the two calendar files and index by date string.
    Returns:
      - by_date: dict 'YYYY-MM-DD' -> day object
      - min_date: earliest date string
      - max_date: latest date string
      - loaded_files: list of file paths actually loaded
    """
    by_date: Dict[str, Dict[str, Any]] = {}
    min_d: str | None = None
    max_d: str | None = None
    loaded_files: List[str] = []

    for configured in DATA_FILES:
        path = _first_existing_path(configured)
        if not path:
            continue  # skip missing file
        payload = _read_json(path)
        loaded_files.append(path)
        for d in payload.get("days", []):
            ds = d.get("date")
            if not isinstance(ds, str):
                continue
            by_date[ds] = d
            if min_d is None or ds < min_d:
                min_d = ds
            if max_d is None or ds > max_d:
                max_d = ds

    if not by_date:
        raise RuntimeError(
            "No calendar data found. Ensure your files exist "
            "(lunar_calendar_baghdad_2025[.json], lunar_calendar_baghdad_2026[.json]) "
            "or set BAGHDAD_2025_PATH / BAGHDAD_2026_PATH."
        )

    return by_date, min_d or "", max_d or "", loaded_files


BY_DATE, MIN_DATE, MAX_DATE, LOADED_FILES = _load_data()


def _parse_iso(d: str) -> date:
    try:
        return date.fromisoformat(d)
    except Exception:
        raise HTTPException(status_code=422, detail=f"Invalid date format: '{d}'. Use YYYY-MM-DD.")


# @router.get("/health")
# def health():
#     return {
#         "status": "ok",
#         "available_date_range": {"min": MIN_DATE, "max": MAX_DATE},
#         "files": LOADED_FILES,
#         "total_days": len(BY_DATE),
#     }


@router.get("/lunar")
def get_lunar_range(
    start: str = Query(..., description="Start date in YYYY-MM-DD"),
    end: str = Query(..., description="End date in YYYY-MM-DD"),
    # include_missing: bool = Query(False, description="Include placeholders for dates that aren't in the files"),
    country_shortcode: str = "IQ"
):
    start_d = _parse_iso(start)
    end_d = _parse_iso(end)
    if start_d > end_d:
        raise HTTPException(status_code=400, detail="start must be <= end")

    results: List[Dict[str, Any]] = []
    missing: List[str] = []

    cur = start_d
    while cur <= end_d:
        key = cur.isoformat()
        entry = BY_DATE.get(key)
        if entry is not None:
            results.append(entry)
        else:
            missing.append(key)
            if include_missing:
                results.append({"date": key, "available": False})
        cur = cur + timedelta(days=1)

    payload: Dict[str, Any] = {
        "range": {"start": start, "end": end},
        "days": results,
    }
    if missing:
        payload["missing"] = missing

    return JSONResponse(payload)
