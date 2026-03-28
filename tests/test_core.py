"""Testes básicos do Velox Framework"""

import os
import sys
import tempfile
import pathlib

# Adicionar o diretório do projeto ao path (necessário para execução manual)
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Imports do Velox
from velox import Velox, Router
from velox.template import TemplateEngine
from velox.database import _safe_col, AsyncDatabase, AsyncModel
from velox.csrf import _tokens_match, _generate_token
from velox.testing import _encode_multipart, VeloxTestClient
from velox.config import Config
from velox.cache import Cache
from velox.session import SessionManager
from velox.validators import EmailValidator, MinLengthValidator, RegexValidator, ValidationError
from velox.paginator import Paginator
from velox.exceptions import (
    VeloxException, HTTPException, NotFoundError,
    ForbiddenError, UnauthorizedError, BadRequestError
)
from velox.middleware import (
    Middleware, CORSMiddleware, LoggingMiddleware,
    RateLimitMiddleware, cors
)
from velox.forms import CharField, EmailField
from velox.websocket import WebSocketMessage
from velox.serializers import to_json, from_json


def test_app_creation():
    app = Velox(__name__)
    assert app is not None


def test_route_registration():
    app = Velox(__name__)

    @app.get('/test')
    def handler(req, res):
        res.json({'ok': True})

    routes = app.routes()
    assert any(r['path'] == '/test' for r in routes)


def test_router_prefix():
    router = Router(prefix='/api')

    @router.get('/users')
    def users(req, res):
        pass

    assert router._routes[0][1].raw == '/api/users'


def test_template_escape(monkeypatch):
    """Testa escape XSS - usa monkeypatch para isolar alteração de env"""
    monkeypatch.setenv('TEMPLATE_CACHE', 'false')
    with tempfile.TemporaryDirectory() as tmp:
        p = pathlib.Path(tmp) / 'test.html'
        p.write_text('{{ name }}')
        engine = TemplateEngine(tmp)
        result = engine.render('test.html', {'name': '<script>alert(1)</script>'})
        assert '<script>' not in result
        assert "&lt;script&gt;" in result


def test_template_safe_filter(monkeypatch):
    """Testa filtro safe - usa monkeypatch para isolar alteração de env"""
    monkeypatch.setenv('TEMPLATE_CACHE', 'false')
    with tempfile.TemporaryDirectory() as tmp:
        p = pathlib.Path(tmp) / 'test.html'
        p.write_text('{{ html|safe }}')
        engine = TemplateEngine(tmp)
        result = engine.render('test.html', {'html': '<b>bold</b>'})
        assert '<b>bold</b>' in result


def test_database_safe_col():
    assert _safe_col('username') == 'username'
    assert _safe_col('user_id') == 'user_id'

    try:
        _safe_col('user; DROP TABLE users--')
        assert False, "Should have raised"
    except ValueError:
        pass


def test_csrf_tokens_match():
    t = _generate_token()
    assert _tokens_match(t, t)
    assert not _tokens_match(t, 'wrong')
    assert not _tokens_match('', t)


def test_multipart_encoding():
    body, ct = _encode_multipart(
        fields={'nome': 'João'},
        files={'arquivo': ('test.txt', b'conteudo do arquivo', 'text/plain')}
    )
    assert b'Content-Disposition: form-data' in body
    assert b'conteudo do arquivo' in body
    assert b'Jo' in body
    assert 'multipart/form-data; boundary=' in ct


def test_test_client_post_files():
    app = Velox(__name__)

    @app.post('/upload')
    def upload(req, res):
        ct = req.content_type
        res.json({'content_type': ct, 'ok': 'multipart' in ct})

    client = VeloxTestClient(app)
    response = client.post('/upload', files={'file': ('a.txt', b'hello', 'text/plain')})
    assert response.status_code == 200
    assert response.json['ok'] is True


def test_async_database_class_exists():
    assert AsyncDatabase is not None
    assert AsyncModel is not None
    db = AsyncDatabase('db/test_async.db')
    assert db.driver == 'sqlite'


def test_config_from_env(monkeypatch):
    """Testa Config.from_env - usa monkeypatch para isolar alterações"""
    # Salvar originais
    orig_host = os.environ.get('APP_HOST')
    orig_port = os.environ.get('APP_PORT')
    orig_secret = os.environ.get('VELOX_SECRET_KEY')

    try:
        monkeypatch.setenv('APP_HOST', '0.0.0.0')
        monkeypatch.setenv('APP_PORT', '9000')
        monkeypatch.setenv('VELOX_SECRET_KEY', 'test-key-123')

        # Resetar valores padrão
        Config.HOST = 'localhost'
        Config.PORT = 8000
        Config.SECRET_KEY = 'default'

        Config.from_env()

        assert Config.HOST == '0.0.0.0'
        assert Config.PORT == 9000
        assert Config.SECRET_KEY == 'test-key-123'
    finally:
        # Restaurar originais
        if orig_host:
            monkeypatch.setenv('APP_HOST', orig_host)
        else:
            monkeypatch.delenv('APP_HOST', raising=False)
        if orig_port:
            monkeypatch.setenv('APP_PORT', orig_port)
        else:
            monkeypatch.delenv('APP_PORT', raising=False)
        if orig_secret:
            monkeypatch.setenv('VELOX_SECRET_KEY', orig_secret)
        else:
            monkeypatch.delenv('VELOX_SECRET_KEY', raising=False)


def test_cache_memory():
    cache = Cache(prefix='test')
    cache.set('key1', 'value1', timeout=60)
    assert cache.get('key1') == 'value1'
    assert cache.has('key1') is True
    cache.delete('key1')
    assert cache.get('key1') is None


def test_session_manager():
    sm = SessionManager(secret_key='test-secret')
    assert sm is not None


def test_validators():
    # EmailValidator
    email_val = EmailValidator()
    try:
        email_val('test@example.com')
        assert True
    except ValidationError:
        assert False, "Deveria ser válido"

    try:
        email_val('invalid')
        assert False, "Deveria falhar"
    except ValidationError:
        pass

    # MinLengthValidator
    min_len = MinLengthValidator(3)
    try:
        min_len('abc')
    except ValidationError:
        assert False

    try:
        min_len('ab')
        assert False
    except ValidationError:
        pass

    # RegexValidator
    regex = RegexValidator(r'^\d{3}-\d{4}$')
    try:
        regex('123-4567')
    except ValidationError:
        assert False

    try:
        regex('abc-defg')
        assert False
    except ValidationError:
        pass


def test_paginator():
    items = list(range(1, 101))
    paginator = Paginator(items, per_page=10)

    assert paginator.num_pages == 10
    page = paginator.page(1)
    assert len(page.object_list) == 10
    assert page.has_next is True
    assert page.has_previous is False


def test_exceptions():
    assert issubclass(NotFoundError, HTTPException)
    assert issubclass(HTTPException, VeloxException)

    e = NotFoundError('Page not found')
    assert e.status_code == 404
    assert str(e) == 'Page not found'


def test_middleware_imports():
    assert Middleware is not None
    assert CORSMiddleware is not None
    assert LoggingMiddleware is not None


def test_forms_basic():
    nome_field = CharField(min_length=2)
    assert nome_field.clean('João') == 'João'

    email_field = EmailField()
    assert email_field.clean('test@example.com') == 'test@example.com'

    try:
        nome_field.clean('A')
        assert False, "Deveria falhar"
    except Exception:
        pass


def test_websocket_message():
    msg = WebSocketMessage('text', 'Hello', sender='user1', room='room1')
    data = msg.to_dict()

    assert data['type'] == 'text'
    assert data['data'] == 'Hello'
    assert data['sender'] == 'user1'
    assert data['room'] == 'room1'


def test_serializer():
    data = {'name': 'Test', 'value': 123}
    json_str = to_json(data)
    assert '"name": "Test"' in json_str

    parsed = from_json(json_str)
    assert parsed['name'] == 'Test'
    assert parsed['value'] == 123