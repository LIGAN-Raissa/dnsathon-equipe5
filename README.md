# DNSathon 2026 — Équipe 5 — guide unique (RPKI / anycast / GNS3)

> Documentation consolidée : plan, transposition GNS3, branchement RPKI, modèles FRR/BIRD et démos. Sauvegarde d’origine : `/home/line/GNS3/backups/equipe5_20261126.tar.gz`.

## 1. Plan d’action — activité 5

Source unique : les fichiers du dossier `Bureau/dnsathon`
(Agenda, Récapitulatif participants, Guide des activités et évaluation).

## 1. Ce que les fichiers demandent

D'après le **Récapitulatif participants**, activité 5 :
- « Sécuriser le routage et la résilience DNS (RPKI, anycast) »
- Environnement : la topologie de l'activité 4 (mêmes routeurs FRR ou BIRD).
- Outils : Routinator ou rpki-client **installé par l'équipe**, avec des **ROA simulés en local**.
- Anycast : deux instances du résolveur de l'activité 1 (Resolver 1 et Resolver 2).
- Accès aux caches RPKI/ROA préparés par les organisateurs.
- À livrer : filtrage BGP basé sur RPKI, démo ou schéma anycast, note sur la protection de l'utilisateur final.

D'après le **Guide des activités et évaluation**, points de contrôle pour la notation :
1. Le filtrage RPKI rejette effectivement une annonce invalide simulée par le jury.
2. Le principe d'anycast est démontré ou correctement expliqué et schématisé.
3. Le lien entre sécurité du routage et disponibilité du DNS pour l'utilisateur est clairement argumenté.

Livrables généraux : un rapport technique et 5 à 8 diapositives ; restitution de 10 min de présentation/démo + 5 min d'échanges ; synthèse commune dans le livre blanc.

D'après l'**Agenda** :
- Jour 1, 16h30–17h30 : démarrage de l'activité 5.
- Jour 2, 08h30–13h00 : poursuite et finalisation, préparation des supports.
- Jour 2, 13h00–13h15 : intégration finale avec les 5 activités.
- Jour 2, 14h00–15h15 : restitutions.
- Jour 2, 15h15–16h15 : atelier livre blanc.

## 2. Prérequis (d'après le Récapitulatif)

- Portable chargé avec chargeur, client SSH, `dig` (ou `nslookup`), Wireshark.
- Pour les activités 4 et 5 : installer **GNS3, Containerlab ou EVE-NG** et **FRR** avant d'arriver si possible.
- **8 Go de RAM minimum, 16 Go conseillés.**
- Connexion au Wi-Fi du lab, puis accès aux machines en SSH (identifiants donnés par le mentor).
- Routinator installé par l'équipe : ✅ déjà fait.

## 3. Plan étape par étape

1. **Installer l'environnement** : GNS3 / Containerlab / EVE-NG + FRR (ou BIRD) sur le portable.
2. **Reprendre la topologie de l'activité 4** : au moins 2 AS interconnectés via un switch/IXP, sessions BGP `Established`, échange de préfixes.
3. **Installer et brancher le validateur RPKI** : Routinator en serveur RTR (port 3323) ; connecter les routeurs FRR/BIRD au cache. Utiliser les caches RPKI/ROA fournis par les organisateurs, ou un fichier de ROA simulé en local.
4. **Configurer le filtrage** : appliquer une politique qui refuse les annonces invalides (`match rpki invalid` en FRR, `roa_check = ROA_INVALID` en BIRD).
5. **Préparer la démo avec le jury** : demander quel préfixe et quel AS serviront à l'annonce invalide simulée, et adapter le ROA local en conséquence (le `maxLength` doit rendre l'annonce simulée invalide).
6. **Démontrer l'anycast** : deux instances du résolveur (Resolver 1 et Resolver 2) annonçant la même adresse depuis deux AS ; couper l'une et montrer que le service continue. À défaut, schéma clair + explication.
7. **Rédiger** : note de synthèse (routage vérifiable → DNS disponible → utilisateur protégé), rapport technique avec les commandes et captures, 5 à 8 diapositives.
8. **Répéter la démo** pour tenir dans les 10 minutes, puis participer au livre blanc.

## 4. Fichiers du kit (modèles génériques à adapter)

- `slurm-roa-lab.json` : ROA simulé (RFC 8416) à adapter avec le préfixe/AS du jury.
- Voir §4 (FRR) : cache RTR + route-map de rejet.
- Voir §4 (BIRD 2) : modèle équivalent.
- Voir §5 : script de démonstration (à adapter avec les adresses du lab).
- `demarrer-lab.sh` : script unique — `configure|start|stop|status|web|attack|withdraw|invalid|repair|show`.
- `demarrer-lab.sh` : lance/retire l'annonce attaquante (`attack|withdraw|invalid|repair|show`).
- `web-ui.py` + `demarrer-lab.sh web` : interface web **locale** (127.0.0.1:8080) pour piloter la démo.
- `demarrer-lab.sh configure` : **commande à lancer en premier**. Pose la question « mini-topologie locale ou routeurs de l'équipe 4 ? », demande les valeurs (AS, IP, préfixes), écrit `lab.conf` + le SLURM, puis lance si on répond oui.
- `lab.conf` : valeurs actives partagées par tous les scripts.

Démarrage normal :

```bash
cd ~/Bureau/dnsathon/equipe5
sudo ./demarrer-lab.sh configure
```

## 2. Transposition GNS3 (alignée plan équipe 4 + RPKI réel)

## Plan d'adressage (identique à l'équipe 4)
- IXP : `172.16.100.0/24` — .1 = R1(AS65001), .2 = R2(AS65002), .3 = R3(AS65003), .254 = Routinator
- LAN : `10.1.0.0/24` (R1), `10.2.0.0/24` (R2), `10.3.0.0/24` (R3)
- Attaque : R3 annonce `10.3.0.0/25` (maxLength /24 violé)
- AS privés uniquement : 65001 / 65002 / 65003

## RPKI
- FRR `quay.io/frrouting/frr:10.7.1` + `bgpd -M rpki` (module `bgpd_rpki.so`)
- Nœud Routinator GNS3 (`routinator-lab:latest`), ROA locaux :
  - `10.1.0.0/24 -> AS65001, max /24`
  - `10.3.0.0/24 -> AS65003, max /24`
- R2 : `rpki cache tcp 172.16.100.254 3323` + route-map `ROV-IN` (`match rpki invalid`)
- Filtres prefix-list `AS65001/AS65002/AS65003` conservés comme l'équipe 4 (AS65003 autorise jusqu'à /32 pour laisser la décision au RPKI)

## Vérification finale
- 3 sessions BGP Established
- `show rpki prefix-table` : 2 VRP
- `show ip bgp` sur R2 : `V*> 10.1.0.0/24` (Valide), `N*> 10.2.0.0/24` (local), `10.3.0.0/25` rejetée après `clear bgp 172.16.100.3 in`

## 3. Branchement FRR → Routinator (jour J)

## 0. À remplacer avant de taper

| Placeholder | À remplacer par |
|---|---|
| `<AS_GROUP4>` | le numéro d'AS donné par le groupe 4 (ex. 65001) |
| `<IP_VOISIN>` | l'IP du routeur voisin sur l'IXP (ex. 10.0.0.2) |
| `<IP_CACHE_RPKI>` | `127.0.0.1` si FRR tourne sur ton portable ; l'IP de ton portable si FRR tourne dans une VM/conteneur |

Routinator écoute déjà sur le port **3323** et diffuse notre VRP :
`AS65001,192.0.2.0/24,24,N/A`.

## 1. Prérequis (le jour J seulement)

```bash
sudo apt install -y frr frr-rpki-rtrlib
echo 'bgpd_options="   -A 127.0.0.1 -M rpki"' | sudo tee -a /etc/frr/daemons
sudo systemctl restart frr
```

Sans `frr-rpki-rtrlib` et sans `-M rpki`, la commande `rpki` n'existe pas dans vtysh.

## 2. Commande de branchement (à copier-coller)

```bash
vtysh -c 'configure terminal' \
  -c 'rpki' \
  -c 'rpki polling_period 60' \
  -c 'rpki cache tcp <IP_CACHE_RPKI> 3323 preference 1' \
  -c 'exit' \
  -c 'router bgp <AS_GROUP4>' \
  -c 'neighbor <IP_VOISIN> soft-reconfiguration inbound' \
  -c 'neighbor <IP_VOISIN> route-map ROV-IN in' \
  -c 'exit' \
  -c 'route-map ROV-IN deny 10' \
  -c 'match rpki invalid' \
  -c 'exit' \
  -c 'route-map ROV-IN permit 20' \
  -c 'match rpki valid' \
  -c 'set local-preference 200' \
  -c 'exit' \
  -c 'route-map ROV-IN permit 30' \
  -c 'match rpki notfound' \
  -c 'set local-preference 100' \
  -c 'exit' \
  -c 'end' \
  -c 'write memory'
```

Version équivalente en §4 (FRR).

## 3. Vérifications (à montrer au jury)

```bash
vtysh -c 'show rpki cache-connection'   # doit être "Connected"
vtysh -c 'show rpki prefix-table'       # doit contenir AS65001 192.0.2.0/24 max 24
vtysh -c 'show bgp rpki invalid'        # la fausse annonce doit apparaître ici
```

## 4. Équivalent BIRD 2 (si le groupe 4 utilise BIRD)

Voir §4 (BIRD 2) :

```bird
roa4 table rpki4;
protocol rpki routinator {
    roa4 { table rpki4; };
    remote <IP_CACHE_RPKI> port 3323;
    retry 30;
}
filter ebgp_in {
    if roa_check(rpki4, net, bgp_path.last) = ROA_INVALID then reject;
    accept;
}
```

Puis : `birdc show protocol` et `birdc show route table rpki4`.

## 4. Modèles de configuration RPKI (FRR / BIRD)

### FRR
```
! Modele FRR - a coller dans /etc/frr/frr.conf (ou vtysh -f)
! Prerequis : apt install frr frr-rpki-rtrlib
! /etc/frr/daemons : bgpd_options="  -A 127.0.0.1 -M rpki"
!
hostname R1
!
rpki
 rpki polling_period 60
 rpki retry_interval 30
 rpki cache 127.0.0.1 3323 preference 1
 exit
!
router bgp 65001
 bgp router-id 192.0.2.1
 no bgp ebgp-requires-policy
 neighbor 10.0.0.2 remote-as 65002
 !
 address-family ipv4
  network 192.0.2.0/24
  neighbor 10.0.0.2 soft-reconfiguration inbound
  neighbor 10.0.0.2 route-map ROV-IN in
 exit-address-family
!
route-map ROV-IN deny 10
 match rpki invalid
!
route-map ROV-IN permit 20
 match rpki valid
 set local-preference 200
!
route-map ROV-IN permit 30
 match rpki notfound
 set local-preference 100
!
! Verification :
!   show rpki cache-connection
!   show rpki prefix-table
!   show bgp rpki invalid
!   show bgp 192.0.2.0/25
```

### BIRD 2
```
# Modele BIRD 2 - equivalent du modele FRR
# Prerequis : apt install bird2

roa4 table rpki4;

protocol rpki routinator {
    roa4 { table rpki4; };
    remote 127.0.0.1 port 3323;
    retry 30;
}

filter ebgp_in {
    if roa_check(rpki4, net, bgp_path.last) = ROA_INVALID then reject;
    accept;
}

protocol bgp peer_ixp {
    local 10.0.0.1 as 65001;
    neighbor 10.0.0.2 as 65002;
    ipv4 {
        import filter ebgp_in;
        export all;
    };
}

# Verification :
#   birdc show protocol
#   birdc show route table rpki4
#   birdc show route for 192.0.2.0/25
```

## 5. Démo « détourner, constater, réparer » — 3 commandes

Préfixe de démonstration : `192.0.2.0/24`, origine légitime AS65001, attaquant AS65003.
Adresse anycast du résolveur : `192.0.2.53` (à adapter selon le lab).

## A — Situation normale

```bash
dig @192.0.2.53 www.lab.bj A +short      # -> site A
vtysh -c 'show bgp 192.0.2.0/24'          # origine AS65001, code V (valid)
```

## B — Détournement

Sur le routeur de l'AS65003 :

```bash
vtysh -c 'configure terminal' -c 'router bgp 65003' \
      -c 'network 192.0.2.0/25' -c 'end'
```

Puis, côté victime :

```bash
dig @192.0.2.53 www.lab.bj A +short      # -> site B (!)
vtysh -c 'show bgp 192.0.2.0/25'          # prefixe /25 prefere, code I (invalid)
```

À dire : « le trafic part ailleurs sans message d'erreur : c'est le danger. »

## C — Réparation par le ROA + filtrage ROV

```bash
vtysh -c 'show bgp rpki invalid'          # la /25 apparait comme invalide
vtysh -c 'show bgp 192.0.2.0/25'          # plus rien : annonce rejetee
dig @192.0.2.53 www.lab.bj A +short      # -> site A, service retabli
```

À dire : « le ROA (maxLength /24) rend la /25 invalide ; le routeur la rejette ;
le DNS redevient joignable. DNSSEC protege la donnee, RPKI protege le chemin. »

## Anycast (à enchainer)

```bash
# Retirer un site : sur Resolver 1
sudo ip link down <interface_anycast>     # ou arreter le conteneur du resolver 1
dig @192.0.2.53 www.lab.bj A +short      # repond encore via Resolver 2 (AS65002)
```

Schéma à projeter : `utilisateur -> IP unique 192.0.2.53 -> [AS65001 | AS65002] -> resolver`.
Si un AS tombe, BGP annonce l'autre : une IP, deux sites, continuité de service.

## 6. Démo simulation locale (namespaces)

Routinator diffuse : `AS65001,192.0.2.0/24,24,N/A`
Routeurs : R1=AS65001 (légitime), R2=AS65002 (filtre), R3=AS65003 (attaquant).

## Vérification RPKI (jury)
```bash
sudo ip netns exec as65002 vtysh -N as65002 -c 'show rpki cache-connection'
sudo ip netns exec as65002 vtysh -N as65002 -c 'show rpki prefix-table'
```
Attendu : `Connected`, `192.0.2.0 24-24 65001`.

## A — Attaque visible (filtre temporairement retiré)
```bash
sudo ip netns exec as65002 vtysh -N as65002 \
 -c 'configure terminal' -c 'router bgp 65002' -c 'address-family ipv4' \
 -c 'no neighbor 10.0.23.2 route-map ROV-IN in' -c 'end' -c 'clear bgp 10.0.23.2 in'
sleep 5
sudo ip netns exec as65002 vtysh -N as65002 -c 'show ip bgp 192.0.2.0/25'
```
Attendu : `65003 ... rpki validation-state: invalid`.

## B — Réparation (filtre réappliqué)
```bash
sudo ip netns exec as65002 vtysh -N as65002 \
 -c 'configure terminal' -c 'router bgp 65002' -c 'address-family ipv4' \
 -c 'neighbor 10.0.23.2 route-map ROV-IN in' -c 'end' -c 'write memory' -c 'clear bgp 10.0.23.2 in'
sleep 5
sudo ip netns exec as65002 vtysh -N as65002 -c 'show ip bgp 192.0.2.0/25'
sudo ip netns exec as65002 vtysh -N as65002 -c 'show ip bgp 192.0.2.0/24'
```
Attendu : `/25` = `% Network not in table` ; `/24` = origine `65001`, `rpki validation-state: valid`.
