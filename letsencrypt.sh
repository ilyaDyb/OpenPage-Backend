#!/bin/sh
set -eu

compose() {
    if docker compose version >/dev/null 2>&1; then
        docker compose "$@"
    else
        docker-compose "$@"
    fi
}

env_value() {
    key="$1"
    default="${2:-}"
    current="$(printenv "$key" 2>/dev/null || true)"

    if [ -n "$current" ]; then
        printf "%s" "$current"
        return
    fi

    if [ -f .env ]; then
        value="$(grep -m 1 "^${key}=" .env 2>/dev/null | sed "s/^${key}=//; s/\r$//; s/^['\"]//; s/['\"]$//")"
        if [ -n "$value" ]; then
            printf "%s" "$value"
            return
        fi
    fi

    printf "%s" "$default"
}

usage() {
    cat <<EOF
Usage:
  sh letsencrypt.sh issue
  sh letsencrypt.sh enable
  sh letsencrypt.sh renew

Before issue:
  1. Point DNS to the VPS.
  2. Open ports 80 and 443.
  3. Set LETSENCRYPT_EMAIL in .env.

Optional .env values:
  NGINX_SERVER_NAME=xn--e1aamodgc0e.xn--p1ai www.xn--e1aamodgc0e.xn--p1ai
  LETSENCRYPT_DOMAIN=xn--e1aamodgc0e.xn--p1ai
  LETSENCRYPT_EXTRA_DOMAINS=www.xn--e1aamodgc0e.xn--p1ai
EOF
}

issue() {
    LETSENCRYPT_EMAIL="$(env_value LETSENCRYPT_EMAIL)"
    LETSENCRYPT_DOMAIN="$(env_value LETSENCRYPT_DOMAIN xn--e1aamodgc0e.xn--p1ai)"
    LETSENCRYPT_EXTRA_DOMAINS="$(env_value LETSENCRYPT_EXTRA_DOMAINS www.xn--e1aamodgc0e.xn--p1ai)"

    if [ -z "$LETSENCRYPT_EMAIL" ]; then
        echo "Set LETSENCRYPT_EMAIL in .env before running this command"
        exit 1
    fi

    domain_args="-d ${LETSENCRYPT_DOMAIN}"
    for domain in ${LETSENCRYPT_EXTRA_DOMAINS}; do
        domain_args="${domain_args} -d ${domain}"
    done

    compose up -d nginx
    compose run --rm certbot certonly \
        --webroot \
        --webroot-path /var/www/certbot \
        --email "${LETSENCRYPT_EMAIL}" \
        --agree-tos \
        --no-eff-email \
        ${domain_args}

    echo "Certificate issued. Run: sh letsencrypt.sh enable"
}

enable_https() {
    if [ ! -f nginx/default.ssl.conf.template.example ]; then
        echo "Missing nginx/default.ssl.conf.template.example"
        exit 1
    fi

    if [ -f nginx/default.conf.template ] && [ ! -f nginx/default.http.conf.disabled ]; then
        mv nginx/default.conf.template nginx/default.http.conf.disabled
    fi

    cp nginx/default.ssl.conf.template.example nginx/default.conf.template
    compose up -d --force-recreate nginx
}

renew() {
    compose run --rm certbot renew --webroot --webroot-path /var/www/certbot
    compose exec nginx nginx -s reload
}

case "${1:-}" in
    issue)
        issue
        ;;
    enable)
        enable_https
        ;;
    renew)
        renew
        ;;
    *)
        usage
        exit 1
        ;;
esac
