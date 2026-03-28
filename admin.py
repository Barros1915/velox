"""
Admin - Velox Framework
========================
Painel admin completo inspirado no Django Admin.

Funcionalidades:
  - Dashboard com estatísticas por modelo
  - CRUD completo (listar, criar, editar, excluir)
  - Busca por campos configuráveis (search_fields)
  - Filtros laterais por campo (list_filter)
  - Ordenação por coluna (ordering)
  - Paginação configurável (per_page)
  - Ações em lote (actions) — ex: "Excluir selecionados"
  - Campos readonly (readonly_fields)
  - Campos excluídos (exclude)
  - Campos agrupados em fieldsets
  - Campos inline (inline_fields)
  - Exibição customizada por campo (display_*)
  - Permissões por operação (has_add/change/delete_permission)
  - Log de atividade (últimas 200 ações)
  - Exportação CSV
  - Dark theme profissional

Configuração via .env:
  VELOX_ADMIN_USER=admin
  VELOX_ADMIN_PASSWORD=admin
  VELOX_ADMIN_PREFIX=/admin
  VELOX_SECRET_KEY=...
"""

import os
import hashlib
import secrets
import csv
import io
from datetime import datetime
from urllib.parse import parse_qs, urlencode
from typing import Any, Callable, Dict, List, Optional, Tuple

# ─────────────────────────────────────────
# Configuração
# ─────────────────────────────────────────

ADMIN_USER     = os.environ.get("VELOX_ADMIN_USER")     or os.environ.get("PYCORE_ADMIN_USER",     "admin")
ADMIN_EMAIL    = os.environ.get("VELOX_ADMIN_EMAIL")    or os.environ.get("PYCORE_ADMIN_EMAIL",    "admin@velox.dev")
ADMIN_PASSWORD = os.environ.get("VELOX_ADMIN_PASSWORD") or os.environ.get("PYCORE_ADMIN_PASSWORD", "admin")
ADMIN_PREFIX   = os.environ.get("VELOX_ADMIN_PREFIX")   or os.environ.get("PYCORE_ADMIN_PREFIX",   "/admin")
SESSION_KEY    = os.environ.get("VELOX_SECRET_KEY")     or os.environ.get("PYCORE_SECRET_KEY",     secrets.token_hex(32))

# ─────────────────────────────────────────
# Auth helpers
# ─────────────────────────────────────────

def _sign(v: str) -> str:
    import hmac as _h
    return v + "." + _h.new(SESSION_KEY.encode(), v.encode(), hashlib.sha256).hexdigest()

def _unsign(signed: str) -> Optional[str]:
    import hmac as _h
    try:
        v, s = signed.rsplit(".", 1)
        e = _h.new(SESSION_KEY.encode(), v.encode(), hashlib.sha256).hexdigest()
        return v if _h.compare_digest(s, e) else None
    except Exception:
        return None

def _authed(request) -> bool:
    try:
        raw = (getattr(request, 'cookies', {}) or {}).get('_pca') or ''
        if not raw:
            cookie_hdr = (
                request.headers.get("Cookie") or
                request.headers.get("cookie") or ""
            )
            for part in cookie_hdr.split(";"):
                part = part.strip()
                if part.startswith("_pca="):
                    raw = part[5:]
                    break
        return bool(raw) and _unsign(raw) == "ok"
    except Exception:
        return False

def _set_session(response):
    val = "_pca=" + _sign("ok") + "; Path=/; HttpOnly; SameSite=Lax; Max-Age=86400"
    if hasattr(response, "set_header"):
        response.set_header("Set-Cookie", val)
    else:
        response.headers["Set-Cookie"] = val

def _clear_session(response):
    val = "_pca=; Path=/; HttpOnly; Expires=Thu, 01 Jan 1970 00:00:00 GMT"
    if hasattr(response, "set_header"):
        response.set_header("Set-Cookie", val)
    else:
        response.headers["Set-Cookie"] = val

def _check_pw(plain: str, stored: str) -> bool:
    if "$" in stored:
        try:
            salt, hx = stored.split("$", 1)
            new_hash = hashlib.pbkdf2_hmac("sha256", plain.encode(), salt.encode(), 260000)
            return secrets.compare_digest(new_hash.hex(), hx)
        except Exception:
            return False
    return secrets.compare_digest(plain, stored)

def _qs(request) -> dict:
    """Extrai query string do request de forma compatível WSGI/ASGI."""
    raw = ""
    try:
        path = getattr(request, 'full_path', None) or getattr(request, 'path', '') or ''
        if '?' in path:
            raw = path.split('?', 1)[1]
        if not raw:
            raw = getattr(request, 'query_string', '') or ''
    except Exception:
        pass
    return {k: v[0] for k, v in parse_qs(raw).items()}


# ─────────────────────────────────────────
# CSS / JS - Carregados de arquivos externos
# ─────────────────────────────────────────

def _load_assets():
    """Carrega CSS e JS de arquivos externos (com fallback inline)"""
    import pathlib
    
    # Caminho para os arquivos de assets
    base_path = pathlib.Path(__file__).parent / 'assets'
    
    css_content = ""
    js_content = ""
    
    # Tentar carregar CSS externo
    css_file = base_path / 'admin.css'
    if css_file.exists():
        try:
            css_content = css_file.read_text(encoding='utf-8')
        except Exception:
            pass
    
    # Tentar carregar JS externo
    js_file = base_path / 'admin.js'
    if js_file.exists():
        try:
            js_content = js_file.read_text(encoding='utf-8')
        except Exception:
            pass
    
    return css_content, js_content


# Carregar assets na inicialização
_CSS_CONTENT, _JS_CONTENT = _load_assets()


# Funções para obter CSS/JS (usa arquivos externos quando disponíveis)
def get_admin_css():
    """Retorna o CSS do admin (de arquivo externo ou inline)"""
    if _CSS_CONTENT:
        return _CSS_CONTENT
    # Fallback: CSS inline mínimo (será carregado se arquivo não existir)
    return """/* Admin CSS - Velox Framework */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
:root{--bg:#0f172a;--bg2:#1e293b;--bg3:#334155;--bgh:#2d3f55;--bd:#334155;--bdf:#475569;--t1:#e2e8f0;--t2:#94a3b8;--t3:#475569;--ac:#3b82f6;--ach:#2563eb;--acm:rgba(59,130,246,.15);--gn:#22c55e;--gnm:rgba(34,197,94,.12);--rd:#f87171;--rdm:rgba(248,113,113,.12);--yw:#fbbf24;--ywm:rgba(251,191,36,.12);--bl:#60a5fa;--blm:rgba(96,165,250,.12);--sw:230px;--th:52px;--r:6px;--rl:10px;font-size:14px}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;background:var(--bg);color:var(--t1);font-family:'Inter',-apple-system,sans-serif;line-height:1.5;-webkit-font-smoothing:antialiased}
a{color:inherit;text-decoration:none}
code{font-family:'SF Mono',monospace;font-size:.82em;background:var(--bg3);padding:1px 5px;border-radius:4px;color:var(--bl)}
/* Layout e componentes básicos */
.layout{display:flex;height:100vh;overflow:hidden}
.main{flex:1;display:flex;flex-direction:column;overflow:hidden}
.pg-content{flex:1;overflow-y:auto;padding:20px 24px}
.btn{display:inline-flex;align-items:center;gap:6px;padding:6px 13px;border-radius:var(--r);font-size:13px;font-weight:500;border:1px solid transparent;cursor:pointer;transition:all .12s;white-space:nowrap;line-height:1.4;text-decoration:none;font-family:inherit}
.bp{background:var(--ac);color:#fff;border-color:var(--ac)}.bp:hover{background:var(--ach);border-color:var(--ach)}
.bs{background:var(--bg3);color:var(--t2);border-color:var(--bd)}.bs:hover{background:var(--bgh);color:var(--t1)}
.bd2{background:var(--rdm);color:var(--rd);border-color:rgba(248,113,113,.2)}.bd2:hover{background:var(--rd);color:#fff}
/* Formulários */
.fc{padding:8px 11px;background:var(--bg);border:1px solid var(--bd);border-radius:var(--r);color:var(--t1);font-size:13px;font-family:inherit;width:100%}
.fc:focus{outline:none;border-color:var(--ac);box-shadow:0 0 0 3px var(--acm)}
/* Modal */
.mbk{display:none;position:fixed;inset:0;background:rgba(0,0,0,.75);z-index:200;align-items:center;justify-content:center}
.mbk.open{display:flex}
.modal{background:var(--bg2);border:1px solid var(--bd);border-radius:var(--rl);padding:24px;max-width:420px;width:90%}
/* Login */
.lp{min-height:100vh;display:flex;align-items:center;justify-content:center;background:var(--bg)}
.lc{width:100%;max-width:360px;background:var(--bg2);border:1px solid var(--bd);border-radius:var(--rl);padding:32px}
/* Table */
table{width:100%;border-collapse:collapse}
thead th{padding:9px 16px;text-align:left;font-size:10px;font-weight:600;color:var(--t3);text-transform:uppercase;background:var(--bg);border-bottom:1px solid var(--bd)}
tbody td{padding:10px 16px;font-size:13px;color:var(--t1);border-bottom:1px solid var(--bd)}
/* Badge e outros */
.badge{display:inline-flex;align-items:center;padding:2px 8px;border-radius:99px;font-size:11px;font-weight:600}
.bgn{background:var(--gnm);color:var(--gn)}.brd{background:var(--rdm);color:var(--rd)}
"""


def get_admin_js():
    """Retorna o JS do admin (de arquivo externo ou inline)"""
    if _JS_CONTENT:
        return _JS_CONTENT
    # Fallback: JS inline mínimo
    return """// Admin JS - Velox Framework
document.querySelectorAll('.alert[data-ah]').forEach(el=>{setTimeout(()=>{el.remove()},3500)});
function od(url,lbl){document.getElementById('dl').textContent=lbl;document.getElementById('df').action=url;document.getElementById('dm').classList.add('open');}
function cd(){document.getElementById('dm').classList.remove('open');}
document.addEventListener('click',e=>{if(e.target.id==='dm')cd();});
document.addEventListener('keydown',e=>{if(e.key==='Escape')cd();});
function tc(){const el=document.getElementById('clk');if(el)el.textContent=new Date().toLocaleTimeString('pt-BR');}
tc();setInterval(tc,1000);"""


# Alias para compatibilidade (mantido para não quebrar código existente)
CSS = property(lambda self: get_admin_css())
JS = property(lambda self: get_admin_js())
CSS = get_admin_css()
JS = get_admin_js()


# ─────────────────────────────────────────
# HTML helpers
# ─────────────────────────────────────────

def _page(title, body, breadcrumb=None, meta=None, active="", alert=None):
    P = ADMIN_PREFIX
    meta = meta or []
    breadcrumb = breadcrumb or []

    links = ""
    for m in meta:
        on = "on" if active == m["slug"] else ""
        links += (
            f'<a href="{P}/{m["slug"]}/" class="sb-a {on}">'
            f'<span class="ic">◈</span>{m["label"]}'
            f'<span class="ct">{m.get("count","")}</span></a>'
        )
    if not links:
        links = '<div class="sb-a" style="opacity:.35;cursor:default"><span class="ic">◇</span>Nenhum modelo</div>'

    bc = f'<a href="{P}/">Admin</a>'
    for lbl, url in breadcrumb:
        bc += '<span class="sep">/</span>'
        bc += (f'<a href="{url}">{lbl}</a>' if url else f'<span class="cur">{lbl}</span>')

    al = ""
    if alert:
        k, m2 = alert
        cm = {"success": "als", "error": "ale", "info": "ali"}
        al = f'<div class="alert {cm.get(k,"ali")}" data-ah>{m2}</div>'

    dash_on = "on" if active == "__d__" else ""
    logs_on = "on" if active == "__l__" else ""
    sett_on = "on" if active == "__s__" else ""
    av_char = ADMIN_USER[0].upper()

    return (
        '<!DOCTYPE html><html lang="pt-BR">'
        '<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>{title} — Velox Admin</title>'
        f'<style>{CSS}</style></head>'
        '<body><div class="layout">'
        '<aside class="sb">'
        f'  <div class="sb-brand">'
        f'  <img src="{P}/_logo.png" alt="Velox" class="sb-logo">'
        f'  <div><div class="sb-name">Velox Admin</div><div class="sb-ver">v1.0.0</div></div></div>'
        f'  <div class="sb-sec"><div class="sb-lbl">Geral</div>'
        f'  <a href="{P}/" class="sb-a {dash_on}"><span class="ic">◉</span>Dashboard</a></div>'
        f'  <div class="sb-sec"><div class="sb-lbl">Modelos</div>{links}</div>'
        f'  <div class="sb-sec"><div class="sb-lbl">Sistema</div>'
        f'  <a href="{P}/logs/" class="sb-a {logs_on}"><span class="ic">≡</span>Logs</a>'
        f'  <a href="{P}/settings/" class="sb-a {sett_on}"><span class="ic">⚙</span>Config</a></div>'
        f'  <div class="sb-ft"><div class="sb-user"><div class="sb-av">{av_char}</div>'
        f'  <div><div class="sb-un">{ADMIN_USER}</div><div class="sb-ur">Admin</div></div></div>'
        f'  <a href="{P}/logout/" class="sb-out">↩ Sair</a></div>'
        '</aside>'
        '<div class="main">'
        f'  <header class="topbar"><nav class="bc">{bc}</nav>'
        f'  <div class="tr"><span class="clk" id="clk"></span>'
        f'  <a href="/" class="btn bg2 sm" target="_blank">↗ Site</a></div></header>'
        f'  <div class="pg-content">{al}{body}</div>'
        '</div></div>'
        '<div class="mbk" id="dm"><div class="modal">'
        '  <div class="mt2">Confirmar exclusão</div>'
        '  <div class="mx">Excluir <strong id="dl"></strong>?<br>Esta ação não pode ser desfeita.</div>'
        '  <div class="mac"><button class="btn bs sm" onclick="cd()">Cancelar</button>'
        '  <form id="df" method="POST" style="display:inline">'
        '  <button class="btn bd2 sm" type="submit">Excluir</button></form></div>'
        '</div></div>'
        f'<script>{JS}</script>'
        '</body></html>'
    )


def _login_page(error=""):
    P = ADMIN_PREFIX
    err = f'<div class="lerr">⚠ {error}</div>' if error else ""
    return (
        '<!DOCTYPE html><html lang="pt-BR">'
        '<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>Entrar — Velox Admin</title><style>{CSS}</style></head>'
        '<body><div class="lp"><div class="lc">'
        '  <div class="ll">'
        f'  <img src="{P}/_logo.png" alt="Velox" class="llo">'
        '  <div><div class="lln">Velox</div><div class="lls">Painel Admin</div></div></div>'
        '  <h1 class="lti">Bem-vindo</h1>'
        '  <p class="lsu">Entre com suas credenciais para continuar.</p>'
        f'  {err}'
        f'  <form class="lf" method="POST" action="{P}/login/">'
        '    <div class="fg"><label class="fl">Usuário</label>'
        '    <input class="fc" type="text" name="username" placeholder="admin" autofocus autocomplete="username"></div>'
        '    <div class="fg"><label class="fl">Senha</label>'
        '    <input class="fc" type="password" name="password" placeholder="••••••••" autocomplete="current-password"></div>'
        '    <button class="btn bp lbtn" type="submit">Entrar →</button>'
        '  </form>'
        f'</div></div><script>{JS}</script></body></html>'
    )


# ─────────────────────────────────────────
# ModelAdmin — configuração por modelo
# ─────────────────────────────────────────

class ModelAdmin:
    """
    Configuração do admin para um modelo.
    Inspirado no Django ModelAdmin.

    Atributos:
        list_display    : colunas exibidas na listagem
        list_filter     : campos para filtro lateral
        search_fields   : campos pesquisáveis
        ordering        : ordenação padrão [('campo', 'asc'|'desc')]
        readonly_fields : campos somente leitura no form
        exclude         : campos excluídos do form
        fields          : ordem/seleção de campos no form
        fieldsets       : agrupamento de campos [(título, [campos])]
        per_page        : registros por página (padrão 25)
        actions         : ações em lote [(nome, label, função)]
        list_per_page   : alias de per_page
        date_hierarchy  : campo de data para navegação hierárquica
        show_full_result_count : mostra total de resultados
        save_on_top     : botão salvar no topo do form também
        verbose_name    : nome legível do modelo
        verbose_name_plural : nome plural

    Métodos customizáveis:
        get_queryset(request)           -> lista de objetos
        get_object(id)                  -> objeto por id
        has_add_permission(request)     -> bool
        has_change_permission(request)  -> bool
        has_delete_permission(request)  -> bool
        display_<campo>(obj)            -> str HTML para coluna customizada
        save_model(request, obj, form, change) -> salva o objeto
        delete_model(request, obj)      -> deleta o objeto
    """

    list_display             = []
    list_filter              = []
    search_fields            = []
    ordering                 = []
    readonly_fields          = []
    exclude                  = []
    fields                   = None
    fieldsets                = None
    per_page                 = 25
    list_per_page            = 25
    actions                  = []
    date_hierarchy           = None
    show_full_result_count   = True
    save_on_top              = False
    verbose_name             = None
    verbose_name_plural      = None

    def __init__(self, model_class):
        self.model_class  = model_class
        self.model_name   = model_class.__name__
        self.slug         = model_class.__name__.lower()
        self.verbose_name = self.verbose_name or model_class.__name__
        self.verbose_name_plural = self.verbose_name_plural or (self.verbose_name + 's')
        self.per_page     = self.list_per_page or self.per_page

    # ── Permissões ────────────────────────────────────────
    def has_add_permission(self, request):    return True
    def has_change_permission(self, request): return True
    def has_delete_permission(self, request): return True

    # ── Queryset ──────────────────────────────────────────
    def get_queryset(self, request):
        try:
            return self.model_class.all()
        except Exception:
            return []

    def get_object(self, id):
        try:
            return self.model_class.get(int(id))
        except Exception:
            return None

    # ── Campos ────────────────────────────────────────────
    def get_fields(self):
        if self.fields:
            return [f for f in self.fields if f not in self.exclude]
        schema = getattr(self.model_class, 'schema', {})
        return [f for f in schema if f not in self.exclude]

    def get_list_display(self):
        if self.list_display:
            return self.list_display
        schema = getattr(self.model_class, 'schema', {})
        return ['id'] + list(schema.keys())[:5]

    def get_fieldsets(self):
        if self.fieldsets:
            return self.fieldsets
        return [('', self.get_fields())]

    # ── Serialização ──────────────────────────────────────
    def obj_dict(self, obj) -> dict:
        if hasattr(obj, 'to_dict'):
            return obj.to_dict()
        if hasattr(obj, '__dict__'):
            return {k: v for k, v in obj.__dict__.items() if not k.startswith('_')}
        return {}

    # ── Exibição de valor ─────────────────────────────────
    def display_val(self, obj, field) -> str:
        # Método customizado display_<campo>
        custom = getattr(self, f'display_{field}', None)
        if custom:
            try:
                return str(custom(obj))
            except Exception:
                pass

        d   = self.obj_dict(obj)
        val = d.get(field)

        if val is None:
            return '<span style="color:var(--t3)">—</span>'
        if isinstance(val, bool):
            return ('<span class="badge bgn">✓ Sim</span>' if val
                    else '<span class="badge bgr">✗ Não</span>')
        if isinstance(val, datetime):
            return val.strftime('%d/%m/%Y %H:%M')

        s = str(val)
        return (s[:60] + '…') if len(s) > 60 else s

    # ── Ações padrão ──────────────────────────────────────
    def action_delete_selected(self, request, queryset):
        """Ação padrão: excluir selecionados"""
        count = 0
        for obj in queryset:
            try:
                self.delete_model(request, obj)
                count += 1
            except Exception:
                pass
        return f'{count} registro(s) excluído(s).'

    def get_actions(self):
        acts = [('delete_selected', 'Excluir selecionados', self.action_delete_selected)]
        for a in self.actions:
            if isinstance(a, tuple):
                acts.append(a)
            elif isinstance(a, str):
                fn = getattr(self, a, None)
                if fn:
                    acts.append((a, a.replace('_', ' ').capitalize(), fn))
        return acts

    # ── Save / Delete ─────────────────────────────────────
    def save_model(self, request, obj, form_data: dict, change: bool):
        if change:
            obj.update(**form_data)
        else:
            obj = self.model_class.create(**form_data)
        return obj

    def delete_model(self, request, obj):
        obj.delete()

    # ── Filtro e busca ────────────────────────────────────
    def apply_search(self, objects, q: str):
        if not q or not self.search_fields:
            return objects
        q = q.lower()
        return [o for o in objects
                if any(q in str(getattr(o, f, '')).lower() for f in self.search_fields)]

    def apply_filters(self, objects, params: dict):
        for field in self.list_filter:
            val = params.get(f'f_{field}')
            if val:
                objects = [o for o in objects
                           if str(getattr(o, field, '')) == val]
        return objects

    def apply_ordering(self, objects, o: str, ot: str):
        if not o:
            if self.ordering:
                col, direction = (self.ordering[0] if isinstance(self.ordering[0], tuple)
                                  else (self.ordering[0], 'asc'))
                reverse = direction.lower() == 'desc'
                objects = sorted(objects, key=lambda x: (getattr(x, col, None) or ''), reverse=reverse)
            return objects
        reverse = ot == 'desc'
        try:
            objects = sorted(objects, key=lambda x: (getattr(x, o, None) or ''), reverse=reverse)
        except Exception:
            pass
        return objects

    # ─────────────────────────────────────────────────────
    # Render: listagem
    # ─────────────────────────────────────────────────────
    def render_list(self, request, meta, alert=None):
        P      = ADMIN_PREFIX
        params = _qs(request)
        q      = params.get('q', '')
        page   = max(1, int(params.get('p', 1) or 1))
        o      = params.get('o', '')   # campo de ordenação
        ot     = params.get('ot', 'asc')  # asc | desc

        objects = self.get_queryset(request)
        objects = self.apply_search(objects, q)
        objects = self.apply_filters(objects, params)
        objects = self.apply_ordering(objects, o, ot)

        total      = len(objects)
        per_page   = self.per_page
        total_pages = max(1, (total + per_page - 1) // per_page)
        page       = min(page, total_pages)
        start      = (page - 1) * per_page
        page_objs  = objects[start:start + per_page]

        cols = self.get_list_display()

        # ── Cabeçalho da tabela ──
        def th_link(col):
            label = col.replace('_', ' ').upper()
            schema = getattr(self.model_class, 'schema', {})
            if col not in schema and col != 'id':
                return f'<th>{label}</th>'
            new_ot = 'desc' if (o == col and ot == 'asc') else 'asc'
            cls = f'sort-{"asc" if ot=="asc" else "desc"}' if o == col else ''
            url = f'{P}/{self.slug}/?q={q}&o={col}&ot={new_ot}&p=1'
            for field in self.list_filter:
                fv = params.get(f'f_{field}', '')
                if fv:
                    url += f'&f_{field}={fv}'
            return f'<th><a href="{url}" class="{cls}">{label}</a></th>'

        ths = '<th class="chk-col"><input type="checkbox" id="sel-all"></th>'
        ths += ''.join(th_link(c) for c in cols)
        ths += '<th style="text-align:right">AÇÕES</th>'

        # ── Linhas ──
        rows = ''
        if page_objs:
            for obj in page_objs:
                d   = self.obj_dict(obj)
                oid = d.get('id', '')
                vals = list(d.values())
                lbl = str(vals[1]) if len(vals) > 1 else f'#{oid}'
                tds = f'<td class="chk-col"><input type="checkbox" class="row-chk" value="{oid}"></td>'
                tds += ''.join(f'<td>{self.display_val(obj, c)}</td>' for c in cols)
                edit_url   = f'{P}/{self.slug}/{oid}/edit/'
                delete_url = f'{P}/{self.slug}/{oid}/delete/'
                tds += (
                    f'<td class="tac">'
                    f'<a href="{edit_url}" class="btn bg2 xs">✎ Editar</a>'
                    f'<button class="btn bd2 xs" onclick="od(\'{delete_url}\',\'{self.model_name} {lbl}\')">✕ Excluir</button>'
                    f'</td>'
                )
                rows += f'<tr>{tds}</tr>'
        else:
            n   = len(cols) + 2
            msg = f'Sem resultados para "{q}"' if q else 'Nenhum registro ainda.'
            rows = (
                f'<tr><td colspan="{n}">'
                f'<div class="empty"><div class="eic">◇</div>'
                f'<div class="ett">{msg}</div>'
                + (f'<div class="etx"><a href="{P}/{self.slug}/add/" class="btn bp sm" style="margin-top:12px">+ Adicionar {self.verbose_name}</a></div>' if not q else '')
                + '</div></td></tr>'
            )

        # ── Barra de busca ──
        search_html = ''
        if self.search_fields:
            search_html = (
                f'<div class="sw2"><span class="si">⌕</span>'
                f'<input class="sinp" type="text" placeholder="Buscar por {", ".join(self.search_fields)}…" '
                f'value="{q}" data-url="{P}/{self.slug}/"></div>'
            )

        # ── Filtros laterais ──
        filters_html = ''
        if self.list_filter:
            filters_html = '<div class="filters">'
            for field in self.list_filter:
                cur_val = params.get(f'f_{field}', '')
                all_vals = sorted({str(getattr(o, field, '')) for o in objects if getattr(o, field, None) is not None})
                opts = f'<option value="">Todos {field.replace("_"," ")}</option>'
                for v in all_vals:
                    sel = 'selected' if v == cur_val else ''
                    opts += f'<option value="{v}" {sel}>{v}</option>'
                filters_html += f'<select class="filter-select" name="f_{field}">{opts}</select>'
            filters_html += '</div>'

        # ── Ações em lote ──
        actions = self.get_actions()
        action_opts = ''.join(f'<option value="{a[0]}">{a[1]}</option>' for a in actions)
        actions_bar = (
            f'<div class="actions-bar">'
            f'<form id="bulk-form" method="POST" action="{P}/{self.slug}/action/">'
            f'<select name="action">{action_opts}</select>'
            f'<button type="submit" class="btn bs sm" style="margin-left:6px">Executar</button>'
            f'<span class="sel-count" id="sel-count"></span>'
            f'</form></div>'
        )

        # ── Paginação ──
        def pag_url(pg):
            url = f'{P}/{self.slug}/?q={q}&o={o}&ot={ot}&p={pg}'
            for field in self.list_filter:
                fv = params.get(f'f_{field}', '')
                if fv:
                    url += f'&f_{field}={fv}'
            return url

        pag_html = ''
        if total_pages > 1:
            pag_html = '<div class="pag">'
            if page > 1:
                pag_html += f'<a href="{pag_url(page-1)}">‹</a>'
            for pg in range(1, total_pages + 1):
                if pg == page:
                    pag_html += f'<span class="cur">{pg}</span>'
                elif abs(pg - page) <= 2 or pg in (1, total_pages):
                    pag_html += f'<a href="{pag_url(pg)}">{pg}</a>'
                elif abs(pg - page) == 3:
                    pag_html += '<span class="dots">…</span>'
            if page < total_pages:
                pag_html += f'<a href="{pag_url(page+1)}">›</a>'
            showing_start = start + 1
            showing_end   = min(start + per_page, total)
            pag_html += f'<span class="pag-info">{showing_start}–{showing_end} de {total}</span>'
            pag_html += '</div>'

        # ── Botões de cabeçalho ──
        add_btn = ''
        if self.has_add_permission(request):
            add_btn = f'<a href="{P}/{self.slug}/add/" class="btn bp sm">+ Adicionar {self.verbose_name}</a>'
        export_btn = f'<a href="{P}/{self.slug}/export/" class="btn byw sm">↓ CSV</a>'

        count_label = f'{total} {self.verbose_name_plural if total != 1 else self.verbose_name}'

        body = (
            f'<div class="ph">'
            f'<div><div class="pt">{self.verbose_name_plural}</div>'
            f'<div class="pd">{count_label}</div></div>'
            f'<div class="pa">{export_btn}{add_btn}</div></div>'
            f'<div class="card">'
            f'<div class="tb">{search_html}{filters_html}'
            f'<div class="tbr"><span style="font-size:11px;color:var(--t3)">{total} total</span></div></div>'
            f'{actions_bar}'
            f'<div class="tw"><table>'
            f'<thead><tr>{ths}</tr></thead>'
            f'<tbody>{rows}</tbody>'
            f'</table></div>'
            f'{pag_html}'
            f'</div>'
        )
        return _page(self.verbose_name_plural, body,
                     [(self.verbose_name_plural, None)], meta, self.slug, alert)

    # ─────────────────────────────────────────────────────
    # Render: formulário (criar / editar)
    # ─────────────────────────────────────────────────────
    def render_form(self, request, obj=None, errors=None, meta=None, alert=None):
        errors  = errors or {}
        is_edit = obj is not None
        title   = ('Editar ' if is_edit else 'Adicionar ') + self.verbose_name
        d       = self.obj_dict(obj) if obj else {}
        oid     = d.get('id', '')
        P       = ADMIN_PREFIX
        action  = f'{P}/{self.slug}/{oid + "/" if is_edit else ""}save/'
        schema  = getattr(self.model_class, 'schema', {})

        type_map = {str: 'text', int: 'number', float: 'number', bool: 'checkbox'}

        def render_field(field):
            val    = d.get(field, '')
            err    = errors.get(field, '')
            ft     = type_map.get(schema.get(field, str), 'text')
            is_ro  = field in self.readonly_fields
            lbl    = field.replace('_', ' ').capitalize()
            req    = '' if is_ro else '<span class="req">*</span>'
            hint   = ''

            if ft == 'checkbox':
                chk = ' checked' if str(val) in ('True', '1', 'true') else ''
                inp = f'<input type="checkbox" name="{field}"{chk} class="fc" style="width:18px;height:18px">'
            elif schema.get(field) == str and (field.endswith('content') or field.endswith('body') or field.endswith('descricao') or field.endswith('description')):
                inp = f'<textarea name="{field}" class="fc"{"readonly" if is_ro else ""}>{val}</textarea>'
            else:
                roa = ' readonly' if is_ro else ''
                inp = f'<input type="{ft}" name="{field}" value="{val}" class="fc"{roa}>'

            err_html  = f'<div class="fe">⚠ {err}</div>' if err else ''
            hint_html = f'<div class="fh">{hint}</div>' if hint else ''
            return (
                f'<div class="fg">'
                f'<label class="fl">{lbl}{req}</label>'
                f'{inp}{err_html}{hint_html}'
                f'</div>'
            )

        # Fieldsets
        fieldsets_html = ''
        for fs_title, fs_fields in self.get_fieldsets():
            rows_html = ''
            for i in range(0, len(fs_fields), 2):
                pair = fs_fields[i:i+2]
                if len(pair) == 1:
                    rows_html += f'<div class="fr"><div class="fg full">{render_field(pair[0]).replace("fg","fg full",1)}</div></div>'
                else:
                    rows_html += f'<div class="fr">{"".join(render_field(f) for f in pair)}</div>'

            title_html = f'<div class="fieldset-title">{fs_title}</div>' if fs_title else ''
            fieldsets_html += (
                f'<div class="fieldset">'
                f'{title_html}'
                f'<div class="fieldset-body">{rows_html}</div>'
                f'</div>'
            )

        save_txt = 'Salvar alterações' if is_edit else 'Adicionar ' + self.verbose_name
        back     = f'{P}/{self.slug}/'

        save_btns = (
            f'<button type="submit" name="_save" class="btn bp">{save_txt}</button>'
            f'<button type="submit" name="_addanother" class="btn bs">Salvar e adicionar outro</button>'
            + (f'<button type="submit" name="_continue" class="btn bs">Salvar e continuar editando</button>' if is_edit else '')
            + f'<a href="{back}" class="btn bs">Cancelar</a>'
        )
        if is_edit and self.has_delete_permission(request):
            delete_url = f'{P}/{self.slug}/{oid}/delete/'
            save_btns += f'<button type="button" class="btn bd2" style="margin-left:auto" onclick="od(\'{delete_url}\',\'{self.verbose_name} #{oid}\')">Excluir</button>'

        save_top = f'<div class="fa" style="margin-bottom:16px">{save_btns}</div>' if self.save_on_top else ''

        body = (
            f'<div class="ph">'
            f'<div><div class="pt">{title}</div></div>'
            f'<div class="pa"><a href="{back}" class="btn bs sm">← Voltar</a></div>'
            f'</div>'
            f'<form method="POST" action="{action}">'
            f'{save_top}'
            f'{fieldsets_html}'
            f'<div class="fa">{save_btns}</div>'
            f'</form>'
        )
        return _page(title, body,
                     [(self.verbose_name_plural, back), (title, None)],
                     meta or [], self.slug, alert)


# ─────────────────────────────────────────
# AdminSite — registro e rotas
# ─────────────────────────────────────────

class AdminSite:
    def __init__(self):
        self._registry: Dict[Any, ModelAdmin] = {}
        self._logs: List[dict] = []

    def register(self, model_class, admin_class=None):
        """
        Registra um modelo no admin.

        Uso:
            site.register(Post)
            site.register(Post, PostAdmin)

            # Como decorador:
            @site.register(Post)
            class PostAdmin(ModelAdmin):
                list_display = ['id', 'title']
        """
        if isinstance(model_class, type) and admin_class is None:
            # Usado como decorador sem classe admin
            def decorator(adm_cls):
                self._registry[model_class] = adm_cls(model_class)
                return adm_cls
            return decorator
        self._registry[model_class] = (admin_class or ModelAdmin)(model_class)

    def unregister(self, model_class):
        self._registry.pop(model_class, None)

    def _meta(self, request=None):
        out = []
        for cls, adm in self._registry.items():
            try:
                count = len(adm.get_queryset(request)) if request else '?'
            except Exception:
                count = '?'
            out.append({
                'label': adm.verbose_name_plural,
                'slug':  adm.slug,
                'count': count,
            })
        return out

    def _log(self, action: str, model: str, oid):
        self._logs.insert(0, {
            'time':   datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
            'action': action,
            'model':  model,
            'obj_id': oid,
            'user':   ADMIN_USER,
        })
        self._logs = self._logs[:200]

    def _get_adm_by_slug(self, slug: str) -> Optional[ModelAdmin]:
        for cls, adm in self._registry.items():
            if adm.slug == slug:
                return adm
        return None

    # ── Dashboard ─────────────────────────────────────────
    def _dashboard(self, request):
        meta = self._meta(request)
        P    = ADMIN_PREFIX
        now  = datetime.now()
        ics  = ['◉', '◈', '⬡', '⬢', '◆', '▣', '◇', '⬟']

        cards = ''
        for i, m in enumerate(meta):
            cards += (
                f'<a href="{P}/{m["slug"]}/" class="stat">'
                f'<div class="st-ic">{ics[i % len(ics)]}</div>'
                f'<div class="st-lb">{m["label"]}</div>'
                f'<div class="st-vl">{m["count"]}</div>'
                f'<div class="st-sb">registros</div></a>'
            )
        if not cards:
            cards = (
                '<div class="stat" style="grid-column:1/-1">'
                '<div class="empty"><div class="eic">◇</div>'
                '<div class="ett">Nenhum modelo registrado</div>'
                '<div class="etx">Use site.register(MeuModel)</div>'
                '</div></div>'
            )

        bm = {'criou': 'bgn', 'editou': 'bbl', 'excluiu': 'brd'}
        lrows = ''
        for log in self._logs[:15]:
            bc = bm.get(log['action'], 'bgr')
            lrows += (
                f'<tr>'
                f'<td class="tm">{log["time"]}</td>'
                f'<td><span class="badge {bc}">{log["action"]}</span></td>'
                f'<td>{log["model"]} #{log["obj_id"]}</td>'
                f'<td class="tm">{log["user"]}</td>'
                f'</tr>'
            )
        if not lrows:
            lrows = '<tr><td colspan="4"><div class="empty" style="padding:24px"><div class="ett">Nenhuma atividade ainda</div></div></td></tr>'

        body = (
            f'<div class="ph">'
            f'<div><div class="pt">Dashboard</div>'
            f'<div class="pd">{now.strftime("%A, %d de %B de %Y")}</div>'
            f'</div></div>'
            f'<div class="stats">{cards}</div>'
            f'<div class="card">'
            f'<div class="ch"><span class="ct2">Atividade recente</span>'
            f'<a href="{P}/logs/" class="btn bg2 sm">Ver todos</a></div>'
            f'<div class="tw"><table>'
            f'<thead><tr><th>Horário</th><th>Ação</th><th>Objeto</th><th>Usuário</th></tr></thead>'
            f'<tbody>{lrows}</tbody>'
            f'</table></div></div>'
            f'<div class="card">'
            f'<div class="ch"><span class="ct2">Sistema</span></div>'
            f'<div class="cb"><table><tbody>'
            f'<tr><td class="tm" style="width:160px">Framework</td><td>Velox v1.0.0</td></tr>'
            f'<tr><td class="tm">Modelos registrados</td><td>{len(self._registry)}</td></tr>'
            f'<tr><td class="tm">Admin URL</td><td><code>{P}/</code></td></tr>'
            f'<tr><td class="tm">Data/Hora</td><td>{now.strftime("%d/%m/%Y %H:%M:%S")}</td></tr>'
            f'</tbody></table></div></div>'
        )
        return _page('Dashboard', body, meta=meta, active='__d__')

    # ── Registro de rotas ─────────────────────────────────
    def register_routes(self, app):
        P    = ADMIN_PREFIX
        site = self

        # ── Logo do pacote ──
        @app.get(P + '/_logo.png')
        def adm_logo(request, response):
            """Serve o logo PNG do pacote Velox."""
            import pathlib as _pl
            logo = _pl.Path(__file__).parent / 'assets' / 'velox-logo.png'
            if logo.exists():
                response.status_code = 200
                response.set_header('Content-Type', 'image/png')
                response.set_header('Cache-Control', 'public, max-age=86400')
                response.body = logo.read_bytes()
            else:
                response.status_code = 404
                response.body = b''

        # ── Login / Logout ──
        @app.get(P + '/login/')
        def adm_login_get(request, response):
            if _authed(request):
                response.redirect(P + '/')
                return
            response.html(_login_page())

        @app.post(P + '/login/')
        def adm_login_post(request, response):
            data = request.form or {}
            def _g(k): v = data.get(k, ''); return v[0] if isinstance(v, list) else v
            u, pw = _g('username'), _g('password')
            if u == ADMIN_USER and _check_pw(pw, ADMIN_PASSWORD):
                _set_session(response)
                response.redirect(P + '/')
            else:
                response.html(_login_page('Usuário ou senha incorretos.'))

        @app.get(P + '/logout/')
        def adm_logout(request, response):
            _clear_session(response)
            response.redirect(P + '/login/')

        # ── Dashboard ──
        @app.get(P + '/')
        def adm_dash(request, response):
            if not _authed(request):
                response.redirect(P + '/login/')
                return
            response.html(site._dashboard(request))

        # ── Logs ──
        @app.get(P + '/logs/')
        def adm_logs(request, response):
            if not _authed(request):
                response.redirect(P + '/login/')
                return
            meta = site._meta(request)
            bm   = {'criou': 'bgn', 'editou': 'bbl', 'excluiu': 'brd'}
            rows = ''
            for log in site._logs:
                bc = bm.get(log['action'], 'bgr')
                rows += (
                    f'<tr><td class="tm">{log["time"]}</td>'
                    f'<td><span class="badge {bc}">{log["action"]}</span></td>'
                    f'<td>{log["model"]} #{log["obj_id"]}</td>'
                    f'<td class="tm">{log["user"]}</td></tr>'
                )
            if not rows:
                rows = '<tr><td colspan="4"><div class="empty" style="padding:24px"><div class="ett">Sem atividade</div></div></td></tr>'
            body = (
                '<div class="ph"><div class="pt">Logs de Atividade</div></div>'
                '<div class="card"><div class="tw"><table>'
                '<thead><tr><th>Horário</th><th>Ação</th><th>Objeto</th><th>Usuário</th></tr></thead>'
                f'<tbody>{rows}</tbody></table></div></div>'
            )
            response.html(_page('Logs', body, [('Logs', None)], meta, '__l__'))

        # ── Settings ──
        @app.get(P + '/settings/')
        def adm_settings(request, response):
            if not _authed(request):
                response.redirect(P + '/login/')
                return
            meta = site._meta(request)
            body = (
                '<div class="ph"><div class="pt">Configurações</div></div>'
                '<div class="card">'
                '<div class="ch"><span class="ct2">Variáveis de ambiente</span></div>'
                '<div class="cb"><table><tbody>'
                f'<tr><td class="tm" style="width:220px">VELOX_ADMIN_USER</td><td><code>{ADMIN_USER}</code></td></tr>'
                '<tr><td class="tm">VELOX_ADMIN_PASSWORD</td><td><code>••••••••</code></td></tr>'
                f'<tr><td class="tm">VELOX_ADMIN_PREFIX</td><td><code>{P}</code></td></tr>'
                '<tr><td class="tm">VELOX_SECRET_KEY</td><td><code>••••••••••••••••</code></td></tr>'
                '</tbody></table></div></div>'
            )
            response.html(_page('Configurações', body, [('Configurações', None)], meta, '__s__'))

        # ── Rotas por modelo ──
        for cls, adm in self._registry.items():
            slug = adm.slug
            _a   = adm

            @app.get(P + '/' + slug + '/')
            def adm_list(request, response, _adm=_a):
                if not _authed(request):
                    response.redirect(P + '/login/')
                    return
                response.html(_adm.render_list(request, site._meta(request)))

            @app.get(P + '/' + slug + '/add/')
            def adm_add(request, response, _adm=_a):
                if not _authed(request):
                    response.redirect(P + '/login/')
                    return
                if not _adm.has_add_permission(request):
                    response.html(_page('Sem permissão', '<p>Você não tem permissão para adicionar.</p>',
                                        meta=site._meta(request)))
                    return
                response.html(_adm.render_form(request, meta=site._meta(request)))

            @app.post(P + '/' + slug + '/save/')
            def adm_create(request, response, _adm=_a):
                if not _authed(request):
                    response.redirect(P + '/login/')
                    return
                data = dict(request.form or {})
                # Converter checkboxes
                schema = getattr(_adm.model_class, 'schema', {})
                for k, v in schema.items():
                    if v == bool:
                        data[k] = k in data
                try:
                    obj = _adm.save_model(request, None, data, change=False)
                    site._log('criou', _adm.model_name, getattr(obj, 'id', '?'))
                    next_action = (request.form or {}).get('_addanother')
                    if next_action:
                        response.redirect(P + '/' + _adm.slug + '/add/')
                    else:
                        response.redirect(P + '/' + _adm.slug + '/')
                except Exception as e:
                    response.html(_adm.render_form(request,
                        meta=site._meta(request),
                        alert=('error', f'Erro ao salvar: {e}')))

            @app.get(P + '/' + slug + '/<int:id>/edit/')
            def adm_edit(request, response, id, _adm=_a):
                if not _authed(request):
                    response.redirect(P + '/login/')
                    return
                obj = _adm.get_object(id)
                if not obj:
                    response.redirect(P + '/' + _adm.slug + '/')
                    return
                response.html(_adm.render_form(request, obj=obj, meta=site._meta(request)))

            @app.post(P + '/' + slug + '/<int:id>/save/')
            def adm_update(request, response, id, _adm=_a):
                if not _authed(request):
                    response.redirect(P + '/login/')
                    return
                obj = _adm.get_object(id)
                if not obj:
                    response.redirect(P + '/' + _adm.slug + '/')
                    return
                data = dict(request.form or {})
                schema = getattr(_adm.model_class, 'schema', {})
                for k, v in schema.items():
                    if v == bool:
                        data[k] = k in data
                try:
                    _adm.save_model(request, obj, data, change=True)
                    site._log('editou', _adm.model_name, id)
                    next_action = (request.form or {}).get('_continue')
                    if next_action:
                        response.redirect(P + '/' + _adm.slug + f'/{id}/edit/')
                    else:
                        response.redirect(P + '/' + _adm.slug + '/')
                except Exception as e:
                    response.html(_adm.render_form(request, obj=obj,
                        meta=site._meta(request),
                        alert=('error', f'Erro ao salvar: {e}')))

            @app.post(P + '/' + slug + '/<int:id>/delete/')
            def adm_delete(request, response, id, _adm=_a):
                if not _authed(request):
                    response.redirect(P + '/login/')
                    return
                if not _adm.has_delete_permission(request):
                    response.redirect(P + '/' + _adm.slug + '/')
                    return
                obj = _adm.get_object(id)
                if obj:
                    try:
                        _adm.delete_model(request, obj)
                        site._log('excluiu', _adm.model_name, id)
                    except Exception as e:
                        response.html(_adm.render_list(request, site._meta(request),
                                                       alert=('error', f'Erro ao excluir: {e}')))
                        return
                response.redirect(P + '/' + _adm.slug + '/')

            @app.post(P + '/' + slug + '/action/')
            def adm_action(request, response, _adm=_a):
                if not _authed(request):
                    response.redirect(P + '/login/')
                    return
                form    = request.form or {}
                action  = form.get('action', '')
                ids_raw = form.get('ids', [])
                if isinstance(ids_raw, str):
                    ids_raw = [ids_raw]

                acts = {a[0]: a[2] for a in _adm.get_actions()}
                fn   = acts.get(action)
                if not fn or not ids_raw:
                    response.redirect(P + '/' + _adm.slug + '/')
                    return

                queryset = [_adm.get_object(i) for i in ids_raw if _adm.get_object(i)]
                try:
                    msg = fn(request, queryset) or 'Ação executada.'
                    site._log(action, _adm.model_name, f'{len(queryset)} objetos')
                    response.html(_adm.render_list(request, site._meta(request),
                                                   alert=('success', msg)))
                except Exception as e:
                    response.html(_adm.render_list(request, site._meta(request),
                                                   alert=('error', f'Erro: {e}')))

            @app.get(P + '/' + slug + '/export/')
            def adm_export(request, response, _adm=_a):
                if not _authed(request):
                    response.redirect(P + '/login/')
                    return
                objects = _adm.get_queryset(request)
                cols    = _adm.get_list_display()
                buf     = io.StringIO()
                writer  = csv.writer(buf)
                writer.writerow(cols)
                for obj in objects:
                    d = _adm.obj_dict(obj)
                    writer.writerow([d.get(c, '') for c in cols])
                csv_data = buf.getvalue()
                response.status_code = 200
                response.set_header('Content-Type', 'text/csv; charset=utf-8')
                response.set_header('Content-Disposition',
                                    f'attachment; filename="{_adm.slug}.csv"')
                response.body = csv_data.encode('utf-8')


# ─────────────────────────────────────────
# Instância global
# ─────────────────────────────────────────

site = AdminSite()


def register(model_class, admin_class=None):
    """
    Registra um modelo no admin global.

    Uso:
        from velox.admin import register
        register(Post)
        register(Post, PostAdmin)
    """
    return site.register(model_class, admin_class)
