import pytest
from pydantic import ValidationError

from jobfinder.settings import Settings


def _settings_from_environment_only() -> Settings:
    return Settings(_env_file=None)  # ignore the developer's .env


def test_settings_without_any_setting_names_every_missing_one(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SERVICE_TOKEN", raising=False)

    with pytest.raises(ValidationError, match=r"(?s)database_url.*service_token"):
        _settings_from_environment_only()


def test_settings_hides_the_service_token_when_printed(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/jobfinder")
    monkeypatch.setenv("SERVICE_TOKEN", "secret-token")

    settings = _settings_from_environment_only()

    assert "secret-token" not in repr(settings)
    assert settings.service_token.get_secret_value() == "secret-token"
