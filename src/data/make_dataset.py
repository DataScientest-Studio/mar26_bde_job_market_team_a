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
    try:
        with open(HISTORY_PATH, 'r') as history:
            history_dict = yaml.safe_load(history)

        latest_ft_date = history_dict['latest_builds']['francetravail']
        latest_wttj_date = history_dict['latest_builds']['welcometothejungle']
    except:
        print("There was a problem loading the history yaml file.")
    return latest_ft_date, latest_wttj_date

def make_history(source):
    history_dict = {
        "latest_builds": {
            "francetravail":"",
            "welcometothejungle":""
        }
    }
    
    now_utc = datetime.now(timezone(timedelta(hours=2))).strftime("%Y-%m-%dT%H:%M:%SZ")

    if source=="all":
        history_dict["latest_builds"]["francetravail"]=now_utc
        history_dict["latest_builds"]["welcometothejungle"]=now_utc

    else:
        history_dict["latest_builds"][source]=now_utc

    with open(HISTORY_PATH, 'w') as history:
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