"""The app's settings, from the environment or .env (see .env.example). No defaults: a missing
setting fails at startup, with every missing one named at once."""

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class _EnvironmentSettings(BaseSettings):
    # Environment variables win over .env; other variables in .env (e.g. for tests) are ignored.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class DatabaseSettings(_EnvironmentSettings):
    """Only what migrations need, so they run without the app's other settings."""

    database_url: str


class LLMSettings(_EnvironmentSettings):
    """Only what the LLM needs, so the CV scripts and the eval run without a database."""

    ollama_url: str
    llm_model: str  # e.g. "qwen3:8b"; pulled with `ollama pull <model>`
    # Tokens the model reads at once: the prompt, the CV and the answer must fit.
    llm_context_length: int = Field(gt=0)


class Settings(DatabaseSettings):
    # The token machine callers (e.g. the scheduler) send as "Authorization: Bearer <token>".
    # SecretStr: printed as ********** in logs and tracebacks. Not empty: no request could match.
    service_token: SecretStr = Field(min_length=1)
