FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

# Unbound = résolution récursive + DNSSEC ; DNSdist = frontend anti-DDoS/DoH/DoT.
RUN apt-get update && apt-get install -y --no-install-recommends \
        unbound dnsdist openssl iproute2 ca-certificates dnsutils curl \
    && rm -rf /var/lib/apt/lists/*

# Configurations issues du dépôt de l'équipe résolveur, adaptées aux chemins Ubuntu.
COPY unbound.conf /etc/unbound/unbound.conf
COPY blocklists/ /etc/unbound/blocklists/
COPY dnsdist.conf /etc/dnsdist/dnsdist.conf

# Certificat auto-signé pour DoH/DoT (le dépôt attends server.crt / server.key).
RUN mkdir -p /etc/dnsdist/certs /var/lib/unbound /var/run/unbound /var/run/dnsdist \
    && openssl req -x509 -newkey rsa:2048 -nodes -days 365 \
        -keyout /etc/dnsdist/certs/server.key \
        -out /etc/dnsdist/certs/server.crt \
        -subj "/CN=dnsaton.local" \
    && unbound-anchor -a /var/lib/unbound/root.key || true \
    && chown -R unbound:unbound /var/lib/unbound /var/run/unbound /etc/unbound/blocklists \
    && chmod 600 /etc/dnsdist/certs/server.key

COPY start-resolver.sh /usr/local/bin/start-resolver.sh
RUN chmod +x /usr/local/bin/start-resolver.sh

EXPOSE 53/udp 53/tcp 443/tcp 853/tcp 8083/tcp

CMD ["/usr/local/bin/start-resolver.sh"]
