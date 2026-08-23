import secrets

from tortoise.transactions import in_transaction

from app.core.security import pwd_context
from app.models.oauth import OAuthAccount
from app.models.user import User
from app.oauth.types import OAuthProvider


class InactiveOAuthUserError(Exception):
    """Raised when an OAuth identity resolves to an inactive local user."""


async def authenticate_oauth_user(
    provider: OAuthProvider,
    code: str,
    redirect_uri: str,
) -> User:
    authentication = await provider.exchange_code(code, redirect_uri)
    email = authentication.identity.email.strip().lower()

    async with in_transaction() as connection:
        account = await (
            OAuthAccount.filter(
                provider=provider.name,
                subject=authentication.identity.subject,
            )
            .using_db(connection)
            .select_for_update()
            .first()
        )

        if account is not None:
            user = await User.filter(id=account.user_id).using_db(connection).first()
            if user is None or not user.is_active:
                raise InactiveOAuthUserError
        else:
            user = await (
                User.filter(email=email)
                .using_db(connection)
                .select_for_update()
                .first()
            )
            if user is not None and not user.is_active:
                raise InactiveOAuthUserError
            if user is None:
                user = await User.create(
                    using_db=connection,
                    email=email,
                    hashed_password=pwd_context.hash(secrets.token_urlsafe(32)),
                )

            account = await OAuthAccount.create(
                using_db=connection,
                provider=provider.name,
                subject=authentication.identity.subject,
                user_id=user.id,
                access_token=authentication.credentials.access_token,
                refresh_token=authentication.credentials.refresh_token,
                expires_at=authentication.credentials.expires_at,
            )

        account.access_token = authentication.credentials.access_token
        if authentication.credentials.refresh_token is not None:
            account.refresh_token = authentication.credentials.refresh_token
        account.expires_at = authentication.credentials.expires_at
        await account.save(
            using_db=connection,
            update_fields=("access_token", "refresh_token", "expires_at"),
        )

    return user
