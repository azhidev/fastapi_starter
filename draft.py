from praytimes import PrayTimes
from datetime import date, datetime, timedelta, timezone
import math
from pydantic import BaseModel
from typing import Optional, Literal
# Choose method: "Tehran" (Jafari, Univ. of Tehran)
pt = PrayTimes("Tehran")

# Coordinates of Tehran
lat, lon, tz = 35.6892, 51.3890, 3.5
d = date(2025, 8, 30)

times = pt.getTimes(d, (lat, lon), tz)

print(times)
# {'imsak': '04:40', 'fajr': '04:50', 'sunrise': '06:12',
#  'dhuhr': '12:05', 'asr': '15:34', 'sunset': '17:58',
#  'maghrib': '18:02', 'isha': '19:15', 'midnight': '23:03'}
