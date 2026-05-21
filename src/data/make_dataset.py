from __future__ import annotations

import argparse
import sys, os, yaml
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
load_dotenv(".env")

HISTORY_PATH = os.getenv("HISTORY_FILE_PATH")
PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import src.data.connectors.welcometothejungle_scraper as wttj
import src.data.connectors.francetravail_requester as ft

def get_history():
    # On va chercher la valeur des dernières extractions dans le fichier history.yaml
    latest_ft_date = ""
    latest_wttj_date = ""

    if not HISTORY_PATH:
        raise ValueError("HISTORY_FILE_PATH is not defined in .env")

    try:
        with open(HISTORY_PATH, "r", encoding="utf-8") as history:
            history_dict = yaml.safe_load(history) or {}

        latest_builds = history_dict.get("latest_builds", {})

        latest_ft_date = latest_builds.get("francetravail") or ""
        latest_wttj_date = latest_builds.get("welcometothejungle") or ""

    except Exception as e:
        raise RuntimeError(f"There was a problem loading the history yaml file: {e}")

    return latest_ft_date, latest_wttj_date

def make_history(source):
    if not HISTORY_PATH:
        raise ValueError("HISTORY_FILE_PATH is not defined in .env")

    try:
        with open(HISTORY_PATH, "r", encoding="utf-8") as history:
            history_dict = yaml.safe_load(history) or {}
    except FileNotFoundError:
        history_dict = {}

    history_dict.setdefault("latest_builds", {})
    history_dict["latest_builds"].setdefault("francetravail", "")
    history_dict["latest_builds"].setdefault("welcometothejungle", "")

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if source == "all":
        history_dict["latest_builds"]["francetravail"] = now_utc
        history_dict["latest_builds"]["welcometothejungle"] = now_utc
    else:
        history_dict["latest_builds"][source] = now_utc

    with open(HISTORY_PATH, "w", encoding="utf-8") as history:
        yaml.safe_dump(history_dict, history)


def run_france_travail(update_bool=False, latest_ft='') -> None:
    ft.initialize(update_bool, latest_ft)
    print(f"[France Travail] Completed requests successfully.")


def run_welcome() -> None:
    wttj.initialize()
    print(f"[WelcomeToTheJungle] Completed scraping successfully.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect raw job offers.")
    parser.add_argument(
        "--source",
        choices=["francetravail", "welcometothejungle", "all"],
        default="all",
    )
    parser.add_argument(
        "--update",
        action="store_true"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.update:
        latest_ft, latest_wttj = get_history()
        update_bool = True

    else:
        update_bool = False
        latest_ft=""

    if args.source == "francetravail":
        run_france_travail(update_bool, latest_ft)
    
    if args.source == "welcometothejungle":
        run_welcome()

    if args.source == "all":
        run_france_travail(update_bool, latest_ft)
        run_welcome()

    make_history(args.source)

if __name__ == "__main__":
    main()