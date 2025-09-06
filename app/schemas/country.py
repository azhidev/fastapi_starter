from tortoise.contrib.pydantic import pydantic_model_creator
from app.models.country import Country, Province
# Expose provinces on countries (one level deep)
class CountryReadMeta:
    include = ("id", "name", "label","iso_alpha2", "provinces")
    max_recursion = 1

CountryRead = pydantic_model_creator(
    Country, name="CountryRead", meta_override=CountryReadMeta
)

# (Optional) If you need a Province schema too
class ProvinceReadMeta:
    exclude = ("country",)  # avoid back-reference in output

ProvinceRead = pydantic_model_creator(
    Province, name="ProvinceRead", meta_override=ProvinceReadMeta
)
