from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy.dialects.postgresql import insert

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data.landing.migrations import drop_landing_tables, ensure_landing_schema
from src.data.landing.tables import landing_table
from src.database import get_dbt_target, get_engine, load_project_env

load_project_env()


RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"
FRANCE_TRAVAIL_URL = "https://candidat.francetravail.fr/offres/recherche/detail/{offer_id}"
FRANCE_TRAVAIL_SOURCE_DIR = "france_travail"
WELCOME_TO_THE_JUNGLE_SOURCE_DIR = "welcome_to_the_jungle"
RAW_FILE_DATE_FORMAT = "%Y-%m-%d"


def build_raw_hash(payload: dict) -> str:
    raw_text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw_text.encode("utf-8")).hexdigest()


def parse_load_date(value: str) -> date:
    if value.lower() == "today":
        return date.today()

    try:
        return datetime.strptime(value, RAW_FILE_DATE_FORMAT).date()
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"invalid date '{value}'. Use 'today' or YYYY-MM-DD."
        ) from exc


def file_name_ends_with_date(file_path: Path, target_date: date) -> bool:
    target = f"{target_date:{RAW_FILE_DATE_FORMAT}}"
    return re.search(rf"(?:^|_){re.escape(target)}(?:_|$)", file_path.stem) is not None


def iter_json_files(
    *source_names: str,
    target_date: date | None = None,
    include_processed: bool = False,
) -> list[Path]:
    files: list[Path] = []
    data_dirs = [RAW_DATA_DIR]
    if include_processed:
        data_dirs.append(PROCESSED_DATA_DIR)

    for source_name in source_names:
        for data_dir in data_dirs:
            source_dir = data_dir / source_name
            if source_dir.exists():
                files.extend(source_dir.glob("*.json"))

    unique_files = sorted(set(files))
    if target_date is None:
        return unique_files

    return [
        file_path
        for file_path in unique_files
        if file_name_ends_with_date(file_path, target_date)
    ]


def load_json_file(file_path: Path) -> dict | list:
    return json.loads(file_path.read_text(encoding="utf-8"))


def is_url(value: str | None) -> bool:
    if not value:
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def extract_id_from_url(url: str | None) -> str | None:
    if not url:
        return None

    parsed = urlparse(url)
    path_parts = [part for part in parsed.path.split("/") if part]
    if not path_parts:
        return None

    return path_parts[-1]


def normalize_welcome_offer_id(value: str | None) -> str | None:
    if not value:
        return None
    return extract_id_from_url(value) if is_url(value) else value


def iter_france_travail_pages(payload: dict | list) -> list[dict]:
    if isinstance(payload, dict):
        return [payload]

    if isinstance(payload, list):
        return [page for page in payload if isinstance(page, dict)]

    return []


def extract_france_travail_records(file_path: Path) -> list[dict]:
    payload = load_json_file(file_path)
    records: list[dict] = []

    for page in iter_france_travail_pages(payload):
        offers = page.get("resultats", [])
        collection_region = page.get("region")
        collection_region_code = page.get("region_code")

        for offer in offers:
            if collection_region or collection_region_code:
                offer = {
                    **offer,
                    "_collection_region": collection_region,
                    "_collection_region_code": collection_region_code,
                }

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
        raw_id = offer.get("source_job_id") or offer.get("id")
        raw_url = offer.get("source_url") or offer.get("job_url") or offer.get("url")
        source_url = raw_url or (raw_id if is_url(raw_id) else None)
        source_offer_id = normalize_welcome_offer_id(raw_id or source_url) or offer.get("_source_key")

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


def processed_destination(file_path: Path) -> Path:
    source_name = file_path.parent.name
    destination_dir = PROCESSED_DATA_DIR / source_name
    destination = destination_dir / file_path.name

    if not destination.exists():
        return destination

    suffix = 2
    while True:
        candidate = destination_dir / f"{file_path.stem}_{suffix}{file_path.suffix}"
        if not candidate.exists():
            return candidate
        suffix += 1


def move_processed_files(files: list[Path]) -> None:
    for file_path in files:
        try:
            file_path.relative_to(RAW_DATA_DIR)
        except ValueError:
            continue

        destination = processed_destination(file_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        file_path.replace(destination)
        print(
            "[processed] "
            f"{file_path.relative_to(PROJECT_ROOT).as_posix()} -> "
            f"{destination.relative_to(PROJECT_ROOT).as_posix()}"
        )


def iter_welcome_to_the_jungle_files(
    target_date: date | None = None,
    *,
    include_processed: bool = False,
) -> list[Path]:
    return iter_json_files(
        WELCOME_TO_THE_JUNGLE_SOURCE_DIR,
        target_date=target_date,
        include_processed=include_processed,
    )


def insert_records(
    conn,
    table_name: str,
    records: list[dict],
) -> tuple[int, int]:
    if not records:
        return 0, 0

    table = landing_table(table_name)
    statement = insert(table).values(records).on_conflict_do_nothing(
        index_elements=["source_system", "source_offer_id"],
        index_where=table.c.source_offer_id.is_not(None),
    ).returning(table.c.raw_hash)
    result = conn.execute(statement)
    inserted = len(result.all())

    return inserted, len(records) - inserted


def load_france_travail(
    conn,
    *,
    target_date: date | None,
) -> tuple[int, int, list[Path]]:
    total_inserted = 0
    total_skipped = 0
    files = iter_json_files(
        FRANCE_TRAVAIL_SOURCE_DIR,
        target_date=target_date,
        include_processed=target_date is None,
    )

    if not files:
        print("[france_travail] aucun fichier JSON a charger")

    for file_path in files:
        records = extract_france_travail_records(file_path)
        inserted, skipped = insert_records(
            conn,
            "raw_france_travail_offers",
            records,
        )
        total_inserted += inserted
        total_skipped += skipped
        print(
            f"[france_travail] {file_path.name}: "
            f"{inserted} offres chargees, {skipped} doublons ignores"
        )

    return total_inserted, total_skipped, files


def load_welcome_to_the_jungle(
    conn,
    *,
    target_date: date | None,
) -> tuple[int, int, list[Path]]:
    total_inserted = 0
    total_skipped = 0
    files = iter_welcome_to_the_jungle_files(
        target_date=target_date,
        include_processed=target_date is None,
    )

    if not files:
        print("[welcome_to_the_jungle] aucun fichier JSON a charger")

    for file_path in files:
        records = extract_welcome_to_the_jungle_records(file_path)
        inserted, skipped = insert_records(
            conn,
            "raw_welcome_to_the_jungle_offers",
            records,
        )
        total_inserted += inserted
        total_skipped += skipped
        print(
            f"[welcome_to_the_jungle] {file_path.name}: "
            f"{inserted} offres chargees, {skipped} doublons ignores"
        )

    return total_inserted, total_skipped, files


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load raw JSON offers into PostgreSQL landing tables.")
    parser.add_argument(
        "--source",
        choices=[
            "all",
            "francetravail",
            "france_travail",
            "welcometothejungle",
            "welcome_to_the_jungle",
        ],
        default="all",
        help="Choose which source to load.",
    )
    parser.add_argument(
        "--date",
        type=parse_load_date,
        default=parse_load_date("today"),
        help="Only load files for this date. Use 'today' or YYYY-MM-DD. Default: today.",
    )
    parser.add_argument(
        "--all-files",
        action="store_true",
        help="Load every JSON file, ignoring --date.",
    )
    parser.add_argument(
        "--reset-landing",
        action="store_true",
        help="Drop landing raw tables before loading files.",
    )
    parser.add_argument(
        "--xcom-inserted-rows",
        action="store_true",
        help="Print the inserted row count as the last output line for Airflow XCom.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    total_inserted = 0
    total_skipped = 0
    loaded_files: list[Path] = []
    target_date = None if args.all_files else args.date

    print(f"TARGET: {get_dbt_target()}")
    if target_date is None:
        print("File selection: all JSON files")
    else:
        print(f"File selection: files dated {target_date:%Y-%m-%d}")

    engine = get_engine()
    with engine.begin() as conn:
        if args.reset_landing:
            print("Reset landing: dropping raw landing tables")
            drop_landing_tables(conn)

        ensure_landing_schema(conn)

        if args.source in {"all", "francetravail", "france_travail"}:
            inserted, skipped, files = load_france_travail(
                conn,
                target_date=target_date,
            )
            total_inserted += inserted
            total_skipped += skipped
            loaded_files.extend(files)

        if args.source in {"all", "welcometothejungle", "welcome_to_the_jungle"}:
            inserted, skipped, files = load_welcome_to_the_jungle(
                conn,
                target_date=target_date,
            )
            total_inserted += inserted
            total_skipped += skipped
            loaded_files.extend(files)

    print(f"Total inserted rows: {total_inserted}")
    print(f"Total skipped duplicate rows: {total_skipped}")
    move_processed_files(loaded_files)

    if args.xcom_inserted_rows:
        print(total_inserted)


if __name__ == "__main__":
    main()
