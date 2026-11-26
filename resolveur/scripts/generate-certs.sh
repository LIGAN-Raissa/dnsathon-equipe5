#!/usr/bin/env bash
set -euo pipefail

# Répertoire du script et destination des certificats
CERTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../certs" && pwd)"

echo "=== [1/3] Génération de la clé privée et du certificat TLS auto-signé ==="

openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout "${CERTS_DIR}/server.key" \
  -out "${CERTS_DIR}/server.crt" \
  -subj "/CN=dnsaton.local/O=Hackathon DNS Resolver/C=FR" \
  -addext "subjectAltName=DNS:localhost,DNS:dnsaton.local,IP:127.0.0.1"

chmod 600 "${CERTS_DIR}/server.key"
chmod 644 "${CERTS_DIR}/server.crt"

echo "=== [2/3] Génération de la clé API pour la console web et les métriques DNSdist ==="
# Clé secrète pour l'API REST DNSdist
API_KEY=$(openssl rand -hex 16)
echo "API_KEY=${API_KEY}" > "${CERTS_DIR}/dnsdist-api.env"

echo "=== [3/3] Certificats et clés générés avec succès dans ${CERTS_DIR} ==="
ls -l "${CERTS_DIR}"
