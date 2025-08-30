#!/usr/bin/env python3
import argparse
import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, time
from typing import Dict, Tuple

from tortoise import Tortoise, fields
from tortoise.models import Model

try:
    # Python 3.9+
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    from backports.zoneinfo import ZoneInfo  # type: ignore


# ----------------------------
# Models (Tortoise ORM)
# ----------------------------
class MoonSign(Model):
    id = fields.IntField(pk=True)
    en_name = fields.CharField(max_length=50)
    ar_name = fields.CharField(max_length=50)
    fa_name = fields.CharField(max_length=50)

    events: fields.ReverseRelation["Calendar"]

    class Meta:
        table = "moon_signs"


class Phase(Model):
    id = fields.IntField(pk=True)
    en_name = fields.CharField(max_length=50)
    ar_name = fields.CharField(max_length=50)
    fa_name = fields.CharField(max_length=50)

    events: fields.ReverseRelation["Calendar"]

    class Meta:
        table = "phases"


class Recommendation(Model):
    id = fields.IntField(pk=True)
    en_name = fields.CharField(max_length=300)
    ar_name = fields.CharField(max_length=300)
    fa_name = fields.CharField(max_length=300)

    events: fields.ReverseRelation["Calendar"]

    class Meta:
        table = "recommendations"


class Calendar(Model):
    id = fields.IntField(pk=True)

    # Storing UTC components as strings, per your schema.
    utc_year = fields.CharField(max_length=4)
    utc_month = fields.CharField(max_length=2)
    utc_day = fields.CharField(max_length=2)

    moon_sign = fields.ForeignKeyField("models.MoonSign", related_name="events")
    phase = fields.ForeignKeyField("models.Phase", related_name="events")
    recommendation = fields.ForeignKeyField("models.Recommendation", related_name="events")

    # Optional forward relation hints
    moon_sign: fields.ForeignKeyRelation[MoonSign]
    phase: fields.ForeignKeyRelation[Phase]
    recommendation: fields.ForeignKeyRelation[Recommendation]

    class Meta:
        table = "calendars"
        # Prevent duplicate day rows if run multiple times:
        # Note: This is a partial safeguard; it won't stop duplicates with different FKs.
        # unique_together = (("utc_year", "utc_month", "utc_day"),)


# ----------------------------
# Helpers
# ----------------------------
async def init_orm(db_url: str):
    await Tortoise.init(
        db_url=db_url,
        modules={"models": ["__main__"]},
    )
    # Create tables if not present
    await Tortoise.generate_schemas(safe=True)


@dataclass
class Caches:
    signs: Dict[str, MoonSign]
    phases: Dict[str, Phase]
    recs: Dict[str, Recommendation]


async def get_or_create_sign(cache: Dict[str, MoonSign], data: Dict) -> MoonSign:
    key = data["en"].strip()
    if key in cache:
        return cache[key]
    obj = await MoonSign.get_or_none(en_name=key)
    if obj is None:
        obj = await MoonSign.create(
            en_name=key,
            ar_name=data.get("ar", "").strip(),
            fa_name=data.get("fa", "").strip(),
        )
    cache[key] = obj
    return obj


async def get_or_create_phase(cache: Dict[str, Phase], data: Dict) -> Phase:
    key = data["en"].strip()
    if key in cache:
        return cache[key]
    obj = await Phase.get_or_none(en_name=key)
    if obj is None:
        obj = await Phase.create(
            en_name=key,
            ar_name=data.get("ar", "").strip(),
            fa_name=data.get("fa", "").strip(),
        )
    cache[key] = obj
    return obj


async def get_or_create_recommendation(cache: Dict[str, Recommendation], data: Dict) -> Recommendation:
    # We use English text as the key (consistent across the dataset),
    # and store AR/FA from the first occurrence.
    key = data["en"].strip()
    if key in cache:
        return cache[key]
    obj = await Recommendation.get_or_none(en_name=key)
    if obj is None:
        obj = await Recommendation.create(
            en_name=key,
            ar_name=data.get("ar", "").strip(),
            fa_name=data.get("fa", "").strip(),
        )
    cache[key] = obj
    return obj


def compute_utc_components(local_date_str: str, local_time_str: str, tz_name: str) -> Tuple[str, str, str]:
    """
    Convert local date + local time (e.g., 12:00) in tz_name to UTC,
    return (year, month, day) as zero-padded strings.
    """
    # Expect date like "2025-01-01" and time like "12:00"
    local_dt = datetime.fromisoformat(f"{local_date_str}T{local_time_str}")
    aware_local = local_dt.replace(tzinfo=ZoneInfo(tz_name))
    utc_dt = aware_local.astimezone(ZoneInfo("UTC"))
    return (f"{utc_dt.year:04d}", f"{utc_dt.month:02d}", f"{utc_dt.day:02d}")


async def load_calendar(json_path: str, db_url: str):
    await init_orm(db_url)

    with open(json_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    tz_name = payload.get("timezone", "Asia/Baghdad")
    local_time_reference = payload.get("localTimeReference", "12:00")

    caches = Caches(signs={}, phases={}, recs={})

    # Collect Calendar objects for bulk create
    calendar_rows = []

    days = payload.get("days", [])
    for day in days:
        date_str = day["date"]  # e.g., "2025-01-01"

        moon_sign = await get_or_create_sign(caches.signs, day["moonSign"])
        phase = await get_or_create_phase(caches.phases, day["phase"])
        rec = await get_or_create_recommendation(caches.recs, day["recommendations"])

        y, m, d = compute_utc_components(date_str, local_time_reference, tz_name)

        calendar_rows.append(
            Calendar(
                utc_year=y,
                utc_month=m,
                utc_day=d,
                moon_sign=moon_sign,
                phase=phase,
                recommendation=rec,
            )
        )

    if calendar_rows:
        # Bulk insert Calendar rows
        await Calendar.bulk_create(calendar_rows, batch_size=200)

    # Report
    total_signs = await MoonSign.all().count()
    total_phases = await Phase.all().count()
    total_recs = await Recommendation.all().count()
    total_calendar = await Calendar.all().count()
    print(f"Inserted/seen: {len(caches.signs)} signs, {len(caches.phases)} phases, {len(caches.recs)} recommendations.")
    print(f"Totals in DB   signs={total_signs}, phases={total_phases}, recs={total_recs}, calendar={total_calendar}")

    await Tortoise.close_connections()


# def main():
#     parser = argparse.ArgumentParser(description="Load moon calendar JSON into Tortoise ORM database.")
#     parser.add_argument("--json", required=True, help="Path to the JSON file (2025–2026 data).")
#     parser.add_argument("--db", default="sqlite://db.sqlite3", help="Database URL (e.g., sqlite://db.sqlite3 or postgres://user:pass@host:5432/db)")
#     # args = parser.parse_args()
#     asyncio.run(load_calendar("app/data/calendar/astrology/lunar_calendar_baghdad_2026.json", "postgres://root:a82a33ba09ccef637b35a8ae04c95478@localhost:5432/calendar"))

# if __name__ == "__main__":
#     main()
