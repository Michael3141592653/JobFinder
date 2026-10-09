"""The app's settings, from the environment or .env (see .env.example). No defaults: a missing
setting fails at startup, with every missing one named at once."""

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Only what migrations need, so they run without the app's other settings."""

    # Environment variables win over .env; other variables in .env (e.g. for tests) are ignored.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str


class Settings(DatabaseSettings):
    # The token machine callers (e.g. the scheduler) send as "Authorization: Bearer <token>".
    # SecretStr: printed as ********** in logs and tracebacks. Not empty: no request could match.
    service_token: SecretStr = Field(min_length=1)
