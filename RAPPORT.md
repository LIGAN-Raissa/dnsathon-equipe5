# Activité 5 — Sécurisation du routage et résilience DNS (RPKI, anycast)

**Équipe 5 — DNSathon 2026 — 26 novembre 2026**

## 0. Contexte et consigne — le B.A.-BA

Avant toute manipulation, voici ce que l’équipe avait à faire et dans quel état elle a reçu le travail.

**La consigne simple :** reprendre la topologie BGP de l’activité 4, déployer un validateur RPKI local avec des ROA simulés, faire apparaître une annonce invalide puis prouver qu’elle est rejetée par un filtre, expliquer et montrer l’anycast, enfin rédiger ce rapport et préparer 5 à 8 diapositives.

**Point de départ reçu :**

| Ce qui était reçu | État initial |
|---|---|
| `IXP_and_BGP_Peering.gns3` | Topologie brute fonctionnelle, **sans RPKI actif** |
| Configs IP/BGP équipe 4 | AS65001/65002/65003, IXP `172.16.100.0/24`, voisins et prefix-lists |
| Nœud Routinator | Déclaré mais hors écran, à l’état « Created » |
| Résolveur équipe 1 | Pas encore livré au début du travail préliminaire |
| Environnement GNS3 | À assainir : conteneurs fantômes, erreurs 409, VPCS trop ancien |

**Résultat attendu, en une phrase :** « `10.3.0.0/25` doit être *invalid* puis rejetée, `10.3.0.0/24` doit rester valide, et l’utilisateur doit continuer à joindre son résolveur. »

## 1. Objectif

Démontrer, sur la maquette GNS3 fournie, qu'une annonce BGP frauduleuse peut être détectée puis rejetée grâce à RPKI, afin que le trafic DNS ne soit pas détourné. Nous nous concentrons d'abord sur le **chemin** (routage), puis nous intégrons le résolveur reçu ensuite pour montrer que le service DNS légitime reste joignable (section 12).

Résultat attendu : une annonce `10.3.0.0/25` émise par l'AS65003 est déclarée **invalid** par notre validateur local, puis **rejetée** par le routeur filtre, tandis que le préfixe légitime `10.3.0.0/24` reste accepté.

## 2. Vocabulaire utile

| Terme | Signification concrète dans notre maquette |
|---|---|
| **AS** (Autonomous System) | Réseau identifié par un numéro : FRR-A = AS65001, FRR-B = AS65002, FRR-C = AS65003. |
| **BGP** | Protocole d'échange de routes entre AS. Chaque routeur annonce son LAN aux deux autres. |
| **Préfixe** | Bloc d'adresses IP annoncé, par exemple `10.3.0.0/24` ou `10.3.0.0/25`. |
| **IXP** | Point d'échange : réseau commun `172.16.100.0/24` où les 3 routeurs et Routinator se connectent. |
| **ROA** | Autorisation d'origine : « tel préfixe peut être annoncé par tel AS, jusqu'à telle longueur ». |
| **VRP** | Entrée validée issue du ROA (ici 2 VRP), fournie au routeur par le validateur. |
| **RPKI** | Infrastructure qui publie et valide ces autorisations. |
| **Routinator** | Notre validateur local ; il parle RTR aux routeurs sur le port `3323`. |
| **maxLength** | Longueur maximale autorisée : notre ROA sur `10.3.0.0/24` a `maxLength = 24`, donc une `/25` est **invalid**. |
| **SLURM** | Format JSON (RFC 8416) utilisé pour injecter nos ROA locaux dans Routinator. |
| **route-map ROV-IN** | Politique appliquée sur FRR-B : rejette `invalid`, privilégie `valid`. |
| **local-preference** | Valeur de préférence BGP : `200` pour `valid`, `100` pour `notfound`. |
| **Established** | État d'une session BGP correctement établie (le chiffre affiché est le nombre de préfixes reçus). |
| **Null0** | Interface virtuelle qui abandonne les paquets ; sert à créer la route locale nécessaire pour annoncer la `/25`. |
| **VPCS** | PC simulés (PC1/PC2/PC3) du projet GNS3, sans rôle dans cette démonstration. |

## 3. Compréhension de la consigne

Le guide de l'activité 5 demande : reprendre la topologie BGP de l'activité 4, déployer un validateur RPKI local avec des ROA simulés, filtrer une annonce invalide, présenter le principe de l'anycast, et expliquer le lien « routage sécurisé → DNS disponible → utilisateur protégé ». Le rapport et 5 à 8 diapositives sont attendus. Nous avons décidé de valider d'abord le scénario RPKI complet, sans intégrer le résolveur.

## 4. Réception de la maquette GNS3

Projet source de vérité : `/home/line/GNS3/projects/Projet5DNS/IXP_and_BGP_Peering.gns3`.

Éléments reçus et identifiés :

- 3 conteneurs FRR (image `quay.io/frrouting/frr:10.7.1`) sur l'IXP `172.16.100.0/24` :
  - `quay.io-frrouting-frr-1` → FRR-A, AS65001, LAN `10.1.0.0/24`, console 5004 ;
  - `quay.io-frrouting-frr-2` → FRR-B, AS65002, LAN `10.2.0.0/24`, console 5005 ;
  - `quay.io-frrouting-frr-3` → FRR-C, AS65003, LAN `10.3.0.0/24`, console 5008 ;
- les configurations FRR de l'équipe 4 : router-id, `network` des LAN, voisins BGP et prefix-lists ;
- 3 VPCS et un switch IXP ;
- un nœud `Routinator-GNS3-1` présent dans le projet mais hors de l'écran et à l'état `Created`.

Avant toute modification, sauvegarde effectuée dans `/home/line/GNS3/backups/Projet5DNS_20261126/`. Les anciens scripts de lab local ont été retirés ; seul ce projet GNS3 est utilisé.

**Dépannage Initial :** conteneurs fantômes supprimés (erreur `409 Conflict`), GNS3 relancé sur le bon chemin (jamais `gns3 start`, mais `gns3start` ou l'ouverture du `.gns3`), et VPCS remplacé par la version `0.6.1` dans `/home/line/gns3env/bin/vpcs` car la version système `0.5b2` était refusée par GNS3 3.0.6.

## 5. Mise en service du nœud Routinator

Le nœud `Routinator-GNS3-1`, déjà déclaré dans la topologie mais hors écran, a été remis en service et intégré au scénario :

- image : `routinator-lab:latest` ;
- commande : `routinator --no-rir-tals --exceptions /tmp/slurm-roa-lab.json --disable-rrdp --disable-rsync server --rtr 0.0.0.0:3323 --http 0.0.0.0:8323` ;
- adresse de démonstration sur l'IXP : `172.16.100.254:3323` (RTR) ;
- ROA local injecté via `slurm-roa-lab.json` (2 VRP) :

| Préfixe | ASN autorisé | maxLength |
|---|---|---|
| `10.1.0.0/24` | AS65001 | `/24` |
| `10.3.0.0/24` | AS65003 | `/24` |

C'est le second VRP qui rend l'annonce attaquante `10.3.0.0/25` invalide (elle dépasse le `maxLength /24`).

**Attention opérationnelle :** le redémarrage du nœud doit se faire depuis GNS3 (Stop puis Start). Un simple `docker restart` casserait l'interface réseau injectée par GNS3 dans le namespace du conteneur. Le script gère cela : il copie le ROA et, si besoin, assigne `172.16.100.254/24` à `eth0` et relance le processus Routinator.

## 6. Activation du module RPKI sur les routeurs

Les 3 conteneurs montent leur `/etc/frr` depuis `project-files/docker/`. Le fichier `daemons` de chaque routeur contient :

```
bgpd_options="  -A 127.0.0.1 -M rpki"
```

Le module `bgpd_rpki.so` est présent dans l'image. L'option `-M rpki` n'est effective qu'après démarrage des nœuds dans GNS3. Vérification possible avec les commandes `show rpki cache-connection` et `show rpki prefix-table`.

## 7. Choix du routeur filtre et connexion au cache

**FRR-B (AS65002)** a été choisi comme point de filtrage : il reçoit les annonces de FRR-C, les compare aux VRP et décide de les accepter ou non.

Configuration ajoutée sur FRR-B :

```
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
router bgp 65002
 address-family ipv4 unicast
  neighbor 172.16.100.3 route-map ROV-IN in
 exit-address-family
exit
```

Politique appliquée :

- **invalid** → rejeté, n'entre pas dans la table BGP ;
- **valid** → accepté et préféré (`local-pref 200`) ;
- **notfound** → accepté mais moins préféré (`local-pref 100`).

RPKI seul ne bloque rien : c'est bien la route-map `ROV-IN` qui traduit la validation en décision de routage.

**Sécurité BGP supplémentaire — authentification des voisins :** en plus du filtrage d'origine RPKI, chaque session BGP est protégée par un mot de passe TCP MD5 (`neighbor 172.16.100.x password dnsathon5`) appliqué aux 6 voisins. Un routeur pirate branché sur l'IXP ne peut donc pas établir de peering : le handshake TCP échoue si le mot de passe ne correspond pas. RPKI vérifie *l'origine du préfixe*, MD5 vérifie *l'identité du voisin* : les deux protections sont complémentaires.

## 8. Script de configuration et de vérification

Fichier : `/home/line/Bureau/dnsathon/equipe5/configurer_gns3.py` (aucune dépendance Python externe).

Fonctions principales :

| Fonction | Rôle |
|---|---|
| `discover_ports()` | Lit le `.gns3` et retrouve les ports consoles A/B/C (5004, 5005, 5008). |
| `Console` | Exécute les commandes via `docker exec -i <conteneur> vtysh` ; le mode `configure terminal` est envoyé dans la **même session** que les commandes, sinon vtysh les refuse. |
| `prepare_roa()` | Écrit le SLURM, le pousse dans Routinator, assure l'IP et le processus. |
| `apply_config()` | Nettoie l'ancien BGP de façon idempotente, applique les configs équipe 4, ajoute l'overlay RPKI sur FRR-B et sauvegarde. |
| `attack()` | Annonce `10.3.0.0/25` depuis FRR-C et ouvre temporairement les prefix-lists + retire `ROV-IN` pour rendre l'annonce visible. |
| `repair()` | Réapplique `ROV-IN` **sans retirer l'attaque**, puis vérifie que la `/25` a disparu et que la `/24` reste valide. |
| `clean()` | Retire l'annonce attaquante et les autorisations temporaires. |
| `verify_router()` / `verify_all()` | Affichent `show ip bgp summary` (contrôle `Established`), `show rpki cache-connection`, `show rpki prefix-table`, `show ip bgp` et un bilan `OK / À VÉRIFIER`. |

Options : `--check` (vérification seule), `--rpki` (défaut), `--no-rpki`, `--attack`, `--repair`, `--clean`, `--prefix`, `--project`, `--port-a/b/c`.

## 9. Interface web de démonstration

Fichier : `/home/line/Bureau/dnsathon/equipe5/demo-web.py`, écoute uniquement sur `127.0.0.1:8080`.

Elle affiche une console colorée et 8 boutons : **Vérifier l'état**, **Appliquer la config**, **Lancer l'attaque**, **Réappliquer le filtre**, **Nettoyer la démo**, **Afficher les VRP Routinator**, **Tester l'anycast (bascule)**, **Tester le DNS (drill)**. Chaque bouton appelle le script Python avec une action autorisée par une liste blanche : aucune commande arbitraire n'est exécutée depuis le navigateur.

## 10. Procédure de démonstration devant le jury

1. Démarrer la topologie dans GNS3, puis ouvrir `http://127.0.0.1:8080/`.
2. Cliquer sur **Vérifier l'état** : 6 sessions `Established`, cache `172.16.100.254:3323` **connecté**, 4 VRP, `10.3.0.0/24` et `10.53.0.53/32` marquées `V`.
3. Cliquer sur **Lancer l'attaque** : `show ip bgp 10.3.0.0/25` affiche `rpki validation-state: invalid` (filtre temporairement désactivé).
4. Cliquer sur **Réappliquer le filtre** : la `/25` devient `% Network not in table` **alors que FRR-C l'annonce toujours**, et la `/24` reste valide. C'est la preuve que le filtre RPKI, et non la suppression de l'annonce, bloque l'attaque.
5. Cliquer sur **Vérifier l'état** pour montrer que toutes les sessions restent établies.
6. Cliquer sur **Nettoyer la démo** pour retirer l'attaque.
7. Cliquer sur **Afficher les VRP Routinator** (4 VRP, dont les deux `/32` anycast), puis sur **Tester l'anycast (bascule)** : deux chemins `valid`, retrait d'un site, restauration automatique. Le test DNS est rejoué **à chaque phase** : deux instances actives, puis une seule restante après la coupure, puis les deux après restauration — le service répond `NOERROR` dans les trois cas.
8. Cliquer sur **Tester le DNS (drill)** : site-A (`.53` → TXT `site-A`), site-C (`.54` → TXT `site-C`) et anycast (`10.53.0.53` → `NOERROR`).
9. Terminer par la note utilisateur : DNSSEC protège la donnée, RPKI protège le chemin vers le résolveur.

Équivalent en ligne de commande :

```bash
cd /home/line/Bureau/dnsathon/equipe5
python3 configurer_gns3.py --check
python3 configurer_gns3.py --attack
python3 configurer_gns3.py --repair
python3 configurer_gns3.py --check
python3 configurer_gns3.py --clean
python3 configurer_gns3.py --vrp
python3 configurer_gns3.py --anycast
python3 configurer_gns3.py --dns
```

## 11. État validé

- 3 routeurs FRR configurés, 6 sessions BGP `ESTABLISHED` ;
- module RPKI actif (`-M rpki`) sur les 3 routeurs ;
- Routinator connecté à FRR-B, **4 VRP** chargées ;
- `10.3.0.0/24` → `valid` (local-pref 200) ;
- `10.53.0.53/32` → `valid` avec **deux chemins** (AS65001 et AS65003), soit un anycast réellement opérationnel ;
- bascule anycast vérifiée (retrait puis restauration de l'instance AS65003) ;
- `10.3.0.0/25` → `invalid` avec le filtre désactivé, absente de la table avec le filtre actif ;
- aucune erreur résiduelle lors du run complet, interface web opérationnelle.

## 12. Interface avec l'équipe résolveur

**Reçu le 26/11 :** dépôt `https://github.com/Fabrice000/dnsathon.2026`, copié localement dans `resolveur/`. Il contient une pile Docker Compose : DNSdist (frontend, `172.28.0.3`, ports hôte 53/853/443/8083) → Unbound (récursif, `172.28.0.2`, validation DNSSEC stricte), plus Prometheus et Grafana. Le script `scripts/test-suite.sh` valide 8 mécanismes (résolution, flag `ad` DNSSEC, `SERVFAIL` sur signature corrompue, sinkhole malware, blocage ANY, DoH, DoT, métriques).

**Intégration réalisée dans le projet GNS3 :** le dépôt ne fournit pas d'IP annonçable ni d'AS (pile Docker `172.28.0.0/24`). Nous avons donc retenu la convention de lab `10.53.0.53/32`, annoncée simultanément par **AS65001 (FRR-A)** et **AS65003 (FRR-C)** pour simuler l'anycast. **Deux instances anycast** (`Unbound-Resolveur` et `Unbound-Resolveur-2`, image `mvance/unbound:latest`, configs durcies du dépôt) ont été ajoutées à la topologie `IXP_and_BGP_Peering.gns3` et connectées au switch IXP : `172.16.100.53/24` et `172.16.100.54/24`, chacune portant la **même** adresse `10.53.0.53/32` en loopback. FRR-A route vers `172.16.100.54`, FRR-C vers `172.16.100.53`. FRR-B voit donc **deux chemins `valid`** pour le /32 (AS65001 via `.1` et AS65003 via `.3`) avec `local-pref 200` : c'est un vrai anycast, pas seulement un schéma. Deux VRP supplémentaires (`10.53.0.53/32 → AS65001` et `→ AS65003`, `maxLength 32`) ont été ajoutés au SLURM de Routinator : le cache expose désormais **4 VRP** et le préfixe du résolveur est **`valid`** avec `local-pref 200` sur FRR-B.

Vérification rapide (tout est OK) :
```bash
python3 configurer_gns3.py --check
# Cache RTR CONNECTÉ ; 3 sessions BGP OK ; V*> 10.53.0.53/32 via 172.16.100.3, rpki validation-state: valid
drill @10.53.0.53 localhost A     # SERVER: 10.53.0.53, réponse NOERROR
```

La suite complète DNSdist/DoH/DoT/Prometheus du dépôt reste démontrable séparément (`cd resolveur && docker compose up -d && ./scripts/test-suite.sh`) ; le cœur DNSSEC, lui, est maintenant dans GNS3.

Checklist initiale — **satisfaite par convention de lab** faute d'IP/AS fournis par l'équipe :

| Élément attendu | Retenu dans la maquette |
|---|---|
| IP du résolveur à annoncer | `10.53.0.53/32` |
| AS d'origine | AS65001 **et** AS65003 (anycast) |
| Deux instances, même IP | `Unbound-Resolveur` (`.53`) et `Unbound-Resolveur-2` (`.54`) |
| VRP correspondants | 2 assertions `/32`, `maxLength 32`, dans le SLURM |
| Preuve de validation | `rpki validation-state: valid` sur FRR-B, deux chemins |
| Test DNS reproductible | `--dns` : site-A (`.53` → TXT `site-A`), site-C (`.54` → TXT `site-C`) et anycast (`10.53.0.53` → `NOERROR`) |

La suite complète DNSdist/DoH/DoT du dépôt reste disponible si l'équipe veut présenter ses 8 tests tels quels ; notre intégration GNS3, elle, est terminée et autonome.

## 13. Livrables et suites

**Livrés :** `configurer_gns3.py`, `demo-web.py`, `slurm-roa-lab.json`, ce rapport. Sauvegardes dans `/home/line/GNS3/backups/`.

**Reste à produire pour le dossier final :** courte note utilisateur, 5 à 8 diapositives et captures des sorties (`show ip bgp summary`, `show rpki prefix-table`, rejet de la `/25`, bascule anycast). L'intégration du résolveur et le schéma anycast sont désormais réalisés (section 12) : plus rien n'attend l'équipe résolveur.
