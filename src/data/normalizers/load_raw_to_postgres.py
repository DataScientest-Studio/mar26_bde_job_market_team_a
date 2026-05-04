from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Iterable

from psycopg.types.json import Json

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.database import get_dbt_target, load_project_env, raw_database_connection

load_project_env()


DATA_DIR = Path("data/raw")
WELCOME_JSON_EXPORT_PATH = Path("src/data/json_export/welcometothejungle.json")
INIT_SQL_PATH = Path("models/create_postgredb.sql")
FRANCE_TRAVAIL_URL = "https://candidat.francetravail.fr/offres/recherche/detail/{offer_id}"


def ensure_landing_tables(conn) -> None:
    init_sql = INIT_SQL_PATH.read_text(encoding="utf-8")

    with conn.cursor() as cur:
        cur.execute(init_sql)
    conn.commit()


def build_raw_hash(payload: dict) -> str:
    raw_text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw_text.encode("utf-8")).hexdigest()


def iter_json_files(source_name: str) -> Iterable[Path]:
    source_dir = DATA_DIR / source_name
    if not source_dir.exists():
        return []
    return sorted(source_dir.glob("*.json"))


def load_json_file(file_path: Path) -> dict | list:
    return json.loads(file_path.read_text(encoding="utf-8"))


def extract_france_travail_records(file_path: Path) -> list[dict]:
    payload = load_json_file(file_path)
    offers = payload.get("resultats", []) if isinstance(payload, dict) else []
    records: list[dict] = []

    for offer in offers:
        source_offer_id = offer.get("id")
        source_url = (
            offer.get("origineOffre", {}).get("urlOrigine")
            or offer.get("contact", {}).get("urlPostulation")
            or (FRANCE_TRAVAIL_URL.format(offer_id=source_offer_id) if source_offer_id else None)
        )

        records.append(
            {
                "source_system": "france_travail",
                "source_offer_id": source_offer_id,
                "source_url": source_url,
                "source_file_name": file_path.name,
                "source_file_path": str(file_path.as_posix()),
                "raw_hash": build_raw_hash(offer),
                "raw_payload": offer,
            }
        )

    return records


def extract_welcome_to_the_jungle_records(file_path: Path) -> list[dict]:
    payload = load_json_file(file_path)
    if isinstance(payload, dict):
        offers = [
            {**offer, "_source_key": source_key}
            for source_key, offer in payload.items()
            if isinstance(offer, dict)
        ]
    elif isinstance(payload, list):
        offers = payload
    else:
        offers = []

    records: list[dict] = []

    for offer in offers:
        source_offer_id = offer.get("source_job_id") or offer.get("id") or offer.get("_source_key")
        source_url = offer.get("source_url") or offer.get("job_url") or offer.get("url")

        records.append(
            {
                "source_system": "welcome_to_the_jungle",
                "source_offer_id": source_offer_id,
                "source_url": source_url,
                "source_file_name": file_path.name,
                "source_file_path": str(file_path.as_posix()),
                "raw_hash": build_raw_hash(offer),
                "raw_payload": offer,
            }
        )

    return records


def iter_welcome_to_the_jungle_files() -> Iterable[Path]:
    files = list(iter_json_files("welcome_to_the_jungle"))
    if WELCOME_JSON_EXPORT_PATH.exists():
        files.append(WELCOME_JSON_EXPORT_PATH)
    return sorted(set(files))


def insert_records(conn, table_name: str, records: list[dict]) -> int:
    if not records:
        return 0

    insert_sql = f"""
        insert into landing.{table_name} (
            source_system,
            source_offer_id,
            source_url,
            source_file_name,
            source_file_path,
            raw_hash,
            raw_payload
        )
        values (
            %(source_system)s,
            %(source_offer_id)s,
            %(source_url)s,
            %(source_file_name)s,
            %(source_file_path)s,
            %(raw_hash)s,
            %(raw_payload)s
        )
    """

    prepared_records = [
        {**record, "raw_payload": Json(record["raw_payload"])}
        for record in records
    ]

    with conn.cursor() as cur:
        cur.executemany(insert_sql, prepared_records)
    conn.commit()

    return len(records)


def load_france_travail(conn) -> int:
    total_inserted = 0

    for file_path in iter_json_files("france_travail"):
        records = extract_france_travail_records(file_path)
        inserted = insert_records(conn, "raw_france_travail_offers", records)
        total_inserted += inserted
        print(f"[france_travail] {file_path.name}: {inserted} offres chargees")

    return total_inserted


def load_welcome_to_the_jungle(conn) -> int:
    total_inserted = 0

    for file_path in iter_welcome_to_the_jungle_files():
        records = extract_welcome_to_the_jungle_records(file_path)
        inserted = insert_records(conn, "raw_welcome_to_the_jungle_offers", records)
        total_inserted += inserted
        print(f"[welcome_to_the_jungle] {file_path.name}: {inserted} offres chargees")

    return total_inserted


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load raw JSON offers into PostgreSQL landing tables.")
    parser.add_argument(
        "--source",
        choices=["all", "france_travail", "welcome_to_the_jungle", "welcome"],
        default="all",
        help="Choose which source to load.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    total_inserted = 0

    print(f"TARGET: {get_dbt_target()}")
    with raw_database_connection() as conn:
        ensure_landing_tables(conn)

        if args.source in {"all", "france_travail"}:
            total_inserted += load_france_travail(conn)

        if args.source in {"all", "welcome_to_the_jungle", "welcome"}:
            total_inserted += load_welcome_to_the_jungle(conn)

    print(f"Total inserted rows: {total_inserted}")


if __name__ == "__main__":
    main()
