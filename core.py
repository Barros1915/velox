"""
Core - Velox Framework
=======================
Modos de execucao:
  1. WSGI/Threading  -> app.run()              (sem deps, stdlib Python)
  2. ASGI/uvicorn    -> app.run(asgi=True)      (requer: pip install uvicorn)
                     -> uvicorn meuapp:app      (CLI do uvicorn diretamente)

Rotas sync e async funcionam juntas no mesmo app:

    @app.get('/')
    def home(req, res):              # sync - igual ao antes
        return app.render('index.html')

    @app.get('/api/dados')
    async def dados(req, res):       # async - roda no event loop
        resultado = await buscar()
        res.json(resultado)

    @app.websocket('/ws/chat')
    async def chat(ws):              # WebSocket (apenas ASGI)
        while True:
            msg = await ws.receive()
            if msg is None: break
            await ws.send(f'echo: {msg}')
"""

import asyncio
import inspect
import json
import mimetypes
import os
import re
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from socketserver import ThreadingMixIn
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, unquote

from .request import Request
from .response import Response
from .template import TemplateEngine


# ─────────────────────────────────────────────────────────────────
# .env loader
# ─────────────────────────────────────────────────────────────────

def _load_env(path='.env'):
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, _, val = line.partition('=')
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val

_load_env()


# ─────────────────────────────────────────────────────────────────
# Converters de tipo nas rotas
# ─────────────────────────────────────────────────────────────────

CONVERTERS = {
    'int':   (r'\d+',            int),
    'float': (r'\d+\.?\d*',      float),
    'str':   (r'[^/]+',          str),
    'slug':  (r'[a-z0-9\-]+',    str),
    'uuid':  (r'[0-9a-f\-]{36}', str),
    'path':  (r'.+',             str),
}


# ─────────────────────────────────────────────────────────────────
# RoutePattern
# ─────────────────────────────────────────────────────────────────

class RoutePattern:
    def __init__(self, path: str):
        self.raw    = path
        self.params: Dict[str, Callable] = {}
        self._regex = self._compile(path)
        self.is_dyn = '<' in path

    def _compile(self, path: str) -> re.Pattern:
        pattern = re.escape(path)
        for m in re.finditer(r'\\<(?:(\w+):)?(\w+)\\>', pattern):
            conv  = m.group(1) or 'str'
            param = m.group(2)
            regex, converter = CONVERTERS.get(conv, CONVERTERS['str'])
            self.params[param] = converter
            pattern = pattern.replace(m.group(0), f'(?P<{param}>{regex})', 1)
        return re.compile(f'^{pattern}$')

    def match(self, path: str) -> Optional[Dict]:
        path = path.split('?')[0]
        m    = self._regex.match(path)
        if not m:
            return None
        return {k: self.params[k](v) for k, v in m.groupdict().items()}

    def __repr__(self):
        return f'<RoutePattern {self.raw}>'


# ─────────────────────────────────────────────────────────────────
# Router / Blueprint
# ─────────────────────────────────────────────────────────────────

class Router:
    """
    Router modular — use como Blueprint para separar rotas:

        api = Router()

        @api.get('/users')
        async def list_users(req, res):
            res.json(await User.all())

        app.include(api, prefix='/api')
    """

    def __init__(self, prefix: str = ''):
        self.prefix  = prefix.rstrip('/')
        self._routes: List[Tuple[str, RoutePattern, Callable]] = []
        self._error_handlers: Dict[int, Callable] = {}
        self.static_folder   = 'static'
        self.template_folder = 'templates'

    def add_route(self, path: str, method: str, handler: Callable):
        full = self.prefix + path
        self._routes.append((method.upper(), RoutePattern(full), handler))

    def match(self, path: str, method: str) -> Tuple[Optional[Callable], Dict]:
        clean = path.split('?')[0]
        for m, pattern, handler in self._routes:
            if m != method.upper():
                continue
            kwargs = pattern.match(clean)
            if kwargs is not None:
                return handler, kwargs
        return None, {}

    def add_error_handler(self, code: int, handler: Callable):
        self._error_handlers[code] = handler

    def get_error_handler(self, code: int) -> Optional[Callable]:
        return self._error_handlers.get(code)

    def list_routes(self) -> List[Dict]:
        return [
            {
                'method':  m,
                'path':    p.raw,
                'async':   inspect.iscoroutinefunction(h),
                'handler': h.__name__,
            }
            for m, p, h in self._routes
        ]

    def get(self, path: str):
        def d(fn): self.add_route(path, 'GET', fn); return fn
        return d

    def post(self, path: str):
        def d(fn): self.add_route(path, 'POST', fn); return fn
        return d

    def put(self, path: str):
        def d(fn): self.add_route(path, 'PUT', fn); return fn
        return d

    def delete(self, path: str):
        def d(fn): self.add_route(path, 'DELETE', fn); return fn
        return d

    def patch(self, path: str):
        def d(fn): self.add_route(path, 'PATCH', fn); return fn
        return d

    def route(self, path: str, methods: List[str] = None):
        methods = methods or ['GET']
        def d(fn):
            for m in methods:
                self.add_route(path, m, fn)
            return fn
        return d

    def websocket(self, path: str):
        def d(fn): self.add_route(path, 'WS', fn); return fn
        return d

    def resource(self, path: str):
        """
        Define múltiplos métodos HTTP para uma rota usando uma classe.

        Uso:
            @app.resource('/api/produtos')
            class Produtos:
                def get(req, res):
                    res.json({'produtos': []})
                    return res

                def post(req, res):
                    body = req.json or {}
                    res.json({'criado': True, 'dados': body})
                    return res

                def put(req, res):
                    res.json({'atualizado': True})
                    return res

                def delete(req, res):
                    res.json({'deletado': True})
                    return res
        """
        def decorator(cls):
            for method in ['get', 'post', 'put', 'delete', 'patch']:
                handler = getattr(cls, method, None)
                if handler:
                    self.add_route(path, method.upper(), handler)
            return cls
        return decorator


Blueprint = Router  # alias


# ─────────────────────────────────────────────────────────────────
# Helpers async
# ─────────────────────────────────────────────────────────────────

async def _call(handler: Callable, *args, **kwargs) -> Any:
    """Chama handler sync ou async de forma transparente"""
    if inspect.iscoroutinefunction(handler):
        return await handler(*args, **kwargs)
    return handler(*args, **kwargs)


# ─────────────────────────────────────────────────────────────────
# Pagina de erro padrao
# ─────────────────────────────────────────────────────────────────

def _error_html(code: int, message: str) -> str:
    colors = {404: '#5865f2', 500: '#ef4444', 403: '#f59e0b', 400: '#6b7280'}
    titles = {404: 'Nao encontrado', 500: 'Erro interno',
              403: 'Proibido', 400: 'Requisicao invalida'}
    color = colors.get(code, '#5865f2')
    title = titles.get(code, 'Erro')
    return (
        f'<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8">'
        f'<title>{code}</title>'
        f'<style>*{{margin:0;padding:0;box-sizing:border-box}}'
        f'body{{font-family:-apple-system,sans-serif;background:#0d0d0d;color:#f0f0f0;'
        f'display:flex;align-items:center;justify-content:center;min-height:100vh}}'
        f'.b{{text-align:center;padding:40px}}'
        f'.c{{font-size:80px;font-weight:700;color:{color};line-height:1}}'
        f'.m{{font-size:18px;color:#999;margin:12px 0 16px}}'
        f'.d{{font-size:13px;color:#555;margin-bottom:24px}}'
        f'a{{color:{color};font-size:14px}}</style></head>'
        f'<body><div class="b"><div class="c">{code}</div>'
        f'<div class="m">{title}</div><div class="d">{message}</div>'
        f'<a href="/">Voltar ao inicio</a></div></body></html>'
    )


# ─────────────────────────────────────────────────────────────────
# WSGI Handler (modo sync / threading — sem deps)
# ─────────────────────────────────────────────────────────────────

class _SyncHandler(BaseHTTPRequestHandler):
    app = None

    def do_GET(self):     self._dispatch('GET')
    def do_POST(self):    self._dispatch('POST')
    def do_PUT(self):     self._dispatch('PUT')
    def do_DELETE(self):  self._dispatch('DELETE')
    def do_PATCH(self):   self._dispatch('PATCH')
    def do_OPTIONS(self): self._dispatch('OPTIONS')
    def do_HEAD(self):    self._dispatch('HEAD')

    def _dispatch(self, method: str):
        app = self.app
        if self._serve_static(app):
            return

        request  = Request(self)
        response = Response()
        handler, kwargs = app.router.match(self.path, method)

        if handler is None:
            self._send_err(app, request, response, 404, 'Pagina nao encontrada')
            return

        try:
            if inspect.iscoroutinefunction(handler):
                loop   = asyncio.new_event_loop()
                result = loop.run_until_complete(handler(request, response, **kwargs))
                loop.close()
            else:
                result = handler(request, response, **kwargs)

            if isinstance(result, str):
                response.html(result)
            elif isinstance(result, dict):
                response.json(result)
            self._write_response(response)
        except Exception as e:
            self._send_err(app, request, response, 500, str(e))

    def _serve_static(self, app) -> bool:
        path = self.path.split('?')[0]
        if not path.startswith('/static/'):
            return False
        full = Path(app.router.static_folder) / unquote(path[8:])
        if not (full.exists() and full.is_file()):
            return False
        mime, _ = mimetypes.guess_type(str(full))
        data = full.read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', mime or 'application/octet-stream')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'public, max-age=3600')
        self.end_headers()
        self.wfile.write(data)
        return True

    def _write_response(self, response: Response):
        self.send_response(response.status_code)
        for k, v in response.headers.items():
            self.send_header(k, v)
        self.end_headers()
        if response.body:
            body = response.body
            if isinstance(body, str):
                body = body.encode('utf-8')
            elif not isinstance(body, bytes):
                body = str(body).encode('utf-8')
            self.wfile.write(body)

    def _send_err(self, app, request, response, code: int, message: str):
        h = app.router.get_error_handler(code)
        if h:
            try:
                result = h(request, response, message)
                if isinstance(result, str):
                    response.html(result)
                self._write_response(response)
                return
            except Exception:
                pass
        html = _error_html(code, message)
        self.send_response(code)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

    def log_message(self, fmt, *args):
        now  = datetime.now().strftime('%H:%M:%S')
        code = args[1] if len(args) > 1 else '???'
        path = args[0].split(' ')[1] if ' ' in str(args[0]) else str(args[0])
        cm   = {'2': '\033[92m', '3': '\033[93m', '4': '\033[91m', '5': '\033[91m'}
        c    = cm.get(str(code)[0], '\033[0m')
        print(f'  \033[90m{now}\033[0m  {c}{code}\033[0m  {path}')


class _ThreadingServer(ThreadingMixIn, HTTPServer):
    daemon_threads      = True
    allow_reuse_address = True


# ─────────────────────────────────────────────────────────────────
# Request ASGI
# ─────────────────────────────────────────────────────────────────

class _AsgiRequest:
    """
    Request para handlers ASGI — interface idêntica ao Request WSGI.
    Todas as propriedades disponíveis: method, path, args, form, json,
    data, cookies, headers, ip, is_ajax, is_secure, content_type, etc.
    """

    def __init__(self, method: str, path: str, query: str,
                 headers: Dict, body: bytes, scope: Dict):
        self.method        = method
        self._path_raw     = path
        self._query        = query
        self.headers       = headers
        self._body         = body
        self._scope        = scope
        self._args         = None
        self._form         = None
        self._json_data    = None
        self._cookies      = None
        self._parsed_body  = False

    # ── path / full_path ──────────────────────────────────
    @property
    def path(self) -> str:
        return self._path_raw

    @property
    def full_path(self) -> str:
        return self._path_raw + ('?' + self._query if self._query else '')

    # ── query params ──────────────────────────────────────
    @property
    def args(self) -> Dict:
        if self._args is None:
            params = parse_qs(self._query, keep_blank_values=True)
            self._args = {k: v[0] if len(v) == 1 else v for k, v in params.items()}
        return self._args

    @property
    def query_params(self) -> Dict:
        return self.args

    def get(self, key: str, default=None):
        if key in self.args:
            return self.args[key]
        if key in (self.form or {}):
            return self.form[key]
        return default

    # ── body ──────────────────────────────────────────────
    def _parse_body(self):
        if self._parsed_body:
            return
        self._parsed_body = True
        ct = self.content_type
        if 'application/x-www-form-urlencoded' in ct and self._body:
            params = parse_qs(self._body.decode('utf-8', errors='replace'), keep_blank_values=True)
            self._form = {k: v[0] if len(v) == 1 else v for k, v in params.items()}
        elif 'application/json' in ct and self._body:
            try:
                self._json_data = json.loads(self._body)
                self._form = {}
            except Exception:
                self._form = {}
        else:
            self._form = {}

    @property
    def form(self) -> Dict:
        self._parse_body()
        return self._form or {}

    @property
    def json(self):
        self._parse_body()
        if self._json_data is None and self._body:
            try:
                self._json_data = json.loads(self._body)
            except Exception:
                pass
        return self._json_data

    @property
    def data(self) -> bytes:
        return self._body

    @property
    def text(self) -> str:
        return self._body.decode('utf-8', errors='replace')

    @property
    def content_type(self) -> str:
        return self.headers.get('content-type', '')

    @property
    def content_length(self) -> int:
        try:
            return int(self.headers.get('content-length', 0))
        except (ValueError, TypeError):
            return 0

    # ── cookies ───────────────────────────────────────────
    @property
    def cookies(self) -> Dict:
        if self._cookies is None:
            self._cookies = {}
            raw = self.headers.get('cookie', '')
            for part in raw.split(';'):
                part = part.strip()
                if '=' in part:
                    k, _, v = part.partition('=')
                    self._cookies[k.strip()] = v.strip()
        return self._cookies

    # ── IP e info do cliente ──────────────────────────────
    @property
    def ip(self) -> str:
        xff = self.headers.get('x-forwarded-for', '')
        if xff:
            return xff.split(',')[0].strip()
        real = self.headers.get('x-real-ip', '')
        if real:
            return real.strip()
        cf = self.headers.get('cf-connecting-ip', '')
        if cf:
            return cf.strip()
        client = self._scope.get('client')
        return client[0] if client else 'unknown'

    @property
    def remote_addr(self) -> str:
        return self.ip

    @property
    def host(self) -> str:
        return self.headers.get('host', 'localhost')

    @property
    def url(self) -> str:
        scheme = 'https' if self.is_secure else 'http'
        return f'{scheme}://{self.host}{self.full_path}'

    @property
    def base_url(self) -> str:
        scheme = 'https' if self.is_secure else 'http'
        return f'{scheme}://{self.host}{self.path}'

    @property
    def is_ajax(self) -> bool:
        return (self.headers.get('x-requested-with') == 'XMLHttpRequest' or
                'application/json' in self.headers.get('accept', ''))

    @property
    def is_secure(self) -> bool:
        return (self.headers.get('x-forwarded-proto') == 'https' or
                self._scope.get('scheme') == 'https')

    @property
    def is_json(self) -> bool:
        return 'application/json' in self.content_type

    @property
    def user_agent(self) -> str:
        return self.headers.get('user-agent', '')

    @property
    def referer(self) -> str:
        return self.headers.get('referer', '')

    @property
    def accept_languages(self) -> list:
        raw = self.headers.get('accept-language', '')
        return [p.split(';')[0].strip() for p in raw.split(',') if p.strip()]

    @property
    def language(self) -> str:
        langs = self.accept_languages
        return langs[0] if langs else 'en'

    def __repr__(self):
        return f'<Request {self.method} {self.path} ip={self.ip}>'


# ─────────────────────────────────────────────────────────────────
# WebSocket
# ─────────────────────────────────────────────────────────────────

class WebSocket:
    """
    WebSocket para rotas ASGI.

    Uso:
        @app.websocket('/ws/chat')
        async def chat(ws):
            while True:
                msg = await ws.receive()
                if msg is None: break
                await ws.send(f'echo: {msg}')

        # JSON helpers:
        data = await ws.receive_json()
        await ws.send_json({'status': 'ok'})
    """

    def __init__(self, scope: Dict, receive: Callable, send: Callable):
        self._scope   = scope
        self._receive = receive
        self._send    = send
        self._closed  = False
        self.path     = scope['path']
        self.headers  = {k.decode(): v.decode() for k, v in scope.get('headers', [])}
        self.query    = scope.get('query_string', b'').decode()

    async def accept(self, subprotocol: str = None):
        msg: Dict = {'type': 'websocket.accept'}
        if subprotocol:
            msg['subprotocol'] = subprotocol
        await self._send(msg)

    async def receive(self) -> Optional[str]:
        """Recebe mensagem de texto. Retorna None se conexao fechada."""
        while True:
            event = await self._receive()
            if event['type'] == 'websocket.receive':
                text  = event.get('text')
                bdata = event.get('bytes', b'')
                msg   = text if text is not None else bdata.decode('utf-8', errors='replace')
                # Limite de tamanho
                import os as _os
                max_size = int(_os.getenv('WS_MAX_MESSAGE_SIZE', 1024 * 1024))
                if len(msg.encode()) > max_size:
                    await self.close(1009)  # 1009 = Message Too Big
                    return None
                return msg
            if event['type'] == 'websocket.disconnect':
                self._closed = True
                return None

    async def receive_bytes(self) -> Optional[bytes]:
        while True:
            event = await self._receive()
            if event['type'] == 'websocket.receive':
                return event.get('bytes') or event.get('text', '').encode()
            if event['type'] == 'websocket.disconnect':
                self._closed = True
                return None

    async def receive_json(self) -> Optional[Any]:
        msg = await self.receive()
        return json.loads(msg) if msg else None

    async def send(self, data):
        if isinstance(data, bytes):
            await self._send({'type': 'websocket.send', 'bytes': data})
        else:
            await self._send({'type': 'websocket.send', 'text': str(data)})

    async def send_json(self, data: Any):
        await self.send(json.dumps(data, ensure_ascii=False))

    async def close(self, code: int = 1000):
        self._closed = True
        await self._send({'type': 'websocket.close', 'code': code})

    @property
    def closed(self) -> bool:
        return self._closed


def _make_mw_wrapper(middleware: Callable, next_handler: Callable) -> Callable:
    """Cria wrapper de middleware sem closure bug (captura por valor)."""
    async def wrapper(*args, **kwargs):
        return await _call(middleware, next_handler, *args, **kwargs)
    return wrapper


# ─────────────────────────────────────────────────────────────────
# ASGI Application
# ─────────────────────────────────────────────────────────────────

class _AsgiApp:
    """Interface ASGI — compativel com uvicorn, hypercorn, daphne"""

    def __init__(self, pycore):
        self._app = pycore

    async def __call__(self, scope: Dict, receive: Callable, send: Callable):
        t = scope['type']
        if t == 'http':
            await self._http(scope, receive, send)
        elif t == 'websocket':
            await self._ws(scope, receive, send)
        elif t == 'lifespan':
            await self._lifespan(scope, receive, send)

    async def _http(self, scope, receive, send):
        app     = self._app
        method  = scope['method']
        path    = scope['path']
        query   = scope.get('query_string', b'').decode()
        headers = {k.decode(): v.decode() for k, v in scope.get('headers', [])}

        # Ler body completo
        body = b''
        while True:
            event = await receive()
            body += event.get('body', b'')
            if not event.get('more_body', False):
                break

        # Arquivos estaticos
        if await self._static(app, path, send):
            return

        request  = _AsgiRequest(method, path, query, headers, body, scope)
        response = Response()

        handler, kwargs = app.router.match(path, method)

        if handler is None:
            await self._error(app, request, response, send, 404,
                              'Pagina nao encontrada')
            return

        try:
            # Middlewares — cada um recebe (next_handler, req, res, **kw)
            if app._middlewares:
                fn = handler
                for mw in reversed(app._middlewares):
                    fn = _make_mw_wrapper(mw, fn)
                result = await _call(fn, request, response, **kwargs)
            else:
                result = await _call(handler, request, response, **kwargs)

            if isinstance(result, str):
                response.html(result)
            elif isinstance(result, dict):
                response.json(result)
        except Exception as e:
            await self._error(app, request, response, send, 500, str(e))
            return

        await self._send(send, response)

    async def _ws(self, scope, receive, send):
        app = self._app
        path = scope['path']
        handler, kwargs = app.router.match(path, 'WS')

        if handler is None:
            await send({'type': 'websocket.close', 'code': 4004})
            return

        ws = WebSocket(scope, receive, send)
        await ws.accept()
        try:
            await _call(handler, ws, **kwargs)
        except Exception:
            pass
        finally:
            if not ws._closed:
                await ws.close()

    async def _lifespan(self, scope, receive, send):
        app = self._app
        while True:
            event = await receive()
            if event['type'] == 'lifespan.startup':
                for fn in app._on_startup:
                    await _call(fn)
                await send({'type': 'lifespan.startup.complete'})
            elif event['type'] == 'lifespan.shutdown':
                for fn in app._on_shutdown:
                    await _call(fn)
                await send({'type': 'lifespan.shutdown.complete'})
                return

    async def _static(self, app, path: str, send) -> bool:
        if not path.startswith('/static/'):
            return False
        full = Path(app.router.static_folder) / unquote(path[8:])
        if not (full.exists() and full.is_file()):
            return False
        mime, _ = mimetypes.guess_type(str(full))
        data = full.read_bytes()
        await send({
            'type': 'http.response.start', 'status': 200,
            'headers': [
                [b'content-type', (mime or 'application/octet-stream').encode()],
                [b'content-length', str(len(data)).encode()],
                [b'cache-control', b'public, max-age=3600'],
            ],
        })
        await send({'type': 'http.response.body', 'body': data})
        return True

    async def _error(self, app, request, response, send, code, message):
        h = app.router.get_error_handler(code)
        if h:
            try:
                result = await _call(h, request, response, message)
                if isinstance(result, str):
                    response.html(result)
                response.status_code = code
                await self._send(send, response)
                return
            except Exception:
                pass
        response.status_code = code
        response.html(_error_html(code, message))
        await self._send(send, response)

    async def _send(self, send, response: Response):
        body = response.body or b''
        if isinstance(body, str):
            body = body.encode('utf-8')
        elif not isinstance(body, bytes):
            body = str(body).encode('utf-8')

        raw_headers = []
        for k, v in response.headers.items():
            raw_headers.append([k.lower().encode(), v.encode()])

        has_ct = any(h[0] == b'content-type' for h in raw_headers)
        if not has_ct:
            raw_headers.append([b'content-type', b'text/html; charset=utf-8'])

        await send({
            'type': 'http.response.start',
            'status': response.status_code,
            'headers': raw_headers,
        })
        await send({'type': 'http.response.body', 'body': body})


# ─────────────────────────────────────────────────────────────────
# Velox — app principal
# ─────────────────────────────────────────────────────────────────

class Velox:
    """
    Velox - Fast Python Web Framework.

    Modos:
        app.run()            -> WSGI threading (sem deps)
        app.run(asgi=True)   -> ASGI uvicorn  (pip install uvicorn)
        uvicorn meuapp:app   -> ASGI diretamente pelo CLI

    Exemplos rapidos:

        app = Velox(__name__)

        @app.get('/')
        def home(req, res):
            return app.render('index.html', {'nome': 'Mundo'})

        @app.get('/api')
        async def api(req, res):
            data = await meu_servico()
            res.json(data)

        @app.websocket('/ws')
        async def ws(ws):
            while True:
                msg = await ws.receive()
                if not msg: break
                await ws.send(f'echo: {msg}')

        @app.on_startup
        async def init():
            await db.connect()

        app.run()           # WSGI
        app.run(asgi=True)  # ASGI
    """

    def __init__(self, import_name: str = None):
        self.name              = import_name or __name__
        self.router            = Router()
        self._middlewares:     List[Callable] = []
        self._on_startup:      List[Callable] = []
        self._on_shutdown:     List[Callable] = []
        self._template_engine: Optional[TemplateEngine] = None
        self._template_folder  = 'templates'
        self._asgi_app         = _AsgiApp(self)

    # ── ASGI interface (para uvicorn) ─────────────
    async def __call__(self, scope: Dict, receive: Callable, send: Callable):
        """Interface ASGI — uso: uvicorn meuapp:app"""
        await self._asgi_app(scope, receive, send)

    # ── Middlewares ───────────────────────────────
    def use(self, fn: Callable):
        """
        Adiciona middleware global (sync ou async).

            @app.use
            async def cors(next_handler, req, res, **kw):
                res.set_header('Access-Control-Allow-Origin', '*')
                return await next_handler(req, res, **kw)
        """
        self._middlewares.append(fn)
        return fn

    # ── Blueprints ────────────────────────────────
    def include(self, router: Router, prefix: str = ''):
        """Inclui um Blueprint/Router com prefixo"""
        p = prefix.rstrip('/')
        for method, pattern, handler in router._routes:
            full = p + pattern.raw
            self.router.add_route(full, method, handler)
        self.router._error_handlers.update(router._error_handlers)

    # ── Lifecycle ─────────────────────────────────
    def on_startup(self, fn: Callable):
        """Executado ao iniciar (apenas ASGI)"""
        self._on_startup.append(fn)
        return fn

    def on_shutdown(self, fn: Callable):
        """Executado ao parar (apenas ASGI)"""
        self._on_shutdown.append(fn)
        return fn

    # ── Rotas ─────────────────────────────────────
    def route(self, path: str, methods: List[str] = None):
        return self.router.route(path, methods)

    def get(self, path: str):
        return self.router.get(path)

    def post(self, path: str):
        return self.router.post(path)

    def put(self, path: str):
        return self.router.put(path)

    def delete(self, path: str):
        return self.router.delete(path)

    def patch(self, path: str):
        return self.router.patch(path)

    def websocket(self, path: str):
        """Rota WebSocket (apenas ASGI). Handler recebe ws: WebSocket"""
        return self.router.websocket(path)

    def resource(self, path: str):
        """Define múltiplos métodos HTTP para uma rota usando uma classe"""
        return self.router.resource(path)

    # ── Error handlers ────────────────────────────
    def error_handler(self, code: int):
        def d(fn):
            self.router.add_error_handler(code, fn)
            return fn
        return d

    def not_found(self, fn: Callable):
        return self.error_handler(404)(fn)

    def server_error(self, fn: Callable):
        return self.error_handler(500)(fn)

    # ── Templates & Static ────────────────────────
    def static(self, folder: str = 'static'):
        self.router.static_folder = folder

    def template(self, folder: str = 'templates'):
        self._template_folder = folder
        self._template_engine = None

    def render(self, template_name: str, context: Dict = None) -> str:
        if self._template_engine is None:
            self._template_engine = TemplateEngine(self._template_folder)
        return self._template_engine.render(template_name, context or {})

    # ── Utilitarios ───────────────────────────────
    def routes(self) -> List[Dict]:
        """Lista todas as rotas registradas"""
        return self.router.list_routes()

    def __repr__(self):
        n = len(self.router._routes)
        return f'<Velox {self.name} — {n} rota{"s" if n != 1 else ""}>'

    # ── Servidor ──────────────────────────────────
    def run(self, host: str = None, port: int = None,
            debug: bool = None, asgi: bool = False,
            workers: int = 1, reload: bool = False):
        """
        Inicia o servidor.

        Args:
            host    : Host. Padrao: APP_HOST do .env ou 'localhost'
            port    : Porta. Padrao: APP_PORT do .env ou 8000
            debug   : Modo debug. Padrao: APP_DEBUG do .env
            asgi    : True para uvicorn/ASGI  (requer: pip install uvicorn)
                      False para WSGI/threading (sem deps)
            workers : Numero de workers ASGI (default: 1)
            reload  : Auto-reload em mudancas de arquivo (dev ASGI)
        """
        host  = host  or os.environ.get('APP_HOST', 'localhost')
        port  = int(port or os.environ.get('APP_PORT', 8000))
        if debug is None:
            debug = os.environ.get('APP_DEBUG', 'false').lower() == 'true'

        if asgi:
            self._run_asgi(host, port, debug, workers, reload)
        else:
            self._run_wsgi(host, port, debug)

    def _run_wsgi(self, host: str, port: int, debug: bool):
        _SyncHandler.app = self
        server = _ThreadingServer((host, port), _SyncHandler)

        print(f'\033[92m\u2713\033[0m  Velox \033[90m[WSGI/threading]\033[0m  '
              f'\033[96mhttp://{host}:{port}\033[0m')
        if debug:
            print(f'\033[93m\u26a0\033[0m  Debug ativo')
        print(f'  \033[90mCtrl+C para parar\033[0m\n')

        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print('\n\033[90mServidor parado.\033[0m')
            server.shutdown()

    def _run_asgi(self, host: str, port: int, debug: bool,
                  workers: int, reload: bool):
        try:
            import uvicorn
        except ImportError:
            print('\033[91m\u2717\033[0m  uvicorn nao instalado.')
            print('  \033[96mpip install uvicorn\033[0m')
            raise SystemExit(1)

        print(f'\033[92m\u2713\033[0m  Velox \033[90m[ASGI/uvicorn]\033[0m  '
              f'\033[96mhttp://{host}:{port}\033[0m')
        if debug:
            print(f'\033[93m\u26a0\033[0m  Debug ativo')
        print(f'  \033[90mCtrl+C para parar\033[0m\n')

        uvicorn.run(
            self,
            host=host,
            port=port,
            log_level='debug' if debug else 'info',
            workers=workers if not reload else 1,
            reload=reload,
        )


# ─────────────────────────────────────────────────────────────────
# App Discovery — Sistema de Apps Modulares
# ─────────────────────────────────────────────────────────────────

    def load_apps(self, app_names: List[str] = None):
        """
        Carrega apps modulares (criados com velox startapp).
        
        Uso:
            app = Velox(__name__)
            app.load_apps(['blog', 'api', 'usuarios'])
        
        O sistema procura por:
            - {app}/views.py  -> Registra routers/blueprints
            - {app}/admin.py  -> Registra no painel admin
            - {app}/models.py -> Importa models
        
        Args:
            app_names: Lista de nomes de apps. Se None, autodiscover todos.
        """
        if app_names is None:
            # Autodiscovery: procura todas as pastas com apps.py
            app_names = self._discover_apps()
        
        for app_name in app_names:
            self._load_app(app_name)
        
        print(f'\033[92m✓\033[0m  {len(app_names)} app(s) carregado(s)')
    
    def _discover_apps(self) -> List[str]:
        """Descobre apps automaticamente no diretório atual"""
        apps = []
        for item in Path('.').iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                apps_py = item / 'apps.py'
                if apps_py.exists():
                    apps.append(item.name)
        return apps
    
    def _load_app(self, app_name: str):
        """Carrega um app individual"""
        try:
            # Importar o app
            import importlib
            app_module = importlib.import_module(app_name)
            
            # 1. Carregar views (router/blueprint)
            try:
                views_module = importlib.import_module(f'{app_name}.views')
                if hasattr(views_module, 'router'):
                    router = views_module.router
                    self.include(router)
                    print(f'  \033[90m  → {app_name}/views.py (rotas)\033[0m')
            except ImportError:
                pass
            
            # 2. Carregar admin
            try:
                admin_module = importlib.import_module(f'{app_name}.admin')
                # Admin é carregado via site.register_routes(app) no app.py principal
            except ImportError:
                pass
            
            # 3. Carregar models (para migrations)
            try:
                models_module = importlib.import_module(f'{app_name}.models')
                print(f'  \033[90m  → {app_name}/models.py\033[0m')
            except ImportError:
                pass
            
            # 4. Executar ready() se existir
            try:
                apps_module = importlib.import_module(f'{app_name}.apps')
                if hasattr(apps_module, 'ready'):
                    ready_fn = apps_module.ready
                    if callable(ready_fn):
                        ready_fn(self)
                elif hasattr(apps_module, 'AppConfig'):
                    config = apps_module.AppConfig
                    if hasattr(config, 'get_urls'):
                        urls = config.get_urls()
                        print(f'  \033[90m  → {app_name}/apps.py (config)\033[0m')
            except ImportError:
                pass
            
            print(f'  \033[92m✓\033[0m  App \033[96m{app_name}\033[0m carregado')
            
        except Exception as e:
            print(f'  \033[91m✗\033[0m  Erro ao carregar app {app_name}: {e}')


# ─────────────────────────────────────────────────────────────────
# Alias (compatibilidade)
# ─────────────────────────────────────────────────────────────────

MeuFramework = Velox

def create_app() -> Velox:
    return Velox()
