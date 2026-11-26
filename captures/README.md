# Captures pour le rapport — Activité 5

**Captures privilégiées : console de l’interface web** (auto-clic via `?action=…&auto=1`) :

| Demande | Capture web |
|---|---|
| Vérification complète (sessions + cache + BGP) | `web-check.png` |
| VRP Routinator (4 VRP + SLURM) | `web-vrp.png` |
| Attaque visible (`invalid`) | `web-attack.png` |
| Rejet par le filtre (`Network not in table`) | `web-repair.png` |
| Nettoyage | `web-clean.png` |
| Anycast : 2 chemins → 1 chemin → 2 chemins, DNS testé à chaque phase | `web-anycast.png` |
| Test DNS (`NOERROR`) | `web-dns.png` |
| Interface seule | `web-interface.png` |

Les sorties texte brutes correspondantes sont conservées ci-dessous à titre de preuve complémentaire.

| Demande | Fichier |
|---|---|
| Topologie GNS3 complète, nœuds démarrés | `12-topologie-GNS3.png`, `00-desktop.png` |
| Sessions BGP (FRR-B) | `01-bgp-summary-FRR-B.txt` |
| Connexion au cache RPKI | `02-cache-rpki.txt` |
| VRP chargées (4 entrées) | `03-vrp-table.txt` |
| Situation normale (`10.3.0.0/24` valide) | `04-normal-valide.txt` |
| Attaque visible, filtre retiré | `05-attaque-invalide.txt` |
| Rejet par `ROV-IN` + annonce toujours présente sur FRR-C | `06-rejet-filtre.txt` |
| Config `rpki` + route-map `ROV-IN` | `07-routemap-ROV-IN.txt` |
| Anycast : deux chemins `valid` | `08-anycast-avant.txt` |
| Bascule : un seul chemin, service maintenu | `09-anycast-bascule.txt` |
| Restauration : deux chemins | `10-anycast-restauration.txt` |
| Test DNS `drill @10.53.0.53` | `11-test-DNS.txt` |
| Interface web locale | `13-interface-web.png` |

Les fichiers `log-attaque.txt`, `log-reparation.txt` et `log-nettoyage.txt` sont les traces complètes des actions correspondantes.

Note : la page HTTP de Routinator (`172.16.100.254:8323`) n'est pas joignable depuis l'hôte (réseau GNS3 isolé) ; la preuve des VRP est donc apportée par `show rpki prefix-table` et par le SLURM local (`slurm-roa-lab.json`).
