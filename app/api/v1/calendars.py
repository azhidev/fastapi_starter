from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from tortoise.exceptions import DoesNotExist
from tortoise.expressions import Q

from app.core.security import require_active_user
from app.models.calendar import Calendar
from app.repositories.task import TaskRepository
from app.schemas.task import TaskRead, TaskCreate

router = APIRouter(prefix="/calendar", tags=["calendar"])
repo = TaskRepository()

# app.py
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from datetime import date, timedelta, datetime, timezone
from typing import Dict, Any, List, Tuple, Optional, Literal
import os, json, math
from app.models.country import Province
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
import pytz  # pip install pytz


class RelatedBase(BaseModel):
    id: int
    en_name: str
    ar_name: str
    fa_name: str

class CalendarItem(BaseModel):
    id: int
    # always include the UTC day stored in DB
    utc_date: date = Field(..., description="UTC calendar date of the record")
    # also expose the date as seen in the requested country's local time
    local_date: date = Field(..., description="Local date for requested country")
    moon_sign: RelatedBase
    phase: RelatedBase
    recommendation: RelatedBase

    class Config:
        orm_mode = True
class LunarResponse(BaseModel):
    country: str
    timezone: str
    start_local: date
    end_local: date
    start_utc: date
    end_utc: date
    items: List[CalendarItem]

def _country_to_timezone(country_shortcode: str) -> str:
    """
    Resolve an IANA timezone string from a 2-letter ISO country code using pytz.
    Prefer the most populous zone if multiple are available.
    """
    cc = (country_shortcode or "IQ").upper()
    try:
        zones = pytz.country_timezones(cc)
        if not zones:
            return "UTC"
        # crude preference: pick one with a city (no Etc/*), else first
        for z in zones:
            if not z.startswith("Etc/"):
                return z
        return zones[0]
    except Exception:
        return "UTC"

def _parse_date_yyyy_mm_dd(value: Optional[str], field_name: str) -> Optional[date]:
    if value is None:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=422, detail=f"{field_name} must be in YYYY-MM-DD format")

def _month_bounds(d: date) -> (date, date):
    first = d.replace(day=1)
    if first.month == 12:
        next_month_first = first.replace(year=first.year + 1, month=1, day=1)
    else:
        next_month_first = first.replace(month=first.month + 1, day=1)
    last = next_month_first - timedelta(days=1)
    return first, last

def _local_range_to_utc_date_span(
    start_local: date, end_local: date, tzname: str
) -> (datetime, datetime, date, date):
    """
    Convert a local [start_date .. end_date] (inclusive by local calendar date)
    into UTC datetime span and the inclusive UTC date bounds that intersect that local span.
    """
    tz = pytz.timezone(tzname)
    # local midnight at start
    start_local_dt = tz.localize(datetime.combine(start_local, datetime.min.time()))
    # local midnight after end date
    end_local_next_dt = tz.localize(datetime.combine(end_local + timedelta(days=1), datetime.min.time()))
    # map to UTC instants
    start_utc_dt = start_local_dt.astimezone(pytz.UTC)
    end_utc_dt = end_local_next_dt.astimezone(pytz.UTC) - timedelta(microseconds=1)

    # inclusive UTC calendar dates covered by that instant span
    start_utc_date = start_utc_dt.date()
    end_utc_date = end_utc_dt.date()
    return start_utc_dt, end_utc_dt, start_utc_date, end_utc_date


def _date_iter(d0: date, d1: date):
    cur = d0
    while cur <= d1:
        yield cur
        cur = cur + timedelta(days=1)


def _has_attr(model_cls, name: str) -> bool:
    # Tortoise models expose fields via _meta.fields_map
    return hasattr(model_cls, "_meta") and (name in getattr(model_cls._meta, "fields_map", {}))

@router.get("/lunar", response_model=LunarResponse)
async def get_lunar_range(
    start: Optional[str] = Query(None, description="Start date in YYYY-MM-DD (local to country)"),
    end: Optional[str] = Query(None, description="End date in YYYY-MM-DD (local to country)"),
    country_shortcode: str = Query("IQ", min_length=2, max_length=2, description="ISO 3166-1 alpha-2 country code"),
):
    """
    Returns calendar entries (with related moon_sign, phase, recommendation) for the requested local-date range.
    Dates are interpreted in the given country's local timezone; results are mapped to the underlying UTC-day records.

    If no start/end are provided, returns the current month's data in the given country's timezone.
    """

    # Resolve timezone from country
    tzname = _country_to_timezone(country_shortcode)

    # Decide local date range
    today_local = datetime.now(pytz.timezone(tzname)).date()
    if start is None or end is None:
        # default: whole current month in local tz
        month_start, month_end = _month_bounds(today_local)
        start_local = month_start
        end_local = month_end
    else:
        start_local = _parse_date_yyyy_mm_dd(start, "start")  # type: ignore
        end_local = _parse_date_yyyy_mm_dd(end, "end")        # type: ignore
        if start_local > end_local:
            raise HTTPException(status_code=422, detail="start cannot be after end")

    # Convert that local span to UTC date window
    _, _, start_utc_date, end_utc_date = _local_range_to_utc_date_span(start_local, end_local, tzname)

    # Build query for either schema flavor (single DateField vs split CharFields)
    has_single_date = _has_attr(Calendar, "utc_date")

    if has_single_date:
        # Simple range filter
        queryset = (
            Calendar.filter(utc_date__gte=start_utc_date, utc_date__lte=end_utc_date)
            .prefetch_related("moon_sign", "phase", "recommendation")
            .order_by("utc_date")
        )
    else:
        # Generate OR of (Y,M,D) tuples for all UTC dates in the span
        q = Q()
        for d in _date_iter(start_utc_date, end_utc_date):
            q |= Q(
                utc_year=str(d.year).zfill(4),
                utc_month=str(d.month).zfill(2),
                utc_day=str(d.day).zfill(2),
            )
        queryset = (
            Calendar.filter(q)
            .prefetch_related("moon_sign", "phase", "recommendation")
            .order_by("utc_year", "utc_month", "utc_day")
        )

    rows = await queryset

    # Shape response items with both UTC and local dates
    items: List[Dict[str, Any]] = []
    tz = pytz.timezone(tzname)

    for r in rows:
        # get the UTC date stored in DB
        if has_single_date:
            utc_d: date = r.utc_date  # type: ignore[attr-defined]
        else:
            # combine split fields
            utc_d = date(int(r.utc_year), int(r.utc_month), int(r.utc_day))

        # compute what local calendar date that UTC day corresponds to at local time
        # We choose 12:00 UTC on that day to avoid DST edge at midnight UTC -> local date won't be off by one.
        local_date = datetime.combine(utc_d, datetime.min.time(), tzinfo=timezone.utc).astimezone(tz).date()

        items.append(
            {
                "id": r.id,
                "utc_date": utc_d,
                "local_date": local_date,
                "moon_sign": {
                    "id": r.moon_sign.id,
                    "en_name": r.moon_sign.en_name,
                    "ar_name": r.moon_sign.ar_name,
                    "fa_name": r.moon_sign.fa_name,
                },
                "phase": {
                    "id": r.phase.id,
                    "en_name": r.phase.en_name,
                    "ar_name": r.phase.ar_name,
                    "fa_name": r.phase.fa_name,
                },
                "recommendation": {
                    "id": r.recommendation.id,
                    "en_name": r.recommendation.en_name,
                    "ar_name": r.recommendation.ar_name,
                    "fa_name": r.recommendation.fa_name,
                },
            }
        )

    return LunarResponse(
        country=country_shortcode.upper(),
        timezone=tzname,
        start_local=start_local,
        end_local=end_local,
        start_utc=start_utc_date,
        end_utc=end_utc_date,
        items=items,
    )

# @router.get("/lunar-bc")
def get_lunar_range_bc(
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


class Times(BaseModel):
    fajr: str            # اذان صبح
    sunrise: str         # طلوع آفتاب
    dhuhr: str           # اذان ظهر
    sunset: str          # غروب آفتاب
    maghrib: str         # اذان مغرب
    midnight: str        # نیمه شب


class PrayerTimesResponse(BaseModel):
    province_code: str
    city_name: str
    date: str
    lat: float
    lng: float
    tz: float
    params: dict
    times: Times
def _equation_of_time_and_declination(n: int):
    gamma = 2 * math.pi / 365 * (n - 1)
    eot = 229.18 * (
        0.000075
        + 0.001868 * math.cos(gamma)
        - 0.032077 * math.sin(gamma)
        - 0.014615 * math.cos(2 * gamma)
        - 0.040849 * math.sin(2 * gamma)
    )
    decl = (
        0.006918
        - 0.399912 * math.cos(gamma)
        + 0.070257 * math.sin(gamma)
        - 0.006758 * math.cos(2 * gamma)
        + 0.000907 * math.sin(2 * gamma)
        - 0.002697 * math.cos(3 * gamma)
        + 0.00148 * math.sin(3 * gamma)
    )
    return eot, decl

def _solar_noon_minutes(lon_east_deg: float, tz_hours: float, eot_min: float) -> float:
    time_offset = eot_min + 4 * lon_east_deg - 60 * tz_hours
    return 720 - time_offset

def _event_time_by_zenith(lat_rad: float, decl: float, solar_noon_min: float, zenith_deg: float, sign: int) -> float:
    # sign -1 = morning, +1 = evening
    zen = math.radians(zenith_deg)
    cos_omega = (math.cos(zen) - math.sin(lat_rad) * math.sin(decl)) / (math.cos(lat_rad) * math.cos(decl))
    cos_omega = max(-1.0, min(1.0, cos_omega))
    omega_deg = math.degrees(math.acos(cos_omega))
    return solar_noon_min + sign * 4 * omega_deg

def _to_local_datetime(d: date, minutes_from_midnight: float, tz_hours: float) -> datetime:
    m = minutes_from_midnight
    # normalize across day bounds
    while m < 0:
        d = d - timedelta(days=1)
        m += 1440
    while m >= 1440:
        d = d + timedelta(days=1)
        m -= 1440
    hh = int(m // 60)
    mm = int(round(m % 60))
    if mm == 60:
        mm = 0
        hh += 1
    tz = timezone(timedelta(hours=int(tz_hours), minutes=int(round((tz_hours - int(tz_hours)) * 60))))
    return datetime(d.year, d.month, d.day, hh, mm, tzinfo=tz)

def compute_six_times(
    the_date: date,
    lat_deg: float,
    lon_east_deg: float,
    tz_hours: float,
    *,
    fajr_angle: float = 17.7,
    maghrib_offset_min: float = 4.0,
    midnight_mode: Literal["maghrib_to_fajr", "sunset_to_sunrise"] = "maghrib_to_fajr",
):
    lat_rad = math.radians(lat_deg)
    n = the_date.timetuple().tm_yday
    eot, decl = _equation_of_time_and_declination(n)
    solar_noon_min = _solar_noon_minutes(lon_east_deg, tz_hours, eot)

    # Sunrise/Sunset with refraction & solar radius
    sunrise_min = _event_time_by_zenith(lat_rad, decl, solar_noon_min, 90.833, -1)
    sunset_min  = _event_time_by_zenith(lat_rad, decl, solar_noon_min, 90.833, +1)

    # Fajr at twilight angle
    fajr_zenith = 90 + fajr_angle
    fajr_min = _event_time_by_zenith(lat_rad, decl, solar_noon_min, fajr_zenith, -1)

    # Dhuhr (solar noon)
    dhuhr_min = solar_noon_min

    # Maghrib as sunset + offset (set 0 to equal sunset)
    maghrib_min = sunset_min + maghrib_offset_min

    # Midnight (nisf al-layl)
    if midnight_mode == "maghrib_to_fajr":
        start_dt = _to_local_datetime(the_date, maghrib_min, tz_hours)
        end_dt = _to_local_datetime(the_date, fajr_min, tz_hours)
        if end_dt <= start_dt:
            end_dt = end_dt + timedelta(days=1)
    else:  # "sunset_to_sunrise"
        start_dt = _to_local_datetime(the_date, sunset_min, tz_hours)
        end_dt = _to_local_datetime(the_date, sunrise_min, tz_hours)
        if end_dt <= start_dt:
            end_dt = end_dt + timedelta(days=1)
    midnight_dt = start_dt + (end_dt - start_dt) / 2

    return {
        "fajr": _to_local_datetime(the_date, fajr_min, tz_hours),
        "sunrise": _to_local_datetime(the_date, sunrise_min, tz_hours),
        "dhuhr": _to_local_datetime(the_date, dhuhr_min, tz_hours),
        "sunset": _to_local_datetime(the_date, sunset_min, tz_hours),
        "maghrib": _to_local_datetime(the_date, maghrib_min, tz_hours),
        "midnight": midnight_dt,
    }

# ---------------------------
@router.get("/prayer-times/{province_code}", response_model=PrayerTimesResponse)
async def get_prayer_times_for_province(
    province_code: str,
    date_str: Optional[str] = Query(None, description="YYYY-MM-DD (defaults to today)"),
    fajr_angle: float = Query(17.7, ge=8.0, le=30.0, description="Twilight angle for Fajr"),
    maghrib_offset_min: float = Query(4.0, ge=0.0, le=20.0, description="Minutes after sunset for Maghrib"),
    # midnight_mode: Literal["maghrib_to_fajr", "sunset_to_sunrise"] = Query("maghrib_to_fajr"),
):
    city = await Province.get_or_none(iso_3166_2=province_code)
    if not city:
        raise HTTPException(status_code=404, detail="Province code not found")
    if city.lat is None or city.lng is None or city.tz is None:
        raise HTTPException(status_code=422, detail="lat/lng/tz not set for this province")

    # parse date or use today in that locale's tz
    if date_str:
        try:
            the_date = date.fromisoformat(date_str)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
    else:
        # "today" relative to province tz
        tz = timezone(timedelta(hours=int(city.tz), minutes=int(round((city.tz - int(city.tz)) * 60))))
        the_date = datetime.now(tz=tz).date()

    times_dt = compute_six_times(
        the_date,
        city.lat,
        city.lng,
        city.tz,
        fajr_angle=fajr_angle,
        maghrib_offset_min=maghrib_offset_min,
        midnight_mode="maghrib_to_fajr",
    )

    def fmt(dt: datetime) -> str:
        return dt.strftime("%H:%M")

    payload = PrayerTimesResponse(
        province_code=city.iso_3166_2,
        city_name=city.name,
        date=the_date.isoformat(),
        lat=city.lat,
        lng=city.lng,
        tz=city.tz,
        params={
            "fajr_angle": fajr_angle,
            # "maghrib_offset_min": maghrib_offset_min,
            "midnight_mode": "maghrib_to_fajr",
            # "zenith_sunrise_sunset": 90.833,
        },
        times=Times(
            fajr=fmt(times_dt["fajr"]),
            sunrise=fmt(times_dt["sunrise"]),
            dhuhr=fmt(times_dt["dhuhr"]),
            sunset=fmt(times_dt["sunset"]),
            maghrib=fmt(times_dt["maghrib"]),
            midnight=fmt(times_dt["midnight"]),
        ),
    )
    return payload
