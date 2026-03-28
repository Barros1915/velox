"""
Request - Velox Framework
Representa uma requisicao HTTP recebida pelo servidor.

Propriedades disponiveis:
    request.method          -> 'GET', 'POST', etc
    request.path            -> '/api/produtos'
    request.ip              -> IP real do cliente
    request.host            -> host da requisicao
    request.headers         -> dict de headers
    request.args            -> query params (?page=1)
    request.form            -> dados de formulario POST
    request.json            -> body JSON
    request.data            -> body raw bytes
    request.files           -> arquivos enviados
    request.cookies         -> cookies da requisicao
    request.is_ajax         -> True se for requisicao XHR
    request.is_secure       -> True se for HTTPS
    request.user_agent      -> user agent do navegador
    request.referer         -> pagina de origem
    request.content_type    -> Content-Type do body
    request.content_length  -> tamanho do body
"""

import json as _json
from urllib.parse import parse_qs, urlparse


class Request:
    """
    Objeto de requisicao HTTP — disponivel em todo handler como primeiro parametro.

    Uso:
        @app.get('/api/info')
        def info(request, response):
            print(request.ip)          # IP do cliente
            print(request.method)      # GET
            print(request.path)        # /api/info
            print(request.args)        # query params
            print(request.form)        # form POST
            print(request.json)        # body JSON
            print(request.cookies)     # cookies
    """

    def __init__(self, handler):
        self._handler       = handler
        self._query_params  = None
        self._form_data     = None
        self._json_data     = None
        self._body_data     = None
        self._cookies_data  = None

    # ── Basicos ───────────────────────────────────────────

    @property
    def method(self) -> str:
        """Metodo HTTP: GET, POST, PUT, DELETE, PATCH"""
        return self._handler.command

    @property
    def path(self) -> str:
        """Caminho da URL sem query string: /api/produto"""
        return self._handler.path.split('?')[0]

    @property
    def full_path(self) -> str:
        """Caminho completo com query string: /api/produto?page=1"""
        return self._handler.path

    @property
    def headers(self) -> dict:
        """Headers da requisicao (case-insensitive)"""
        return self._handler.headers

    # ── IP do cliente ─────────────────────────────────────

    @property
    def ip(self) -> str:
        """
        IP real do cliente.
        Funciona corretamente atras de nginx/proxy/load balancer.

        Uso:
            print(request.ip)   # '177.92.10.45'
        """
        # X-Forwarded-For: ip_cliente, proxy1, proxy2
        xff = (
            self.headers.get('X-Forwarded-For') or
            self.headers.get('x-forwarded-for') or
            ''
        )
        if xff:
            # Pega o primeiro IP da cadeia (cliente real)
            return xff.split(',')[0].strip()

        # X-Real-IP (nginx)
        real_ip = (
            self.headers.get('X-Real-IP') or
            self.headers.get('x-real-ip') or
            ''
        )
        if real_ip:
            return real_ip.strip()

        # CF-Connecting-IP (Cloudflare)
        cf_ip = (
            self.headers.get('CF-Connecting-IP') or
            self.headers.get('cf-connecting-ip') or
            ''
        )
        if cf_ip:
            return cf_ip.strip()

        # IP direto da conexao TCP (sem proxy)
        try:
            return self._handler.client_address[0]
        except Exception:
            return 'desconhecido'

    @property
    def remote_addr(self) -> str:
        """Alias para .ip — compatibilidade com Flask"""
        return self.ip

    # ── Host e URL ────────────────────────────────────────

    @property
    def host(self) -> str:
        """Host da requisicao: 'meusite.com' ou 'localhost:8000'"""
        return (
            self.headers.get('Host') or
            self.headers.get('host') or
            'localhost'
        )

    @property
    def url(self) -> str:
        """URL completa: 'http://meusite.com/api/produto?page=1'"""
        scheme = 'https' if self.is_secure else 'http'
        return f'{scheme}://{self.host}{self.full_path}'

    @property
    def base_url(self) -> str:
        """URL sem query string: 'http://meusite.com/api/produto'"""
        scheme = 'https' if self.is_secure else 'http'
        return f'{scheme}://{self.host}{self.path}'

    # ── Query params ──────────────────────────────────────

    @property
    def args(self) -> dict:
        """
        Parametros da query string (?chave=valor).

        Uso:
            # URL: /buscar?q=notebook&page=2
            q    = request.args.get('q')      # 'notebook'
            page = request.args.get('page', '1')  # '2'
        """
        if self._query_params is None:
            parsed = urlparse(self._handler.path)
            params = parse_qs(parsed.query, keep_blank_values=True)
            self._query_params = {
                k: v[0] if len(v) == 1 else v
                for k, v in params.items()
            }
        return self._query_params

    # Alias
    @property
    def query_params(self) -> dict:
        return self.args

    def get(self, key: str, default=None):
        """Busca valor em args ou form"""
        if key in self.args:
            return self.args[key]
        if key in (self.form or {}):
            return self.form[key]
        return default

    # ── Body ─────────────────────────────────────────────

    @property
    def form(self) -> dict:
        """
        Dados de formulario HTML (application/x-www-form-urlencoded).

        Uso:
            nome  = request.form.get('nome')
            email = request.form.get('email')
        """
        if self._form_data is None:
            self._parse_body()
        return self._form_data or {}

    @property
    def json(self):
        """
        Body da requisicao como dict/list Python (application/json).

        Uso:
            dados = request.json
            nome  = dados.get('nome')
        """
        if self._json_data is None:
            self._parse_body()
        return self._json_data

    @property
    def data(self) -> bytes:
        """Body raw da requisicao em bytes"""
        if self._body_data is None:
            self._parse_body()
        return self._body_data or b''

    @property
    def text(self) -> str:
        """Body da requisicao como string UTF-8"""
        return self.data.decode('utf-8', errors='replace')

    @property
    def content_type(self) -> str:
        """Content-Type do body: 'application/json', 'multipart/form-data', etc"""
        return (
            self.headers.get('Content-Type') or
            self.headers.get('content-type') or
            ''
        )

    @property
    def content_length(self) -> int:
        """Tamanho do body em bytes"""
        try:
            return int(
                self.headers.get('Content-Length') or
                self.headers.get('content-length') or
                0
            )
        except (ValueError, TypeError):
            return 0

    def _parse_body(self):
        """Faz parse do body da requisicao"""
        ct = self.content_type
        try:
            length = self.content_length
            if length > 0:
                raw = self._handler.rfile.read(length)
                self._body_data = raw

                if 'application/json' in ct:
                    try:
                        self._json_data = _json.loads(raw.decode('utf-8'))
                    except Exception:
                        self._json_data = None
                    self._form_data = {}

                elif 'application/x-www-form-urlencoded' in ct:
                    params = parse_qs(raw.decode('utf-8', errors='replace'),
                                      keep_blank_values=True)
                    self._form_data = {
                        k: v[0] if len(v) == 1 else v
                        for k, v in params.items()
                    }
                    self._json_data = None

                elif 'multipart/form-data' in ct:
                    # Formulario com upload de arquivo — parse basico
                    self._form_data = {}
                    self._json_data = None

                else:
                    self._form_data = {}
                    self._json_data = None
            else:
                self._body_data = b''
                self._form_data = {}
                self._json_data = None
        except Exception:
            self._body_data = b''
            self._form_data = {}
            self._json_data = None

    # ── Cookies ───────────────────────────────────────────

    @property
    def cookies(self) -> dict:
        """
        Cookies da requisicao como dict.

        Uso:
            token    = request.cookies.get('token')
            sessao   = request.cookies.get('session_id')
        """
        if self._cookies_data is None:
            self._cookies_data = {}
            raw = (
                self.headers.get('Cookie') or
                self.headers.get('cookie') or
                ''
            )
            for part in raw.split(';'):
                part = part.strip()
                if '=' in part:
                    k, _, v = part.partition('=')
                    self._cookies_data[k.strip()] = v.strip()
        return self._cookies_data

    # ── Informacoes extras ────────────────────────────────

    @property
    def user_agent(self) -> str:
        """User-Agent do navegador/cliente"""
        return (
            self.headers.get('User-Agent') or
            self.headers.get('user-agent') or
            ''
        )

    @property
    def referer(self) -> str:
        """URL da pagina de origem (Referer header)"""
        return (
            self.headers.get('Referer') or
            self.headers.get('referer') or
            ''
        )

    @property
    def is_ajax(self) -> bool:
        """
        True se a requisicao foi feita via JavaScript (fetch/XHR).

        Uso:
            if request.is_ajax:
                response.json({'ok': True})
            else:
                return app.render('pagina.html')
        """
        return (
            self.headers.get('X-Requested-With') == 'XMLHttpRequest' or
            self.headers.get('x-requested-with') == 'XMLHttpRequest' or
            'application/json' in self.headers.get('Accept', '') or
            'application/json' in self.headers.get('accept', '')
        )

    @property
    def is_secure(self) -> bool:
        """True se a requisicao veio via HTTPS"""
        return (
            self.headers.get('X-Forwarded-Proto') == 'https' or
            self.headers.get('x-forwarded-proto') == 'https'
        )

    @property
    def is_json(self) -> bool:
        """True se o Content-Type for application/json"""
        return 'application/json' in self.content_type

    @property
    def accept_languages(self) -> list:
        """Idiomas aceitos pelo cliente: ['pt-BR', 'pt', 'en']"""
        raw = (
            self.headers.get('Accept-Language') or
            self.headers.get('accept-language') or
            ''
        )
        langs = []
        for part in raw.split(','):
            lang = part.split(';')[0].strip()
            if lang:
                langs.append(lang)
        return langs

    @property
    def language(self) -> str:
        """Primeiro idioma aceito pelo cliente: 'pt-BR'"""
        langs = self.accept_languages
        return langs[0] if langs else 'en'

    # ── Representacao ─────────────────────────────────────

    def __repr__(self):
        return f'<Request {self.method} {self.path} ip={self.ip}>'