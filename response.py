"""
Módulo Response - Manipulação de respostas HTTP

Type hints adicionados para melhorar IntelliSense e experiência do desenvolvedor.
"""

import json
from typing import Any, Dict, Optional, Union


class Response:
    """
    Classe que representa uma resposta HTTP
    
    Fornece métodos fácil para retornar diferentes tipos de resposta:
    - HTML
    - JSON
    - Texto
    - Arquivos
    
    Uso:
        @app.get('/')
        def home(req, res):
            return res.html('<h1>Olá Mundo</h1>')
        
        @app.get('/api/dados')
        def api(req, res):
            return res.json({'status': 'ok', 'data': []})
    """
    
    body: Union[str, bytes, dict, list, None]
    status_code: int
    _headers: Dict[str, str]
    
    def __init__(self, body: Union[str, bytes, dict, list, None] = '', 
                 status_code: int = 200, 
                 headers: Optional[Dict[str, str]] = None):
        self.body = body
        self.status_code = status_code
        self._headers = headers or {}
    
    @property
    def headers(self) -> Dict[str, str]:
        """Retorna os headers da resposta"""
        return self._headers
    
    def set_header(self, name: str, value: str) -> 'Response':
        """Define um header específico. Retorna self para chaining."""
        self._headers[name] = value
        return self
    
    def set_headers(self, headers: Dict[str, str]) -> 'Response':
        """Define múltiplos headers de uma vez. Retorna self para chaining."""
        self._headers.update(headers)
        return self
    
    def html(self, html_content: str, status_code: int = 200) -> 'Response':
        """Retorna conteúdo HTML"""
        self.body = html_content
        self.status_code = status_code
        self._headers['Content-Type'] = 'text/html; charset=utf-8'
        return self
    
    def json(self, data: Any, status_code: int = 200) -> 'Response':
        """Retorna dados JSON"""
        self.body = json.dumps(data, ensure_ascii=False, indent=2)
        self.status_code = status_code
        self._headers['Content-Type'] = 'application/json; charset=utf-8'
        return self
    
    def text(self, content: str, status_code: int = 200) -> 'Response':
        """Retorna texto puro"""
        self.body = content
        self.status_code = status_code
        self._headers['Content-Type'] = 'text/plain; charset=utf-8'
        return self
    
    def send(self, content: Any, status_code: int = 200) -> 'Response':
        """Envia conteúdo genérico como texto"""
        self.body = str(content)
        self.status_code = status_code
        self._headers['Content-Type'] = 'text/plain; charset=utf-8'
        return self
    
    def file(self, file_path: str, content_type: Optional[str] = None) -> 'Response':
        """Retorna um arquivo para download"""
        import os
        if os.path.exists(file_path):
            with open(file_path, 'rb') as f:
                self.body = f.read()
            self.status_code = 200
            
            # Detectar tipo MIME
            if content_type is None:
                import mimetypes
                content_type, _ = mimetypes.guess_type(file_path)
                if content_type is None:
                    content_type = 'application/octet-stream'
            
            self._headers['Content-Type'] = content_type
            self._headers['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
        else:
            self.body = 'Arquivo não encontrado'
            self.status_code = 404
            self._headers['Content-Type'] = 'text/plain'
        return self
    
    def redirect(self, location: str, status_code: int = 302) -> 'Response':
        """Redireciona para outra URL"""
        self.body = ''
        self.status_code = status_code
        self._headers['Location'] = location
        return self
    
    def set_cookie(self, name: str, value: str, 
                   expires: Optional[int] = None,
                   path: str = '/',
                   secure: bool = False,
                   httponly: bool = False,
                   samesite: Optional[str] = None) -> 'Response':
        """
        Define um cookie na resposta.
        
        Args:
            name: Nome do cookie
            value: Valor do cookie
            expires: Tempo de expiração em segundos
            path: Caminho do cookie
            secure: HTTPS only
            httponly: Inacessível via JavaScript
            samesite: Política SameSite ('Strict', 'Lax', 'None')
        """
        parts = [f'{name}={value}']
        if expires:
            parts.append(f'Max-Age={expires}')
        parts.append(f'Path={path}')
        if secure:
            parts.append('Secure')
        if httponly:
            parts.append('HttpOnly')
        if samesite:
            parts.append(f'SameSite={samesite}')
        
        self._headers['Set-Cookie'] = '; '.join(parts)
        return self
    
    def delete_cookie(self, name: str, path: str = '/') -> 'Response':
        """Remove um cookie definindo expiração no passado"""
        self._headers['Set-Cookie'] = f'{name}=; Path={path}; Expires=Thu, 01 Jan 1970 00:00:00 GMT'
        return self
    
    @property
    def content_type(self) -> Optional[str]:
        """Retorna o Content-Type da resposta"""
        return self._headers.get('Content-Type')
    
    @property
    def location(self) -> Optional[str]:
        """Retorna o header Location (para redirects)"""
        return self._headers.get('Location')
    
    def __repr__(self) -> str:
        return f"<Response {self.status_code} content_type='{self.content_type}'>"
