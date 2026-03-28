"""
Módulo Testing - Cliente de testes para Velox Framework

Fornece VeloxTestClient para simular requisições HTTP sem precisar
subir o servidor, facilitando a criação de testes unitários.

Uso:
    from velox import Velox
    from velox.testing import VeloxTestClient
    
    app = Velox(__name__)
    
    @app.get('/api/users')
    def list_users(req, res):
        return res.json({'users': [{'id': 1, 'name': 'João'}]})
    
    # Teste
    client = VeloxTestClient(app)
    
    response = client.get('/api/users')
    assert response.status_code == 200
    assert response.json['users'][0]['name'] == 'João'
"""

import json as _json
import io as _io
import uuid as _uuid
from typing import Any, Dict, Optional, Union
from urllib.parse import urlparse, parse_qs

from .request import Request
from .response import Response


def _encode_multipart(fields: Dict, files: Dict) -> tuple:
    """
    Codifica dados e arquivos como multipart/form-data.

    files aceita:
        {'campo': b'conteudo'}
        {'campo': ('nome.txt', b'conteudo')}
        {'campo': ('nome.txt', b'conteudo', 'text/plain')}
        {'campo': io.BytesIO(...)}

    Retorna: (body_bytes, content_type_header)
    """
    boundary = _uuid.uuid4().hex
    buf      = _io.BytesIO()

    def write(s: str):
        buf.write(s.encode('utf-8'))

    # Campos de texto
    for name, value in fields.items():
        write(f'--{boundary}\r\n')
        write(f'Content-Disposition: form-data; name="{name}"\r\n\r\n')
        write(str(value))
        write('\r\n')

    # Arquivos
    for name, file_info in files.items():
        if isinstance(file_info, bytes):
            filename     = name
            content      = file_info
            content_type = 'application/octet-stream'
        elif isinstance(file_info, _io.IOBase):
            filename     = name
            content      = file_info.read()
            content_type = 'application/octet-stream'
        elif isinstance(file_info, tuple):
            if len(file_info) == 2:
                filename, content = file_info
                content_type = 'application/octet-stream'
            else:
                filename, content, content_type = file_info
            if isinstance(content, _io.IOBase):
                content = content.read()
        else:
            continue

        write(f'--{boundary}\r\n')
        write(f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n')
        write(f'Content-Type: {content_type}\r\n\r\n')
        buf.write(content if isinstance(content, bytes) else content.encode('utf-8'))
        write('\r\n')

    write(f'--{boundary}--\r\n')
    return buf.getvalue(), f'multipart/form-data; boundary={boundary}'


class TestRequest:
    """
    Request fake para testes — simula um HTTPRequest real.
    """
    
    def __init__(self, method: str, path: str, 
                 headers: Optional[Dict[str, str]] = None,
                 body: Optional[bytes] = None):
        self.command = method.upper()
        self.path = path
        self.headers = headers or {}
        self.rfile = _FakeRFile(body or b'')
        self.client_address = ('127.0.0.1', 8000)
        self._parsed = urlparse(path)
        self._body = body or b''
        self._json_data = None
        self._form_data = None
    
    @property
    def query_string(self) -> str:
        return self._parsed.query
    
    @property
    def json(self):
        """Retorna o body como JSON parseado"""
        if self._json_data is None and self._body:
            try:
                self._json_data = _json.loads(self._body.decode('utf-8'))
            except Exception:
                self._json_data = None
        return self._json_data
    
    @property
    def form(self):
        """Retorna dados do form (se for form-urlencoded)"""
        if self._form_data is None and self._body:
            ct = self.headers.get('Content-Type', '')
            if 'application/x-www-form-urlencoded' in ct:
                parsed = parse_qs(self._body.decode('utf-8', errors='replace'))
                self._form_data = {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}
            else:
                self._form_data = {}
        return self._form_data or {}
    
    @property
    def data(self) -> bytes:
        """Retorna o body raw"""
        return self._body
    
    @property
    def args(self) -> dict:
        """Query params"""
        parsed = parse_qs(self._parsed.query, keep_blank_values=True)
        return {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}
    
    @property
    def content_type(self) -> str:
        return self.headers.get('Content-Type', '')
    
    @property
    def content_length(self) -> int:
        return int(self.headers.get('Content-Length', 0))
    
    @property
    def cookies(self) -> dict:
        raw = self.headers.get('Cookie', '')
        cookies = {}
        for part in raw.split(';'):
            part = part.strip()
            if '=' in part:
                k, _, v = part.partition('=')
                cookies[k.strip()] = v.strip()
        return cookies


class _FakeRFile:
    """Fake file para simular leitura do body"""
    
    def __init__(self, data: bytes):
        self._data = data
        self._pos = 0
    
    def read(self, size: int = -1) -> bytes:
        if size < 0:
            result = self._data[self._pos:]
            self._pos = len(self._data)
        else:
            result = self._data[self._pos:self._pos + size]
            self._pos += size
        return result


class TestResponse:
    """
    Response wrapper para testes — facilita acesso aos dados.
    """
    
    def __init__(self, response: Response):
        self._response = response
    
    @property
    def status_code(self) -> int:
        return self._response.status_code
    
    @property
    def headers(self) -> Dict[str, str]:
        return self._response.headers
    
    @property
    def body(self) -> str:
        body = self._response.body
        if isinstance(body, bytes):
            return body.decode('utf-8', errors='replace')
        return str(body)
    
    @property
    def json(self) -> Any:
        """Parse do body como JSON"""
        try:
            return _json.loads(self.body)
        except _json.JSONDecodeError:
            return None
    
    @property
    def content_type(self) -> Optional[str]:
        return self._response.content_type
    
    def __repr__(self) -> str:
        return f'<TestResponse {self.status_code}>'


class VeloxTestClient:
    """
    Cliente de testes para Velox.
    
    Simula requisições HTTP sem subir o servidor.
    
    Uso:
        from velox.testing import VeloxTestClient
        
        client = VeloxTestClient(app)
        
        # GET
        response = client.get('/path')
        response = client.get('/path?key=value')
        
        # POST
        response = client.post('/path', json={'key': 'value'})
        response = client.post('/path', data={'key': 'value'})
        
        # PUT
        response = client.put('/path', json={'key': 'value'})
        
        # DELETE
        response = client.delete('/path')
        
        # Verificações
        assert response.status_code == 200
        assert response.json['status'] == 'ok'
    """
    
    def __init__(self, app):
        """
        Inicializa o cliente de testes com uma instância do Velox.
        
        Args:
            app: Instância do Velox ou Router/Blueprint
        """
        self.app = app
    
    def _make_request(self, method: str, path: str,
                      headers: Optional[Dict[str, str]] = None,
                      body: Optional[bytes] = None) -> TestResponse:
        """
        Executa uma requisição simulada.
        """
        # Merge headers
        req_headers = headers or {}
        if body and 'Content-Length' not in req_headers:
            req_headers['Content-Length'] = str(len(body))
        
        # Criar request fake
        test_request = TestRequest(method, path, req_headers, body)
        
        # Criar response
        response = Response()
        
        # Encontrar handler
        if hasattr(self.app, 'router'):
            handler, kwargs = self.app.router.match(path, method)
        elif hasattr(self.app, 'match'):
            handler, kwargs = self.app.match(path, method)
        else:
            return TestResponse(response)
        
        if handler is None:
            response.status_code = 404
            response.body = 'Not Found'
            return TestResponse(response)
        
        # Chamar handler (sync ou async)
        import inspect
        if inspect.iscoroutinefunction(handler):
            import asyncio
            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(handler(test_request, response, **kwargs))
            finally:
                loop.close()
        else:
            result = handler(test_request, response, **kwargs)
        
        # Processar resultado
        if result is not None:
            if isinstance(result, str):
                response.body = result
                if response.content_type is None:
                    response._headers['Content-Type'] = 'text/html; charset=utf-8'
            elif isinstance(result, dict):
                response.json(result)
            elif isinstance(result, Response):
                pass  # Já configurado
        
        return TestResponse(response)
    
    def get(self, path: str, 
            headers: Optional[Dict[str, str]] = None) -> TestResponse:
        """Executa GET"""
        return self._make_request('GET', path, headers)
    
    def post(self, path: str,
             json: Optional[Dict] = None,
             data: Optional[Dict] = None,
             files: Optional[Dict] = None,
             headers: Optional[Dict[str, str]] = None) -> TestResponse:
        """
        Executa POST.

        Args:
            json:    dict enviado como application/json
            data:    dict enviado como application/x-www-form-urlencoded
            files:   dict de uploads — {'campo': ('nome.txt', b'conteudo', 'text/plain')}
                     ou {'campo': b'conteudo'}
            headers: headers adicionais
        """
        body = None
        req_headers = dict(headers or {})

        if json is not None:
            body = _json.dumps(json).encode('utf-8')
            req_headers['Content-Type'] = 'application/json'
        elif files is not None:
            body, content_type = _encode_multipart(data or {}, files)
            req_headers['Content-Type'] = content_type
        elif data is not None:
            body = '&'.join(f'{k}={v}' for k, v in data.items()).encode('utf-8')
            req_headers['Content-Type'] = 'application/x-www-form-urlencoded'

        return self._make_request('POST', path, req_headers, body)

    def put(self, path: str,
            json: Optional[Dict] = None,
            data: Optional[Dict] = None,
            files: Optional[Dict] = None,
            headers: Optional[Dict[str, str]] = None) -> TestResponse:
        """Executa PUT (suporta files igual ao post)."""
        body = None
        req_headers = dict(headers or {})

        if json is not None:
            body = _json.dumps(json).encode('utf-8')
            req_headers['Content-Type'] = 'application/json'
        elif files is not None:
            body, content_type = _encode_multipart(data or {}, files)
            req_headers['Content-Type'] = content_type
        elif data is not None:
            body = '&'.join(f'{k}={v}' for k, v in data.items()).encode('utf-8')
            req_headers['Content-Type'] = 'application/x-www-form-urlencoded'

        return self._make_request('PUT', path, req_headers, body)

    def patch(self, path: str,
              json: Optional[Dict] = None,
              data: Optional[Dict] = None,
              files: Optional[Dict] = None,
              headers: Optional[Dict[str, str]] = None) -> TestResponse:
        """Executa PATCH (suporta files igual ao post)."""
        body = None
        req_headers = dict(headers or {})

        if json is not None:
            body = _json.dumps(json).encode('utf-8')
            req_headers['Content-Type'] = 'application/json'
        elif files is not None:
            body, content_type = _encode_multipart(data or {}, files)
            req_headers['Content-Type'] = content_type
        elif data is not None:
            body = '&'.join(f'{k}={v}' for k, v in data.items()).encode('utf-8')
            req_headers['Content-Type'] = 'application/x-www-form-urlencoded'

        return self._make_request('PATCH', path, req_headers, body)
    
    def delete(self, path: str, 
              headers: Optional[Dict[str, str]] = None) -> TestResponse:
        """Executa DELETE"""
        return self._make_request('DELETE', path, headers)
    
    def options(self, path: str, 
                headers: Optional[Dict[str, str]] = None) -> TestResponse:
        """Executa OPTIONS"""
        return self._make_request('OPTIONS', path, headers)
    
    def head(self, path: str, 
             headers: Optional[Dict[str, str]] = None) -> TestResponse:
        """Executa HEAD (sem body)"""
        return self._make_request('HEAD', path, headers)


# --- Fixtures para pytest (opcionais) ---
# Se pytest estiver instalado, as fixtures funcionam automaticamente

def _try_import_pytest():
    """Tenta importar pytest, retorna None se não disponível"""
    try:
        import pytest
        return pytest
    except ImportError:
        return None


# As fixtures abaixo só funcionam se pytest estiver instalado
# Para usar, crie um arquivo tests/conftest.py com:
# 
# import pytest
# from velox import Velox
# from velox.testing import VeloxTestClient
#
# @pytest.fixture
# def app():
#     return Velox(__name__)
#
# @pytest.fixture
# def client(app):
#     return VeloxTestClient(app)


# --- Compatibilidade com unittest ---

class TestCase:
    """
    Classe base para testes unitários com Velox.
    
    Uso:
        from velox.testing import TestCase, VeloxTestClient
        
        class MyTest(TestCase):
            def setUp(self):
                self.app = create_my_app()
                self.client = VeloxTestClient(self.app)
            
            def test_home_page(self):
                response = self.client.get('/')
                self.assertEqual(response.status_code, 200)
                self.assertIn('Hello', response.body)
    """
    
    def setUp(self):
        """Override em subclasses"""
        pass
    
    def tearDown(self):
        """Override em subclasses"""
        pass
    
    def assertEqual(self, a, b):
        assert a == b, f'{a} != {b}'
    
    def assertNotEqual(self, a, b):
        assert a != b, f'{a} == {b}'
    
    def assertTrue(self, x):
        assert x, 'Expected True'
    
    def assertFalse(self, x):
        assert not x, 'Expected False'
    
    def assertIn(self, member, container):
        assert member in container, f'{member} not in {container}'
    
    def assertNotIn(self, member, container):
        assert member not in container, f'{member} in {container}'
    
    def assertIsNone(self, x):
        assert x is None, f'Expected None, got {x}'
    
    def assertIsNotNone(self, x):
        assert x is not None, 'Expected not None'
    
    def assertRaises(self, exception_type, func, *args, **kwargs):
        try:
            func(*args, **kwargs)
            raise AssertionError(f'{exception_type.__name__} not raised')
        except exception_type:
            pass