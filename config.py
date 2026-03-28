"""
Configuração do Velox Framework
"""

import os
from pathlib import Path


class Config:
    """Classe base de configuração"""
    
    # Configurações do servidor
    HOST = 'localhost'
    PORT = 8000
    DEBUG = False
    
    # Configurações de segurança
    SECRET_KEY = 'dev-secret-key-change-in-production'
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Configurações de banco de dados
    DATABASE_URI = 'sqlite:///app.db'
    DATABASE_ECHO = False
    
    # Configurações de templates
    TEMPLATES_FOLDER = 'templates'
    TEMPLATES_AUTO_RELOAD = False
    
    # Configurações de arquivos estáticos
    STATIC_FOLDER = 'static'
    STATIC_URL_PATH = '/static'
    
    # Configurações de logging
    LOG_LEVEL = 'INFO'
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Configurações de CORS
    CORS_ORIGINS = ['*']
    CORS_METHODS = ['GET', 'POST', 'PUT', 'DELETE']
    CORS_HEADERS = ['Content-Type']
    
    # Configurações de rate limiting
    RATE_LIMIT_ENABLED = False
    RATE_LIMIT_DEFAULT = '100/hour'
    
    @classmethod
    def from_object(cls, obj):
        """Carrega configurações de um objeto"""
        for key in dir(obj):
            if key.isupper():
                setattr(cls, key, getattr(obj, key))
        return cls
    
    @classmethod
    def from_env(cls):
        """Carrega configurações de variáveis de ambiente"""
        cls.HOST = os.getenv('APP_HOST', cls.HOST)
        cls.PORT = int(os.getenv('APP_PORT', cls.PORT))
        cls.DEBUG = os.getenv('APP_DEBUG', 'false').lower() == 'true'
        # Suporta tanto VELOX_SECRET_KEY quanto SECRET_KEY
        cls.SECRET_KEY = os.getenv('VELOX_SECRET_KEY', os.getenv('SECRET_KEY', cls.SECRET_KEY))
        cls.DATABASE_URI = os.getenv('DATABASE_URI', cls.DATABASE_URI)
        cls.LOG_LEVEL = os.getenv('LOG_LEVEL', cls.LOG_LEVEL)
        # Configurações admin
        cls.ADMIN_USER = os.getenv('VELOX_ADMIN_USER', 'admin')
        cls.ADMIN_PASSWORD = os.getenv('VELOX_ADMIN_PASSWORD', 'admin')
        cls.ADMIN_PREFIX = os.getenv('VELOX_ADMIN_PREFIX', '/admin')
        return cls


class DevelopmentConfig(Config):
    """Configuração para desenvolvimento"""
    DEBUG = True
    TEMPLATES_AUTO_RELOAD = True
    DATABASE_ECHO = True
    LOG_LEVEL = 'DEBUG'


class ProductionConfig(Config):
    """Configuração para produção"""
    DEBUG = False
    TEMPLATES_AUTO_RELOAD = False
    DATABASE_ECHO = False
    LOG_LEVEL = 'WARNING'
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = 'Strict'


class TestingConfig(Config):
    """Configuração para testes"""
    TESTING = True
    DATABASE_URI = 'sqlite:///:memory:'
    LOG_LEVEL = 'DEBUG'


# Dicionário de configurações
config_by_name = {
    'development': DevelopmentConfig,
    'dev': DevelopmentConfig,
    'production': ProductionConfig,
    'prod': ProductionConfig,
    'testing': TestingConfig,
    'test': TestingConfig,
    'default': Config
}


def get_config(name='default'):
    """Retorna a configuração pelo nome"""
    return config_by_name.get(name, Config)
