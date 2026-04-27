#!/bin/sh
set -eu

POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-$POSTGRES_USER}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-}"

/usr/local/bin/docker-entrypoint.sh postgres &
postgres_pid="$!"

stop_postgres() {
  kill -TERM "$postgres_pid" 2>/dev/null || true
  wait "$postgres_pid" 2>/dev/null || true
}

trap stop_postgres INT TERM

if [ -n "$POSTGRES_PASSWORD" ]; then
  until pg_isready -q -U "$POSTGRES_USER" -d postgres; do
    if ! kill -0 "$postgres_pid" 2>/dev/null; then
      wait "$postgres_pid"
      exit $?
    fi
    sleep 1
  done

  escaped_user=$(printf "%s" "$POSTGRES_USER" | sed 's/"/""/g')
  escaped_password=$(printf "%s" "$POSTGRES_PASSWORD" | sed "s/'/''/g")

  psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d postgres \
    -c "ALTER USER \"$escaped_user\" WITH PASSWORD '$escaped_password';"
fi

wait "$postgres_pid"
