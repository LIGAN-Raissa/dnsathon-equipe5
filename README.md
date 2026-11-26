# DNSathon 2026 — Équipe 5 — Sécurisation du routage et résilience DNS (RPKI, anycast)

Démonstration complète et reproductible : une annonce BGP frauduleuse est détectée puis rejetée par RPKI, tandis qu'un résolveur DNS anycast reste joignable.

> Le guide technique détaillé et les modèles de configuration sont conservés dans [`GUIDE-DETAILLE.md`](GUIDE-DETAILLE.md).

## 1. En une phrase

Parti de la topologie BGP brute de l'équipe 4, nous avons ajouté un validateur Routinator local, des ROA simulés, un filtre `ROV-IN` sur FRR-B, une authentification MD5 des voisins BGP, un outil Python unique, une interface web locale, puis le résolveur anycast reçu de l'équipe 1.

## 2. Ce que le projet prouve

| Protection | Ce qui est démontré |
|---|---|
| RPKI | `10.3.0.0/25` est `invalid` puis rejetée, alors que FRR-C continue de l'annoncer |
| RPKI | `10.3.0.0/24` reste `valid` et acceptée (`local-pref 200`) |
| BGP MD5 | Un routeur pirate branché sur l'IXP ne peut pas établir de session BGP |
| Anycast | `10.53.0.53/32` est annoncée par AS65001 et AS65003 : deux chemins `valid` |
| Disponibilité | Coupure d'un site → un seul chemin, service DNS toujours actif, puis restauration |

**Résumé utilisateur :** « DNSSEC protège ce que vous lisez, RPKI protège par où cela passe, l'anycast protège la disponibilité. »

## 3. Architecture

| Nœud | AS / adresse | Rôle |
|---|---|---|
| FRR-A | AS65001 · IXP `.1` · LAN `10.1.0.0/24` | Préfixe légitime + instance anycast vers `.54` |
| FRR-B | AS65002 · IXP `.2` | Routeur filtre : cache RPKI + route-map `ROV-IN` |
| FRR-C | AS65003 · IXP `.3` · LAN `10.3.0.0/24` | Annonce attaquante + instance anycast vers `.53` |
| Routinator | IXP `.254:3323` (RTR), `:8323` (HTTP) | Validateur local, 4 VRP via SLURM |
| Unbound-Resolveur | IXP `.53` · loopback `10.53.0.53/32` | Instance DNS site A |
| Unbound-Resolveur-2 | IXP `.54` · loopback `10.53.0.53/32` | Instance DNS site C |
| IXP | `172.16.100.0/24` | BGP, RTR et résolveurs |

## 4. Démarrage rapide

### Dans GNS3

Ouvrir `/home/line/GNS3/projects/Projet5DNS/IXP_and_BGP_Peering.gns3`, puis **Start all** sur les 6 nœuds. Une copie du projet et de ses configurations container est fournie dans [`gns3/`](gns3/) pour archive.

> Ne jamais lancer `gns3 start`. Ne jamais faire `docker restart` sur Routinator : utiliser Stop/Start depuis GNS3, sinon l'interface `eth0` injectée par GNS3 est perdue.

### Vérification complète

```bash
cd /home/line/Bureau/dnsathon/equipe5
python3 configurer_gns3.py --check
```

Attendu : `FRR-A/B/C : OK`, `Cache RPKI : OK`, 6 sessions `ESTABLISHED`, 4 VRP.

### Interface web

```bash
python3 demo-web.py
# ouvrir http://127.0.0.1:8080/
```

Sept boutons : vérifier, appliquer, attaquer, réparer, nettoyer, afficher les VRP, tester l'anycast. L'écoute est limitée à `127.0.0.1` et chaque bouton appelle une action autorisée par liste blanche : aucune commande arbitraire n'est acceptée.

## 5. Scénario de démonstration

```bash
python3 configurer_gns3.py --check     # état sain
python3 configurer_gns3.py --vrp       # 4 VRP dans le cache
python3 configurer_gns3.py --attack    # /25 visible, invalid, filtre retiré
python3 configurer_gns3.py --repair    # /25 rejetée, annonce toujours présente sur FRR-C
python3 configurer_gns3.py --clean     # retrait de l'annonce attaquante
python3 configurer_gns3.py --anycast   # 2 chemins → 1 chemin → 2 chemins
python3 configurer_gns3.py --dns       # drill @10.53.0.53 localhost A
```

Points clés à commenter :

- `--repair` ne supprime pas l'annonce : c'est bien `ROV-IN` qui bloque.
- `--anycast` coupe réellement le peering de FRR-C puis le restaure.
- Test DNS : bouton **Tester le DNS (drill)** ou `--dns` → `SERVER: 10.53.0.53`, `rcode: NOERROR`.

## 6. Sécurité ajoutée

```text
rpki
 rpki polling_period 30
 rpki cache tcp 172.16.100.254 3323 preference 1
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
```

En complément, les 6 sessions BGP sont authentifiées par TCP MD5 :

```text
neighbor 172.16.100.x password dnsathon5
```

- **MD5** vérifie qu'on parle au bon voisin ;
- **RPKI** vérifie que le préfixe vient du bon AS ;
- la liste blanche de l'interface web empêche toute commande arbitraire.

## 7. Fichiers principaux

| Fichier | Rôle |
|---|---|
| [`configurer_gns3.py`](configurer_gns3.py) | Configuration, ROA, attaque, réparation, nettoyage, VRP, anycast, vérification |
| [`demo-web.py`](demo-web.py) | Interface locale à 8 boutons, mode capture `?action=…&auto=1` |
| [`slurm-roa-lab.json`](slurm-roa-lab.json) | 4 assertions SLURM injectées dans Routinator |
| [`RAPPORT.md`](RAPPORT.md) | Rapport détaillé, historique complet depuis la maquette brute |
| [`RAPPORT-DNSathon-Equipe5.docx`](RAPPORT-DNSathon-Equipe5.docx) | Version de présentation (19 pages, figures intégrées) |
| [`generer_rapport_docx.py`](generer_rapport_docx.py) | Générateur du DOCX / PDF |
| [`gns3/`](gns3/) | Copie du `.gns3` et des configs FRR/interface des conteneurs |
| [`captures/`](captures/) | Captures web primaires + sorties texte, voir `captures/README.md` |
| [`resolveur/`](resolveur/) | Dépôt reçu de l'équipe 1 : DNSdist, Unbound, Prometheus, Grafana |
| [`GUIDE-DETAILLE.md`](GUIDE-DETAILLE.md) | Guide initial, modèles FRR/BIRD et transposition GNS3 |

## 8. Limites connues

- La page HTTP de Routinator (`:8323`) n'est pas joignable depuis l'hôte : le réseau GNS3 est isolé. La preuve des VRP passe par `show rpki prefix-table` et le SLURM local.
- Le nœud Unbound GNS3 n'a pas d'accès Internet : seuls les tests DNS locaux sont rejoués dans GNS3. Les tests DNSSEC externes du dépôt restent démontrables à part avec `docker compose up -d && ./scripts/test-suite.sh` dans `resolveur/`.
- Le mot de passe MD5 `dnsathon5` est une valeur de lab, à changer pour un environnement réel.

## 9. Restitution

Ordre recommandé : contexte B.A.-BA → topologie → VRP attaque → rejet → vérification sessions → anycast → test DNS → note utilisateur. Le rapport contient la procédure complète et le tableau de correspondance des captures.

---

**Équipe 5 — DNSathon 2026 — 26 novembre 2026**
