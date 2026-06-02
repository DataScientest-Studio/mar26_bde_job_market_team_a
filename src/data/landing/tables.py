from __future__ import annotations

from sqlalchemy import BigInteger, Column, DateTime, Identity, Index, MetaData, Table, Text, func
from sqlalchemy.dialects.postgresql import JSONB

metadata = MetaData(schema="landing")

raw_france_travail_offers = Table(
    "raw_france_travail_offers",
    metadata,
    Column("raw_offer_id", BigInteger, Identity(), primary_key=True),
    Column("source_system", Text, nullable=False),
    Column("source_offer_id", Text),
    Column("source_url", Text),
    Column("source_file_name", Text, nullable=False),
    Column("source_file_path", Text, nullable=False),
    Column("raw_hash", Text, nullable=False),
    Column("ingested_at", DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()),
    Column("raw_payload", JSONB, nullable=False),
    schema="landing",
)

raw_welcome_to_the_jungle_offers = Table(
    "raw_welcome_to_the_jungle_offers",
    metadata,
    Column("raw_offer_id", BigInteger, Identity(), primary_key=True),
    Column("source_system", Text, nullable=False),
    Column("source_offer_id", Text),
    Column("source_url", Text),
    Column("source_file_name", Text, nullable=False),
    Column("source_file_path", Text, nullable=False),
    Column("raw_hash", Text, nullable=False),
    Column("ingested_at", DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()),
    Column("raw_payload", JSONB, nullable=False),
    schema="landing",
)

landing_indexes = [
    Index(
        "ix_raw_france_travail_offers_raw_hash",
        raw_france_travail_offers.c.raw_hash,
    ),
    Index(
        "uq_raw_france_travail_offers_source_offer_id",
        raw_france_travail_offers.c.source_system,
        raw_france_travail_offers.c.source_offer_id,
        unique=True,
        postgresql_where=raw_france_travail_offers.c.source_offer_id.is_not(None),
    ),
    Index(
        "ix_raw_welcome_to_the_jungle_offers_raw_hash",
        raw_welcome_to_the_jungle_offers.c.raw_hash,
    ),
    Index(
        "uq_raw_welcome_to_the_jungle_offers_source_offer_id",
        raw_welcome_to_the_jungle_offers.c.source_system,
        raw_welcome_to_the_jungle_offers.c.source_offer_id,
        unique=True,
        postgresql_where=raw_welcome_to_the_jungle_offers.c.source_offer_id.is_not(None),
    ),
]

legacy_landing_indexes = (
    "uq_raw_france_travail_offers_raw_hash",
    "ix_raw_france_travail_offers_source_offer_id",
    "uq_raw_welcome_to_the_jungle_offers_raw_hash",
    "ix_raw_welcome_to_the_jungle_offers_source_offer_id",
)


def landing_table(table_name: str) -> Table:
    return metadata.tables[f"landing.{table_name}"]
