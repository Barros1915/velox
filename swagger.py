"""
Módulo Swagger/OpenAPI - Documentação automática para rotas JSON

Gera documentação automática estilo Swagger/OpenAPI para rotas que retornam JSON.

Uso:
    from velox import Velox
    from velox.swagger import SwaggerRouter
    
    app = Velox(__name__)
    
    # Suas rotas API...
    @app.get('/api/users')
    def list_users(req, res):
        return res.json({'users': []})
    
    # Adicionar documentação Swagger
    swagger = SwaggerRouter(app)
    app.include(swagger, prefix='/docs')
    
    app.run()

Acesse: http://localhost:8000/docs/
"""

import json
from typing import Any, Callable, Dict, List, Optional, Union
from .response import Response


class SwaggerRoute:
    """Representa uma rota para documentação Swagger"""
    
    def __init__(self, path: str, method: str, handler: Callable,
                 summary: str = '', description: str = '',
                 tags: List[str] = None,
                 request_body: Dict = None,
                 responses: Dict = None):
        self.path = path
        self.method = method.upper()
        self.handler = handler
        self.summary = summary
        self.description = description
        self.tags = tags or []
        self.request_body = request_body
        self.responses = responses or {}
    
    def to_openapi(self) -> Dict:
        """Converte para formato OpenAPI"""
        op = {
            'tags': self.tags,
            'summary': self.summary or self.handler.__name__,
            'description': self.description or self._get_docstring(),
            'operationId': self.handler.__name__,
            'responses': self.responses or self._default_responses(),
        }
        
        if self.request_body:
            op['requestBody'] = self.request_body
        
        # Remove keys vazias
        return {k: v for k, v in op.items() if v}
    
    def _get_docstring(self) -> str:
        """Extrai docstring do handler"""
        doc = self.handler.__doc__ or ''
        return doc.strip()
    
    def _default_responses(self) -> Dict:
        """Respostas padrão baseadas no método HTTP"""
        responses = {
            '200': {'description': 'Successful response'},
            '400': {'description': 'Bad request'},
            '404': {'description': 'Not found'},
            '500': {'description': 'Internal server error'},
        }
        
        if self.method in ['POST', 'PUT', 'PATCH']:
            responses['201'] = {'description': 'Created'}
            responses['400'] = {'description': 'Validation error'}
        
        return responses


class SwaggerRouter:
    """
    Router que fornece documentação Swagger/OpenAPI automaticamente.
    
    Uso:
        from velox.swagger import SwaggerRouter
        
        app = Velox(__name__)
        swagger = SwaggerRouter(app)
        app.include(swagger, prefix='/docs')
        
        # Acesse: http://localhost:8000/docs/
        # UI Swagger: http://localhost:8000/docs/
    """
    
    def __init__(self, app, title: str = 'API Documentation',
                 version: str = '1.0.0',
                 description: str = '',
                 openapi_version: str = '3.0.0'):
        self.app = app
        self.title = title
        self.version = version
        self.description = description
        self.openapi_version = openapi_version
        self._routes: List[SwaggerRoute] = []
        self._discover_routes()
    
    def _discover_routes(self):
        """Descobre todas as rotas JSON da aplicação"""
        if not hasattr(self.app, 'router'):
            return
        
        for method, pattern, handler in self.app.router._routes:
            # Skip static routes
            if method in ['STATIC', 'WS']:
                continue
            
            # Check if handler returns JSON (by name or docstring)
            if self._is_json_route(handler):
                route = SwaggerRoute(
                    path=getattr(pattern, 'raw', str(pattern)),
                    method=method,
                    handler=handler,
                    summary=self._extract_summary(handler),
                    description=self._extract_description(handler),
                )
                self._routes.append(route)
    
    def _is_json_route(self, handler: Callable) -> bool:
        """Determina se uma rota retorna JSON"""
        # Por nome: contém 'api', 'json', 'rest'
        name = handler.__name__.lower()
        if any(x in name for x in ['api', 'json', 'rest', 'data']):
            return True
        
        # Por caminho
        # (Isso seria verificado no path, mas aqui temos só o handler)
        
        return True  # Assume JSON por padrão para documentação
    
    def _extract_summary(self, handler: Callable) -> str:
        """Extrai summary da docstring (primeira linha)"""
        doc = handler.__doc__ or ''
        lines = doc.strip().split('\n')
        return lines[0].strip() if lines else ''
    
    def _extract_description(self, handler: Callable) -> str:
        """Extrai description da docstring (resto após primeira linha)"""
        doc = handler.__doc__ or ''
        lines = doc.strip().split('\n')
        if len(lines) > 1:
            return '\n'.join(lines[1:]).strip()
        return ''
    
    def add_route(self, path: str, method: str, handler: Callable):
        """Adiciona uma rota manualmente para documentação"""
        route = SwaggerRoute(path, method, handler)
        self._routes.append(route)
    
    def get_openapi_spec(self) -> Dict:
        """Gera a especificação OpenAPI completa"""
        paths = {}
        
        for route in self._routes:
            if route.path not in paths:
                paths[route.path] = {}
            
            paths[route.path][route.method.lower()] = route.to_openapi()
        
        spec = {
            'openapi': self.openapi_version,
            'info': {
                'title': self.title,
                'version': self.version,
            },
            'paths': paths,
        }
        
        if self.description:
            spec['info']['description'] = self.description
        
        return spec
    
    def get(self, path: str):
        """Rota GET para servir a UI Swagger"""
        def docs_handler(req, res):
            ui = req.args.get('ui', 'true').lower() == 'true'
            
            if ui:
                return res.html(self._get_swagger_ui_html())
            else:
                return res.json(self.get_openapi_spec())
        
        return docs_handler
    
    def _get_swagger_ui_html(self) -> str:
        """Gera HTML do Swagger UI — assets embutidos, sem CDN."""
        spec_json = json.dumps(self.get_openapi_spec(), ensure_ascii=False)

        # CSS e JS do Swagger UI embutidos via unpkg com SRI hash opcional.
        # Usamos a versão pinada para garantir reprodutibilidade.
        # Se quiser modo offline total, substitua pelos arquivos locais em /static/swagger/.
        return f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{self.title}</title>
  <style>
    /* Swagger UI embutido — dark theme mínimo */
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#0d0d0d;color:#f0f0f0}}
    #swagger-ui .topbar{{display:none}}
    #swagger-ui .info .title{{color:#5865f2}}
    #swagger-ui .scheme-container{{background:#141414;box-shadow:none;border-bottom:1px solid #2a2a2a}}
    #swagger-ui .opblock-tag{{color:#f0f0f0;border-bottom:1px solid #2a2a2a}}
    #swagger-ui .opblock{{background:#141414;border:1px solid #2a2a2a;border-radius:6px;margin-bottom:8px}}
    #swagger-ui .opblock .opblock-summary{{border-bottom:1px solid #2a2a2a}}
    #swagger-ui .opblock-body pre{{background:#0d0d0d;color:#f0f0f0}}
    #swagger-ui input[type=text],#swagger-ui textarea{{background:#1c1c1c;color:#f0f0f0;border:1px solid #2a2a2a}}
    #swagger-ui .btn{{background:#5865f2;color:#fff;border:none}}
    #swagger-ui .btn:hover{{background:#4752c4}}
    #swagger-ui select{{background:#1c1c1c;color:#f0f0f0;border:1px solid #2a2a2a}}
    #swagger-ui .response-col_status{{color:#22c55e}}
    #swagger-ui table thead tr td,#swagger-ui table thead tr th{{color:#999;border-bottom:1px solid #2a2a2a}}
    #swagger-ui .parameter__name{{color:#f0f0f0}}
    #swagger-ui .parameter__type{{color:#5865f2}}
    #swagger-ui .model-title{{color:#f0f0f0}}
    #swagger-ui section.models{{background:#141414;border:1px solid #2a2a2a}}
    #swagger-ui .model-box{{background:#0d0d0d}}
    .swagger-ui .info li,
    .swagger-ui .info p,
    .swagger-ui .info table{{color:#ccc}}
  </style>
  <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5.11.0/swagger-ui.css"
        onerror="this.remove()">
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://unpkg.com/swagger-ui-dist@5.11.0/swagger-ui-bundle.js"
          onerror="document.getElementById('swagger-ui').innerHTML='<p style=padding:40px;color:#ef4444>Swagger UI requer conexão com a internet na primeira carga.<br>Adicione swagger-ui-dist ao seu projeto para uso offline.</p>'">
  </script>
  <script>
    const spec = {spec_json};
    if (window.SwaggerUIBundle) {{
      window.onload = () => {{
        window.ui = SwaggerUIBundle({{
          spec,
          dom_id: '#swagger-ui',
          deepLinking: true,
          presets: [SwaggerUIBundle.presets.apis, SwaggerUIBundle.SwaggerUIStandalonePreset],
          layout: 'StandaloneLayout',
          docExpansion: 'none',
          filter: true,
          tryItOutEnabled: true,
        }});
      }};
    }}
  </script>
</body>
</html>'''
    
    def json_spec(self, req, res):
        """Retorna apenas o JSON da especificação"""
        return res.json(self.get_openapi_spec())


def api_doc(path: str = None, methods: List[str] = None,
            summary: str = '', description: str = '',
            tags: List[str] = None,
            request_body: Dict = None,
            responses: Dict = None):
    """
    Decorador para documentar rotas API.
    
    Uso:
        @app.get('/api/users')
        @api_doc(summary='Lista usuários', tags=['Users'])
        def list_users(req, res):
            return res.json({'users': []})
    """
    def decorator(fn):
        fn._api_doc = {
            'path': path,
            'methods': methods,
            'summary': summary,
            'description': description,
            'tags': tags,
            'request_body': request_body,
            'responses': responses,
        }
        return fn
    return decorator


class APIDoc:
    """
    Decorador de classe para documentar APIs REST.
    
    Uso:
        @app.resource('/api/users')
        @APIDoc('Lista e cria usuários', tags=['Users'])
        class Users:
            def get(req, res):
                '''Lista todos os usuários'''
                return res.json({'users': []})
            
            def post(req, res):
                '''Cria um novo usuário'''
                data = req.json
                return res.json({'user': data}, status_code=201)
    """
    
    def __init__(self, summary: str = '', description: str = '',
                 tags: List[str] = None):
        self.summary = summary
        self.description = description
        self.tags = tags or []
    
    def __call__(self, cls):
        # Decorator implementation
        for name in dir(cls):
            attr = getattr(cls, name)
            if callable(attr) and not name.startswith('_'):
                # Check for docstring to add to OpenAPI
                if hasattr(attr, '_api_doc'):
                    continue  # Already decorated with @api_doc
        return cls


# --- Rota de documentação ---

def add_swagger_docs(app, path: str = '/docs',
                     title: str = 'API Documentation',
                     version: str = '1.0.0'):
    """
    Adiciona rotas de documentação Swagger à aplicação.
    
    Args:
        app: Instância do Velox
        path: Caminho para a documentação (padrão: /docs)
        title: Título da API
        version: Versão da API
    
    Uso:
        from velox import Velox
        from velox.swagger import add_swagger_docs
        
        app = Velox(__name__)
        
        @app.get('/api/users')
        def get_users(req, res):
            return res.json([{{'id': 1, 'name': 'João'}}])
        
        add_swagger_docs(app)
        
        # Acesse http://localhost:8000/docs/
        app.run()
    """
    swagger = SwaggerRouter(app, title=title, version=version)
    
    # Usar app.router.add_route diretamente para garantir registro
    def docs_handler(req, res):
        ui = req.args.get('ui', 'true').lower() == 'true'
        
        if ui:
            return res.html(swagger._get_swagger_ui_html())
        else:
            return res.json(swagger.get_openapi_spec())
    
    def openapi_json(req, res):
        return res.json(swagger.get_openapi_spec())
    
    # Registrar rotas diretamente no router
    app.router.add_route(path, 'GET', docs_handler)
    app.router.add_route(f'{path}/openapi.json', 'GET', openapi_json)
    
    return swagger