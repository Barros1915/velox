"""
Sistema de Cache - Velox
Similar ao django.core.cache

Backends disponíveis:
    memory  -> Cache em memória (padrão, dev)
    file    -> Cache persistente em SQLite (produção)
    redis   -> Cache Redis (produção, alta performance)

Configuração via .env:
    CACHE_BACKEND=redis
    CACHE_REDIS_URL=redis://localhost:6379/0
    CACHE_DB=cache.db
    CACHE_PREFIX=velox
    CACHE_DEFAULT_TIMEOUT=300
"""

import time
import json
import os
import sqlite3
import hashlib
from typing import Any, Optional, Callable, List
from functools import wraps


# ─────────────────────────────────────────
# Backend 1 — Memória (padrão em dev)
# ─────────────────────────────────────────

class Cache:
    """Cache em memória — rápido, mas não persiste entre reinicializações"""

    def __init__(self, prefix: str = 'velox'):
        self._cache  = {}
        self._expiry = {}
        self._hits   = 0
        self._misses = 0
        self.prefix  = prefix

    def get(self, key: str, default: Any = None) -> Any:
        """Obtém um valor do cache"""
        key = self._make_key(key)
        if key in self._expiry:
            if time.time() > self._expiry[key]:
                self.delete(key)
                self._misses += 1
                return default
        result = self._cache.get(key, default)
        if result is default:
            self._misses += 1
        else:
            self._hits += 1
        return result

    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> None:
        """Define um valor no cache"""
        key = self._make_key(key)
        self._cache[key] = value
        if timeout:
            self._expiry[key] = time.time() + timeout
        else:
            # Default timeout from env
            default_timeout = int(os.getenv('CACHE_DEFAULT_TIMEOUT', 300))
            self._expiry[key] = time.time() + default_timeout

    def delete(self, key: str) -> None:
        """Remove uma chave do cache"""
        key = self._make_key(key)
        self._cache.pop(key, None)
        self._expiry.pop(key, None)

    def clear(self) -> None:
        """Limpa todo o cache"""
        self._cache.clear()
        self._expiry.clear()
        self._hits = 0
        self._misses = 0

    def has(self, key: str) -> bool:
        """Verifica se chave existe e não expirou"""
        key = self._make_key(key)
        if key not in self._cache:
            return False
        if key in self._expiry and time.time() > self._expiry[key]:
            self.delete(key)
            return False
        return True

    def touch(self, key: str, timeout: Optional[int] = None) -> bool:
        """Atualiza o TTL de uma chave"""
        key = self._make_key(key)
        if key in self._cache:
            if timeout:
                self._expiry[key] = time.time() + timeout
            else:
                default_timeout = int(os.getenv('CACHE_DEFAULT_TIMEOUT', 300))
                self._expiry[key] = time.time() + default_timeout
            return True
        return False

    def get_many(self, keys: List[str]) -> dict:
        """Obtém múltiplas chaves de uma vez"""
        return {k: self.get(k) for k in keys if self.has(k)}

    def set_many(self, data: dict, timeout: Optional[int] = None) -> None:
        """Define múltiplas chaves de uma vez"""
        for key, value in data.items():
            self.set(key, value, timeout)

    def delete_many(self, keys: List[str]) -> None:
        """Remove múltiplas chaves"""
        for key in keys:
            self.delete(key)

    def _make_key(self, key: str) -> str:
        """Gera chave com prefixo"""
        return f"{self.prefix}:{key}"

    @property
    def stats(self) -> dict:
        """Retorna estatísticas do cache"""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        return {
            'hits': self._hits,
            'misses': self._misses,
            'hit_rate': round(hit_rate, 2),
            'keys': len(self._cache),
        }

    def __repr__(self):
        return f'<Cache backend=memory keys={len(self._cache)} prefix={self.prefix}>'


# ─────────────────────────────────────────
# Backend 2 — SQLite (persiste em produção)
# ─────────────────────────────────────────

class FileCache:
    """
    Cache persistente usando SQLite.
    Sobrevive a reinicializações do servidor.
    Funciona com SQLite e não precisa de nenhuma dependência extra.

    Uso:
        cache = FileCache('cache.db')
        cache.set('chave', {'dados': 123}, timeout=300)
        valor = cache.get('chave')

    Via .env:
        CACHE_BACKEND=file
        CACHE_DB=cache.db
        CACHE_PREFIX=velox
    """

    def __init__(self, db_path: str = 'cache.db', prefix: str = 'velox'):
        self.db_path = db_path
        self.prefix  = prefix
        self._hits   = 0
        self._misses = 0
        self._init_db()

    def _init_db(self):
        """Cria a tabela de cache se não existir"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS pycore_cache (
                    key    TEXT PRIMARY KEY,
                    value  TEXT NOT NULL,
                    expiry REAL
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_expiry ON pycore_cache(expiry)')
            conn.commit()

    def _make_key(self, key: str) -> str:
        """Gera chave com prefixo"""
        return f"{self.prefix}:{key}"

    def _cleanup(self):
        """Remove entradas expiradas"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                'DELETE FROM pycore_cache WHERE expiry IS NOT NULL AND expiry < ?',
                (time.time(),)
            )
            conn.commit()

    def get(self, key: str, default: Any = None) -> Any:
        """Obtém um valor do cache"""
        key = self._make_key(key)
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                'SELECT value, expiry FROM pycore_cache WHERE key = ?',
                (key,)
            ).fetchone()

        if not row:
            self._misses += 1
            return default

        value, expiry = row

        # Verificar expiração
        if expiry and time.time() > expiry:
            self.delete(key)
            self._misses += 1
            return default

        self._hits += 1
        try:
            return json.loads(value)
        except Exception:
            return default

    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> None:
        """Define um valor no cache"""
        key = self._make_key(key)
        if timeout is None:
            timeout = int(os.getenv('CACHE_DEFAULT_TIMEOUT', 300))
        expiry = time.time() + timeout if timeout else None
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                'INSERT OR REPLACE INTO pycore_cache (key, value, expiry) VALUES (?, ?, ?)',
                (key, json.dumps(value), expiry)
            )
            conn.commit()

    def delete(self, key: str) -> None:
        """Remove uma chave do cache"""
        key = self._make_key(key)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('DELETE FROM pycore_cache WHERE key = ?', (key,))
            conn.commit()

    def clear(self) -> None:
        """Limpa todo o cache"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('DELETE FROM pycore_cache')
            conn.commit()
        self._hits = 0
        self._misses = 0

    def has(self, key: str) -> bool:
        """Verifica se chave existe e não expirou"""
        return self.get(key) is not None

    def touch(self, key: str, timeout: Optional[int] = None) -> bool:
        """Atualiza o TTL de uma chave"""
        key = self._make_key(key)
        if timeout is None:
            timeout = int(os.getenv('CACHE_DEFAULT_TIMEOUT', 300))
        expiry = time.time() + timeout
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute(
                'UPDATE pycore_cache SET expiry = ? WHERE key = ?',
                (expiry, key)
            )
            conn.commit()
            return result.rowcount > 0

    def keys(self) -> list:
        """Lista todas as chaves ativas"""
        self._cleanup()
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute('SELECT key FROM pycore_cache').fetchall()
        return [r[0].replace(f"{self.prefix}:", "") for r in rows]

    def get_many(self, keys: List[str]) -> dict:
        """Obtém múltiplas chaves de uma vez"""
        return {k: self.get(k) for k in keys if self.has(k)}

    def set_many(self, data: dict, timeout: Optional[int] = None) -> None:
        """Define múltiplas chaves de uma vez"""
        for key, value in data.items():
            self.set(key, value, timeout)

    def delete_many(self, keys: List[str]) -> None:
        """Remove múltiplas chaves"""
        for key in keys:
            self.delete(key)

    @property
    def stats(self) -> dict:
        """Retorna estatísticas do cache"""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        return {
            'hits': self._hits,
            'misses': self._misses,
            'hit_rate': round(hit_rate, 2),
            'keys': len(self.keys()),
        }

    def __repr__(self):
        return f'<FileCache backend=sqlite path={self.db_path} prefix={self.prefix}>'


# ─────────────────────────────────────────
# Backend 3 — Redis (produção, alta perf)
# ─────────────────────────────────────────

class RedisCache:
    """
    Cache usando Redis.
    Alta performance para produção com múltiplos workers.

    Uso:
        CACHE_BACKEND=redis
        CACHE_REDIS_URL=redis://localhost:6379/0
        CACHE_PREFIX=velox

    Requer:
        pip install redis
    """

    def __init__(self, url: str = None, prefix: str = 'velox', timeout: int = None):
        self.url     = url or os.getenv('CACHE_REDIS_URL', 'redis://localhost:6379/0')
        self.prefix  = prefix
        self.timeout = timeout or int(os.getenv('CACHE_DEFAULT_TIMEOUT', 300))
        self._client = None
        self._hits   = 0
        self._misses = 0

    def _get_client(self):
        """Obtém conexão Redis (lazy)"""
        if self._client is None:
            try:
                import redis
                self._client = redis.from_url(self.url, decode_responses=True)
                # Testa conexão
                self._client.ping()
            except ImportError:
                raise ImportError(
                    "Redis não instalado. Para usar cache Redis, instale:\n"
                    "  pip install redis"
                )
            except Exception as e:
                raise RuntimeError(f"Erro ao conectar ao Redis: {e}")
        return self._client

    def _make_key(self, key: str) -> str:
        """Gera chave com prefixo"""
        return f"{self.prefix}:{key}"

    def get(self, key: str, default: Any = None) -> Any:
        """Obtém um valor do cache"""
        key = self._make_key(key)
        try:
            client = self._get_client()
            value = client.get(key)
            if value is None:
                self._misses += 1
                return default
            self._hits += 1
            return json.loads(value)
        except Exception:
            self._misses += 1
            return default

    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> None:
        """Define um valor no cache"""
        key = self._make_key(key)
        if timeout is None:
            timeout = self.timeout
        try:
            client = self._get_client()
            serialized = json.dumps(value)
            if timeout:
                client.setex(key, timeout, serialized)
            else:
                client.set(key, serialized)
        except Exception as e:
            print(f"[Cache] Erro ao definir {key}: {e}")

    def delete(self, key: str) -> None:
        """Remove uma chave do cache"""
        key = self._make_key(key)
        try:
            client = self._get_client()
            client.delete(key)
        except Exception:
            pass

    def clear(self) -> None:
        """Limpa todo o cache"""
        try:
            client = self._get_client()
            # Usa SCAN para ser seguro em produção
            for key in client.scan_iter(f"{self.prefix}:*"):
                client.delete(key)
            self._hits = 0
            self._misses = 0
        except Exception:
            pass

    def has(self, key: str) -> bool:
        """Verifica se chave existe e não expirou"""
        return self.get(key) is not None

    def touch(self, key: str, timeout: Optional[int] = None) -> bool:
        """Atualiza o TTL de uma chave"""
        key = self._make_key(key)
        if timeout is None:
            timeout = self.timeout
        try:
            client = self._get_client()
            return client.expire(key, timeout)
        except Exception:
            return False

    def keys(self) -> list:
        """Lista todas as chaves ativas"""
        try:
            client = self._get_client()
            prefix = f"{self.prefix}:"
            return [k.replace(prefix, "") for k in client.scan_iter(f"{prefix}*")]
        except Exception:
            return []

    def get_many(self, keys: List[str]) -> dict:
        """Obtém múltiplas chaves de uma vez"""
        result = {}
        try:
            client = self._get_client()
            full_keys = [self._make_key(k) for k in keys]
            values = client.mget(full_keys)
            for k, v in zip(keys, values):
                if v:
                    result[k] = json.loads(v)
        except Exception:
            pass
        return result

    def set_many(self, data: dict, timeout: Optional[int] = None) -> None:
        """Define múltiplas chaves de uma vez"""
        for key, value in data.items():
            self.set(key, value, timeout)

    def delete_many(self, keys: List[str]) -> None:
        """Remove múltiplas chaves"""
        try:
            client = self._get_client()
            full_keys = [self._make_key(k) for k in keys]
            client.delete(*full_keys)
        except Exception:
            pass

    @property
    def stats(self) -> dict:
        """Retorna estatísticas do cache"""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        return {
            'hits': self._hits,
            'misses': self._misses,
            'hit_rate': round(hit_rate, 2),
            'keys': len(self.keys()),
        }

    def __repr__(self):
        return f'<RedisCache url={self.url} prefix={self.prefix}>'


# ─────────────────────────────────────────
# Seleção automática do backend
# ─────────────────────────────────────────

def _create_cache() -> Any:
    """
    Cria o cache conforme variável de ambiente CACHE_BACKEND.

    .env:
        CACHE_BACKEND=memory   -> Cache em memória (padrão)
        CACHE_BACKEND=file     -> Cache em SQLite (produção)
        CACHE_BACKEND=redis    -> Cache em Redis (produção alta perf)
        CACHE_DB=cache.db      -> Caminho do banco (SQLite)
        CACHE_REDIS_URL=...    -> URL do Redis
        CACHE_PREFIX=velox     -> Prefixo das chaves
    """
    backend = os.getenv('CACHE_BACKEND', 'memory').lower()
    prefix  = os.getenv('CACHE_PREFIX', 'velox')
    
    if backend == 'redis':
        url = os.getenv('CACHE_REDIS_URL', 'redis://localhost:6379/0')
        print(f'✓ Cache backend: Redis ({url})')
        return RedisCache(url, prefix)
    
    if backend == 'file':
        db_path = os.getenv('CACHE_DB', 'cache.db')
        print(f'✓ Cache backend: SQLite ({db_path})')
        return FileCache(db_path, prefix)
    
    print('✓ Cache backend: memória')
    return Cache(prefix)


# Instância global — usada por todo o framework
cache = _create_cache()


# ─────────────────────────────────────────
# Funções de conveniência
# ─────────────────────────────────────────

def get_cache(key: str, default: Any = None) -> Any:
    """Obtém valor do cache"""
    return cache.get(key, default)

def set_cache(key: str, value: Any, timeout: Optional[int] = None) -> None:
    """Define valor no cache"""
    cache.set(key, value, timeout)

def delete_cache(key: str) -> None:
    """Remove valor do cache"""
    cache.delete(key)

def clear_cache() -> None:
    """Limpa todo o cache"""
    cache.clear()

def cache_on(key_func: Callable, timeout: int = None):
    """
    Decorador para cachear resultado de função.
    
    Uso:
        @cache_on(lambda args: f"user:{args[0]}", timeout=60)
        def get_user(user_id):
            return db.get(user_id)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = key_func(*args, **kwargs)
            result = cache.get(cache_key)
            if result is not None:
                return result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, timeout)
            return result
        return wrapper
    return decorator


# ─────────────────────────────────────────
# Cache de templates compilados
# ─────────────────────────────────────────

class TemplateCache:
    """
    Cache específico para templates compilados.
    Melhora performance em produção.
    """
    
    def __init__(self, cache_backend=None):
        self._backend = cache_backend or cache
        self._template_cache = {}
        self.enabled = os.getenv('TEMPLATE_CACHE', 'true').lower() == 'true'
    
    def get(self, template_name: str) -> Optional[str]:
        """Obtém template compilado do cache"""
        if not self.enabled:
            return None
        return self._template_cache.get(template_name)
    
    def set(self, template_name: str, compiled: str) -> None:
        """Armazena template compilado no cache"""
        if not self.enabled:
            return
        self._template_cache[template_name] = compiled
        # Também salva no cache backend para persistência
        cache.set(f"template:{template_name}", compiled)
    
    def get_persistent(self, template_name: str) -> Optional[str]:
        """Obtém do cache persistente"""
        return self._backend.get(f"template:{template_name}")
    
    def clear(self) -> None:
        """Limpa cache de templates"""
        self._template_cache.clear()
        if self.enabled:
            for key in self._backend.keys():
                if key.startswith("template:"):
                    self._backend.delete(key)


# Instância global do cache de templates
template_cache = TemplateCache()
