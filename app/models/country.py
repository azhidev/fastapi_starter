from tortoise import Tortoise, models, fields
class Country(models.Model):
    id = fields.IntField(pk=True, auto=True)
    name = fields.CharField(255)
    label = fields.CharField(255)
    iso_alpha2 = fields.CharField(5, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    time_offset_minutes = fields.SmallIntField(null=True)
    timezone = fields.CharField(20, null=True)

    # typing-only (helps IDEs)
    provinces: fields.ReverseRelation["Province"]

    class Meta:
        table = "countries"


class Province(models.Model):
    id = fields.IntField(pk=True, auto=True)
    name = fields.CharField(255)
    label = fields.CharField(255)
    iso_3166_2 = fields.CharField(10, null=True)
    country = fields.ForeignKeyField("models.Country", related_name="provinces")
    lat = fields.FloatField(null=True)
    lng = fields.FloatField(null=True)
    tz = fields.FloatField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "provinces"

# 👇 IMPORTANT: early init so relations exist when Pydantic models are created
# Replace "yourapp.models" with the REAL import path of THIS module.
Tortoise.init_models(["app.models.country"], "models")
