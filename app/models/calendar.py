from tortoise import Tortoise, fields
from tortoise.models import Model

class MoonSign(Model):
    id = fields.IntField(pk=True)
    en_name = fields.CharField(max_length=50)
    ar_name = fields.CharField(max_length=50)
    fa_name = fields.CharField(max_length=50)

    # reverse accessor from Calendar.related_name="events"
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

    # If you can, prefer a single DateField:
    # utc_date = fields.DateField()
    # Otherwise keep split fields (use small max_lengths):
    utc_year = fields.CharField(max_length=4)
    utc_month = fields.CharField(max_length=2)
    utc_day = fields.CharField(max_length=2)

    moon_sign = fields.ForeignKeyField("models.MoonSign", related_name="events")
    phase = fields.ForeignKeyField("models.Phase", related_name="events")
    recommendation = fields.ForeignKeyField("models.Recommendation", related_name="events")

    # optional type hints for forward FKs
    moon_sign: fields.ForeignKeyRelation[MoonSign]
    phase: fields.ForeignKeyRelation[Phase]
    recommendation: fields.ForeignKeyRelation[Recommendation]

    class Meta:
        table = "calendars"
        # If using split date fields, this prevents duplicates:
        unique_together = (("utc_year", "utc_month", "utc_day"),)

# 👇 IMPORTANT: early init so relations exist when Pydantic models are created
# Replace "yourapp.models" with the REAL import path of THIS module.
Tortoise.init_models(["app.models.country"], "models")
