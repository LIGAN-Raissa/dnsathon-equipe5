# DNSaton : Résolveur Public DNS Sécurisé & Résilient

Projet conçu pour le Hackathon : **Déploiement et sécurisation d'un résolveur DNS public moderne**.

---

## 1. Vue d'Ensemble & Architecture

Un résolveur DNS public ne doit jamais être exposé tel quel sur Internet sans couches de protection actives, sous peine d'être détourné pour des attaques par réflexion/amplification DDoS ou de souffrir d'empoisonnement de cache.

Notre architecture sépare strictement les responsabilités en deux tiers :

```
                  [ Clients Internet & Démonstrations ]
                                   |
         +-------------------------+-------------------------+
         | (DoH : 443 TCP)         | (DoT : 853 TCP)         | (DNS : 53 UDP/TCP)
         v                         v                         v
+--------------------------------------------------------------------+
|               DNSdist (Frontend Sécurisé & Anti-DDoS)              |
|  - Terminaison TLS (DoH via HTTP/2 et DoT)                         |
|  - Response Rate Limiting (RRL) contre les attaques par réflexion  |
|  - Drop immédiat des requêtes de type ANY                          |
|  - Rate-limiting par IP client (MaxQPSIPRule)                      |
|  - Exportateur Prometheus natif (Port 8083)                        |
+--------------------------------------------------------------------+
                                   | (Réseau privé Docker interne)
                                   v
+--------------------------------------------------------------------+
|                  Unbound (Moteur Récursif Durci)                   |
|  - Validation stricte DNSSEC (Root trust anchor)                   |
|  - QNAME Minimization (RFC 7816 - Vie privée)                      |
|  - Randomisation de casse (0x20 bit encoding)                      |
|  - Threat Intelligence Sinkholing (Blocage Malware / Phishing)     |
|  - Buffer EDNS à 1232 octets (DNS Flag Day anti-fragmentation)      |
+--------------------------------------------------------------------+
                                   |
                                   v (Internet)
                   [ Serveurs Racines (.) et TLDs ]
```

---

## 2. Piliers de Sécurité Implémentés

| Risque classique | Contre-mesure implémentée dans DNSaton | Composant responsable |
| :--- | :--- | :--- |
| **Écoute passive / Espionnage FAI** | DNS-over-HTTPS (DoH) et DNS-over-TLS (DoT) | **DNSdist** (Port 443 & 853) |
| **DDoS par Amplification DNS** | Blocage des requêtes `ANY` + Response Rate Limiting (RRL) | **DNSdist** |
| **Flood de requêtes par un botnet** | Bridation dynamique par IP (`MaxQPSIPRule`) | **DNSdist** |
| **DNS Spoofing / Empoisonnement** | Validation cryptographique stricte **DNSSEC** | **Unbound** (`auto-trust-anchor`) |
| **Attaque de Kaminsky (Force brute)** | Randomisation des ports + Encodage **0x20** de la casse | **Unbound** (`use-caps-for-id: yes`) |
| **Fuite de métadonnées de navigation** | **QNAME Minimization** (RFC 7816) | **Unbound** (`qname-minimisation: yes`) |
| **Exploits par fragmentation IP** | Taille de paquet EDNS plafonnée à **1232 octets** | **Unbound & DNSdist** |
| **Sites frauduleux & Malwares** | Filtrage préventif dynamique (**Threat Sinkhole**) | **Unbound** (`local-zone redirect`) |
| **Traçage des utilisateurs** | Politique **No-Log** (aucune IP persistée) | **DNSdist & Unbound** |

---

## 3. Guide de Démarrage Rapide

### Étape 1 : Générer les certificats TLS
```bash
cd /home/d4rkc4rl/hack/dnsaton
./scripts/generate-certs.sh
```

### Étape 2 : Démarrer l'infrastructure
```bash
docker compose up -d
```

### Étape 3 : Lancer la suite de tests automatisée
```bash
./scripts/test-suite.sh
```

---

## 4. Scénario de Présentation pour le Jury du Hackathon

1. **Introduction (1 min) :** Présenter le dilemme du DNS public (indispensable, mais vecteur d'attaques numéro 1 si mal configuré).
2. **Démonstration en direct (2 min) :**
   * Lancer `./scripts/test-suite.sh` pour prouver le bon fonctionnement de l'ensemble des 7 mécanismes de sécurité.
   * Montrer la requête sur `sigfail.verteiltesysteme.net` qui retourne `SERVFAIL` (preuve de l'action de DNSSEC contre l'usurpation).
   * Montrer le blocage du malware de test `malware-test.evil.local` qui renvoie `0.0.0.0`.
   * Montrer le blocage de l'amplification sur les requêtes `ANY`.
3. **Monitoring & Télémétrie (1 min) :**
   * Ouvrir l'URL des métriques : `http://localhost:8083/metrics`
   * Expliquer que ces métriques permettent d'alimenter un SOC / Grafana en temps réel.
