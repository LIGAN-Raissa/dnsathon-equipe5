#!/usr/bin/env python3
"""Génère le rapport DOCX de l'activité 5 (équipe 5) à partir du travail réalisé.

Aucune dépendance autre que python-docx (pip install python-docx).
Sortie : RAPPORT-DNSathon-Equipe5.docx, dans le même dossier.
"""
from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

BASE = Path(__file__).resolve().parent
CAP = BASE / "captures"
OUT = BASE / "RAPPORT-DNSathon-Equipe5.docx"

BLEU = RGBColor(0x1D, 0x4E, 0x89)
GRIS = RGBColor(0x44, 0x55, 0x70)
ROUGE = RGBColor(0x9B, 0x2C, 0x3D)
VERT = RGBColor(0x1E, 0x7A, 0x55)


def shade(cell, color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:fill"), color)
    tcPr.append(shd)


def code(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Inches(0.18)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.space_before = Pt(2)
    r = p.add_run(text)
    r.font.name = "Consolas"
    r.font.size = Pt(8.5)
    r.font.color.rgb = GRIS
    return p


def bullets(doc, items, level=0):
    for it in items:
        p = doc.add_paragraph(style="List Bullet" if level == 0 else "List Bullet 2")
        p.paragraph_format.space_after = Pt(2)
        p.add_run(it)


def numbered(doc, items):
    for it in items:
        p = doc.add_paragraph(style="List Number")
        p.paragraph_format.space_after = Pt(3)
        p.add_run(it)


def table(doc, headers, rows, widths=None):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Light Grid Accent 1"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(headers):
        cell = t.rows[0].cells[i]
        cell.text = ""
        run = cell.paragraphs[0].add_run(h)
        run.bold = True
        run.font.color.rgb = BLEU
        run.font.size = Pt(9)
        shade(cell, "E8EFF8")
    for row in rows:
        cells = t.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = ""
            r = cells[i].paragraphs[0].add_run(str(val))
            r.font.size = Pt(8.8)
    if widths:
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Inches(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def image(doc, name, caption, width=6.1):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    path = CAP / name
    if path.exists():
        p.add_run().add_picture(str(path), width=Inches(width))
    c = doc.add_paragraph(caption)
    c.alignment = WD_ALIGN_PARAGRAPH.CENTER
    c.runs[0].italic = True
    c.runs[0].font.size = Pt(8.5)
    c.runs[0].font.color.rgb = GRIS
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def h(doc, text, level=1):
    p = doc.add_heading(text, level=level)
    p.paragraph_format.space_before = Pt(12 if level == 1 else 8)
    p.paragraph_format.space_after = Pt(5)
    return p


# ---------------------------------------------------------------------------
doc = Document()
sec = doc.sections[0]
sec.top_margin = Inches(0.75)
sec.bottom_margin = Inches(0.7)
sec.left_margin = Inches(0.85)
sec.right_margin = Inches(0.85)

normal = doc.styles["Normal"]
normal.font.name = "Aptos"
normal.font.size = Pt(10.2)
normal.paragraph_format.space_after = Pt(5)
normal.paragraph_format.line_spacing = 1.12
for name, size in (("Title", 26), ("Heading 1", 15), ("Heading 2", 12)):
    st = doc.styles[name]
    st.font.name = "Aptos Display"
    st.font.size = Pt(size)
    st.font.color.rgb = BLEU
    st.font.bold = True

# Pied de page avec numéro de page.
footer = sec.footer.paragraphs[0]
footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = footer.add_run("DNSathon 2026 · Équipe 5 · Activité 5 — page ")
r.font.size = Pt(8)
fld = OxmlElement("w:fldSimple")
fld.set(qn("w:instr"), "PAGE")
footer._p.append(fld)

# --- Page de garde ----------------------------------------------------------
t = doc.add_paragraph()
t.alignment = WD_ALIGN_PARAGRAPH.CENTER
t.paragraph_format.space_before = Pt(80)
r = t.add_run("DNSATHON 2026")
r.bold = True
r.font.size = Pt(16)
r.font.color.rgb = VERT

t = doc.add_paragraph()
t.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = t.add_run("Activité 5\nSécurisation du routage et résilience DNS\n(RPKI, anycast)")
r.bold = True
r.font.size = Pt(27)
r.font.color.rgb = BLEU

s = doc.add_paragraph()
s.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = s.add_run("Du fichier GNS3 brut de l’équipe 4 au résolveur anycast de l’équipe 1")
r.font.size = Pt(13)
r.font.color.rgb = GRIS

s = doc.add_paragraph()
s.alignment = WD_ALIGN_PARAGRAPH.CENTER
s.paragraph_format.space_before = Pt(40)
r = s.add_run("Rapport d’activité · Équipe 5 · 26 novembre 2026")
r.font.size = Pt(11)

s = doc.add_paragraph()
s.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = s.add_run("Livrables : configurer_gns3.py · demo-web.py · slurm-roa-lab.json · captures/ · ce rapport")
r.font.size = Pt(9)
r.font.color.rgb = GRIS
doc.add_page_break()

# --- Contexte / B.A.-BA -----------------------------------------------------
h(doc, "0. Contexte et consigne — le B.A.-BA de l’activité")
doc.add_paragraph(
    "Avant toute manipulation, voici ce que l’équipe 5 avait à faire et dans quel état elle a reçu le travail. "
    "Cette section pose le contexte pour que la suite du rapport se lise sans connaissance préalable."
)

h(doc, "0.1 La consigne simple", 2)
doc.add_paragraph(
    "L’activité 5 demandait de démontrer qu’une annonce BGP frauduleuse peut être rejetée grâce à RPKI, "
    "afin que le trafic DNS ne soit pas détourné. Concrètement, l’équipe devait :"
)
numbered(doc, [
    "Reprendre la topologie BGP de l’activité 4 (équipe 4) : trois routeurs FRR, un switch IXP et les PC simulés.",
    "Déployer un validateur RPKI local avec des ROA simulés, puis connecter les routeurs à ce validateur.",
    "Faire apparaître une annonce invalide, puis prouver qu’elle est rejetée par un filtre, "
    "sans casser le préfixe légitime ni les sessions BGP.",
    "Expliquer le principe de l’anycast et montrer son lien avec la disponibilité du service DNS.",
    "Rédiger ce rapport et préparer 5 à 8 diapositives de présentation.",
])

h(doc, "0.2 Point de départ reçu", 2)
table(doc, ["Ce qui était reçu", "État initial"], [
    ["Fichier GNS3 IXP_and_BGP_Peering.gns3", "Topologie brute, fonctionnelle, mais sans RPKI actif."],
    ["Configs IP/BGP de l’équipe 4", "AS65001/65002/65003, IXP 172.16.100.0/24, voisins et prefix-lists."],
    ["Nœud Routinator", "Déclaré dans le projet mais hors écran, à l’état « Created »."],
    ["Résolveur de l’équipe 1", "Pas encore livré au début du travail préliminaire."],
    ["Environnement GNS3", "À assainir : conteneurs fantômes, erreurs 409, VPCS trop ancien."],
], [2.6, 3.9])

h(doc, "0.3 Résultat attendu, en une phrase", 2)
p = doc.add_paragraph()
r = p.add_run("« ")
r.italic = True
p.add_run("10.3.0.0/25 doit être invalid puis rejetée, 10.3.0.0/24 doit rester valide, "
          "et l’utilisateur doit continuer à joindre son résolveur.").bold = True
r = p.add_run(" »")
r.italic = True
doc.add_paragraph(
    "Le reste du rapport explique comment nous sommes passés de ce point de départ à ce résultat, "
    "étape par étape, puis comment nous avons intégré le résolveur reçu ensuite."
)

# --- Synthèse ---------------------------------------------------------------
h(doc, "1. Synthèse exécutive")
doc.add_paragraph(
    "Nous avons repris la topologie BGP de l’activité 4 fournie par l’équipe 4 (trois routeurs FRR, "
    "un switch IXP, aucun RPKI actif), puis construit couche après couche un validateur RPKI local, "
    "une politique de filtrage, un outil de démonstration automatisé et enfin l’intégration du "
    "résolveur reçu de l’équipe 1. La démonstration prouve qu’une annonce BGP frauduleuse est "
    "détectée puis rejetée, alors que le service DNS légitime reste joignable."
)
bullets(doc, [
    "6 sessions BGP établies, cache RPKI connecté à 172.16.100.254:3323, 4 VRP chargées.",
    "10.3.0.0/25 est invalid avec le filtre retiré, puis absente de la table BGP avec le filtre actif, "
    "bien que FRR-C continue de l’annoncer.",
    "10.3.0.0/24 reste valid et acceptée (local-pref 200).",
    "Le résolveur est déployé en anycast réel : deux instances, même IP 10.53.0.53/32, annoncée par AS65001 et AS65003, "
    "deux chemins valid et bascule vérifiée.",
    "Tout est pilotable depuis une interface web locale à liste blanche, et toutes les preuves sont capturées.",
])

# --- Démarche chronologique --------------------------------------------------
h(doc, "2. Démarche chronologique : du brut au résultat")
doc.add_paragraph(
    "Cette section est le fil conducteur du dossier. Elle suit exactement l’ordre dans lequel nous avons travaillé, "
    "y compris le travail préliminaire réalisé avant la réception des éléments des équipes 4 et 1."
)

h(doc, "2.1 Phase 0 — Préparer l’environnement, avant toute réception", 2)
doc.add_paragraph(
    "Avant même de disposer des configurations des autres équipes, nous avons assaini l’environnement GNS3 :"
)
bullets(doc, [
    "Identification du projet source de vérité : /home/line/GNS3/projects/Projet5DNS/IXP_and_BGP_Peering.gns3.",
    "Suppression des conteneurs fantômes à l’origine d’erreurs 409 Conflict.",
    "GNS3 relancé sur le bon chemin, sans jamais utiliser « gns3 start » : uniquement gns3start ou l’ouverture du .gns3.",
    "Remplacement du VPCS système 0.5b2, refusé par GNS3 3.0.6, par la version 0.6.1 dans /home/line/gns3env/bin/vpcs.",
    "Sauvegarde systématique dans /home/line/GNS3/backups/ avant chaque modification.",
    "Décision de travailler uniquement dans ce projet GNS3 : abandon du lab local antérieur.",
])

h(doc, "2.2 Phase 1 — Réception de la topologie brute de l’équipe 4", 2)
doc.add_paragraph(
    "L’équipe 4 nous a transmis le fichier .gns3 et les configurations IP/BGP. La topologie était fonctionnelle "
    "mais totally dépourvue de RPKI : aucun module -M rpki, aucun validateur en service, aucune route-map."
)
table(doc, ["Nœud", "AS", "LAN", "IXP", "Console"], [
    ["FRR-A (frr-1)", "65001", "10.1.0.0/24 (.1)", "172.16.100.1", "5004"],
    ["FRR-B (frr-2)", "65002", "10.2.0.0/24 (.1)", "172.16.100.2", "5005"],
    ["FRR-C (frr-3)", "65003", "10.3.0.0/24 (.1)", "172.16.100.3", "5008"],
], [1.6, 0.8, 1.7, 1.5, 0.9])
bullets(doc, [
    "Voisinages eBGP en full-mesh sur l’IXP 172.16.100.0/24, router-id = adresse IXP.",
    "Prefix-lists d’entrée/sortie de l’équipe 4 conservées telles quelles dans notre script.",
    "Trois VPCS et le switch IXP repris sans modification.",
    "Un nœud Routinator existait dans le projet mais était hors écran et à l’état « Created ».",
])
doc.add_paragraph(
    "Nous n’avons pas réécrit ces configurations : elles sont intégrées telles quelles dans CONFIGS du script, "
    "ce qui garantit la continuité avec le travail de l’équipe 4."
)

h(doc, "2.3 Phase 2 — Mise en service du validateur RPKI local", 2)
bullets(doc, [
    "Activation du module RPKI dans les trois fichiers daemons : bgpd_options=\"  -A 127.0.0.1 -M rpki\".",
    "Vérification de la présence de bgpd_rpki.so dans l’image FRR.",
    "Routinator remis en service avec l’image routinator-lab:latest : RTR 0.0.0.0:3323, HTTP 8323.",
    "Injection d’un SLURM local (slurm-roa-lab.json) avec deux VRP initiaux.",
])
table(doc, ["Préfixe", "AS autorisé", "maxLength", "Rôle"], [
    ["10.1.0.0/24", "AS65001", "/24", "Préfixe légitime de FRR-A"],
    ["10.3.0.0/24", "AS65003", "/24", "Rend la /25 attaquante invalide"],
], [1.7, 1.2, 1.0, 2.6])
p = doc.add_paragraph()
r = p.add_run("Règle d’exploitation : ")
r.bold = True
p.add_run("redémarrer Routinator depuis GNS3 (Stop puis Start), jamais avec docker restart, "
          "qui casserait l’interface eth0 injectée par GNS3.")

h(doc, "2.4 Phase 3 — Politique de filtrage sur FRR-B", 2)
doc.add_paragraph(
    "FRR-B (AS65002) a été choisi comme routeur filtre : il reçoit les annonces de FRR-C et applique la décision RPKI. "
    "RPKI ne fait que classer les routes ; c’est la route-map qui transforme ce classement en action."
)
code(doc,
     "rpki\n"
     " rpki polling_period 30\n"
     " rpki cache tcp 172.16.100.254 3323 preference 1\n"
     "exit\n"
     "route-map ROV-IN deny 10\n"
     " match rpki invalid\n"
     "exit\n"
     "route-map ROV-IN permit 20\n"
     " match rpki valid\n"
     " set local-preference 200\n"
     "exit\n"
     "route-map ROV-IN permit 30\n"
     " match rpki notfound\n"
     " set local-preference 100\n"
     "exit\n"
     "router bgp 65002\n"
     " address-family ipv4 unicast\n"
     "  neighbor 172.16.100.3 route-map ROV-IN in\n"
     " exit-address-family")
table(doc, [" État RPKI", "Décision", "Effet"], [
    ["invalid", "deny", "Rejeté, n’entre pas dans la table BGP"],
    ["valid", "permit", "Accepté et préféré (local-pref 200)"],
    ["notfound", "permit", "Accepté mais moins préféré (local-pref 100)"],
], [1.4, 1.2, 3.9])

doc.add_paragraph(
    "Une sécurité BGP supplémentaire a été ajoutée : authentification TCP MD5 de chaque voisin "
    "(neighbor 172.16.100.x password dnsathon5, appliquée aux 6 sessions). Un routeur pirate branché sur l’IXP "
    "ne peut pas établir de peering, car le handshake TCP échoue sans le bon mot de passe. RPKI vérifie l’origine "
    "du préfixe, MD5 vérifie l’identité du voisin : les deux protections sont complémentaires."
)

h(doc, "2.5 Phase 4 — Automatisation par un seul script Python", 2)
doc.add_paragraph(
    "configurer_gns3.py est l’outil principal. Il n’a aucune dépendance externe et pilote directement vtysh dans les "
    "conteneurs FRR identifiés dans le fichier .gns3. Le port console Telnet ne renvoyant pas la sortie, nous utilisons "
    "docker exec -i <cid> vtysh, avec configure terminal et les commandes dans la même session."
)
table(doc, ["Fonction / option", "Rôle"], [
    ["discover_ports()", "Relit le .gns3 et retrouve les ports 5004/5005/5008 et les IDs conteneurs."],
    ["prepare_roa()", "Écrit le SLURM, le pousse dans Routinator, assure l’IP IXP et le processus."],
    ["apply_config()", "Applique les configs équipe 4 + overlay RPKI de façon idempotente."],
    ["--attack", "FRR-C annonce 10.3.0.0/25 ; le filtre est temporairement retiré pour rendre l’annonce visible."],
    ["--repair", "Réapplique ROV-IN sans retirer l’attaque : preuve que le filtre, pas la suppression, bloque."],
    ["--clean", "Retire l’annonce attaquante et les autorisations temporaires."],
    ["--check", "Vérifie sessions, cache, VRP et validation sans rien modifier."],
    ["--vrp", "Affiche le cache et les quatre VRP."],
    ["--anycast", "Affiche deux chemins, coupe le peering de FRR-C, puis le restaure automatiquement."],
], [1.9, 4.6])
doc.add_paragraph("Commandes de référence :")
code(doc,
     "python3 configurer_gns3.py --check\n"
     "python3 configurer_gns3.py --attack\n"
     "python3 configurer_gns3.py --repair\n"
     "python3 configurer_gns3.py --clean\n"
     "python3 configurer_gns3.py --vrp\n"
     "python3 configurer_gns3.py --anycast")

h(doc, "2.6 Phase 5 — Interface web de démonstration", 2)
doc.add_paragraph(
    "demo-web.py expose une console locale sur http://127.0.0.1:8080/. Chaque bouton appelle le script Python avec "
    "une action autorisée par une liste blanche : aucune commande arbitraire n’est acceptée depuis le navigateur. "
    "Huit actions sont disponibles : Vérifier l’état, Appliquer la config, Lancer l’attaque, Réappliquer le filtre, "
    "Nettoyer la démo, Afficher les VRP Routinator, Tester l’anycast et Tester le DNS (drill)."
)
doc.add_paragraph(
    "Un mode capture ( ?action=…&auto=1 ) exécute automatiquement une action et agrandit la console, "
    "ce qui a permis de générer toutes les captures d’écran primaires du rapport."
)

h(doc, "2.7 Phase 6 — Réception du résolveur de l’équipe 1 et intégration", 2)
doc.add_paragraph(
    "L’équipe 1 a fourni le dépôt https://github.com/Fabrice000/dnsathon.2026 : une pile Docker Compose "
    "DNSdist (172.28.0.3, ports 53/853/443/8083) → Unbound (172.28.0.2, validation DNSSEC stricte), "
    "avec Prometheus, Grafana et une suite de huit tests. Le dépôt ne précisait toutefois ni IP annonçable ni AS d’origine."
)
bullets(doc, [
    "Décision retenue : adresse anycast de lab 10.53.0.53/32, annoncée par AS65001 et AS65003.",
    "Deux VRP supplémentaires ajoutés au SLURM : /32 → AS65001 et /32 → AS65003, maxLength 32 (4 VRP au total).",
    "Prefix-lists équipe 4 assouplies en seq 1 pour autoriser le /32 avant validation RPKI.",
    "Routes statiques sur FRR-A vers 172.16.100.54 et sur FRR-C vers 172.16.100.53, puis network 10.53.0.53/32.",
    "Deux nœuds Unbound ajoutés à GNS3 : Unbound-Resolveur (.53) et Unbound-Resolveur-2 (.54), "
    "chacun avec la même loopback 10.53.0.53/32 et des routes de retour vers les trois LAN.",
    "FRR-B voit deux chemins valid pour le /32, avec local-pref 200 : anycast réel, pas seulement schématique.",
    "Bascule vérifiée par coupure du peering de FRR-C : 2 chemins → 1 chemin → 2 chemins, service maintenu.",
    "Test DNS reproductible : bouton « Tester le DNS (drill) » ou --dns : drill @10.53.0.53 localhost A renvoie NOERROR.",
])
doc.add_paragraph(
    "L’enregistrement « whoami » distinct par instance, évoqué comme option, n’a pas été retenu : "
    "la bascule est déjà prouvée par les chemins BGP. La suite DNSdist/DoH/DoT complète reste démontrable "
    "séparément avec docker compose up -d && ./scripts/test-suite.sh."
)

h(doc, "2.8 Phase 7 — Validation finale et capitalisation", 2)
doc.add_paragraph(
    "Chaque étape a été vérifiée avec --check, puis capturée. Le rapport, les scripts, le SLURM, le dépôt résolveur "
    "et le dossier captures/ constituent un dossier autonome, sans dépendance vis-à-vis des autres équipes."
)

# --- Architecture -----------------------------------------------------------
h(doc, "3. Architecture retenue")
table(doc, ["Élément", "Adresse / AS", "Rôle"], [
    ["FRR-A", "AS65001 · IXP .1 · LAN 10.1.0.0/24", "Origine du /24 légitime et du /32 anycast (instance .54)"],
    ["FRR-B", "AS65002 · IXP .2", "Routeur filtre, cache RPKI et route-map ROV-IN"],
    ["FRR-C", "AS65003 · IXP .3 · LAN 10.3.0.0/24", "Origine du /24 attaqué et du /32 anycast (instance .53)"],
    ["Routinator", "IXP .254:3323 (RTR), :8323 (HTTP)", "Validateur local, 4 VRP via SLURM"],
    ["Unbound-Resolveur", "IXP .53 · lo 10.53.0.53/32", "Instance DNS anycast A"],
    ["Unbound-Resolveur-2", "IXP .54 · lo 10.53.0.53/32", "Instance DNS anycast C"],
    ["IXP", "172.16.100.0/24", "Switch commun : BGP, RTR et résolveurs"],
], [1.8, 2.3, 2.4])

# --- Preuves ----------------------------------------------------------------
h(doc, "4. Preuves et captures")
table(doc, ["Élément demandé", "Capture"], [
    ["Topologie GNS3 complète, nœuds démarrés", "12-topologie-GNS3.png / 00-desktop.png"],
    ["Sessions BGP (FRR-B)", "web-check.png · 01-bgp-summary-FRR-B.txt"],
    ["Connexion au cache RPKI", "web-check.png · 02-cache-rpki.txt"],
    ["4 VRP chargées", "web-vrp.png · 03-vrp-table.txt"],
    ["Situation normale : /24 valide", "web-check.png · 04-normal-valide.txt"],
    ["Attaque visible : /25 invalid", "web-attack.png · 05-attaque-invalide.txt"],
    ["Rejet par ROV-IN + annonce toujours sur FRR-C", "web-repair.png · 06-rejet-filtre.txt"],
    ["Config rpki + route-map ROV-IN", "07-routemap-ROV-IN.txt"],
    ["Anycast : deux chemins valid", "web-anycast.png · 08-anycast-avant.txt"],
    ["Bascule anycast avant / pendant / après", "web-anycast.png · 08/09/10-anycast-*.txt"],
    ["Test DNS", "web-dns.png · 11-test-DNS.txt"],
    ["Interface web colorée", "web-interface.png / 13-interface-web.png"],
], [3.6, 2.9])
p = doc.add_paragraph()
r = p.add_run("Note : ")
r.bold = True
p.add_run("la page HTTP de Routinator n’est pas joignable depuis l’hôte (réseau GNS3 isolé). "
          "La preuve des VRP est apportée par show rpki prefix-table et par le fichier SLURM local.")

image(doc, "web-check.png", "Figure 1 — Console web : vérification complète (sessions, cache, BGP, anycast).")
image(doc, "web-vrp.png", "Figure 2 — Console web : les quatre VRP et les assertions SLURM.")
image(doc, "web-attack.png", "Figure 3 — Attaque visible : 10.3.0.0/25 est invalid, filtre retiré.")
image(doc, "web-repair.png", "Figure 4 — Filtre réappliqué : la /25 n’est plus dans la table.")
image(doc, "web-anycast.png", "Figure 5 — Anycast : deux chemins, coupure du site C, puis restauration.")
image(doc, "web-dns.png", "Figure 6 — Console web : test DNS anycast, statut NOERROR.")
image(doc, "web-interface.png", "Figure 7 — Interface web locale et ses huit boutons.")

# --- Procédure --------------------------------------------------------------
h(doc, "5. Procédure de démonstration devant le jury")
numbered(doc, [
    "Dans GNS3, démarrer tous les nœuds (Start all), puis attendre 20 à 30 s.",
    "Ouvrir http://127.0.0.1:8080/ et cliquer sur Vérifier l’état : 6 sessions OK, cache connecté, 4 VRP.",
    "Montrer la carte ROA local : 4 VRP, dont les deux /32 anycast.",
    "Cliquer sur Afficher les VRP Routinator et commenter les quatre entrées.",
    "Cliquer sur Lancer l’attaque : la /25 apparaît avec rpki validation-state: invalid.",
    "Cliquer sur Réappliquer le filtre : la /25 devient % Network not in table, alors que FRR-C l’annonce toujours.",
    "Cliquer sur Vérifier l’état : toutes les sessions restent établies, la /24 reste valide.",
    "Cliquer sur Tester l’anycast : deux chemins valid, puis un seul pendant la coupure, puis deux à nouveau.",
    "Cliquer sur Tester le DNS (drill) : SERVER 10.53.0.53, statut NOERROR.",
    "Conclure par la note utilisateur : DNSSEC protège la donnée, RPKI protège le chemin, l’anycast protège la disponibilité.",
])

# --- Résultats --------------------------------------------------------------
h(doc, "6. Résultats validés")
bullets(doc, [
    "3 routeurs FRR configurés, 6 sessions BGP ESTABLISHED, aucune erreur résiduelle.",
    "6 sessions protégées par authentification TCP MD5 : un voisin pirate ne peut pas se connecter.",
    "Module RPKI actif sur les trois routeurs ; cache RTR connecté à 172.16.100.254:3323.",
    "4 VRP chargées ; 10.3.0.0/24 et 10.53.0.53/32 classées valid (local-pref 200).",
    "10.3.0.0/25 invalid avec le filtre désactivé, absente de la table avec le filtre actif.",
    "Anycast opérationnel : deux instances, deux chemins valid, bascule vérifiée et restauration automatique.",
    "Interface web opérationnelle, actions limitées à une liste blanche.",
])

# --- Difficultés ------------------------------------------------------------
h(doc, "7. Difficultés rencontrées et décisions prises")
table(doc, ["Problème", "Solution retenue"], [
    ["Console Telnet GNS3 sans sortie vtysh", "Pilotage par docker exec -i <cid> vtysh, dans une seule session."],
    ["Erreur 409 Conflict / conteneurs fantômes", "Nettoyage des conteneurs et relance GNS3 sur le bon projet."],
    ["VPCS 0.5b2 refusé par GNS3 3.0.6", "Installation de VPCS 0.6.1 dans l’environnement gns3env."],
    ["docker restart cassait eth0 du Routinator", "Redémarrage exclusivement depuis GNS3, via l’API du contrôleur."],
    ["Prefix-list équipe 4 bloquait la /25 avant RPKI", "Autorisation temporaire en seq 5 pendant l’attaque seulement."],
    ["Route statique /32 transformée en blackhole", "Configuration après mise en service du nœud résolveur."],
    ["Bascule anycast peu lisible (next-hop récursif)", "Coupure du peering FRR-C → FRR-B plutôt que retrait de route."],
    ["Repo résolveur sans IP/AS annonçable", "Convention de lab 10.53.0.53/32, deux VRP et deux instances."],
], [2.7, 3.8])

# --- Note utilisateur -------------------------------------------------------
h(doc, "8. Ce que cette démonstration prouve pour l’utilisateur")
doc.add_paragraph(
    "Un utilisateur qui interroge le résolveur veut trois choses : une réponse authentique, un chemin non détourné "
    "et un service disponible. Le projet couvre ces trois dimensions :"
)
bullets(doc, [
    "DNSSEC (équipe 1) vérifie l’authenticité et l’intégrité de la réponse DNS : la donnée n’a pas été falsifiée.",
    "RPKI (équipe 5) vérifie que le préfixe par lequel le résolveur est atteint est annoncé par le bon AS : "
    "le chemin n’a pas été détourné.",
    "L’anycast (deux instances, une même IP) maintient le service si un site tombe : la disponibilité est préservée.",
    "La note utilisateur se résume ainsi : « DNSSEC protège ce que vous lisez, RPKI protège par où cela passe. »",
])

# --- Livrables --------------------------------------------------------------
h(doc, "9. Livrables et organisation des fichiers")
table(doc, ["Fichier", "Contenu"], [
    ["configurer_gns3.py", "Configuration complète, ROA, attaque, réparation, nettoyage, VRP, anycast, vérification."],
    ["demo-web.py", "Interface locale à huit boutons, liste blanche, mode capture."],
    ["slurm-roa-lab.json", "Quatre assertions SLURM injectées dans Routinator."],
    ["captures/", "Captures web primaires, sorties texte, README de correspondance."],
    ["resolveur/", "Dépôt reçu de l’équipe 1 (pile DNSdist/Unbound/monitoring)."],
    ["RAPPORT.md / ce DOCX", "Rapport détaillé et version de présentation structurée."],
    ["equipe5.zip", "Archive complète du dossier, hors .git du dépôt résolveur."],
], [2.1, 4.4])

# --- Conclusion -------------------------------------------------------------
h(doc, "10. Conclusion")
doc.add_paragraph(
    "Parti d’une topologie GNS3 brute, sans validation d’origine, nous avons construit une chaîne complète et "
    "reproductible : validateur local, ROA maîtrisés, filtre appliqué au bon endroit, automatisation sûre, "
    "interface de démonstration et résolveur anycast intégré. La démonstration ne se contente pas d’afficher "
    "un statut : elle montre l’attaque, son rejet malgré l’annonce persistante, puis la continuité du service DNS. "
    "Le dossier est complet, autonome et directement présentable."
)

doc.save(OUT)
print(f"Rapport généré : {OUT}")
