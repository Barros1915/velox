"""
Proteção CSRF para Velox
=========================

Implementa proteção contra Cross-Site Request Forgery (CSRF)
usando o padrão Double Submit Cookie + Hidden Field.

Como funciona:
    1. No GET, um token único é gerado e salvo na sessão
    2. O token é enviado ao template via contexto
    3. O formulário inclui o token em um campo hidden
    4. No POST, o middleware valida que o token do form == token da sessão
    5. Se inválido, retorna 403 Forbidden

Uso básico:
    from pycore.csrf import csrf_protect, csrf_token, CSRFMiddleware

    # Opção 1 — Middleware global (protege todas as rotas POST/PUT/DELETE/PATCH)
    app.use(CSRFMiddleware())

    # Opção 2 — Decorador por rota
    @app.post('/contato')
    @csrf_protect
    def contato_post(req, res):
        ...

    # Gerar token para o template
    @app.get('/contato')
    def contato_get(req, res):
        return app.render('contato.html', {
            'csrf_token': csrf_token(req)
        })

No template HTML:
    <form method="POST" action="/contato">
        <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
        ...
    </form>

Rotas excluídas (padrão):
    - /api/*       → APIs JSON geralmente usam Authorization header
    - /auth/*/callback → callbacks OAuth
    Personalizável via CSRFMiddleware(exempt=['/minha-rota'])

Configuração via .env:
    CSRF_TOKEN_LENGTH=32     # Tamanho do token em bytes (padrão: 32)
    CSRF_SESSION_KEY=_csrf   # Chave do token na sessão (padrão: _csrf)
    CSRF_FIELD_NAME=csrf_token  # Nome do campo no form (padrão: csrf_token)
    CSRF_HEADER_NAME=X-CSRF-Token  # Header para APIs (padrão: X-CSRF-Token)
    CSRF_COOKIE_NAME=csrf_token    # Nome do cookie (padrão: csrf_token)
    CSRF_COOKIE_SECURE=false       # Cookie só em HTTPS (padrão: false)
    CSRF_COOKIE_SAMESITE=Lax       # SameSite do cookie (padrão: Lax)
"""

import secrets
import os
import hmac
import hashlib
from functools import wraps
from typing import Optional, List, Callable


# ─────────────────────────────────────────
# Configurações
# ─────────────────────────────────────────

CSRF_TOKEN_LENGTH  = int(os.getenv('CSRF_TOKEN_LENGTH', 32))
CSRF_SESSION_KEY   = os.getenv('CSRF_SESSION_KEY',   '_csrf')
CSRF_FIELD_NAME    = os.getenv('CSRF_FIELD_NAME',    'csrf_token')
CSRF_HEADER_NAME   = os.getenv('CSRF_HEADER_NAME',   'X-CSRF-Token')
CSRF_COOKIE_NAME   = os.getenv('CSRF_COOKIE_NAME',   'csrf_token')
CSRF_COOKIE_SECURE = os.getenv('CSRF_COOKIE_SECURE', 'false').lower() == 'true'
CSRF_COOKIE_SAMESITE = os.getenv('CSRF_COOKIE_SAMESITE', 'Lax')

# Métodos que requerem validação CSRF
CSRF_PROTECTED_METHODS = {'POST', 'PUT', 'DELETE', 'PATCH'}

# Rotas excluídas por padrão
DEFAULT_EXEMPT_PATTERNS = [
    '/api/',
    '/auth/',
]


# ─────────────────────────────────────────
# Geração e validação de tokens
# ─────────────────────────────────────────

def _generate_token() -> str:
    """Gera um token CSRF criptograficamente seguro"""
    return secrets.token_urlsafe(CSRF_TOKEN_LENGTH)


def _tokens_match(token_a: str, token_b: str) -> bool:
    """
    Compara tokens de forma segura contra timing attacks.
    Usa hmac.compare_digest para evitar ataques de tempo.
    """
    if not token_a or not token_b:
        return False
    return hmac.compare_digest(
        token_a.encode('utf-8'),
        token_b.encode('utf-8')
    )


def _get_session_token(request) -> Optional[str]:
    """Recupera o token CSRF da sessão ou cookie"""
    # Tenta da sessão primeiro
    if hasattr(request, 'session') and request.session:
        token = request.session.get(CSRF_SESSION_KEY)
        if token:
            return token

    # Fallback: cookie
    if hasattr(request, 'cookies') and request.cookies:
        return request.cookies.get(CSRF_COOKIE_NAME)

    return None


def _set_session_token(request, token: str):
    """Salva o token CSRF na sessão"""
    if hasattr(request, 'session') and request.session is not None:
        request.session[CSRF_SESSION_KEY] = token
    # Também salva no atributo do request para uso imediato
    request._csrf_token = token


def _get_submitted_token(request) -> Optional[str]:
    """
    Extrai o token CSRF enviado pelo cliente.
    Verifica nesta ordem:
    1. Header X-CSRF-Token (APIs JavaScript)
    2. Campo csrf_token no form (formulários HTML)
    3. Campo csrf_token no body JSON
    """
    # 1. Header (fetch/axios/ajax)
    if hasattr(request, 'headers') and request.headers:
        header_token = request.headers.get(CSRF_HEADER_NAME)
        if header_token:
            return header_token

    # 2. Form data
    if hasattr(request, 'form') and request.form:
        form_token = request.form.get(CSRF_FIELD_NAME)
        if form_token:
            return form_token

    # 3. JSON body
    if hasattr(request, 'json') and request.json:
        json_token = request.json.get(CSRF_FIELD_NAME)
        if json_token:
            return json_token

    return None


def _is_exempt(path: str, exempt_patterns: List[str]) -> bool:
    """Verifica se a rota está na lista de exclusões"""
    for pattern in exempt_patterns:
        if path.startswith(pattern) or path == pattern:
            return True
    return False


# ─────────────────────────────────────────
# API pública
# ─────────────────────────────────────────

def csrf_token(request) -> str:
    """
    Retorna o token CSRF para o request atual.
    Gera um novo token se ainda não existir.

    Uso no controlador:
        @app.get('/contato')
        def contato(req, res):
            return app.render('contato.html', {
                'csrf_token': csrf_token(req)
            })

    Uso no template:
        <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
    """
    # Verifica se já existe token no request
    token = getattr(request, '_csrf_token', None)
    if token:
        return token

    # Verifica se existe na sessão/cookie
    token = _get_session_token(request)
    if token:
        request._csrf_token = token
        return token

    # Gera novo token
    token = _generate_token()
    _set_session_token(request, token)
    return token


def validate_csrf(request) -> bool:
    """
    Valida o token CSRF manualmente.
    Retorna True se válido, False se inválido.

    Uso:
        if not validate_csrf(req):
            res.status_code = 403
            res.json({'error': 'Token CSRF inválido'})
            return res
    """
    session_token    = _get_session_token(request)
    submitted_token  = _get_submitted_token(request)
    return _tokens_match(session_token, submitted_token)


def rotate_token(request) -> str:
    """
    Gera um novo token CSRF e invalida o anterior.
    Recomendado após login para evitar session fixation.

    Uso:
        @app.post('/login')
        def login_post(req, res):
            user = authenticate(req.form.get('username'), req.form.get('password'))
            if user:
                session_key = login(req, user)
                new_token   = rotate_token(req)  # invalida token antigo
                res.set_cookie('session_key', session_key)
                res.set_cookie(CSRF_COOKIE_NAME, new_token)
            ...
    """
    token = _generate_token()
    _set_session_token(request, token)
    return token


# ─────────────────────────────────────────
# Decorador @csrf_protect
# ─────────────────────────────────────────

def csrf_protect(func):
    """
    Decorador que valida o token CSRF antes de executar a rota.
    Retorna 403 se o token for inválido ou ausente.

    Uso:
        @app.post('/contato')
        @csrf_protect
        def contato_post(req, res):
            data = req.form
            ...
    """
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        if request.method in CSRF_PROTECTED_METHODS:
            if not validate_csrf(request):
                from .response import Response
                response = Response()
                response.status_code = 403
                response.json({
                    'error':   'CSRF token inválido ou ausente',
                    'message': 'Inclua o token CSRF no campo "csrf_token" do formulário ou no header "X-CSRF-Token"'
                })
                return response

        return func(request, *args, **kwargs)
    return wrapper


def csrf_exempt(func):
    """
    Marca uma rota como excluída da proteção CSRF.
    Útil para webhooks ou endpoints de API externa.

    Uso:
        @app.post('/webhook/pagamento')
        @csrf_exempt
        def webhook(req, res):
            ...
    """
    func._csrf_exempt = True
    return func


# ─────────────────────────────────────────
# Middleware global
# ─────────────────────────────────────────

class CSRFMiddleware:
    """
    Middleware que protege automaticamente todas as rotas
    POST/PUT/DELETE/PATCH contra ataques CSRF.

    Uso:
        from pycore.csrf import CSRFMiddleware
        app.use(CSRFMiddleware())

    Rotas excluídas por padrão: /api/*, /auth/*
    Personalizável:
        app.use(CSRFMiddleware(
            exempt=['/webhook/', '/api/'],
            cookie=True
        ))
    """

    def __init__(self, exempt: List[str] = None, cookie: bool = True):
        """
        Args:
            exempt: Lista de prefixos de rotas a excluir da proteção
            cookie: Se True, também define o token em um cookie (para SPAs)
        """
        self.exempt_patterns = (exempt or []) + DEFAULT_EXEMPT_PATTERNS
        self.use_cookie      = cookie

    def __call__(self, handler: Callable, request, response, **kwargs):
        """
        Interface de middleware compatível com app.use().
        Bloqueia a request se o token CSRF for inválido.
        Define o cookie CSRF na resposta após execução.
        """
        from .response import Response as _Response

        # Garante que o token existe no request
        token = csrf_token(request)

        method = getattr(request, 'method', 'GET').upper()

        if method in CSRF_PROTECTED_METHODS:
            if not getattr(handler, '_csrf_exempt', False):
                path = getattr(request, 'path', '') or ''
                if not _is_exempt(path, self.exempt_patterns):
                    if not validate_csrf(request):
                        resp = _Response()
                        resp.status_code = 403
                        resp.json({
                            'error':   'CSRF token inválido ou ausente',
                            'message': 'Inclua o token CSRF no formulário ou no header X-CSRF-Token',
                        })
                        # Define cookie mesmo na resposta de erro
                        self._set_csrf_cookie(request, resp)
                        return resp

        result = handler(request, response, **kwargs)
        # Define o cookie CSRF na resposta — DEVE vir antes do return
        self._set_csrf_cookie(request, response)
        return result

    def _set_csrf_cookie(self, request, response):
        """Define o cookie CSRF na resposta se configurado."""
        if not self.use_cookie:
            return
        token   = getattr(request, '_csrf_token', None) or csrf_token(request)
        options = f'SameSite={CSRF_COOKIE_SAMESITE}; Path=/'
        if CSRF_COOKIE_SECURE:
            options += '; Secure'
        try:
            response.set_header('Set-Cookie', f'{CSRF_COOKIE_NAME}={token}; {options}')
        except Exception:
            pass


# ─────────────────────────────────────────
# Helper para templates
# ─────────────────────────────────────────

def csrf_input(request) -> str:
    """
    Retorna o campo hidden HTML com o token CSRF.
    Útil para injetar direto no template sem precisar passar via contexto.

    Uso no template (se o Velox suportar helpers):
        {{ csrf_input() }}

    Retorna:
        <input type="hidden" name="csrf_token" value="TOKEN_AQUI">
    """
    token = csrf_token(request)
    return f'<input type="hidden" name="{CSRF_FIELD_NAME}" value="{token}">'


def get_csrf_headers(request) -> dict:
    """
    Retorna os headers necessários para requisições fetch/axios.

    Uso no JavaScript:
        const headers = await fetch('/csrf-headers').then(r => r.json())
        fetch('/api/dados', { method: 'POST', headers })

    Uso no controlador:
        @app.get('/csrf-headers')
        def csrf_headers_route(req, res):
            res.json(get_csrf_headers(req))
            return res
    """
    token = csrf_token(request)
    return {
        CSRF_HEADER_NAME:   token,
        'Content-Type':     'application/json',
    }
