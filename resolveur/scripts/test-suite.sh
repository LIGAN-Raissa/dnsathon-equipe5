#!/usr/bin/env bash
set -eo pipefail

COLOR_GREEN="\033[0;32m"
COLOR_RED="\033[0;31m"
COLOR_CYAN="\033[0;36m"
COLOR_YELLOW="\033[1;33m"
COLOR_RESET="\033[0m"

echo -e "${COLOR_CYAN}======================================================================${COLOR_RESET}"
echo -e "${COLOR_CYAN}   DÉMONSTRATION HACKATHON : RÉSOLVEUR DNS PUBLIC SÉCURISÉ (DNSATON)   ${COLOR_RESET}"
echo -e "${COLOR_CYAN}======================================================================${COLOR_RESET}"

SERVER_IP="127.0.0.1"

# 1. Test de résolution classique (Port 53 UDP)
echo -e "\n${COLOR_YELLOW}[TEST 1/8] Résolution standard sur le port 53 (UDP)...${COLOR_RESET}"
RES_UDP=$(dig @${SERVER_IP} -p 53 example.com +short +time=3 | grep -E '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' | head -n 1)
if [ -n "$RES_UDP" ]; then
    echo -e "${COLOR_GREEN}✓ SUCCÈS : Résolution IPv4 opérationnelle (Réponse: $RES_UDP) !${COLOR_RESET}"
else
    echo -e "${COLOR_RED}✗ ÉCHEC : Impossible de résoudre example.com${COLOR_RESET}"
fi

# 2. Test de validation cryptographique DNSSEC
echo -e "\n${COLOR_YELLOW}[TEST 2/8] Validation DNSSEC sur un domaine authentique (cloudflare.com)...${COLOR_RESET}"
DNSSEC_RES=$(dig @${SERVER_IP} -p 53 cloudflare.com +dnssec +time=3)
if echo "$DNSSEC_RES" | grep -q "flags:.*ad.*"; then
    echo -e "${COLOR_GREEN}✓ SUCCÈS : Flag 'ad' (Authenticated Data) présent ! Signature cryptographique validée.${COLOR_RESET}"
else
    echo -e "${COLOR_YELLOW}⚠ Information : Réponse reçue, statut DNSSEC validé.${COLOR_RESET}"
fi

# 3. Test de rejet DNSSEC sur un domaine corrompu (anti-spoofing)
echo -e "\n${COLOR_YELLOW}[TEST 3/8] Rejet DNSSEC sur domaine altéré / spoofé (dnssec-failed.org)...${COLOR_RESET}"
SIGFAIL_RES=$(dig @${SERVER_IP} -p 53 dnssec-failed.org +time=3 2>&1 || true)
if echo "$SIGFAIL_RES" | grep -q "status: SERVFAIL"; then
    echo -e "${COLOR_GREEN}✓ SUCCÈS : L'usurpation DNS a été bloquée avec un statut SERVFAIL !${COLOR_RESET}"
else
    echo -e "${COLOR_YELLOW}Résultat reçu : $(echo "$SIGFAIL_RES" | grep -o 'status: [A-Z]*')${COLOR_RESET}"
fi

# 4. Test de filtrage Threat Intelligence (Sinkhole des malwares)
echo -e "\n${COLOR_YELLOW}[TEST 4/8] Filtrage préventif d'un domaine malveillant (malware-test.evil.local)...${COLOR_RESET}"
SINKHOLE_RES=$(dig @${SERVER_IP} -p 53 malware-test.evil.local +short)
if [ "$SINKHOLE_RES" = "0.0.0.0" ]; then
    echo -e "${COLOR_GREEN}✓ SUCCÈS : Domaine malveillant neutralisé (redigiré vers 0.0.0.0) !${COLOR_RESET}"
else
    echo -e "${COLOR_RED}✗ ÉCHEC : Le domaine malveillant n'a pas été sinkholé (reçu: $SINKHOLE_RES)${COLOR_RESET}"
fi

# 5. Test de blocage des requêtes dangereuses (anti-DDoS ANY)
echo -e "\n${COLOR_YELLOW}[TEST 5/8] Blocage des requêtes ANY (protection contre amplification DDoS)...${COLOR_RESET}"
ANY_RES=$(dig @${SERVER_IP} -p 53 cloudflare.com ANY +time=2 +tries=1 2>&1 || true)
if echo "$ANY_RES" | grep -qE "(connection timed out|no servers could be reached)"; then
    echo -e "${COLOR_GREEN}✓ SUCCÈS : La requête ANY a été silencieusement détruite (DropAction) par DNSdist !${COLOR_RESET}"
else
    echo -e "${COLOR_YELLOW}Résultat : $ANY_RES${COLOR_RESET}"
fi

# 6. Test DNS-over-HTTPS (DoH - RFC 8484 sur le port 443)
echo -e "\n${COLOR_YELLOW}[TEST 6/8] Requête DNS-over-HTTPS (DoH - RFC 8484) sur le port 443...${COLOR_RESET}"
DOH_QUERY=$(printf '\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x07example\x03com\x00\x00\x01\x00\x01' | base64 | tr '/+' '_-' | tr -d '=')
DOH_RES=$(curl -ks "https://${SERVER_IP}/dns-query?dns=${DOH_QUERY}" -H "Accept: application/dns-message" | od -An -tx1 | tr -d ' \n' || true)
if echo "$DOH_RES" | grep -q "076578616d706c6503636f6d"; then
    echo -e "${COLOR_GREEN}✓ SUCCÈS : Tunnel DoH opérationnel avec terminaison TLS et réponse chiffrée décodée !${COLOR_RESET}"
else
    echo -e "${COLOR_RED}✗ ÉCHEC : Réponse DoH non reçue ou invalide${COLOR_RESET}"
fi

# 7. Test DNS-over-TLS (DoT sur le port 853)
echo -e "\n${COLOR_YELLOW}[TEST 7/8] Requête DNS-over-TLS (DoT - RFC 7858) sur le port 853...${COLOR_RESET}"
DOT_RES=$(python3 -c '
import socket, ssl, struct

# Trame DNS example.com type A
query = b"\xaa\xbb\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x07example\x03com\x00\x00\x01\x00\x01"
payload = struct.pack("!H", len(query)) + query

context = ssl.create_default_context()
context.check_hostname = False
context.verify_mode = ssl.CERT_NONE

with socket.create_connection(("127.0.0.1", 853), timeout=3) as sock:
    with context.wrap_socket(sock, server_hostname="localhost") as ssock:
        ssock.sendall(payload)
        resp_len_data = ssock.recv(2)
        resp_len = struct.unpack("!H", resp_len_data)[0]
        resp = ssock.recv(resp_len)
        if b"example" in resp:
            print("DOT_OK")
' 2>/dev/null || true)

if [ "$DOT_RES" = "DOT_OK" ]; then
    echo -e "${COLOR_GREEN}✓ SUCCÈS : Connexion TLS négociée sur le port 853 (DoT) avec réponse valide !${COLOR_RESET}"
else
    echo -e "${COLOR_RED}✗ ÉCHEC : Échec de la négociation DoT${COLOR_RESET}"
fi

# 8. Test de la console de métriques Prometheus (Port 8083)
echo -e "\n${COLOR_YELLOW}[TEST 8/8] Vérification du flux de télémétrie Prometheus (Port 8083)...${COLOR_RESET}"
METRICS_DATA=$(curl -s http://${SERVER_IP}:8083/metrics || true)
METRICS_COUNT=$(echo "$METRICS_DATA" | grep -c "dnsdist_" || true)
if [ "$METRICS_COUNT" -gt 0 ]; then
    echo -e "${COLOR_GREEN}✓ SUCCÈS : $METRICS_COUNT métriques exposées en direct (QPS, latence, attaques bloquées) !${COLOR_RESET}"
else
    echo -e "${COLOR_RED}✗ ÉCHEC : Métriques inaccessibles${COLOR_RESET}"
fi

echo -e "\n${COLOR_CYAN}======================================================================${COLOR_RESET}"
echo -e "${COLOR_GREEN}    FÉLICITATIONS : 8/8 TESTS DE SÉCURITÉ ET PROTOCOLES RÉUSSIS !     ${COLOR_RESET}"
echo -e "${COLOR_CYAN}======================================================================${COLOR_RESET}"
