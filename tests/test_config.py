import pytest
from pydantic import ValidationError

from app.core.config import Settings


VALID_SECRET = "phase-nine-production-secret-7Zx4Qp2Lm9Vt"


def make_settings(**overrides) -> Settings:
    values = {
        "SECRET": VALID_SECRET,
        "APP_ENV": "development",
        "DEBUG": False,
        "GOOGLE_CLIENT_ID": None,
        "GOOGLE_CLIENT_SECRET": None,
        "OAUTH_PROVIDER": None,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


@pytest.mark.parametrize("lifetime", [0, 60 * 60 * 24 * 30 + 1])
def test_jwt_lifetime_must_be_positive_and_bounded(lifetime):
    with pytest.raises(ValidationError):
        make_settings(JWT_LIFETIME_SECONDS=lifetime)


def test_oauth_provider_selection_and_credentials_must_be_consistent():
    with pytest.raises(ValidationError, match="required when OAUTH_PROVIDER=google"):
        make_settings(OAUTH_PROVIDER="google")

    with pytest.raises(ValidationError, match="OAUTH_PROVIDER must be selected"):
        make_settings(GOOGLE_CLIENT_ID="client-id", GOOGLE_CLIENT_SECRET="client-secret")

    configured = make_settings(
        OAUTH_PROVIDER="google",
        GOOGLE_CLIENT_ID="client-id",
        GOOGLE_CLIENT_SECRET="client-secret",
    )
    assert configured.oauth_provider == "google"


def test_production_rejects_debug_and_insecure_secrets():
    with pytest.raises(ValidationError, match="DEBUG must be disabled"):
        make_settings(APP_ENV="production", DEBUG=True)

    with pytest.raises(ValidationError, match="SECRET is not suitable"):
        make_settings(
            APP_ENV="production",
            SECRET="test-secret-key-with-at-least-32-characters",
        )


def test_production_oauth_redirect_must_use_https():
    oauth = {
        "APP_ENV": "production",
        "OAUTH_PROVIDER": "google",
        "GOOGLE_CLIENT_ID": "client-id",
        "GOOGLE_CLIENT_SECRET": "client-secret",
    }
    with pytest.raises(ValidationError, match="must use HTTPS"):
        make_settings(**oauth)

    configured = make_settings(
        **oauth,
        OAUTH_REDIRECT_URI="https://api.example.com/api/v1/auth/oauth/callback",
    )
    assert configured.oauth_redirect_uri.startswith("https://")
