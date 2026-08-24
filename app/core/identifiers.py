from typing import Annotated

from fastapi import Path

XIDPath = Annotated[
    str,
    Path(min_length=20, max_length=20, pattern=r"^[0-9a-v]{20}$"),
]

RoleNamePath = Annotated[
    str,
    Path(min_length=1, max_length=50, pattern=r"^[^/\s]+$"),
]
