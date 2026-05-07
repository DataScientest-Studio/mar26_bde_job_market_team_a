from __future__ import annotations

from sqlalchemy import delete, desc, func, select
from sqlalchemy.schema import CreateSchema, DropIndex, Index

from src.data.landing.tables import (
    landing_indexes,
    legacy_landing_indexes,
    metadata,
    raw_france_travail_offers,
    raw_welcome_to_the_jungle_offers,
)


def drop_landing_tables(conn) -> None:
    for table in (raw_welcome_to_the_jungle_offers, raw_france_travail_offers):
        table.drop(conn, checkfirst=True)


def ensure_landing_schema(conn) -> None:
    conn.execute(CreateSchema("landing", if_not_exists=True))
    metadata.create_all(conn, checkfirst=True)

    for table in (raw_france_travail_offers, raw_welcome_to_the_jungle_offers):
        deduplicate_source_offers(conn, table)

    for index_name in legacy_landing_indexes:
        conn.execute(DropIndex(Index(index_name), if_exists=True))

    for index in landing_indexes:
        index.create(conn, checkfirst=True)


def deduplicate_source_offers(conn, table) -> None:
    ranked_rows = (
        select(
            table.c.raw_offer_id,
            func.row_number()
            .over(
                partition_by=(table.c.source_system, table.c.source_offer_id),
                order_by=(desc(table.c.ingested_at), desc(table.c.raw_offer_id)),
            )
            .label("duplicate_rank"),
        )
        .where(table.c.source_offer_id.is_not(None))
        .subquery()
    )

    duplicate_ids = select(ranked_rows.c.raw_offer_id).where(
        ranked_rows.c.duplicate_rank > 1
    )
    conn.execute(delete(table).where(table.c.raw_offer_id.in_(duplicate_ids)))
