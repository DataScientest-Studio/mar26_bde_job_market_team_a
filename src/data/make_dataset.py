from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data.connectors.france_travail import FranceTravailClient
from src.data.connectors.welcomemain import collect_welcome_to_the_jungle

DEFAULT_TARGETS_FILE = "references/collection_targets.yml"


def run_france_travail() -> None:
    client = FranceTravailClient()
    targets = client.load_targets_from_file(DEFAULT_TARGETS_FILE)
    payload = client.collect_offers_from_targets(targets=targets)
    path = client.save_raw(payload)
    print(f"[France Travail] sauvegarde dans {path}")


def run_welcome() -> None:
    path = collect_welcome_to_the_jungle()
    print(f"[WelcomeToTheJungle] offres extraites dans {path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect raw job offers.")
    parser.add_argument(
        "--source",
        choices=["france_travail", "welcome_to_the_jungle", "welcome", "all"],
        default="all",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.source in {"all", "france_travail"}:
        run_france_travail()
    
    if args.source in {"all", "welcome_to_the_jungle", "welcome"}:
        run_welcome()


if __name__ == "__main__":
    main()
