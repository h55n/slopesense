import pytest
from pydantic import ValidationError

from backend.config import Settings


def test_production_secret_key_uses_resolved_environment():
    with pytest.raises(
        ValidationError,
        match="SECRET_KEY must be at least 32 characters in production",
    ):
        Settings(environment="production", secret_key="too-short", _env_file=None)


def test_production_accepts_secret_key_with_minimum_length():
    settings = Settings(
        environment="production",
        secret_key="s" * 32,
        _env_file=None,
    )

    assert settings.secret_key == "s" * 32


def test_development_keeps_short_local_secret_usable():
    settings = Settings(environment="development", secret_key="local", _env_file=None)

    assert settings.secret_key == "local"
