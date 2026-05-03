"""
Shared database configuration and SQLAlchemy engine helpers.

The project follows the same environment convention everywhere:
- DBT_TARGET=dev  -> local PostgreSQL variables: POSTGRES_*
- DBT_TARGET=prod -> Supabase PostgreSQL variables: SUPABASE_DB_*
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from dotenv import load_dotenv
from sqlalchemy import URL, create_engine
from sqlalchemy.engine import Engine


@dataclass(frozen=True)
class DatabaseConfig:
    host: str
    port: int
    dbname: str
    user: str
    password: str
    schema: str
    sslmode: str | None = None

    def sqlalchemy_url(self) -> URL:
        return URL.create(
            drivername="postgresql+psycopg",
            username=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.dbname,
        )

    def connect_args(self) -> dict[str, str]:
        args = {"options": f"-csearch_path={self.schema}"}
        if self.sslmode:
            args["sslmode"] = self.sslmode
        return args


def load_project_env(env_file: str | Path | None = None, *, override: bool = False) -> None:
    if env_file is None:
        load_dotenv(override=override)
        return

    env_path = Path(env_file)
    if env_path.exists():
        load_dotenv(env_path, override=override)


def get_dbt_target() -> str:
    return os.getenv("DBT_TARGET", "dev").strip().lower()


def get_database_config() -> DatabaseConfig:
    target = get_dbt_target()

    if target == "prod":
        return DatabaseConfig(
            host=os.getenv("SUPABASE_DB_HOST", ""),
            port=int(os.getenv("SUPABASE_DB_PORT", "5432")),
            dbname=os.getenv("SUPABASE_DB_NAME", "postgres"),
            user=os.getenv("SUPABASE_DB_USER", "postgres"),
            password=os.getenv("SUPABASE_DB_PASSWORD", ""),
            schema=os.getenv("SUPABASE_DB_SCHEMA", "analytics"),
            sslmode="require",
        )

    return DatabaseConfig(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "job_market"),
        user=os.getenv("POSTGRES_USER", "job_market"),
        password=os.getenv("POSTGRES_PASSWORD", "job_market"),
        schema=os.getenv("DBT_DEV_SCHEMA", "analytics"),
    )


def create_database_engine() -> Engine:
    config = get_database_config()
    return create_engine(
        config.sqlalchemy_url(),
        connect_args=config.connect_args(),
        pool_pre_ping=True,
    )


_engine: Engine | None = None
_engine_config: DatabaseConfig | None = None


def get_engine() -> Engine:
    global _engine, _engine_config

    config = get_database_config()
    if _engine is None or _engine_config != config:
        _engine = create_database_engine()
        _engine_config = config

    return _engine


@contextmanager
def raw_database_connection() -> Iterator:
    connection = get_engine().raw_connection()
    try:
        yield connection
    finally:
        connection.close()
