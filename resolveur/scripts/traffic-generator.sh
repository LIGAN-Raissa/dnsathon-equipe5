#!/usr/bin/env bash
# Générateur de trafic de démonstration pour animer les dashboards Grafana
echo "Démarrage de la simulation de trafic en continu (Ctrl+C pour stopper)..."

DOMAINS=("google.com" "wikipedia.org" "github.com" "cloudflare.com" "kernel.org" "debian.org")

while true; do
    # 1. Requêtes UDP standard
    RANDOM_DOMAIN=${DOMAINS[$RANDOM % ${#DOMAINS[@]}]}
    dig @127.0.0.1 -p 53 "$RANDOM_DOMAIN" +short >/dev/null 2>&1

    # 2. Requête DoH (HTTPS)
    DOH_QUERY=$(printf '\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x07example\x03com\x00\x00\x01\x00\x01' | base64 | tr '/+' '_-' | tr -d '=')
    curl -ks "https://127.0.0.1/dns-query?dns=${DOH_QUERY}" -H "Accept: application/dns-message" >/dev/null 2>&1

    # 3. Simulation occasionnelle d'attaque ANY bloquée
    if [ $((RANDOM % 3)) -eq 0 ]; then
        dig @127.0.0.1 -p 53 cloudflare.com ANY +time=1 +tries=1 >/dev/null 2>&1 || true
    fi

    # 4. Simulation d'accès malware sinkholé
    if [ $((RANDOM % 4)) -eq 0 ]; then
        dig @127.0.0.1 -p 53 malware-test.evil.local +short >/dev/null 2>&1 || true
    fi

    sleep 0.5
done
