"""
CLI - Interface de Linha de Comando do Velox
Versão profissional com:
- Cores no terminal
- Auto-reload ao salvar arquivos
- Estrutura completa de projeto (static, templates, models, views)
- Listagem de rotas formatada
- Suporte a múltiplos comandos
- startapp: criação de apps modulares (como Django)
"""

import sys
import os
import argparse
import time
import threading
from pathlib import Path


# ─────────────────────────────────────────────
# Cores no terminal (ANSI)
# ─────────────────────────────────────────────

class Color:
    RESET   = '\033[0m'
    BOLD    = '\033[1m'
    GREEN   = '\033[92m'
    YELLOW  = '\033[93m'
    BLUE    = '\033[94m'
    CYAN    = '\033[96m'
    RED     = '\033[91m'
    MAGENTA = '\033[95m'
    WHITE   = '\033[97m'
    GRAY    = '\033[90m'

    @staticmethod
    def ok(msg):     return f"{Color.GREEN}✔ {msg}{Color.RESET}"
    @staticmethod
    def warn(msg):   return f"{Color.YELLOW}⚠ {msg}{Color.RESET}"
    @staticmethod
    def error(msg):  return f"{Color.RED}✘ {msg}{Color.RESET}"
    @staticmethod
    def info(msg):   return f"{Color.CYAN}→ {msg}{Color.RESET}"
    @staticmethod
    def bold(msg):   return f"{Color.BOLD}{msg}{Color.RESET}"
    @staticmethod
    def skip(msg):   return f"{Color.GRAY}  {msg}{Color.RESET}"


def banner():
    return f"""
\033[96m\033[1m
  ██╗   ██╗███████╗██╗      ██████╗ ██╗  ██╗
  ██║   ██║██╔════╝██║     ██╔═══██╗╚██╗██╔╝
  ██║   ██║█████╗  ██║     ██║   ██║ ╚███╔╝ 
  ╚██╗ ██╔╝██╔══╝  ██║     ██║   ██║ ██╔██╗ 
   ╚████╔╝ ███████╗███████╗╚██████╔╝██╔╝ ██╗
    ╚═══╝  ╚══════╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝
\033[0m\033[90m  Fast Python Web Framework — v1.0.0\033[0m
"""
# ─────────────────────────────────────────────
# Auto-reload (watch de arquivos)
# ─────────────────────────────────────────────

class FileWatcher:
    """
    Monitora arquivos do projeto e reinicia o servidor ao detectar mudancas.
    Monitora: .py  .html  .css  .js  .env  .json
    Ignora:   __pycache__  .git  node_modules  *.pyc
    """

    EXTENSOES = {'.py', '.html', '.css', '.js', '.env', '.json', '.yaml', '.yml'}
    IGNORAR   = {'__pycache__', '.git', 'node_modules', '.pytest_cache', 'migrations'}

    def __init__(self, directory='.', interval=0.8):
        self.directory = directory
        self.interval  = interval
        self._mtimes   = {}
        self._running  = False

    def _get_mtimes(self):
        mtimes = {}
        base   = Path(self.directory)
        for path in base.rglob('*'):
            partes = path.parts
            if any(ig in partes for ig in self.IGNORAR):
                continue
            if path.suffix not in self.EXTENSOES:
                continue
            try:
                mtimes[str(path)] = path.stat().st_mtime
            except OSError:
                pass
        return mtimes

    def _tipo(self, filepath):
        ext = Path(filepath).suffix
        tipos = {
            '.py':   'Python',
            '.html': 'Template',
            '.css':  'CSS',
            '.js':   'JavaScript',
            '.env':  'Env',
            '.json': 'JSON',
        }
        return tipos.get(ext, 'Arquivo')

    def start(self, callback):
        self._mtimes  = self._get_mtimes()
        self._running = True

        def watch():
            while self._running:
                time.sleep(self.interval)
                new_mtimes = self._get_mtimes()
                changed = [f for f, t in new_mtimes.items() if t != self._mtimes.get(f)]
                deleted = [f for f in self._mtimes if f not in new_mtimes]
                if changed or deleted:
                    print()
                    for f in changed:
                        rel  = os.path.relpath(f)
                        tipo = self._tipo(f)
                        is_new = f not in self._mtimes
                        acao   = "novo" if is_new else "alterado"
                        print(f"  {Color.YELLOW}↺ {tipo}: {rel} ({acao}){Color.RESET}")
                    for f in deleted:
                        rel = os.path.relpath(f)
                        print(f"  {Color.RED}✕ Removido: {rel}{Color.RESET}")
                    self._mtimes = new_mtimes
                    callback()
        t = threading.Thread(target=watch, daemon=True)
        t.start()
        return self

    def stop(self):
        self._running = False


# ─────────────────────────────────────────────
# Templates de arquivos gerados
# ─────────────────────────────────────────────

def _app_py(name: str, apps: list = None) -> str:
    apps_str = str(apps) if apps else "[]"
    return f'''"""
{name} — Aplicação principal do Velox Framework
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from velox import Velox
from velox.admin import site

app = Velox(__name__)
app.static('static')
app.template('templates')

# ============================================================
# APPS MODULARES (autodiscovery automático)
# ============================================================
# Adicione apps criados com 'velox startapp' aqui:
# Os apps serão carregados automaticamente se tiverem:
#   - models/     (importados para migrations)
#   - views/      (Blueprints registrados)
#   - admin.py    (interfaces registradas)
# ============================================================
app.load_apps({apps_str})

# Admin em /admin/ (login: admin / admin)
site.register_routes(app)

@app.get('/')
def home(request, response):
    return app.render('index.html', {{
        'titulo': '{name}',
    }})

@app.not_found
def not_found(request, response, msg):
    return app.render('404.html', {{'url': request.path}})

if __name__ == '__main__':
    app.run()
'''


def _index_html(name: str) -> str:
    return f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{{{{ titulo }}}} — Velox</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    :root{{
      --blue-dark:#0f172a;--blue-mid:#1e3a5f;--blue:#1d4ed8;--blue-light:#3b82f6;
      --blue-pale:#60a5fa;--blue-glow:rgba(59,130,246,.15);
      --gray-900:#0f172a;--gray-800:#1e293b;--gray-700:#334155;
      --gray-600:#475569;--gray-400:#94a3b8;--gray-200:#e2e8f0;--gray-100:#f1f5f9;
      --white:#ffffff;
    }}
    *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
    html{{height:100%;scroll-behavior:smooth}}
    body{{font-family:'Inter',-apple-system,sans-serif;background:var(--gray-900);
      color:var(--gray-200);min-height:100vh;display:flex;flex-direction:column;
      -webkit-font-smoothing:antialiased}}
    a{{color:var(--blue-light);text-decoration:none}}
    a:hover{{color:var(--blue-pale)}}
    /* Navbar */
    .nav{{display:flex;align-items:center;justify-content:space-between;
      padding:0 40px;height:60px;background:var(--gray-800);
      border-bottom:1px solid var(--gray-700);position:sticky;top:0;z-index:10;
      backdrop-filter:blur(8px)}}
    .nav-brand{{display:flex;align-items:center;gap:10px}}
    .nav-logo{{width:36px;height:36px;object-fit:contain}}
    .nav-name{{font-size:16px;font-weight:700;color:var(--white);letter-spacing:-.3px}}
    .nav-badge{{font-size:10px;padding:2px 8px;border-radius:99px;
      background:var(--blue-glow);color:var(--blue-pale);border:1px solid rgba(59,130,246,.3);
      font-weight:600;letter-spacing:.04em}}
    .nav-status{{display:flex;align-items:center;gap:8px;font-size:13px;color:var(--gray-400)}}
    .dot-green{{width:7px;height:7px;border-radius:50%;background:#22c55e;
      box-shadow:0 0 8px #22c55e;flex-shrink:0;animation:pulse 2s infinite}}
    @keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.5}}}}
    /* Hero */
    .hero{{flex:1;display:flex;flex-direction:column;align-items:center;
      justify-content:center;padding:80px 24px 60px;text-align:center;
      position:relative;overflow:hidden}}
    .hero-bg{{position:absolute;inset:0;pointer-events:none;
      background:radial-gradient(ellipse 70% 50% at 50% -10%,rgba(29,78,216,.25),transparent 70%),
                 radial-gradient(ellipse 40% 30% at 80% 80%,rgba(59,130,246,.08),transparent)}}
    .hero-grid{{position:absolute;inset:0;pointer-events:none;opacity:.04;
      background-image:linear-gradient(var(--gray-400) 1px,transparent 1px),
                       linear-gradient(90deg,var(--gray-400) 1px,transparent 1px);
      background-size:40px 40px}}
    .badge-running{{display:inline-flex;align-items:center;gap:8px;padding:6px 16px;
      border-radius:99px;background:rgba(34,197,94,.08);border:1px solid rgba(34,197,94,.2);
      font-size:12px;color:#4ade80;font-weight:500;margin-bottom:32px;position:relative;z-index:1}}
    .hero-logo{{width:100px;height:100px;object-fit:contain;margin-bottom:32px;position:relative;z-index:1;
      filter:drop-shadow(0 0 24px rgba(59,130,246,.4))}}
    .hero h1{{font-size:clamp(40px,6vw,72px);font-weight:800;letter-spacing:-2.5px;
      line-height:1.05;margin-bottom:20px;position:relative;z-index:1;color:var(--white)}}
    .hero h1 .accent{{background:linear-gradient(135deg,var(--blue-light),var(--blue-pale));
      -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}
    .hero-sub{{font-size:18px;color:var(--gray-400);max-width:500px;line-height:1.7;
      margin-bottom:40px;position:relative;z-index:1}}
    .hero-sub strong{{color:var(--gray-200)}}
    /* Chips */
    .chips{{display:flex;flex-wrap:wrap;gap:8px;justify-content:center;
      margin-bottom:44px;position:relative;z-index:1}}
    .chip{{display:flex;align-items:center;gap:6px;padding:5px 12px;border-radius:6px;
      background:var(--gray-800);border:1px solid var(--gray-700);font-size:12px;
      color:var(--gray-400);font-weight:500;transition:all .15s}}
    .chip:hover{{border-color:var(--blue-light);color:var(--blue-pale);
      background:rgba(59,130,246,.08)}}
    .chip-dot{{width:5px;height:5px;border-radius:50%;background:var(--blue-light);flex-shrink:0}}
    /* Code block */
    .code-wrap{{display:inline-flex;align-items:center;gap:12px;padding:12px 20px;
      border-radius:10px;background:var(--gray-800);border:1px solid var(--gray-700);
      font-family:'SF Mono','Fira Code',monospace;font-size:13px;color:var(--gray-400);
      position:relative;z-index:1}}
    .code-wrap .cmd{{color:var(--blue-pale);font-weight:600}}
    .code-wrap .arg{{color:#4ade80}}
    .code-copy{{padding:4px 10px;border-radius:5px;background:var(--gray-700);
      border:1px solid var(--gray-600);color:var(--gray-400);font-size:11px;
      cursor:pointer;font-family:inherit;transition:all .15s}}
    .code-copy:hover{{background:var(--blue);color:var(--white);border-color:var(--blue)}}
    /* Cards */
    .cards-section{{padding:0 24px 60px;max-width:900px;margin:0 auto;width:100%}}
    .cards-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px}}
    .card{{background:var(--gray-800);border:1px solid var(--gray-700);border-radius:12px;
      padding:20px;transition:all .2s;text-align:left;position:relative;overflow:hidden}}
    .card::before{{content:'';position:absolute;inset:0;background:linear-gradient(135deg,
      rgba(59,130,246,.05),transparent);opacity:0;transition:opacity .2s}}
    .card:hover{{border-color:var(--blue-light);transform:translateY(-2px);
      box-shadow:0 8px 24px rgba(29,78,216,.2)}}
    .card:hover::before{{opacity:1}}
    .card-icon{{font-size:22px;margin-bottom:10px}}
    .card-title{{font-size:13px;font-weight:600;color:var(--white);margin-bottom:5px}}
    .card-desc{{font-size:12px;color:var(--gray-400);line-height:1.5}}
    .card-desc code{{background:rgba(59,130,246,.1);color:var(--blue-pale);
      padding:1px 5px;border-radius:3px;font-size:11px}}
    /* Footer */
    .footer{{text-align:center;padding:20px;font-size:12px;color:var(--gray-600);
      border-top:1px solid var(--gray-800)}}
    .footer a{{color:var(--blue-light)}}
    .footer a:hover{{color:var(--blue-pale)}}
  </style>
</head>
<body>
<header class="nav">
  <div class="nav-brand">
    <img src="/static/img/velox-logo.png" alt="Velox" class="nav-logo">
    <span class="nav-name">Velox</span>
    <span class="nav-badge">v1.0.0</span>
  </div>
  <div class="nav-status">
    <span class="dot-green"></span>
    <span>Servidor rodando</span>
  </div>
</header>

<main class="hero">
  <div class="hero-bg"></div>
  <div class="hero-grid"></div>

  <div class="badge-running">
    <span class="dot-green"></span>
    Projeto <strong style="color:#fff;margin:0 3px">{{{{ titulo }}}}</strong> inicializado
  </div>

  <img src="/static/img/velox-logo.png" alt="Velox" class="hero-logo">

  <h1>Bem-vindo ao<br><span class="accent">Velox</span></h1>
  <p class="hero-sub">
    Seu projeto <strong>{{{{ titulo }}}}</strong> está rodando.<br>
    Edite <code style="background:rgba(59,130,246,.1);color:#60a5fa;padding:2px 7px;border-radius:4px;font-size:14px">app.py</code> para começar.
  </p>

  <div class="chips">
    <div class="chip"><span class="chip-dot"></span>WSGI + ASGI</div>
    <div class="chip"><span class="chip-dot"></span>Sync + Async</div>
    <div class="chip"><span class="chip-dot"></span>WebSocket</div>
    <div class="chip"><span class="chip-dot"></span>Admin embutido</div>
    <div class="chip"><span class="chip-dot"></span>ORM nativo</div>
    <div class="chip"><span class="chip-dot"></span>Zero dependências</div>
  </div>

  <div class="code-wrap">
    <span class="cmd">velox</span>
    <span style="color:#475569">·</span>
    <span>startapp <span class="arg">meu-app</span></span>
    <button class="code-copy"
      onclick="navigator.clipboard.writeText('velox startapp meu-app');this.textContent='✓ copiado';setTimeout(()=>this.textContent='copiar',1500)">
      copiar
    </button>
  </div>
</main>

<section class="cards-section">
  <div class="cards-grid">
    <div class="card">
      <div class="card-icon">⚡</div>
      <div class="card-title">Um arquivo só</div>
      <div class="card-desc">Crie um servidor completo em um único <code>app.py</code> — como o Flask, mas com mais poder.</div>
    </div>
    <div class="card">
      <div class="card-icon">🧩</div>
      <div class="card-title">Apps modulares</div>
      <div class="card-desc"><code>velox startapp blog</code><br>Estrutura modular pronta para crescer.</div>
    </div>
    <div class="card">
      <div class="card-icon">🛡️</div>
      <div class="card-title">Painel Admin</div>
      <div class="card-desc">Acesse <code>/admin/</code><br>Login: <code>admin / admin</code></div>
    </div>
    <div class="card">
      <div class="card-icon">🔄</div>
      <div class="card-title">Async nativo</div>
      <div class="card-desc">Use <code>async def</code> em qualquer handler. WebSocket incluído.</div>
    </div>
  </div>
</section>

<footer class="footer">
  Feito com <a href="https://github.com/seuusuario/velox">Velox Framework</a>
  &nbsp;·&nbsp;
  <a href="/admin/">Painel Admin</a>
</footer>

<script>
  // Anima os chips na entrada
  document.querySelectorAll('.chip').forEach((c,i)=>{{
    c.style.opacity='0';c.style.transform='translateY(8px)';
    setTimeout(()=>{{c.style.transition='all .3s ease';c.style.opacity='1';c.style.transform='none';}},100+i*60);
  }});
</script>
</body>
</html>
'''


def _404_html() -> str:
    return '''<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>404 — Página não encontrada</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    :root{
      --blue-dark:#0f172a;--blue-mid:#1e3a5f;--blue:#1d4ed8;--blue-light:#3b82f6;
      --blue-pale:#60a5fa;--gray-800:#1e293b;--gray-700:#334155;
      --gray-400:#94a3b8;--gray-200:#e2e8f0;
    }
    *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
    body{font-family:'Inter',-apple-system,sans-serif;background:var(--blue-dark);
      color:var(--gray-200);display:flex;align-items:center;justify-content:center;
      min-height:100vh;-webkit-font-smoothing:antialiased;overflow:hidden}
    /* Background */
    .bg{position:fixed;inset:0;pointer-events:none;
      background:radial-gradient(ellipse 60% 50% at 50% 50%,rgba(29,78,216,.15),transparent 70%)}
    .grid{position:fixed;inset:0;pointer-events:none;opacity:.03;
      background-image:linear-gradient(var(--gray-400) 1px,transparent 1px),
                       linear-gradient(90deg,var(--gray-400) 1px,transparent 1px);
      background-size:48px 48px}
    /* Card */
    .wrap{position:relative;z-index:1;text-align:center;padding:48px 40px;
      background:var(--gray-800);border:1px solid var(--gray-700);border-radius:20px;
      max-width:480px;width:90%;box-shadow:0 24px 64px rgba(0,0,0,.5),
      0 0 0 1px rgba(59,130,246,.1)}
    /* Logo */
    .logo{width:56px;height:56px;object-fit:contain;margin:0 auto 28px;
      filter:drop-shadow(0 0 16px rgba(59,130,246,.5))}
    /* 404 number */
    .code{font-size:96px;font-weight:800;letter-spacing:-4px;line-height:1;
      background:linear-gradient(135deg,var(--blue-light),var(--blue-pale));
      -webkit-background-clip:text;-webkit-text-fill-color:transparent;
      background-clip:text;margin-bottom:12px}
    .title{font-size:20px;font-weight:600;color:#fff;margin-bottom:8px}
    .desc{font-size:14px;color:var(--gray-400);margin-bottom:28px;line-height:1.6}
    .desc code{background:rgba(59,130,246,.1);color:var(--blue-pale);
      padding:2px 8px;border-radius:4px;font-size:13px;
      font-family:'SF Mono','Fira Code',monospace}
    /* Buttons */
    .actions{display:flex;gap:10px;justify-content:center;flex-wrap:wrap}
    .btn{display:inline-flex;align-items:center;gap:6px;padding:10px 22px;
      border-radius:8px;font-size:14px;font-weight:500;text-decoration:none;
      transition:all .15s;border:1px solid transparent}
    .btn-primary{background:var(--blue);color:#fff;border-color:var(--blue)}
    .btn-primary:hover{background:#1e40af;border-color:#1e40af;
      box-shadow:0 4px 12px rgba(29,78,216,.4)}
    .btn-ghost{background:transparent;color:var(--gray-400);border-color:var(--gray-700)}
    .btn-ghost:hover{background:var(--gray-700);color:#fff}
    /* Divider */
    .divider{width:40px;height:2px;background:linear-gradient(90deg,var(--blue),var(--blue-pale));
      border-radius:99px;margin:20px auto}
  </style>
</head>
<body>
  <div class="bg"></div>
  <div class="grid"></div>
  <div class="wrap">
    <img src="/static/img/velox-logo.png" alt="Velox" class="logo">
    <div class="code">404</div>
    <div class="divider"></div>
    <div class="title">Página não encontrada</div>
    <div class="desc">
      A URL <code>{{ url }}</code> não existe neste projeto.<br>
      Verifique o endereço ou volte ao início.
    </div>
    <div class="actions">
      <a href="/" class="btn btn-primary">← Voltar ao início</a>
      <a href="/admin/" class="btn btn-ghost">Admin</a>
    </div>
  </div>
</body>
</html>
'''


def _style_css() -> str:
    return ''':root {
  --blue-dark:    #0f172a;
  --blue-mid:     #1e3a5f;
  --blue:         #1d4ed8;
  --blue-light:   #3b82f6;
  --blue-pale:    #60a5fa;
  --blue-glow:    rgba(59,130,246,.15);
  --gray-900:     #0f172a;
  --gray-800:     #1e293b;
  --gray-700:     #334155;
  --gray-600:     #475569;
  --gray-400:     #94a3b8;
  --gray-200:     #e2e8f0;
  --white:        #ffffff;
  --radius:       8px;
  --radius-lg:    12px;
}
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Inter', sans-serif;
  background: var(--gray-900);
  color: var(--gray-200);
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}
a { color: var(--blue-light); text-decoration: none; }
a:hover { color: var(--blue-pale); text-decoration: underline; }
code {
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: .85em;
  background: rgba(59,130,246,.1);
  padding: 2px 6px;
  border-radius: 4px;
  color: var(--blue-pale);
}
.container { max-width: 1100px; margin: 0 auto; padding: 0 24px; }
/* Navbar */
.navbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 32px; height: 56px;
  background: var(--gray-800);
  border-bottom: 1px solid var(--gray-700);
  position: sticky; top: 0; z-index: 10;
}
.navbar .brand { font-size: 15px; font-weight: 700; color: var(--white); }
.navbar a { color: var(--gray-400); font-size: 13px; transition: color .15s; }
.navbar a:hover { color: var(--white); text-decoration: none; }
/* Card */
.card {
  background: var(--gray-800);
  border: 1px solid var(--gray-700);
  border-radius: var(--radius-lg);
  padding: 28px;
  transition: border-color .15s;
}
.card:hover { border-color: var(--blue-light); }
.card h1 { font-size: 1.6rem; margin-bottom: 10px; color: var(--white); }
.card p  { color: var(--gray-400); margin-bottom: 20px; font-size: 14px; }
/* Button */
.btn {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 9px 20px;
  background: var(--blue);
  color: #fff;
  border: 1px solid var(--blue);
  border-radius: var(--radius);
  font-size: 14px; font-weight: 500;
  cursor: pointer; transition: all .15s;
  text-decoration: none;
}
.btn:hover { background: #1e40af; border-color: #1e40af;
  box-shadow: 0 4px 12px rgba(29,78,216,.35); text-decoration: none; }
.btn-secondary { background: var(--gray-700); color: var(--gray-200); border-color: var(--gray-700); }
.btn-secondary:hover { background: var(--gray-600); border-color: var(--gray-600); box-shadow: none; }
.btn-danger { background: #dc2626; border-color: #dc2626; }
.btn-danger:hover { background: #b91c1c; border-color: #b91c1c; }
/* Table */
table { width: 100%; border-collapse: collapse; font-size: 13px; }
thead th {
  padding: 10px 16px; text-align: left;
  font-size: 11px; font-weight: 600;
  color: var(--gray-400); text-transform: uppercase; letter-spacing: .06em;
  background: var(--gray-900);
  border-bottom: 1px solid var(--gray-700);
}
tbody td {
  padding: 10px 16px;
  border-bottom: 1px solid var(--gray-700);
  color: var(--gray-200);
}
tbody tr:last-child td { border-bottom: none; }
tbody tr:hover td { background: rgba(59,130,246,.05); }
/* Form */
.form-group { margin-bottom: 16px; }
.form-group label {
  display: block; font-size: 12px; font-weight: 500;
  color: var(--gray-400); margin-bottom: 6px;
}
.form-group input,
.form-group select,
.form-group textarea {
  width: 100%; padding: 9px 12px;
  background: var(--gray-900); border: 1px solid var(--gray-700);
  border-radius: var(--radius);
  color: var(--gray-200); font-size: 14px;
  transition: border-color .15s;
}
.form-group input:focus,
.form-group textarea:focus {
  outline: none;
  border-color: var(--blue-light);
  box-shadow: 0 0 0 3px var(--blue-glow);
}
.error-msg { color: #f87171; font-size: 12px; margin-top: 4px; }
/* Badge */
.badge {
  display: inline-flex; align-items: center;
  padding: 2px 9px; border-radius: 99px;
  font-size: 11px; font-weight: 600;
}
.badge-blue   { background: rgba(59,130,246,.12);  color: var(--blue-pale); }
.badge-green  { background: rgba(34,197,94,.12);   color: #4ade80; }
.badge-red    { background: rgba(239,68,68,.12);   color: #f87171; }
.badge-gray   { background: var(--gray-700); color: var(--gray-400); }
/* Alert */
.alert {
  padding: 12px 16px; border-radius: var(--radius);
  font-size: 13px; margin-bottom: 16px; border: 1px solid;
}
.alert-success { background: rgba(34,197,94,.08);  color: #4ade80; border-color: rgba(34,197,94,.2); }
.alert-error   { background: rgba(239,68,68,.08);  color: #f87171; border-color: rgba(239,68,68,.2); }
.alert-info    { background: rgba(59,130,246,.08); color: var(--blue-pale); border-color: rgba(59,130,246,.2); }
/* Footer */
.footer {
  text-align: center; padding: 20px;
  font-size: 12px; color: var(--gray-600);
  border-top: 1px solid var(--gray-700);
}
'''


def _requirements_txt() -> str:
    return '''# Velox Framework
# pip install -r requirements.txt

# Banco de dados PostgreSQL (opcional)
# psycopg2-binary>=2.9

# Cache Redis (opcional)
# redis>=4.0

# Testes
pytest>=7.0
'''


def _env_file() -> str:
    import secrets
    key = secrets.token_hex(24)
    return f'''# Configuracoes do projeto
APP_HOST=localhost
APP_PORT=8000
APP_DEBUG=true
VELOX_SECRET_KEY={key}
VELOX_ADMIN_USER=admin
VELOX_ADMIN_PASSWORD=admin

# Banco de dados — caminho relativo à pasta do projeto
DATABASE_URI=db/app.db
# DATABASE_URI=postgresql://user:pass@localhost:5432/mydb

# Cache (memory, file, redis)
CACHE_BACKEND=memory
# CACHE_REDIS_URL=redis://localhost:6379/0

# Templates
TEMPLATE_CACHE=true
'''


def _gitignore() -> str:
    return '''__pycache__/
*.py[cod]
*.sqlite3
db/*.db
.env
venv/
.venv/
uploads/
*.log
.DS_Store
node_modules/
*.pyc
'''


# ─────────────────────────────────────────────
# Templates para STARTAPP
# ─────────────────────────────────────────────

def _app_init(name: str) -> str:
    return f'"""\n{name} — App Modular do Velox Framework\n"""\nfrom .views import router\n'



def _app_models(name: str) -> str:
    return f'''"""
models.py — Models do app {name}

Defina seus models aqui usando o ORM do Velox.

Exemplo:
    from velox.database import Model
    
    class Post(Model):
        table = 'posts'
        schema = {{
            'title': str,
            'content': str,
            'published': bool,
        }}
"""

# from velox.database import Model

# class Exemplo(Model):
#     table = '{name}_exemplos'
#     schema = {{
#         'nome': str,
#         'descricao': str,
#     }}
'''

def _app_views(name: str) -> str:
    return f'''"""
views.py — Views/Handlers do app {name}

Defina seus handlers aqui.
Use o Router para criar rotas modulares.
"""
from velox import Router

router = Router(prefix='/{name}')


@router.get('/')
def list_{name}(request, response):
    """Lista todos os {name}"""
    response.json({{'status': 'ok', 'data': []}})


@router.get('/<id:int>')
def get_{name}(request, response, id):
    """Retorna um {name} específico"""
    response.json({{'status': 'ok', 'id': id}})


@router.post('/')
def create_{name}(request, response):
    """Cria um novo {name}"""
    data = request.json or {{}}
    response.json({{'status': 'created', 'data': data}}, status=201)


@router.put('/<id:int>')
def update_{name}(request, response, id):
    """Atualiza um {name}"""
    data = request.json or {{}}
    response.json({{'status': 'updated', 'id': id}})


@router.delete('/<id:int>')
def delete_{name}(request, response, id):
    """Remove um {name}"""
    response.json({{'status': 'deleted'}})
'''

def _app_admin(name: str) -> str:
    return f'''"""
admin.py — Interface Admin do app {name}

Registre seus models no painel admin aqui.
"""
# Exemplo:
# from velox.admin import site
# from .models import Exemplo
#
# @site.register(Exemplo)
# class ExemploAdmin:
#     list_display = ['id', 'nome']
#     search_fields = ['nome']
'''



def _app_tests(name: str) -> str:
    return f'''"""
tests.py — Testes do app {name}
"""
import pytest


def test_{name}_list():
    """Testa listagem de {name}"""
    assert True


def test_{name}_create():
    """Testa criação de {name}"""
    assert True
'''

def _app_template_list(name: str) -> str:
    return f'''<!-- templates/{name}/list.html -->
<!DOCTYPE html>
<html>
<head>
    <title>Lista de {name.title()}</title>
    <link rel="stylesheet" href="/static/css/style.css">
</head>
<body>
    <div class="container">
        <h1>{{{name.title()}}}</h1>
        <a href="/{name}/new/" class="btn">Novo</a>
    </div>
</body>
</html>
'''

def _app_template_form(name: str) -> str:
    return f'''<!-- templates/{name}/form.html -->
<!DOCTYPE html>
<html>
<head>
    <title>Formulário de {name.title()}</title>
    <link rel="stylesheet" href="/static/css/style.css">
</head>
<body>
    <div class="container">
        <h1>Formulário</h1>
        <form method="post">
            <!-- Seus campos aqui -->
            <button type="submit" class="btn">Salvar</button>
        </form>
    </div>
</body>
</html>
'''


def _model_template(name: str) -> str:
    cap   = name.capitalize()
    table = name.lower() + 's'
    return f"""\"\"\"
Model: {cap}
Gerado pelo Velox CLI — edite os campos conforme sua necessidade.
\"\"\"
from velox import Model


class {cap}(Model):
    table = '{table}'
    schema = {{
        'nome':      str,
        'descricao': str,
        'ativo':     bool,
    }}

    @classmethod
    def ativos(cls):
        return cls.query('SELECT * FROM {table} WHERE ativo = 1')

    def __repr__(self):
        return f'<{cap} id={{getattr(self, "id", "?")}}>'
"""


def _view_template(name: str) -> str:
    return f'''\"\"\"
Views: {name}
\"\"\"


def index(request, response):
    response.json({{'view': '{name}', 'action': 'index'}})


def show(request, response, id):
    response.json({{'view': '{name}', 'action': 'show', 'id': id}})
'''


def _middleware_template(name: str) -> str:
    cap = name.capitalize()
    return f'''\"\"\"
Middleware: {cap}
\"\"\"
from functools import wraps


def {name}_middleware(handler):
    @wraps(handler)
    def wrapper(request, response, **kwargs):
        print(f\"[{cap}]\", request.method, request.path)
        return handler(request, response, **kwargs)
    return wrapper
'''


# ─────────────────────────────────────────────
# CLI principal
# ─────────────────────────────────────────────

class CLI:
    """Interface de linha de comando profissional do Velox"""

    VERSION = '1.0.0'

    def __init__(self):
        self.parser = argparse.ArgumentParser(
            prog='velox',
            description='Velox Framework — CLI',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog='''Exemplos:
  velox init meusite          Cria novo projeto
  velox startapp blog         Cria app modular (como Django)
  velox startapp api --api    Cria app API-only (sem templates)
  velox run                   Roda app.py na porta 8000
  velox run --port 5000      Roda em outra porta
  velox create model User     Cria models/user.py
  velox routes                Lista todas as rotas
  velox version               Exibe a versão
'''
        )
        self._setup_commands()

    def _setup_commands(self):
        sub = self.parser.add_subparsers(dest='command')

        # init
        p_init = sub.add_parser('init', help='Cria um novo projeto Velox')
        p_init.add_argument('name', help='Nome do projeto')

        # startapp (NOVO!)
        p_startapp = sub.add_parser('startapp', help='Cria um novo app modular (como Django)')
        p_startapp.add_argument('name', help='Nome do app')
        p_startapp.add_argument('--api', action='store_true', help='Cria app API-only (sem templates)')
        p_startapp.add_argument('--api-only', action='store_true', dest='api_only', help='Alias para --api')
        p_startapp.add_argument('--force', action='store_true', help='Sobrescreve se já existir')

        # run
        p_run = sub.add_parser('run', help='Inicia o servidor')
        p_run.add_argument('app', nargs='?', default='app.py', help='Arquivo principal')
        p_run.add_argument('--host', default='localhost', help='Host')
        p_run.add_argument('--port', type=int, default=8000, help='Porta')
        p_run.add_argument('--reload', action='store_true', help='Auto-reload')

        # create
        p_create = sub.add_parser('create', help='Cria arquivos no projeto')
        p_create.add_argument('type', choices=['model', 'view', 'middleware', 'template'], help='Tipo')
        p_create.add_argument('name', help='Nome do arquivo')

        # routes
        p_routes = sub.add_parser('routes', help='Lista rotas registradas')
        p_routes.add_argument('app', nargs='?', default='app.py')

        # version
        sub.add_parser('version', help='Exibe a versão do Velox')

    def run(self, args=None):
        parsed = self.parser.parse_args(args)
        commands = {
            'init':     self._cmd_init,
            'startapp': self._cmd_startapp,
            'run':      self._cmd_run,
            'create':   self._cmd_create,
            'routes':   self._cmd_routes,
            'version':  self._cmd_version,
        }
        fn = commands.get(parsed.command)
        if fn:
            fn(parsed)
        else:
            print(banner())
            self.parser.print_help()

    def _cmd_init(self, parsed):
        name = parsed.name
        project = Path(name)
        if project.exists():
            print(Color.warn(f"Pasta '{name}' já existe."))
            return
        print(banner())
        print(Color.bold(f"Criando projeto '{name}'...\n"))
        structure = {
            f'{name}/app.py':               _app_py(name),
            f'{name}/.env':                 _env_file(),
            f'{name}/.gitignore':           _gitignore(),
            f'{name}/requirements.txt':     _requirements_txt(),
            f'{name}/templates/index.html': _index_html(name),
            f'{name}/templates/404.html':   _404_html(),
            f'{name}/static/css/style.css': _style_css(),
            f'{name}/__init__.py':          f'# {name}\n',
            f'{name}/db/.gitkeep':          '',
        }
        for filepath, content in structure.items():
            p = Path(filepath)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding='utf-8')
            print(Color.ok(f"  {filepath}"))

        # Copiar logo PNG do pacote para static/img/
        try:
            import importlib.resources as _ir
            import shutil as _sh
            try:
                # Python 3.9+
                with _ir.as_file(_ir.files('velox').joinpath('assets/velox-logo.png')) as src:
                    dest = Path(f'{name}/static/img/velox-logo.png')
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    _sh.copy2(src, dest)
                    print(Color.ok(f"  {name}/static/img/velox-logo.png"))
            except Exception:
                # Fallback: busca relativa ao cli.py
                src = Path(__file__).parent / 'assets' / 'velox-logo.png'
                if src.exists():
                    dest = Path(f'{name}/static/img/velox-logo.png')
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    _sh.copy2(src, dest)
                    print(Color.ok(f"  {name}/static/img/velox-logo.png"))
        except Exception:
            pass
        print()
        print(Color.bold("✅ Projeto criado com sucesso!\n"))
        print(f"  {Color.info(f'cd {name}')}")
        print(f"  {Color.info('velox run')}\n")

    def _cmd_startapp(self, parsed):
        """Cria um app modular (como Django startapp) — apenas arquivos necessários"""
        name     = parsed.name.lower()
        api_only = parsed.api or parsed.api_only
        force    = parsed.force

        if not name.isidentifier():
            print(Color.error(f"Nome inválido: '{name}'. Use apenas letras, números e underscores."))
            return

        if Path(name).exists() and not force:
            print(Color.warn(f"App '{name}' já existe. Use --force para sobrescrever."))
            return

        print(banner())
        print(Color.bold(f"Criando app '{name}'...\n"))

        files = {
            f'{name}/__init__.py': f'"""\n{name} — App Modular do Velox Framework\n"""\nfrom .views import router\n',
            f'{name}/models.py':   _app_models(name),
            f'{name}/views.py':    _app_views(name),
            f'{name}/admin.py':    _app_admin(name),
            f'{name}/tests.py':    _app_tests(name),
        }

        if not api_only:
            files[f'{name}/templates/{name}/list.html'] = _app_template_list(name)
            files[f'{name}/templates/{name}/form.html'] = _app_template_form(name)

        for filepath, content in files.items():
            p = Path(filepath)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding='utf-8')
            print(Color.ok(f"  {filepath}"))

        print()
        print(Color.bold(f"App '{name}' criado!\n"))
        print(f"  Adicione em app.py:")
        print(f"    {Color.CYAN}from {name}.views import router")
        print(f"    app.include(router){Color.RESET}\n")

    def _cmd_run(self, parsed):
        app_file = parsed.app
        if not os.path.exists(app_file):
            print(Color.error(f"Arquivo '{app_file}' não encontrado!"))
            sys.exit(1)
        sys.path.insert(0, os.getcwd())
        import importlib.util
        spec = importlib.util.spec_from_file_location('_velox_app', app_file)
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            print(Color.error(f"Erro ao carregar '{app_file}': {e}"))
            sys.exit(1)
        app = getattr(module, 'app', None)
        if app is None:
            print(Color.error("Variável 'app' não encontrada!"))
            sys.exit(1)
        print(banner())
        host, port = parsed.host, parsed.port
        reload = parsed.reload
        print(f"  🌐 {Color.bold(f'http://{host}:{port}')}")
        if reload:
            print(f"  {Color.YELLOW}↺ Auto-reload ativado{Color.RESET}")
        print(f"  {Color.GRAY}Ctrl+C para parar{Color.RESET}\n")
        try:
            app.run(host=host, port=port, debug=reload)
        except KeyboardInterrupt:
            print(f"\n{Color.YELLOW}Servidor parado.{Color.RESET}")

    def _cmd_create(self, parsed):
        kind = parsed.type
        name = parsed.name.lower()
        targets = {
            'model':      (f'models/{name}.py',       _model_template(name)),
            'view':       (f'views/{name}.py',         _view_template(name)),
            'middleware': (f'middlewares/{name}.py',   _middleware_template(name)),
            'template':   (f'templates/{name}.html',   f'<html><body><h1>{name}</h1></body></html>'),
        }
        filepath, content = targets[kind]
        p = Path(filepath)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding='utf-8')
        print(Color.ok(f"Criado: {filepath}"))

    def _cmd_routes(self, parsed):
        app_file = getattr(parsed, 'app', 'app.py')
        if not os.path.exists(app_file):
            print(Color.error(f"Arquivo '{app_file}' não encontrado!"))
            sys.exit(1)
        sys.path.insert(0, os.getcwd())
        import importlib.util
        spec = importlib.util.spec_from_file_location('_velox_app', app_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        app = getattr(module, 'app', None)
        routes = app.router.list_routes()
        print(f"\n{Color.bold('  Rotas registradas:')}\n")
        for r in routes:
            print(f"  {r['method']:<8}  {r['path']}")
        print(f"\n  {Color.GRAY}Total: {len(routes)} rota(s){Color.RESET}\n")

    def _cmd_version(self, parsed):
        print(f"\n{Color.CYAN}Velox Framework{Color.RESET} v{self.VERSION}")
        print(f"{Color.GRAY}Python {sys.version.split()[0]}{Color.RESET}\n")


def main():
    cli = CLI()
    cli.run()


if __name__ == '__main__':
    main()
