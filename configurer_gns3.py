#!/usr/bin/env python3
"""Configure les 3 routeurs FRR d'une maquette GNS3 avec les configs équipe 4.

Aucune dépendance Python : les commandes passent par « docker exec … vtysh ».
Usage :
    python3 configurer_gns3.py            # applique FRR-A/B/C + RPKI + ROA local, puis vérifie
    python3 configurer_gns3.py --check    # vérification seule (sans rien modifier)
    python3 configurer_gns3.py --no-rpki  # configs équipe 4 seules
    python3 configurer_gns3.py --project /chemin/maquette.gns3
"""

import argparse
import json
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

DEFAULT_PROJECT = "/home/line/GNS3/projects/Projet5DNS/IXP_and_BGP_Peering.gns3"

# --- Configurations fournies par l'équipe 4 (lignes de configuration seules) ---
CONFIGS = {
    "A": {
        "asn": 65001,
        "hostname": "FRR-A",
        "lines": """
hostname FRR-A
log syslog informational
service integrated-vtysh-config
ip prefix-list AS65001 seq 10 permit 10.1.0.0/24
ip prefix-list AS65002 seq 10 permit 10.2.0.0/24
ip prefix-list AS65001 seq 1 permit 10.53.0.53/32
ip prefix-list AS65003 seq 1 permit 10.53.0.53/32
ip prefix-list AS65003 seq 10 permit 10.3.0.0/24
ip route 10.53.0.53/32 172.16.100.53
interface eth0
 description LAN-AS65001
 ip address 10.1.0.1/24
exit
interface eth1
 description PEERING-IXP
 ip address 172.16.100.1/24
exit
router bgp 65001
 bgp router-id 172.16.100.1
 neighbor 172.16.100.2 remote-as 65002
 neighbor 172.16.100.3 remote-as 65003
 address-family ipv4 unicast
  network 10.1.0.0/24
  network 10.53.0.53/32
  neighbor 172.16.100.2 prefix-list AS65002 in
  neighbor 172.16.100.2 prefix-list AS65001 out
  neighbor 172.16.100.3 prefix-list AS65003 in
  neighbor 172.16.100.3 prefix-list AS65001 out
 exit-address-family
exit
""".strip().splitlines(),
    },
    "B": {
        "asn": 65002,
        "hostname": "FRR-B",
        "lines": """
hostname FRR-B
log syslog informational
service integrated-vtysh-config
ip prefix-list AS65001 seq 10 permit 10.1.0.0/24
ip prefix-list AS65002 seq 10 permit 10.2.0.0/24
ip prefix-list AS65001 seq 1 permit 10.53.0.53/32
ip prefix-list AS65003 seq 1 permit 10.53.0.53/32
ip prefix-list AS65003 seq 10 permit 10.3.0.0/24
interface eth0
 description LAN-AS65002
 ip address 10.2.0.1/24
exit
interface eth1
 description PEERING-IXP
 ip address 172.16.100.2/24
exit
router bgp 65002
 bgp router-id 172.16.100.2
 neighbor 172.16.100.1 remote-as 65001
 neighbor 172.16.100.3 remote-as 65003
 address-family ipv4 unicast
  network 10.2.0.0/24
  neighbor 172.16.100.1 prefix-list AS65001 in
  neighbor 172.16.100.1 prefix-list AS65002 out
  neighbor 172.16.100.3 prefix-list AS65003 in
  neighbor 172.16.100.3 prefix-list AS65002 out
 exit-address-family
exit
""".strip().splitlines(),
    },
    "C": {
        "asn": 65003,
        "hostname": "FRR-C",
        "lines": """
hostname FRR-C
log syslog informational
service integrated-vtysh-config
ip prefix-list AS65001 seq 10 permit 10.1.0.0/24
ip prefix-list AS65002 seq 10 permit 10.2.0.0/24
ip prefix-list AS65001 seq 1 permit 10.53.0.53/32
ip prefix-list AS65003 seq 1 permit 10.53.0.53/32
ip prefix-list AS65003 seq 10 permit 10.3.0.0/24
ip route 10.53.0.53/32 172.16.100.53
interface eth0
 description LAN-AS65003
 ip address 10.3.0.1/24
exit
interface eth1
 description PEERING-IXP
 ip address 172.16.100.3/24
exit
router bgp 65003
 bgp router-id 172.16.100.3
 neighbor 172.16.100.1 remote-as 65001
 neighbor 172.16.100.2 remote-as 65002
 address-family ipv4 unicast
  network 10.3.0.0/24
  network 10.53.0.53/32
  neighbor 172.16.100.1 prefix-list AS65001 in
  neighbor 172.16.100.1 prefix-list AS65003 out
  neighbor 172.16.100.2 prefix-list AS65002 in
  neighbor 172.16.100.2 prefix-list AS65003 out
 exit-address-family
exit
""".strip().splitlines(),
    },
}

# --- Sécurité BGP supplémentaire : authentification MD5 des voisins --------
# Un routeur pirate branché sur l'IXP ne peut pas établir de session BGP :
# TCP refuse le 3-way handshake si le mot de passe MD5 ne correspond pas.
BGP_PASSWORD = "dnsathon5"
for _cfg in CONFIGS.values():
    _secured = []
    for _line in _cfg["lines"]:
        _secured.append(_line)
        _m = re.match(r"^ neighbor (\S+) remote-as \d+$", _line)
        if _m:
            _secured.append(f" neighbor {_m.group(1)} password {BGP_PASSWORD}")
    _cfg["lines"] = _secured

# Overlay RPKI appliqué UNIQUEMENT à FRR-B (AS65002) :
# - connecte bgpd au cache RTR de notre Routinator GNS3 ;
# - route-map ROV-IN : rejette les annonces Invalid, préfère les Valid.
RPKI_OVERLAY_B = """
rpki
 rpki polling_period 30
 rpki cache tcp 172.16.100.254 3323 preference 1
exit
router bgp 65002
 address-family ipv4 unicast
  neighbor 172.16.100.3 route-map ROV-IN in
 exit-address-family
exit
route-map ROV-IN deny 10
 match rpki invalid
exit
route-map ROV-IN permit 20
 match rpki valid
 set local-preference 200
exit
route-map ROV-IN permit 30
 match rpki notfound
 set local-preference 100
exit
""".strip().splitlines()

# --- ROA local (format SLURM, RFC 8416) ------------------------------------
# Deux VRP : le /24 légitime de R1 et le /24 de R3 (maxLength /24).
# C’est ce dernier qui rend l’annonce attaquante 10.3.0.0/25 « invalid ».
ROA_LOCAL = {
    "slurmVersion": 1,
    "validationOutputFilters": {"prefixFilters": [], "bgpsecFilters": []},
    "locallyAddedAssertions": {
        "prefixAssertions": [
            {"asn": 65001, "prefix": "10.1.0.0/24", "maxPrefixLength": 24,
             "comment": "ROA local equipe 5 - prefixe legitime"},
            {"asn": 65003, "prefix": "10.3.0.0/24", "maxPrefixLength": 24,
             "comment": "ROA local equipe 5 - rend 10.3.0.0/25 invalide"},
            {"asn": 65001, "prefix": "10.53.0.53/32", "maxPrefixLength": 32,
             "comment": "ROA local - resolveur anycast site A"},
            {"asn": 65003, "prefix": "10.53.0.53/32", "maxPrefixLength": 32,
             "comment": "ROA local - resolveur anycast site C"},
        ],
        "bgpsecAssertions": [],
    },
}


def prepare_roa(output=Path(__file__).resolve().parent / "slurm-roa-lab.json", push=True):
    """Écrit le ROA local (SLURM), le pousse dans Routinator et redémarre le conteneur.

    Si le conteneur n'est pas « Up », le fichier reste prêt sur le disque.
    Le redémarrage du nœud doit se faire dans GNS3 (jamais « docker restart »).
    """
    output.write_text(json.dumps(ROA_LOCAL, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[ROA] fichier local écrit : {output}")
    if not push:
        return
    proc = subprocess.run(
        ["docker", "ps", "-a", "--filter", "name=GNS3.Routinator",
         "--format", "{{.ID}} {{.Status}}"],
        capture_output=True, text=True, timeout=15,
    )
    lines = [l.split(maxsplit=1) for l in proc.stdout.splitlines() if l.strip()]
    if not lines:
        print("[ROA] conteneur Routinator introuvable (démarrez le nœud GNS3).")
        return
    cid, status = lines[0]
    if not status.startswith("Up"):
        print(f"[ROA] Routinator à l'état '{status}' : ROA local prêt, à charger au prochain démarrage.")
        return
    # Le conteneur GNS3 lit /tmp/slurm-roa-lab.json au démarrage (voir son Cmd).
    # Attention : un « docker restart » casserait les interfaces réseau injectées
    # par GNS3 dans le namespace du conteneur. On se contente de copier le ROA :
    # redémarrez le nœud Routinator depuis GNS3 (Stop puis Start) pour le charger.
    subprocess.run(["docker", "cp", str(output), f"{cid}:/tmp/slurm-roa-lab.json"],
                   check=True, capture_output=True, timeout=20)
    print(f"[ROA] ROA poussé dans Routinator ({cid}).")

    def dexec(args):
        return subprocess.run(["docker", "exec", cid] + args,
                              capture_output=True, text=True, timeout=20).stdout

    # GNS3 injecte eth0 dans le namespace du conteneur au démarrage du nœud.
    net = dexec(["ip", "addr", "show", "eth0"])
    if "inet " not in net:
        if "eth0" in net:
            dexec(["ip", "addr", "add", "172.16.100.254/24", "dev", "eth0"])
            print("[ROA] IP 172.16.100.254/24 assignée à eth0.")
        else:
            print("[ROA] eth0 absent : faites Stop puis Start du nœud Routinator dans GNS3.")
    # Le processus Routinator peut être mort après un restart Docker : le relancer.
    if not dexec(["pgrep", "routinator"]).strip():
        dexec(["sh", "-c", "nohup routinator --no-rir-tals "
               "--exceptions /tmp/slurm-roa-lab.json --disable-rrdp --disable-rsync "
               "server --rtr 0.0.0.0:3323 --http 0.0.0.0:8323 >/tmp/routinator.log 2>&1 &"])
        print("[ROA] processus Routinator relancé avec le ROA local.")


# --- Accès aux routeurs -----------------------------------------------------
# Le port console Telnet de GNS3 ne renvoie pas la sortie vtysh dans cette
# maquette ; on utilise donc « docker exec -i <conteneur> vtysh » : fiable et
# sans dépendance externe. Les IDs des conteneurs sont lus dans le .gns3.
import subprocess

CONTAINERS = {}  # port console -> ID conteneur Docker, rempli par discover_ports()


class Console:
    """Exécute des commandes vtysh dans le conteneur FRR (api Docker en CLI)."""

    def __init__(self, host, port, timeout=5):
        """Retrouve le conteneur associé au port console du nœud GNS3."""
        cid = CONTAINERS.get(port)
        if not cid:
            raise RuntimeError(f"Aucun conteneur FRR connu pour le port {port}.")
        self.cid = cid
        self.buf = ""

    def read(self, timeout=3):
        """Renvoie la sortie de la dernière commande exécutée."""
        return self.buf

    def send(self, line, delay=0.03):
        """Exécute une seule commande vtysh et mémorise sa sortie."""
        self.commands([line])

    def commands(self, lines):
        """Envoie une liste de commandes vtysh et renvoie toute la sortie."""
        script = "\n".join(l for l in lines if l.strip()) + "\n"
        proc = subprocess.run(["docker", "exec", "-i", self.cid, "vtysh"],
                              input=script, capture_output=True, text=True, timeout=30)
        self.buf = proc.stdout + proc.stderr
        return self.buf

    def configure(self, lines):
        """Applique des lignes de configuration dans UNE seule session vtysh.

        Indispensable avec docker exec : chaque Session est indépendante, donc
        « configure terminal » et les commandes doivent être envoyés ensemble.
        """
        return self.commands(["configure terminal"] + list(lines) + ["end"])

    def close(self):
        """Rien à fermer : chaque commande est un processus docker exec."""
        pass


def discover_ports(project):
    """Lit le fichier .gns3 et associe FRR-A/B/C à leurs ports console (triés par nom)."""
    """Retourne {'A': port, 'B': port, 'C': port} depuis le fichier .gns3."""
    with open(project, encoding="utf-8") as f:
        data = json.load(f)
    nodes = [n for n in data["topology"]["nodes"]
             if "frr" in str(n.get("properties", {}).get("image", "")).lower()]
    nodes.sort(key=lambda n: n["name"])
    if len(nodes) < 3:
        raise RuntimeError("Moins de 3 nœuds FRR trouvés dans la maquette.")
    ports = {}
    for key, node in zip("ABC", nodes[:3]):
        port = int(node["console"])
        ports[key] = port
        CONTAINERS[port] = node.get("properties", {}).get("container_id")
    return ports


def apply_config(host, port, key, rpki=False, check_only=False):
    """Connecte un routeur, efface son ancien BGP, applique sa config équipe 4 et sauvegarde."""
    cfg = CONFIGS[key]
    con = Console(host, port)
    try:
        banner = con.read(timeout=5)
        if re.search(r"(?i)login|username", banner):
            con.send("")
            banner += con.read(timeout=3)
        print(f"[FRR-{key}] port {port} — connecté")

        if check_only:
            con.send("show ip bgp summary")
            out = con.read(timeout=5)
            con.send("show ip bgp")
            out += con.read(timeout=8)
            print(out.strip())
            return

        # Nettoyage + config en UNE session : sinon vtysh oublie le mode config.
        lines = [f"no router bgp {cfg['asn']}", "no ip prefix-list AS65001",
                 "no ip prefix-list AS65002", "no ip prefix-list AS65003",
                 "no route-map ROV-IN", "no rpki"] + list(cfg["lines"])
        if rpki and key == "B":
            lines += list(RPKI_OVERLAY_B)
        out = con.configure(lines)
        con.commands(["write memory"])
        # Ne signaler que les vraies erreurs (et non « Configuration applied
        # with notes », qui est un message normal de vtysh).
        errors = [l for l in out.splitlines() if re.search(
            r"(?i)unknown command|invalid input|syntax error|unknown neighbor|specify remote-as", l)]
        if errors:
            print(f"[FRR-{key}] attention : certaines lignes ont été refusées :")
            print("\n".join(errors))

        con.send("show ip bgp summary")
        print(con.read(timeout=8).strip())
        print(f"[FRR-{key}] configuration appliquée et sauvegardée.")
    finally:
        con.close()


def run_on(host, port, commands, configure=False):
    """Exécute des commandes vtysh (ou de configuration) sur un routeur."""
    con = Console(host, port)
    try:
        con.read(timeout=3)
        return con.configure(commands) if configure else con.commands(commands)
    finally:
        con.close()


def attack(host, ports, prefix="10.3.0.0/25"):
    """Annonce une /25 invalide depuis FRR-C et la montre sur FRR-B sans filtre."""
    # 1) FRR-C : il faut une route exacte dans la RIB pour que BGP annonce le préfixe.
    out = run_on(host, ports["C"], [
        # prefix-list de sortie équipe 4 : on autorise temporairement la /25
        "ip prefix-list AS65003 seq 5 permit 10.3.0.0/25 le 25",
        f"ip route {prefix} Null0", "router bgp 65003",
        "address-family ipv4 unicast", f"network {prefix}",
    ], configure=True)
    out += run_on(host, ports["C"], ["write memory", "clear bgp *"])
    print(f"[ATTAQUE] FRR-C annonce {prefix}\n{out.strip()}")
    # 2) FRR-B : on retire temporairement ROV-IN pour rendre l'annonce visible.
    # La prefix-list équipe 4 n'autorise que le /24 : on l'assouplit juste le
    # temps de l'attaque, sinon c'est elle (et non RPKI) qui bloquerait le /25.
    out = run_on(host, ports["B"], [
        "ip prefix-list AS65003 seq 5 permit 10.3.0.0/25 le 25",
        "router bgp 65002", "address-family ipv4 unicast",
        "no neighbor 172.16.100.3 route-map ROV-IN in",
    ], configure=True)
    run_on(host, ports["B"], ["clear bgp *"])
    time.sleep(4)  # laisse BGP recalculer avant le show
    out += run_on(host, ports["B"], [f"show ip bgp {prefix}"])
    print(f"[SANS FILTRE] {prefix} doit apparaître avec 'invalid' :\n{out.strip()}")


def repair(host, ports, prefix="10.3.0.0/25"):
    """Réapplique ROV-IN SANS retirer l'attaque : prouve que seul RPKI bloque le /25."""
    out = run_on(host, ports["B"], [
        "router bgp 65002", "address-family ipv4 unicast",
        "neighbor 172.16.100.3 route-map ROV-IN in",
    ], configure=True)
    run_on(host, ports["B"], ["write memory", "clear bgp *"])
    time.sleep(4)
    out += run_on(host, ports["B"], [f"show ip bgp {prefix}", "show ip bgp 10.3.0.0/24"])
    print("[AVEC FILTRE] FRR-C annonce toujours la /25, mais ROV-IN la rejette :\n" + out.strip())


def clean(host, ports, prefix="10.3.0.0/25"):
    """Retire l'annonce attaquante et les prefix-lists temporaires (nettoyage final)."""
    out = run_on(host, ports["C"], [
        "no ip prefix-list AS65003 seq 5", f"no ip route {prefix} Null0",
    ], configure=True)
    out += run_on(host, ports["C"], [
        "router bgp 65003", "address-family ipv4 unicast", f"no network {prefix}",
    ], configure=True)
    out += run_on(host, ports["B"], ["no ip prefix-list AS65003 seq 5"], configure=True)
    out += run_on(host, ports["C"], ["write memory", "clear bgp *"])
    print("[NETTOYAGE] annonce et autorisations temporaires retirées :\n" + out.strip())


def ensure_whoami(project):
    """Garantit un enregistrement TXT distinct dans chaque instance Unbound."""
    data = json.loads(Path(project).read_text(encoding="utf-8"))
    sites = {}
    for node in data["topology"]["nodes"]:
        name = node["name"].lower()
        cid = node.get("properties", {}).get("container_id")
        if "unbound" not in name or not cid:
            continue
        site = "site-C" if "-2" in name or "resolveur-2" in name else "site-A"
        sites[site] = cid
    for site, cid in sites.items():
        conf = "/opt/unbound/etc/unbound/unbound.conf"
        check = subprocess.run(
            ["docker", "exec", cid, "sh", "-c", f"grep -q 'whoami.dnsathon.local' {conf}"],
            capture_output=True,
        )
        if check.returncode != 0:
            zone = (f'\nserver:\n'
                    f'    local-zone: "whoami.dnsathon.local." static\n'
                    f'    local-data: "whoami.dnsathon.local. IN TXT \\"{site}\\""\n')
            subprocess.run(["docker", "exec", "-i", cid, "sh", "-c", f"cat >> {conf}"],
                           input=zone, text=True, capture_output=True)
            subprocess.run(["docker", "exec", cid, "sh", "-c",
                            "kill -HUP $(cat /opt/unbound/etc/unbound/unbound.pid)"],
                           capture_output=True)
            time.sleep(1)
    return sites


def dns_test(host, ports, project=None, quiet=False):
    """Teste les deux instances et le service anycast avec drill."""
    cid = CONTAINERS.get(ports["B"])
    if not cid:
        print("[ERREUR] ID du conteneur FRR-B introuvable dans la maquette.", file=sys.stderr)
        return False
    sites = ensure_whoami(project) if project else {}

    def drill(server, query, net=None):
        cmd = ["docker", "run", "--rm", "--network", f"container:{net or cid}",
               "--entrypoint", "sh", "mvance/unbound:latest",
               "-c", f"drill @{server} {query}"]
        last = ""
        for _ in range(3):
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                last = (proc.stdout + proc.stderr).strip()
                if "network error" not in last.lower():
                    return last
            except Exception as exc:
                last = f"ERREUR : {exc}"
            time.sleep(0.5)
        return last

    cases = [
        ("cas 1 — instance site A (172.16.100.53)", "172.16.100.53",
         "whoami.dnsathon.local TXT", "site-A", sites.get("site-A")),
        ("cas 2 — instance site C (172.16.100.54)", "172.16.100.54",
         "whoami.dnsathon.local TXT", "site-C", sites.get("site-C")),
        ("service anycast (10.53.0.53)", "10.53.0.53",
         "localhost A", "127.0.0.1", None),
    ]
    results = []
    for label, server, query, expected, net in cases:
        output = drill(server, query, net)
        ok = "rcode: NOERROR" in output and expected in output
        results.append(ok)
        if not quiet:
            print(f"\n===== TEST DNS — {label} =====")
            print(output)
        print(f"DNS {label.split(' — ')[0]} : {'OK' if ok else 'À VÉRIFIER'}")
    return all(results)


def verify_router(host, port, key):
    """Affiche « show ip bgp summary » et vérifie que les 2 voisins IXP sont Established."""
    neighbors = {"A": ("172.16.100.2", "172.16.100.3"),
                 "B": ("172.16.100.1", "172.16.100.3"),
                 "C": ("172.16.100.1", "172.16.100.2")}[key]
    con = Console(host, port)
    try:
        con.read(timeout=3)
        con.send("show ip bgp summary")
        summary = con.read(timeout=8)
    finally:
        con.close()
    print(f"\n===== FRR-{key} : show ip bgp summary =====")
    print(summary.strip())
    ok = True
    for line in summary.splitlines():
        fields = line.split()
        if fields and fields[0] in neighbors and len(fields) >= 10:
            # Colonne « State/PfxRcd » (index 9) : un chiffre = Established.
            est = fields[9].isdigit()
            ok &= est
            print(f"  {fields[0]} AS{fields[2]} : {'ESTABLISHED' if est else 'NON ESTABLISHED (' + fields[9] + ')'}")
    return ok


def verify_all(host, ports, rpki=True):
    """Vérifie A/B/C + le cache RPKI de FRR-B, puis imprime le bilan OK / À VÉRIFIER."""
    print("\n########## VÉRIFICATION FINALE ##########")
    results = {k: verify_router(host, ports[k], k) for k in "ABC"}
    cache_ok = True
    if rpki:
        con = Console(host, ports["B"])
        try:
            con.read(timeout=3)
            con.send("show rpki cache-connection")
            cache = con.read(timeout=6)
            con.send("show rpki prefix-table")
            vrps = con.read(timeout=6)
            con.send("show ip bgp")
            bgp = con.read(timeout=8)
        finally:
            con.close()
        print("\n===== FRR-B : show rpki cache-connection =====")
        print(cache.strip())
        print("\n===== FRR-B : show rpki prefix-table =====")
        print(vrps.strip())
        cache_ok = "No connection" not in cache and bool(re.search(r"(?i)connect|up|established", cache))
        print(f"  Cache RTR 172.16.100.254:3323 : {'CONNECTÉ' if cache_ok else 'NON CONNECTÉ'}")
        print("\n===== FRR-B : show ip bgp (validation RPKI) =====")
        print(bgp.strip())
    print("\n########## RÉSULTAT ##########")
    for k in "ABC":
        print(f"  FRR-{k} sessions BGP : {'OK' if results[k] else 'À VÉRIFIER'}")
    if rpki:
        print(f"  Cache RPKI (FRR-B)  : {'OK' if cache_ok else 'À VÉRIFIER'}")
    print("###############################\n")
    return all(results.values()) and cache_ok


def main():
    """Point d'entrée : options CLI, détection des ports, configuration puis vérification."""
    ap = argparse.ArgumentParser(description="Configure les FRR d'une maquette GNS3 (configs équipe 4 + RPKI + ROA local).")
    ap.add_argument("--project", default=DEFAULT_PROJECT, help="fichier .gns3 de la maquette")
    ap.add_argument("--host", default="127.0.0.1", help="hôte GNS3")
    ap.add_argument("--port-a", type=int, help="port console FRR-A (remplace la détection)")
    ap.add_argument("--port-b", type=int, help="port console FRR-B")
    ap.add_argument("--port-c", type=int, help="port console FRR-C")
    ap.add_argument("--rpki", dest="rpki", action="store_true", default=True,
                    help="applique le filtre RPKI et le ROA local (défaut)")
    ap.add_argument("--no-rpki", dest="rpki", action="store_false",
                    help="configs équipe 4 seules")
    ap.add_argument("--check", action="store_true", help="vérification seule, sans modifier")
    ap.add_argument("--attack", action="store_true", help="simule l'annonce invalide depuis FRR-C")
    ap.add_argument("--repair", action="store_true", help="réapplique ROV-IN sans retirer l'attaque (preuve du filtre)")
    ap.add_argument("--clean", action="store_true", help="retire l'annonce attaquante après la démo")
    ap.add_argument("--prefix", default="10.3.0.0/25", help="préfixe attaquant (défaut 10.3.0.0/25)")
    ap.add_argument("--vrp", action="store_true", help="affiche les VRP du cache RPKI (Routinator)")
    ap.add_argument("--anycast", action="store_true",
                    help="prouve l'anycast : 2 chemins valides, puis bascule et restauration")
    ap.add_argument("--dns", action="store_true",
                    help="teste le résolveur anycast : drill @10.53.0.53 localhost A")
    args = ap.parse_args()

    try:
        ports = discover_ports(args.project)
    except Exception as exc:
        print(f"[ERREUR] détection des ports : {exc}", file=sys.stderr)
        ports = {}
    for k, v in (("A", args.port_a), ("B", args.port_b), ("C", args.port_c)):
        if v:
            ports[k] = v
    if set(ports) != {"A", "B", "C"}:
        print("[ERREUR] ports consoles manquants ; utilisez --port-a/--port-b/--port-c.", file=sys.stderr)
        sys.exit(2)

    # Les ports peuvent changer si la maquette est recréée : on les relit à chaque run.
    if args.attack or args.repair or args.clean:
        # L'attaque repart d'une config saine ; la réparation ne doit surtout pas
        # réinitialiser BGP, sinon on effacerait l'annonce attaquante à prouver.
        if args.attack:
            for key in "ABC":
                apply_config(args.host, ports[key], key, rpki=True)
            attack(args.host, ports, args.prefix)
        if args.repair:
            repair(args.host, ports, args.prefix)
        if args.clean:
            clean(args.host, ports, args.prefix)
        return

    if args.anycast:
        print("===== ANYCAST : état initial (2 instances, 2 chemins valides) =====")
        print(run_on(args.host, ports["B"], [
            "show ip bgp 10.53.0.53/32",
        ]).strip())
        print("\n===== BASCULE : coupure temporaire du peering AS65003 (FRR-C) =====")
        try:
            run_on(args.host, ports["C"], [
                "router bgp 65003", "neighbor 172.16.100.2 shutdown",
            ], configure=True)
            time.sleep(4)
            print(run_on(args.host, ports["B"], [
                "show ip bgp 10.53.0.53/32",
            ]).strip())
            print("\nDNS pendant la coupure : service toujours joignable ?")
            dns_test(args.host, ports, args.project, quiet=True)
        finally:
            print("\n===== RESTAURATION automatique du peering AS65003 =====")
            run_on(args.host, ports["C"], [
                "router bgp 65003", "no neighbor 172.16.100.2 shutdown",
            ], configure=True)
            time.sleep(4)
            print(run_on(args.host, ports["B"], [
                "show ip bgp 10.53.0.53/32",
            ]).strip())
            print("\nDNS après restauration : service joignable ?")
            dns_test(args.host, ports, args.project, quiet=True)
        return

    if args.dns:
        print("===== TEST DNS — deux instances + service anycast =====")
        dns_test(args.host, ports, args.project)
        return

    if args.vrp:
        print("===== VRP du cache RPKI (via FRR-B) =====")
        print(run_on(args.host, ports["B"], [
            "show rpki cache-connection", "show rpki prefix-table",
        ]).strip())
        print("\n===== Déclarations SLURM locales (Routinator) =====")
        slurm = Path(__file__).resolve().parent / "slurm-roa-lab.json"
        data = json.loads(slurm.read_text(encoding="utf-8"))
        for a in data["locallyAddedAssertions"]["prefixAssertions"]:
            print(f"  {a['prefix']} -> AS{a['asn']} (maxLength {a['maxPrefixLength']})")
        return

    # Les ports peuvent changer si la maquette est recréée : on les relit à chaque run.
    print("Ports consoles :", ", ".join(f"FRR-{k}={ports[k]}" for k in "ABC"))
    if not args.check:
        if args.rpki:
            prepare_roa(push=True)
        for key in "ABC":
            try:
                apply_config(args.host, ports[key], key, rpki=args.rpki, check_only=False)
            except Exception as exc:
                print(f"[ERREUR] FRR-{key} : {exc}", file=sys.stderr)
    if not args.check:
        time.sleep(6)  # laisse BGP se rétablir après « no router bgp » / « clear bgp * »
    verify_all(args.host, ports, rpki=args.rpki)


if __name__ == "__main__":
    main()
