"""Alembic runs this to apply migrations. They are plain SQL, so there are no models here."""

from alembic import context
from sqlalchemy import URL, create_engine, make_url, pool

from jobfinder.settings import Settings


def _sqlalchemy_url() -> URL:
    """DATABASE_URL, told to use psycopg 3 (SQLAlchemy would otherwise pick psycopg2)."""
    return make_url(Settings().database_url).set(drivername="postgresql+psycopg")


def run_migrations() -> None:
    engine = create_engine(_sqlalchemy_url(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection)
        with context.begin_transaction():
            context.run_migrations()


run_migrations()
