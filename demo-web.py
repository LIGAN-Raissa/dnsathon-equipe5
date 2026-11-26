#!/usr/bin/env python3
"""Interface web LOCALE de démonstration pour l'activité 5 (équipe 5).

Elle ne fait qu'appeler configurer_gns3.py avec des actions autorisées :
aucune commande arbitraire n'est acceptée. Écoute uniquement sur 127.0.0.1:8080.

Lancement : python3 demo-web.py   puis ouvrir http://127.0.0.1:8080/
"""
import json
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

BASE = Path(__file__).resolve().parent
SCRIPT = BASE / "configurer_gns3.py"

# Liste blanche : clé bouton -> arguments du script (jamais de shell, jamais de saisie libre).
ACTIONS = {
    "check": ["--check"],
    "apply": [],
    "attack": ["--attack"],
    "repair": ["--repair"],
    "clean": ["--clean"],
    "vrp": ["--vrp"],
    "anycast": ["--anycast"],
}
LABELS = {
    "check": "Vérifier l'état",
    "apply": "Appliquer la config",
    "attack": "Lancer l'attaque",
    "repair": "Réappliquer le filtre",
    "clean": "Nettoyer la démo",
    "vrp": "Afficher les VRP Routinator",
    "anycast": "Tester l'anycast (bascule)",
}

HTML = r"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>DNSathon · Équipe 5 · Pilotage RPKI</title>
<style>
  :root{--bg:#0a0f1e;--panel:#111a2e;--panel2:#16223b;--line:#263556;--text:#e8eefc;
        --muted:#93a4c4;--green:#34d399;--red:#fb7185;--blue:#60a5fa;--amber:#fbbf24}
  *{box-sizing:border-box}
  body{margin:0;min-height:100vh;padding:26px 18px 40px;color:var(--text);
       font-family:Inter,ui-sans-serif,system-ui,"Segoe UI",sans-serif;
       background:radial-gradient(1000px 560px at 10% -10%,#1b2b52,transparent 55%),
                  radial-gradient(800px 460px at 100% 0%,#12213e,transparent 50%),var(--bg)}
  .wrap{max-width:1180px;margin:0 auto}
  header{display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap;margin-bottom:18px}
  h1{margin:0;font-size:clamp(22px,3vw,32px);letter-spacing:-.02em}
  h1 span{color:var(--blue)}
  .sub{color:var(--muted);font-size:14px;margin-top:6px}
  .pill{border:1px solid var(--line);background:var(--panel);color:var(--muted);
        padding:8px 14px;border-radius:999px;font-size:13px}
  .pill b{color:var(--green)}
  .cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin-bottom:18px}
  .card{background:linear-gradient(180deg,var(--panel2),var(--panel));border:1px solid var(--line);
        border-radius:15px;padding:14px 16px}
  .card small{color:var(--muted);text-transform:uppercase;letter-spacing:.08em;font-size:11px}
  .card div{margin-top:7px;font-weight:650}
  .controls{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:10px;margin-bottom:16px}
  button{font:inherit;cursor:pointer;border-radius:11px;padding:13px 15px;border:1px solid var(--line);
         background:var(--panel2);color:var(--text);text-align:left;transition:.15s transform,.15s border-color}
  button:hover:not(:disabled){transform:translateY(-2px);border-color:var(--blue)}
  button:disabled{opacity:.5;cursor:wait}
  button.primary{border-color:#2f6fb8;background:linear-gradient(135deg,#1d4e89,#16345f)}
  button.danger{border-color:#7f3446;color:#ffc9d2}
  button.good{border-color:#2f7d5b;color:#c8ffe3}
  button.ghost{text-align:center;max-width:110px}
  .console{background:#070c18;border:1px solid var(--line);border-radius:14px;overflow:hidden}
  .bar{display:flex;justify-content:space-between;align-items:center;padding:10px 14px;
       border-bottom:1px solid var(--line);color:var(--muted);font-size:12px}
  .dots i{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:5px}
  .dots i:nth-child(1){background:#fb7185}.dots i:nth-child(2){background:#fbbf24}.dots i:nth-child(3){background:#34d399}
  pre{margin:0;padding:16px;max-height:52vh;min-height:260px;overflow:auto;color:#cfe0ff;
      font:12.5px/1.55 ui-monospace,SFMono-Regular,Menlo,monospace;white-space:pre-wrap;word-break:break-word}
  .ok{color:var(--green)}.bad{color:var(--red)}.warn{color:var(--amber)}.cmd{color:var(--blue)}
  .foot{color:var(--muted);font-size:12px;text-align:center;margin-top:16px}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div><h1>DNSathon <span>· Équipe 5</span></h1>
      <div class="sub">Démo RPKI — configurations équipe 4, ROA local et contrôle du filtrage</div></div>
    <div class="pill">Interface <b>locale</b> · 127.0.0.1:8080</div>
  </header>

  <div class="cards">
    <div class="card"><small>Topologie</small><div>3 AS · IXP 172.16.100.0/24</div></div>
    <div class="card"><small>Validateur</small><div>Routinator · 172.16.100.254:3323</div></div>
    <div class="card"><small>ROA local</small><div>4 VRP · /24 max /24 + /32 anycast</div></div>
    <div class="card"><small>Attaque simulée</small><div>10.3.0.0/25 → invalide</div></div>
  </div>

  <div class="controls">
    <button class="primary" onclick="run('check')">🔍 Vérifier l'état</button>
    <button onclick="run('apply')">⚙️ Appliquer la config</button>
    <button class="danger" onclick="run('attack')">🚀 Lancer l'attaque</button>
    <button class="good" onclick="run('repair')">🛡️ Réappliquer le filtre</button>
    <button onclick="run('clean')">🧽 Nettoyer la démo</button>
    <button class="good" onclick="run('vrp')">📜 Afficher les VRP Routinator</button>
    <button onclick="run('anycast')">🌐 Tester l'anycast (bascule)</button>
    <button class="ghost" onclick="clearConsole()">🧹 Effacer</button>
  </div>

  <div class="console">
    <div class="bar"><span class="dots"><i></i><i></i><i></i></span>
      <span>console de démonstration</span><span id="state">prête</span></div>
    <pre id="out">Cliquez sur « Vérifier l'état » pour afficher les sessions BGP et le cache RPKI.</pre>
  </div>
  <div class="foot">Toutes les actions passent par configurer_gns3.py · aucune commande arbitraire n'est exécutée.</div>
</div>

<script>
const out = document.getElementById('out');
const state = document.getElementById('state');
const buttons = [...document.querySelectorAll('.controls button')];

function line(text, cls='') {
  const span = document.createElement('span');
  span.className = cls;
  span.textContent = text + '\n';
  out.appendChild(span);
  out.scrollTop = out.scrollHeight;
}
function color(text) {
  if (/ERREUR|NON ESTABLISHED|NON CONNECTÉ|À VÉRIFIER|not in table|invalid/i.test(text)) return 'bad';
  if (/ESTABLISHED|CONNECTÉ|connected|valid|OK|Configur|appliqu/i.test(text)) return 'ok';
  if (/write memory|Building configuration|attention/i.test(text)) return 'warn';
  return '';
}
function clearConsole() { out.textContent = ''; }

// Mode capture : ?action=check&auto=1 exécute l'action au chargement et
// agrandit la console pour que toute la sortie soit visible sur la capture.
const params = new URLSearchParams(location.search);
if (params.get('auto')) {
  out.style.maxHeight = 'none';
  out.style.minHeight = '0';
  window.addEventListener('load', () => run(params.get('action')));
}

async function run(action) {
  buttons.forEach(b => b.disabled = true);
  state.textContent = 'exécution…';
  line('$ python3 configurer_gns3.py ' + (action === 'apply' ? '' : '--' + action), 'cmd');
  try {
    const res = await fetch('/run', {method:'POST', headers:{'Content-Type':'application/json'},
                                     body: JSON.stringify({action})});
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'erreur serveur');
    data.output.split('\n').forEach(l => line(l, color(l)));
    state.textContent = 'terminé';
  } catch (e) {
    line('ERREUR : ' + e.message, 'bad');
    state.textContent = 'erreur';
  } finally {
    buttons.forEach(b => b.disabled = false);
  }
}
</script>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, body, content_type="text/html; charset=utf-8", status=200):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if urlsplit(self.path).path in ("/", "/index.html"):
            self._send(HTML)
        else:
            self._send("introuvable", status=404)

    def do_POST(self):
        if urlsplit(self.path).path != "/run":
            self._send("introuvable", status=404)
            return
        try:
            size = int(self.headers.get("Content-Length", 0))
            action = json.loads(self.rfile.read(size) or b"{}").get("action")
        except Exception:
            self._send('{"error":"requête invalide"}', "application/json", 400)
            return
        if action not in ACTIONS:
            self._send('{"error":"action non autorisée"}', "application/json", 400)
            return
        cmd = [sys.executable, str(SCRIPT)] + ACTIONS[action]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180, cwd=str(BASE))
            output = (proc.stdout + proc.stderr).strip() or "(aucune sortie)"
            payload = json.dumps({"output": output, "returncode": proc.returncode}, ensure_ascii=False)
            self._send(payload, "application/json")
        except subprocess.TimeoutExpired:
            self._send('{"error":"timeout : vérifiez que les nœuds GNS3 sont démarrés"}',
                       "application/json", 504)

    def log_message(self, fmt, *args):
        print("[WEB] " + (fmt % args), flush=True)


if __name__ == "__main__":
    print("[WEB] Interface locale : http://127.0.0.1:8080/", flush=True)
    ThreadingHTTPServer(("127.0.0.1", 8080), Handler).serve_forever()
