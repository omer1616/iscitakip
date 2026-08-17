#!/usr/bin/env bash
set -euo pipefail

echo "[entrypoint] Veritabanı bekleniyor..."
python <<'PY'
import os
import sys
import time

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import connections
from django.db.utils import OperationalError

deadline = time.monotonic() + float(os.environ.get("DB_WAIT_TIMEOUT", "60"))
while True:
    try:
        connections["default"].ensure_connection()
        break
    except OperationalError as exc:
        if time.monotonic() >= deadline:
            sys.exit(f"[entrypoint] Veritabanına bağlanılamadı: {exc}")
        time.sleep(1)
PY

echo "[entrypoint] Migration'lar uygulanıyor..."
python manage.py migrate --noinput

echo "[entrypoint] Roller kuruluyor..."
python manage.py setup_roles

echo "[entrypoint] Superuser kontrol ediliyor..."
python manage.py ensure_superuser

echo "[entrypoint] Başlatılıyor: $*"
exec "$@"