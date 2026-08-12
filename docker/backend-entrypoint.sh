#!/bin/bash
set -e

cat > /app/.env.production <<EOF
URI_POSTGRES=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST:-postgres}:${POSTGRES_PORT:-5432}/${POSTGRES_DB}
SECRET_KEY=${SECRET_KEY}
HOST_FRONTEND=${HOST_FRONTEND}
EOF

python -m icm database --start

exec "$@"
