# OpenPage Backend

Django API, Docker Compose, nginx, Redis, and optional Certbot.

## Run

```sh
docker compose up -d --build
```

Useful URLs:

- API: `http://localhost:8000/`
- Swagger: `http://localhost:8000/api/docs/`
- Admin: `http://localhost:8000/admin/`

Logs:

```sh
docker compose logs -f web
```

Stop:

```sh
docker compose down
```

## Environment

Values live in `.env`. The file is ignored by Docker build and passed by Compose at runtime.

Small local example:

```env
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
API_SECRET_KEY=change-me
USE_REDIS=False
```

For Let's Encrypt:

```env
LETSENCRYPT_EMAIL=admin@example.com
```

Then on the server:

```sh
sh letsencrypt.sh issue
sh letsencrypt.sh enable
```

Renew:

```sh
sh letsencrypt.sh renew
```

The certificate is stored in the `certbot_certs` Docker volume. Backend or nginx container restarts do not require issuing it again.

## Database

The active setup uses SQLite: `db.sqlite3`.

A PostgreSQL service is kept commented in `docker-compose.yml` for a stronger server later.
