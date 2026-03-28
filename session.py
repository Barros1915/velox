"""
Módulo de Sessões do Velox Framework

Dois modos:
  - ServerSession (padrão): dados no servidor (cache), só o ID no cookie.
    Seguro, escalável, suporta logout real.
  - Session (legado): dados assinados no próprio cookie (client-side).
    Mantido para compatibilidade.
"""

import secrets
import json
import hashlib
import hmac
import time
import os
from datetime import datetime, timedelta
from typing import Any, Optional

_SESSION_COOKIE   = os.getenv('SESSION_COOKIE_NAME',   'velox_sid')
_SESSION_EXPIRES  = int(os.getenv('SESSION_EXPIRE_SECONDS', 86400))
_SESSION_SECURE   = os.getenv('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
_SESSION_SAMESITE = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')


# ─────────────────────────────────────────
# Server-Side Session (padrão recomendado)
# ─────────────────────────────────────────

class ServerSession:
    """
    Sessão server-side: dados armazenados no cache (memory/Redis/SQLite),
    apenas o ID da sessão viaja no cookie.

    Com Redis (múltiplos workers):
        CACHE_BACKEND=redis
        CACHE_REDIS_URL=redis://localhost:6379/0
    """

    def __init__(self, request, response):
        self.request  = request
        self.response = response
        self._data:   dict = {}
        self._sid:    Optional[str] = None
        self._loaded: bool = False
        self._dirty:  bool = False

    def _get_sid_from_cookie(self) -> Optional[str]:
        cookies = getattr(self.request, 'cookies', {})
        if isinstance(cookies, dict):
            return cookies.get(_SESSION_COOKIE)
        raw = ''
        if hasattr(self.request, 'headers'):
            raw = (self.request.headers.get('Cookie') or
                   self.request.headers.get('cookie') or '')
        for part in raw.split(';'):
            part = part.strip()
            if part.startswith(f'{_SESSION_COOKIE}='):
                return part[len(_SESSION_COOKIE) + 1:]
        return None

    def load(self) -> 'ServerSession':
        if self._loaded:
            return self
        self._loaded = True
        sid = self._get_sid_from_cookie()
        if sid:
            from .cache import cache as _cache
            data = _cache.get(f'session:{sid}')
            if isinstance(data, dict):
                self._sid  = sid
                self._data = data
        return self

    def save(self) -> 'ServerSession':
        from .cache import cache as _cache
        if self._sid is None:
            self._sid = secrets.token_urlsafe(32)
        _cache.set(f'session:{self._sid}', self._data, timeout=_SESSION_EXPIRES)
        flags  = f'Path=/; HttpOnly; SameSite={_SESSION_SAMESITE}; Max-Age={_SESSION_EXPIRES}'
        if _SESSION_SECURE:
            flags += '; Secure'
        cookie = f'{_SESSION_COOKIE}={self._sid}; {flags}'
        if hasattr(self.response, 'set_header'):
            self.response.set_header('Set-Cookie', cookie)
        else:
            self.response.headers['Set-Cookie'] = cookie
        self._dirty = False
        return self

    def destroy(self) -> 'ServerSession':
        if self._sid:
            from .cache import cache as _cache
            _cache.delete(f'session:{self._sid}')
        self._data = {}
        self._sid  = None
        expired = f'{_SESSION_COOKIE}=; Path=/; HttpOnly; Expires=Thu, 01 Jan 1970 00:00:00 GMT'
        if hasattr(self.response, 'set_header'):
            self.response.set_header('Set-Cookie', expired)
        else:
            self.response.headers['Set-Cookie'] = expired
        return self

    def rotate(self) -> 'ServerSession':
        """Gera novo SID mantendo os dados — use após login para prevenir fixation."""
        if self._sid:
            from .cache import cache as _cache
            _cache.delete(f'session:{self._sid}')
        self._sid = None
        return self.save()

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> 'ServerSession':
        self._data[key] = value
        self._dirty = True
        return self

    def pop(self, key: str, default=None):
        val = self._data.pop(key, default)
        self._dirty = True
        return val

    def __getitem__(self, key):         return self._data[key]
    def __setitem__(self, key, value):  self._data[key] = value; self._dirty = True
    def __delitem__(self, key):         del self._data[key]; self._dirty = True
    def __contains__(self, key):        return key in self._data
    def __repr__(self):
        return f'<ServerSession sid={self._sid[:8] if self._sid else "new"}>'


# ─────────────────────────────────────────
# Session legado (client-side, HMAC)
# ─────────────────────────────────────────

class Session:
    """
    Sessão client-side: dados assinados com HMAC no cookie.
    Mantido para compatibilidade. Para novos projetos use ServerSession.
    """

    def __init__(self, request, response, secret_key=None, expires=86400):
        self.request     = request
        self.response    = response
        self.secret_key  = secret_key or secrets.token_hex(32)
        self.expires     = expires
        self._data       = {}
        self._session_id = None
        self._loaded     = False

    def _get_session_cookie(self):
        raw = (getattr(self.request, 'headers', {}) or {}).get('Cookie', '')
        for part in raw.split(';'):
            part = part.strip()
            if part.startswith('session_id='):
                return part[len('session_id='):]
        return None

    def _sign_data(self, data):
        message   = json.dumps(data, sort_keys=True)
        signature = hmac.new(self.secret_key.encode(), message.encode(), hashlib.sha256).hexdigest()
        return f"{message}.{signature}"

    def _verify_data(self, signed_data):
        try:
            message, signature = signed_data.rsplit('.', 1)
            expected = hmac.new(self.secret_key.encode(), message.encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(signature, expected):
                return None
            data    = json.loads(message)
            created = data.get('created', 0)
            if time.time() - created > self.expires * 2:
                return None
            return data
        except Exception:
            return None

    def load(self):
        if self._loaded:
            return self
        self._loaded = True
        sid = self._get_session_cookie()
        if sid:
            data = self._verify_data(sid)
            if data and data.get('expires', 0) > time.time():
                self._data       = data.get('data', {})
                self._session_id = sid
            else:
                self.destroy()
        return self

    def save(self):
        if self._session_id is None:
            self._session_id = secrets.token_urlsafe(32)
        data   = {'data': self._data, 'expires': time.time() + self.expires, 'created': time.time()}
        signed = self._sign_data(data)
        exp    = (datetime.now() + timedelta(seconds=self.expires)).strftime('%a, %d %b %Y %H:%M:%S GMT')
        self.response.set_header('Set-Cookie', f'session_id={signed}; Path=/; HttpOnly; Expires={exp}')
        return self

    def destroy(self):
        self._data       = {}
        self._session_id = None
        self.response.set_header('Set-Cookie', 'session_id=; Path=/; HttpOnly; Expires=Thu, 01 Jan 1970 00:00:00 GMT')
        return self

    def get(self, key, default=None): return self._data.get(key, default)
    def set(self, key, value):        self._data[key] = value; return self
    def __getitem__(self, key):       return self._data[key]
    def __setitem__(self, key, value): self._data[key] = value
    def __contains__(self, key):      return key in self._data
    def __repr__(self):
        return f"<Session {self._session_id[:8] if self._session_id else 'new'}>"


# ─────────────────────────────────────────
# SessionManager — único, sem duplicação
# ─────────────────────────────────────────

class SessionManager:
    """
    Gerenciador de sessões.

    server_side=True  (padrão) → ServerSession (dados no cache)
    server_side=False           → Session legado (dados no cookie HMAC)
    """

    def __init__(self, secret_key: str = None, server_side: bool = True):
        self.secret_key  = secret_key or secrets.token_hex(32)
        self.server_side = server_side

    def get_session(self, request, response):
        """Obtém ou cria uma sessão e já faz load()."""
        if self.server_side:
            s = ServerSession(request, response)
        else:
            s = Session(request, response, self.secret_key)
        s.load()
        return s
