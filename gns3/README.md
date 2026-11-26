# Projet GNS3 archivé

Ce dossier contient une copie de la maquette utilisée pour la démonstration.

- `IXP_and_BGP_Peering.gns3` : fichier projet complet (topologie, nœuds, ports consoles).
- `project-files/docker/<uuid>/etc/frr/` : configurations FRR actives de FRR-A, FRR-B et FRR-C, dont `rpki`, `route-map ROV-IN` et les mots de passe MD5 des voisins.
- `project-files/docker/<uuid>/etc/network/interfaces` : adressage IXP et LAN de chaque conteneur.

Correspondance des UUID :

| UUID | Nœud |
|---|---|
| `18bdcd6b-c458-47fa-a8ed-6b8ac7993a54` | FRR-A (AS65001) |
| `2d43ffef-3e00-45ae-834f-159ccafd9f48` | FRR-B (AS65002, filtre RPKI) |
| `f517ea56-a43c-4846-9066-979374a14b5e` | FRR-C (AS65003) |
| `1d674b40-f997-4357-abb2-78ef8b84477b` | Routinator |
| `a1b2c3d4-5e6f-4789-9abc-0123456789ab` | Unbound-Resolveur (`.53`) |
| `b1b2c3d4-5e6f-4789-9abc-0123456789ab` | Unbound-Resolveur-2 (`.54`) |

Les journaux `*.log`, les binaires Dynamips et les métadonnées `.gns3_perms` sont volontairement exclus de l’archive.
