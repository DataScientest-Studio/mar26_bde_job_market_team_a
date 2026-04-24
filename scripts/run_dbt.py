from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    env_file = repo_root / ".env"

    if env_file.exists():
        load_dotenv(env_file, override=True)
    project_dir = repo_root / "job_market_dbt"


    command = [
       "dbt",
        *sys.argv[1:],
        "--project-dir",
        str(project_dir),
        "--profiles-dir",
        str(project_dir),
    ]

    completed = subprocess.run(command, env=os.environ.copy())
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
