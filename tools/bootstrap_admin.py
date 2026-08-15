import argparse
import asyncio

from tortoise import Tortoise

from app.db.tortoise import TORTOISE_ORM
from app.models.user import Role, User


async def bootstrap_admin(email: str) -> None:
    await Tortoise.init(config=TORTOISE_ORM)
    try:
        user = await User.get_or_none(email=email)
        if user is None:
            raise SystemExit(f"User not found: {email}")
        if not user.is_active:
            raise SystemExit(f"User is inactive: {email}")

        role, _ = await Role.get_or_create(
            name="admin",
            defaults={"description": "Administrator"},
        )
        await user.roles.add(role)
        print(f"Admin role assigned to {email}")
    finally:
        await Tortoise.close_connections()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Assign the admin role to an existing active user.",
    )
    parser.add_argument("--email", required=True, help="Email of the existing user")
    args = parser.parse_args()
    asyncio.run(bootstrap_admin(args.email))


if __name__ == "__main__":
    main()
