"""Comprobaciones mínimas del Live Review (Postgres + Docker)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _leer(ruta: Path) -> str:
    return ruta.read_text(encoding="utf-8")


def _revisar_estatico() -> list[str]:
    fallos: list[str] = []

    cfg = _leer(ROOT / "config.py")
    if "Falta DATABASE_URL" not in cfg:
        fallos.append("config.py debe exigir DATABASE_URL (sin SQLite por defecto)")

    db_src = _leer(ROOT / "src" / "db.py")
    if 'return "postgres"' not in db_src:
        fallos.append('src/db.py → storage_mode() debe devolver "postgres"')

    if not (ROOT / "Dockerfile").is_file():
        fallos.append("Falta Dockerfile")
    else:
        df = _leer(ROOT / "Dockerfile")
        if "PORT" not in df:
            fallos.append("Dockerfile debe respetar ${PORT:-8000}")

    if not (ROOT / ".dockerignore").is_file():
        fallos.append("Falta .dockerignore")

    req = _leer(ROOT / "requirements.txt")
    if "psycopg" not in req:
        fallos.append("requirements.txt debe incluir driver Postgres (psycopg)")

    app_src = _leer(ROOT / "app.py")
    if "CORSMiddleware" not in app_src:
        fallos.append("app.py debe incluir CORSMiddleware (seguridad ya dada)")
    if "duration_ms" not in app_src:
        fallos.append("app.py debe loguear duration_ms en /ask")

    return fallos


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="(opcional) import + /health")
    args = parser.parse_args()

    fallos = _revisar_estatico()
    if args.check and not fallos:
        try:
            import os

            os.environ.setdefault("GEMINI_API_KEY", "verificar-dummy")
            os.environ.setdefault("API_KEY", "verificar-dummy")
            os.environ.setdefault(
                "DATABASE_URL",
                "postgresql://postgres:123456@127.0.0.1:5432/postgres",
            )
            from fastapi.testclient import TestClient

            from app import app

            client = TestClient(app)
            r = client.get("/health")
            if r.status_code != 200:
                fallos.append(f"/health: {r.status_code}")
            elif r.json().get("storage") != "postgres":
                fallos.append(f'/health storage != postgres: {r.json()}')
        except Exception as exc:  # noqa: BLE001
            fallos.append(f"Import/app: {exc}")

    if fallos:
        print("Pendiente:")
        for f in fallos:
            print(f"  - {f}")
        return 1

    print("OK: base Postgres + Docker lista")
    return 0


if __name__ == "__main__":
    sys.exit(main())
