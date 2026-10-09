"""The app's settings, from the environment or .env (see .env.example). No defaults: a missing
setting fails at startup, with every missing one named at once."""

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Environment variables win over .env; other variables in .env (e.g. for tests) are ignored.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    # The token machine callers (e.g. the scheduler) send as "Authorization: Bearer <token>".
    # SecretStr: printed as ********** in logs and tracebacks.
    service_token: SecretStr
