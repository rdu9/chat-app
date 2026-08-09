#!/bin/sh
set -e

alembic upgrade head

exec uvicorn src:app --host 0.0.0.0 --port 8000 -