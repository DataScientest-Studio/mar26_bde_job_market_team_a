from __future__ import annotations

import os


API_BASE_URL = os.getenv("JOB_MARKET_API_URL", "http://localhost:8000").rstrip("/")
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
