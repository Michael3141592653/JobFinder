import pytest
from pydantic import ValidationError

from jobfinder.settings import DatabaseSettings, LLMSettings, Settings


def _settings_from_environment_only() -> Settings:
    return Settings(_env_file=None)  # ignore the developer's .env


def test_settings_without_any_setting_names_every_missing_one(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SERVICE_TOKEN", raising=False)

    with pytest.raises(ValidationError, match=r"(?s)database_url.*service_token"):
        _settings_from_environment_only()


def test_settings_rejects_an_empty_service_token(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/jobfinder")
    monkeypatch.setenv("SERVICE_TOKEN", "")

    with pytest.raises(ValidationError, match="service_token"):
        _settings_from_environment_only()


def test_database_settings_need_no_service_token(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/jobfinder")
    monkeypatch.delenv("SERVICE_TOKEN", raising=False)

    database_settings = DatabaseSettings(_env_file=None)

    assert database_settings.database_url == "postgresql://localhost/jobfinder"


def test_llm_settings_need_no_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("OLLAMA_URL", "http://localhost:11434")
    monkeypatch.setenv("LLM_MODEL", "qwen3:8b")
    monkeypatch.setenv("LLM_CONTEXT_LENGTH", "8192")

    llm_settings = LLMSettings(_env_file=None)

    assert llm_settings.llm_context_length == 8192


def test_settings_hides_the_service_token_when_printed(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/jobfinder")
    monkeypatch.setenv("SERVICE_TOKEN", "secret-token")

    settings = _settings_from_environment_only()

    assert "secret-token" not in repr(settings)
    assert settings.service_token.get_secret_value() == "secret-token"
