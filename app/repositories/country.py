from typing import Sequence
from tortoise.exceptions import DoesNotExist
from tortoise.queryset import QuerySet

from app.models.country import Country
from app.schemas.country import CountryRead



class CountryRepository:
    async def all_countries_with_provinces(self):
        # from_queryset will prefetch relations automatically, but this is also fine:
        return Country.all().prefetch_related("provinces")
