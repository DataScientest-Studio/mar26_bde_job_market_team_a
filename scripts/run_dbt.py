from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(repo_root))

    from src.database import load_project_env

    env_file = repo_root / ".env"

    load_project_env(env_file, override=True)
    project_dir = repo_root / "job_market_dbt"
    dbt_args = sys.argv[1:]

    if dbt_args in (["--version"], ["-v"]):
        completed = subprocess.run(["dbt", *dbt_args], env=os.environ.copy())
        return completed.returncode

    command = [
        "dbt",
        *dbt_args,
        "--project-dir",
        str(project_dir),
        "--profiles-dir",
        str(project_dir),
    ]

    completed = subprocess.run(command, env=os.environ.copy())
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
