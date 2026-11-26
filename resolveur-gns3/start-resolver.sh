#!/bin/sh
# Démarrage du résolveur dans un nœud Docker GNS3.
# GNS3 injecte les interfaces (eth0 = IXP, eth1 = sortie Internet optionnelle)
# après le lancement du conteneur : on attend donc leur présence avant de les
# configurer. L'adresse anycast 10.53.0.53/32 est portée par la loopback.
set -u

log() { echo "[resolveur-gns3] $*"; }

wait_if() {
    i=0
    while [ $i -lt 80 ]; do
        ip link show "$1" >/dev/null 2>&1 && return 0
        i=$((i + 1))
        sleep 0.25
    done
    return 1
}

# --- eth0 : réseau IXP 172.16.100.0/24 --------------------------------------
if wait_if eth0; then
    ip addr add 172.16.100.53/24 dev eth0 2>/dev/null || true
    ip link set eth0 up
    log "eth0 = 172.16.100.53/24 (IXP)"
else
    log "eth0 absent : le nœud n'est pas connecté à l'IXP"
fi

# --- adresse anycast annoncée en BGP par FRR-A et FRR-C ---------------------
ip addr add 10.53.0.53/32 dev lo 2>/dev/null || true
log "loopback = 10.53.0.53/32 (anycast)"

# --- routes de retour vers les LAN des trois AS -----------------------------
ip route replace 10.1.0.0/24 via 172.16.100.1 2>/dev/null || true
ip route replace 10.2.0.0/24 via 172.16.100.2 2>/dev/null || true
ip route replace 10.3.0.0/24 via 172.16.100.3 2>/dev/null || true

# --- eth1 : accès Internet via le cloud GNS3 branché sur docker0 ------------
if wait_if eth1; then
    ip addr add 172.17.0.53/16 dev eth1 2>/dev/null || true
    ip link set eth1 up
    ip route replace default via 172.17.0.1 dev eth1 2>/dev/null || true
    log "eth1 = 172.17.0.53/16, route par défaut via 172.17.0.1"
fi

# --- ancre DNSSEC -----------------------------------------------------------
if [ ! -s /var/lib/unbound/root.key ]; then
    unbound-anchor -a /var/lib/unbound/root.key >/dev/null 2>&1 || true
fi
chown unbound:unbound /var/lib/unbound/root.key 2>/dev/null || true

# --- services ---------------------------------------------------------------
log "démarrage d'Unbound"
unbound -d -c /etc/unbound/unbound.conf &
UNBOUND_PID=$!

i=0
while [ $i -lt 40 ]; do
    if kill -0 "$UNBOUND_PID" 2>/dev/null; then
        if dig @127.0.0.1 -p 53 localhost +short >/dev/null 2>&1; then
            break
        fi
    else
        log "Unbound s'est arrêté"
        break
    fi
    i=$((i + 1))
    sleep 0.25
done

log "démarrage de DNSdist (53/853/443/8083)"
dnsdist -C /etc/dnsdist/dnsdist.conf --supervised &
DNSDIST_PID=$!

# Garde le conteneur vivant tant qu'au moins un service tourne.
while kill -0 "$UNBOUND_PID" 2>/dev/null || kill -0 "$DNSDIST_PID" 2>/dev/null; do
    sleep 5
done
log "aucun service actif, arrêt du conteneur"
