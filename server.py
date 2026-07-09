#!/usr/bin/env python3
"""Run the Mizan HTTP API (serves the API.md contract to the frontend).

Usage:
    python3 server.py                # http://localhost:8000
    MIZAN_DATA_DIR=data python3 server.py
    MIZAN_CORS_ORIGINS="http://localhost:3000" python3 server.py

Interactive docs at /docs once running.
"""

from __future__ import annotations

import os

import uvicorn


def main() -> None:
    host = os.environ.get("MIZAN_HOST", "0.0.0.0")
    port = int(os.environ.get("MIZAN_PORT", "8000"))
    reload = os.environ.get("MIZAN_RELOAD", "false").lower() in {"1", "true", "yes"}
    uvicorn.run("mizan.api:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    main()
