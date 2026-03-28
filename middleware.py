"""
Módulo de Middlewares do Velox Framework
"""

from functools import wraps
import time
import hashlib
import secrets


class Middleware:
    """Classe base para middlewares"""
    
    def __init__(self, app):
        self.app = app
        self._middlewares = []
    
    def use(self, middleware_func):
        """Adiciona um middleware"""
        self._middlewares.append(middleware_func)
        return middleware_func


class CORSMiddleware:
    """Middleware para CORS (Cross-Origin Resource Sharing)"""
    
    def __init__(self, app, allowed_origins=None, allowed_methods=None, allowed_headers=None):
        self.app = app
        self.allowed_origins = allowed_origins or ['*']
        self.allowed_methods = allowed_methods or ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
        self.allowed_headers = allowed_headers or ['Content-Type', 'Authorization']
    
    def __call__(self, handler):
        """Aplica o middleware CORS"""
        def wrapper(request, response):
            # Adicionar headers CORS
            origin = request.headers.get('Origin', '')
            
            if '*' in self.allowed_origins or origin in self.allowed_origins:
                response.set_header('Access-Control-Allow-Origin', origin or '*')
                response.set_header('Access-Control-Allow-Methods', ', '.join(self.allowed_methods))
                response.set_header('Access-Control-Allow-Headers', ', '.join(self.allowed_headers))
                response.set_header('Access-Control-Allow-Credentials', 'true')
            
            # Preflight request
            if request.method == 'OPTIONS':
                response.status_code = 204
                return response
            
            return handler(request, response)
        
        return wrapper


class LoggingMiddleware:
    """Middleware para logging de requisições"""
    
    def __init__(self, app):
        self.app = app
    
    def __call__(self, handler):
        """Aplica o middleware de logging"""
        @wraps(handler)
        def wrapper(request, response):
            start_time = time.time()
            
            # Executar handler
            result = handler(request, response)
            
            # Calcular tempo
            duration = (time.time() - start_time) * 1000
            
            # Log
            print(f"📝 {request.method} {request.path} - {response.status_code} - {duration:.2f}ms")
            
            return result
        
        return wrapper


class AuthMiddleware:
    """Middleware para autenticação simples"""
    
    def __init__(self, app, secret_key=None):
        self.app = app
        self.secret_key = secret_key or secrets.token_hex(32)
    
    def __call__(self, handler):
        """Aplica o middleware de autenticação"""
        @wraps(handler)
        def wrapper(request, response):
            # Verificar token de autenticação
            auth_header = request.headers.get('Authorization', '')
            
            # Adicionar helper de autenticação ao request
            request.is_authenticated = bool(auth_header.startswith('Bearer '))
            request.user_id = None
            
            if request.is_authenticated:
                token = auth_header[7:]  # Remove 'Bearer '
                # Aqui você pode validar o token
                # Por simplicidade, apenas marcamos como autenticado
            
            return handler(request, response)
        
        return wrapper


class RateLimitMiddleware:
    """
    Middleware para rate limiting por IP.

    ATENÇÃO: armazena contadores em memória (self.requests).
    Não funciona corretamente com múltiplos workers (uvicorn --workers N).
    Para produção com múltiplos workers, use o RateLimiter de auth.py
    que integra com Redis automaticamente quando CACHE_BACKEND=redis.
    """

    def __init__(self, app, max_requests=100, window=60):
        self.app          = app
        self.max_requests = max_requests
        self.window       = window
        self.requests: dict = {}  # in-memory — não compartilhado entre workers
    
    def __call__(self, handler):
        """Aplica o middleware de rate limiting"""
        @wraps(handler)
        def wrapper(request, response):
            # Obter IP do cliente
            client_ip = request.headers.get('X-Forwarded-For', 
                           request.headers.get('Remote-Addr', 'unknown'))
            
            # Verificar limite
            now = time.time()
            if client_ip in self.requests:
                # Limpar requisições antigas
                self.requests[client_ip] = [
                    t for t in self.requests[client_ip] 
                    if now - t < self.window
                ]
                
                if len(self.requests[client_ip]) >= self.max_requests:
                    response.status_code = 429
                    response.text("Too many requests. Please try again later.")
                    return response
                
                self.requests[client_ip].append(now)
            else:
                self.requests[client_ip] = [now]
            
            return handler(request, response)
        
        return wrapper


# Decoradores de conveniência
def cors(allowed_origins=None):
    """Decorador para adicionar CORS"""
    def decorator(handler):
        @wraps(handler)
        def wrapper(request, response):
            origin = request.headers.get('Origin', '')
            origins = allowed_origins or ['*']
            
            if '*' in origins or origin in origins:
                response.set_header('Access-Control-Allow-Origin', origin or '*')
                response.set_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
                response.set_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
            
            if request.method == 'OPTIONS':
                response.status_code = 204
                return response
            
            return handler(request, response)
        return wrapper
    return decorator


def login_required(handler):
    """Decorador para rotas que requerem autenticação"""
    @wraps(handler)
    def wrapper(request, response):
        if not getattr(request, 'is_authenticated', False):
            response.status_code = 401
            response.json({'error': 'Unauthorized'})
            return response
        return handler(request, response)
    return wrapper
