"""
Sistema de Autenticação e Login - Velox
Similar ao django.contrib.auth

Backends disponíveis:
    memory    -> Usuários em memória (padrão, dev)
    database  -> Usuários no banco SQLite ou PostgreSQL (produção)

OAuth suportado:
    Google, GitHub, Facebook, Discord

RBAC (Controle de Acesso por Papel):
    Roles e permissões granulares por usuário
    Decoradores: @role_required, @permission_required

Cleanup automático de sessões:
    Thread em background que remove sessões expiradas do banco
    Configurável via SESSION_CLEANUP_INTERVAL_HOURS

Configuração via .env:
    AUTH_BACKEND=database
    DATABASE_URI=sqlite:///app.db
    DATABASE_URI=postgresql://user:pass@localhost/dbname
    SESSION_EXPIRE_HOURS=24
    SESSION_CLEANUP_INTERVAL_HOURS=1

    # Rate Limiting (in-memory — use Redis em produção com múltiplos workers)
    MAX_LOGIN_ATTEMPTS=5
    LOGIN_WINDOW_SECONDS=900

    # OAuth Google
    GOOGLE_CLIENT_ID=...
    GOOGLE_CLIENT_SECRET=...
    GOOGLE_REDIRECT_URI=https://seusite.com/auth/google/callback

    # OAuth GitHub
    GITHUB_CLIENT_ID=...
    GITHUB_CLIENT_SECRET=...
    GITHUB_REDIRECT_URI=https://seusite.com/auth/github/callback

    # OAuth Facebook
    FACEBOOK_CLIENT_ID=...
    FACEBOOK_CLIENT_SECRET=...
    FACEBOOK_REDIRECT_URI=https://seusite.com/auth/facebook/callback

    # OAuth Discord
    DISCORD_CLIENT_ID=...
    DISCORD_CLIENT_SECRET=...
    DISCORD_REDIRECT_URI=https://seusite.com/auth/discord/callback
"""

import hashlib
import secrets
import os
import urllib.parse
import urllib.request
import json
import threading
import time
from functools import wraps
from typing import Optional, List, Set, Dict, Tuple
from datetime import datetime, timedelta, timezone
from collections import defaultdict


# ─────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)

def _parse_dt(value) -> Optional[datetime]:
    """
    Converte valor do banco (string ISO ou datetime) para datetime aware (UTC).
    Corrige offset-naive vs offset-aware do SQLite.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str) and value:
        try:
            dt = datetime.fromisoformat(value)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except Exception:
            return None
    return None

SESSION_EXPIRE_HOURS = int(os.getenv('SESSION_EXPIRE_HOURS', 24))


# ─────────────────────────────────────────
# Rate Limiter
# ─────────────────────────────────────────

MAX_LOGIN_ATTEMPTS   = int(os.getenv('MAX_LOGIN_ATTEMPTS', 5))
LOGIN_WINDOW_SECONDS = int(os.getenv('LOGIN_WINDOW_SECONDS', 900))

class RateLimiter:
    """
    Limitador de taxa para prevenir ataques de força bruta.

    Usa Redis automaticamente se CACHE_BACKEND=redis — funciona com
    múltiplos workers. Fallback para memória em dev.
    """

    def __init__(self, max_attempts: int = MAX_LOGIN_ATTEMPTS,
                 window_seconds: int = LOGIN_WINDOW_SECONDS):
        self.max_attempts   = max_attempts
        self.window_seconds = window_seconds
        self._memory: Dict[str, list] = defaultdict(list)  # fallback

    def _use_redis(self):
        return os.getenv('CACHE_BACKEND', 'memory').lower() == 'redis'

    def check_attempt(self, identifier: str) -> Tuple[bool, int]:
        """Retorna (permitido, segundos_restantes)"""
        if self._use_redis():
            return self._check_redis(identifier)
        return self._check_memory(identifier)

    def record_attempt(self, identifier: str):
        if self._use_redis():
            self._record_redis(identifier)
        else:
            self._memory[identifier].append(time.time())

    def reset_attempts(self, identifier: str):
        if self._use_redis():
            try:
                from .cache import cache as _cache
                _cache.delete(f'rl:{identifier}')
            except Exception:
                pass
        else:
            self._memory.pop(identifier, None)

    # ── memória ───────────────────────────────────────────
    def _check_memory(self, identifier: str) -> Tuple[bool, int]:
        now = time.time()
        self._memory[identifier] = [
            t for t in self._memory[identifier] if now - t < self.window_seconds
        ]
        if len(self._memory[identifier]) >= self.max_attempts:
            oldest    = self._memory[identifier][0]
            remaining = int(self.window_seconds - (now - oldest))
            return False, max(0, remaining)
        return True, 0

    # ── Redis ─────────────────────────────────────────────
    def _check_redis(self, identifier: str) -> Tuple[bool, int]:
        try:
            from .cache import cache as _cache
            key   = f'rl:{identifier}'
            count = _cache.get(key, 0)
            if count >= self.max_attempts:
                # Calcula tempo restante via TTL
                try:
                    ttl = _cache._get_client().ttl(f'{_cache.prefix}:{key}')
                    return False, max(0, ttl)
                except Exception:
                    return False, self.window_seconds
            return True, 0
        except Exception:
            return True, 0  # fail open — não bloqueia se Redis cair

    def _record_redis(self, identifier: str):
        try:
            from .cache import cache as _cache
            key   = f'rl:{identifier}'
            count = _cache.get(key, 0)
            _cache.set(key, count + 1, timeout=self.window_seconds)
        except Exception:
            pass


# Instância global do rate limiter
rate_limiter = RateLimiter()


# ─────────────────────────────────────────
# Modelo de Usuário
# ─────────────────────────────────────────

class User:
    """Modelo de usuário"""

    def __init__(self, id: int = None, username: str = '', email: str = '',
                 password_hash: str = '', is_active: bool = True,
                 is_superuser: bool = False, is_staff: bool = False,
                 oauth_provider: str = None, oauth_id: str = None,
                 last_login: datetime = None,
                 roles: List[str] = None, permissions: Set[str] = None):
        self.id             = id
        self.username       = username
        self.email          = email
        self.password_hash  = password_hash
        self.is_active      = is_active
        self.is_superuser   = is_superuser
        self.is_staff       = is_staff
        self.oauth_provider = oauth_provider
        self.oauth_id       = oauth_id
        self.last_login     = last_login
        self._authenticated = False
        self.roles          = roles or []
        self.permissions    = permissions or set()

    def set_password(self, password: str):
        """Define a senha hasheada com pbkdf2_hmac"""
        self.password_hash = self._hash_password(password)

    def check_password(self, password: str) -> bool:
        """Verifica a senha"""
        if not self.password_hash:
            return False
        return self._verify_password(password, self.password_hash)

    def _hash_password(self, password: str) -> str:
        salt   = secrets.token_hex(16)
        hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 260000)
        return f"{salt}${hashed.hex()}"

    def _verify_password(self, password: str, password_hash: str) -> bool:
        try:
            salt, hash_hex = password_hash.split('$')
            new_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 260000)
            return secrets.compare_digest(new_hash.hex(), hash_hex)
        except Exception:
            return False

    @property
    def is_authenticated(self) -> bool:
        return self._authenticated

    @property
    def is_anonymous(self) -> bool:
        return not self._authenticated

    @property
    def is_oauth_user(self) -> bool:
        return bool(self.oauth_provider and self.oauth_id)

    # ── RBAC ──
    def has_role(self, role: str) -> bool:
        if self.is_superuser:
            return True
        return role in self.roles

    def has_any_role(self, *roles: str) -> bool:
        if self.is_superuser:
            return True
        return bool(set(roles) & set(self.roles))

    def has_permission(self, perm: str) -> bool:
        if self.is_superuser:
            return True
        return perm in self.permissions

    def has_all_permissions(self, *perms: str) -> bool:
        if self.is_superuser:
            return True
        return all(p in self.permissions for p in perms)

    def to_dict(self) -> dict:
        return {
            'id':             self.id,
            'username':       self.username,
            'email':          self.email,
            'is_active':      self.is_active,
            'is_staff':       self.is_staff,
            'is_superuser':   self.is_superuser,
            'oauth_provider': self.oauth_provider,
            'last_login':     self.last_login.isoformat() if self.last_login else None,
            'roles':          self.roles,
            'permissions':    list(self.permissions),
        }

    def __str__(self):
        return self.username or self.email

    def __repr__(self):
        return f'<User id={self.id} username={self.username} oauth={self.oauth_provider}>'


# ─────────────────────────────────────────
# Backend Base
# ─────────────────────────────────────────

class AuthBackend:
    """Backend de autenticação base — sobrescrever para implementar"""

    def authenticate(self, username: str = None, password: str = None) -> Optional[User]:
        return None

    def get_user(self, user_id: int) -> Optional[User]:
        return None

    def create_user(self, username: str, email: str, password: str) -> 'User':
        raise NotImplementedError

    def create_session(self, user: 'User') -> str:
        raise NotImplementedError

    def get_user_from_session(self, session_key: str) -> Optional['User']:
        raise NotImplementedError

    def destroy_session(self, session_key: str):
        raise NotImplementedError

    def get_or_create_oauth_user(self, provider: str, oauth_id: str,
                                  email: str, username: str) -> 'User':
        raise NotImplementedError


# ─────────────────────────────────────────
# Backend 1 — Memória (padrão em dev)
# ─────────────────────────────────────────

class SessionBasedAuthBackend(AuthBackend):
    """
    Backend de autenticação em memória.
    Simples e rápido para desenvolvimento.
    NÃO persiste entre reinicializações.
    """

    def __init__(self):
        self._users           = {}   # id -> User
        self._sessions        = {}   # session_key -> {'user_id', 'expires_at'}
        self._oauth           = {}   # (provider, oauth_id) -> user_id
        self._usernames_to_id = {}   # username -> user_id  O(1)
        self._emails_to_id    = {}   # email -> user_id     O(1)
        self._next_id         = 1

    def create_user(self, username: str, email: str, password: str) -> User:
        if username in self._usernames_to_id:
            raise ValueError(f'Usuário "{username}" já existe')
        if email in self._emails_to_id:
            raise ValueError(f'Email "{email}" já cadastrado')
        user_id = self._next_id
        self._next_id += 1
        user    = User(id=user_id, username=username, email=email)
        user.set_password(password)
        self._users[user_id]            = user
        self._usernames_to_id[username] = user_id
        self._emails_to_id[email]       = user_id
        return user

    def get_user(self, user_id: int) -> Optional[User]:
        user = self._users.get(user_id)
        if user:
            user._authenticated = True
        return user

    def authenticate(self, username: str, password: str) -> Optional[User]:
        user_id = self._usernames_to_id.get(username) or self._emails_to_id.get(username)
        if not user_id:
            return None
        user = self._users.get(user_id)
        if user and user.is_active and user.check_password(password):
            user._authenticated = True
            user.last_login     = _now()
            return user
        return None

    def create_session(self, user: User) -> str:
        session_key = secrets.token_urlsafe(32)
        self._sessions[session_key] = {
            'user_id':    user.id,
            'expires_at': _now() + timedelta(hours=SESSION_EXPIRE_HOURS)
        }
        return session_key

    def get_user_from_session(self, session_key: str) -> Optional[User]:
        if not session_key:
            return None
        session = self._sessions.get(session_key)
        if not session:
            return None
        if _now() > session['expires_at']:
            self.destroy_session(session_key)
            return None
        user = self._users.get(session['user_id'])
        if user:
            user._authenticated = True
        return user

    def destroy_session(self, session_key: str):
        self._sessions.pop(session_key, None)

    def get_or_create_oauth_user(self, provider: str, oauth_id: str,
                                  email: str, username: str) -> User:
        key = (provider, oauth_id)
        if key in self._oauth:
            user = self._users.get(self._oauth[key])
            if user:
                user._authenticated = True
                user.last_login     = _now()
                return user

        user_id = self._emails_to_id.get(email)
        if user_id:
            user = self._users[user_id]
            user.oauth_provider = provider
            user.oauth_id       = oauth_id
            user._authenticated = True
            user.last_login     = _now()
            self._oauth[key]    = user.id
            return user

        safe_username = username
        counter = 1
        while safe_username in self._usernames_to_id:
            safe_username = f"{username}{counter}"
            counter += 1

        user_id = self._next_id
        self._next_id += 1
        user    = User(id=user_id, username=safe_username, email=email,
                       oauth_provider=provider, oauth_id=oauth_id)
        user._authenticated                  = True
        user.last_login                      = _now()
        self._users[user_id]                 = user
        self._usernames_to_id[safe_username] = user_id
        self._emails_to_id[email]            = user_id
        self._oauth[key]                     = user_id
        return user

    def __repr__(self):
        return f'<SessionBasedAuthBackend backend=memory users={len(self._users)}>'


# ─────────────────────────────────────────
# Backend 2 — Banco de Dados (produção)
# ─────────────────────────────────────────

class DatabaseAuthBackend(AuthBackend):
    """
    Backend de autenticação conectado ao banco.
    Suporta SQLite e PostgreSQL.
    Persiste usuários e sessões entre reinicializações.
    """

    def __init__(self, db_uri: str = None):
        from .database import Database
        self.db = Database(db_uri or os.getenv('DATABASE_URI', 'app.db'))
        self._init_tables()

    def _ph(self) -> str:
        return '%s' if self.db.driver == 'postgresql' else '?'

    def _insert_ignore(self, table: str, columns: List[str], values: list):
        """
        INSERT ignorando duplicatas — compatível com SQLite e PostgreSQL.
        CORREÇÃO: INSERT OR IGNORE só funciona no SQLite.
        PostgreSQL usa ON CONFLICT DO NOTHING.
        """
        ph      = self._ph()
        cols    = ', '.join(columns)
        holders = ', '.join([ph] * len(columns))
        if self.db.driver == 'postgresql':
            sql = f'INSERT INTO {table} ({cols}) VALUES ({holders}) ON CONFLICT DO NOTHING'
        else:
            sql = f'INSERT OR IGNORE INTO {table} ({cols}) VALUES ({holders})'
        self.db.execute(sql, values)

    def _init_tables(self):
        """Cria tabelas de usuários e sessões se não existirem"""
        if self.db.driver == 'postgresql':
            self.db.execute('''
                CREATE TABLE IF NOT EXISTS pycore_users (
                    id             SERIAL PRIMARY KEY,
                    username       TEXT UNIQUE NOT NULL,
                    email          TEXT UNIQUE NOT NULL,
                    password_hash  TEXT,
                    is_active      BOOLEAN DEFAULT TRUE,
                    is_staff       BOOLEAN DEFAULT FALSE,
                    is_superuser   BOOLEAN DEFAULT FALSE,
                    oauth_provider TEXT,
                    oauth_id       TEXT,
                    last_login     TIMESTAMP,
                    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            self.db.execute('''
                CREATE TABLE IF NOT EXISTS pycore_sessions (
                    session_key TEXT PRIMARY KEY,
                    user_id     INTEGER NOT NULL REFERENCES pycore_users(id) ON DELETE CASCADE,
                    expires_at  TIMESTAMP NOT NULL,
                    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
        else:
            self.db.execute('''
                CREATE TABLE IF NOT EXISTS pycore_users (
                    id             INTEGER PRIMARY KEY AUTOINCREMENT,
                    username       TEXT UNIQUE NOT NULL,
                    email          TEXT UNIQUE NOT NULL,
                    password_hash  TEXT,
                    is_active      INTEGER DEFAULT 1,
                    is_staff       INTEGER DEFAULT 0,
                    is_superuser   INTEGER DEFAULT 0,
                    oauth_provider TEXT,
                    oauth_id       TEXT,
                    last_login     TIMESTAMP,
                    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            self.db.execute('''
                CREATE TABLE IF NOT EXISTS pycore_sessions (
                    session_key TEXT PRIMARY KEY,
                    user_id     INTEGER NOT NULL,
                    expires_at  TIMESTAMP NOT NULL,
                    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

        print(f'✓ Auth backend: banco ({self.db.driver})')
        self._cleanup = SessionCleanup(self)
        self._cleanup.start()

    def create_user(self, username: str, email: str, password: str) -> User:
        existing = self.get_user_by_username(username)
        if existing:
            raise ValueError(f'Usuário "{username}" já existe')
        user = User(username=username, email=email)
        user.set_password(password)
        ph = self._ph()
        self.db.execute(
            f'INSERT INTO pycore_users (username, email, password_hash) VALUES ({ph}, {ph}, {ph})',
            [username, email, user.password_hash]
        )
        # Sem log aqui — a função de conveniência create_user() é responsável pelo log
        return self.get_user_by_username(username)

    def get_user(self, user_id: int) -> Optional[User]:
        ph  = self._ph()
        row = self.db.fetchone(
            f'SELECT * FROM pycore_users WHERE id = {ph}', (user_id,)
        )
        if row:
            user = self._row_to_user(row)
            user._authenticated = True
            rbac.load_user(user)
            return user
        return None

    def get_user_by_username(self, username: str) -> Optional[User]:
        ph  = self._ph()
        row = self.db.fetchone(
            f'SELECT * FROM pycore_users WHERE username = {ph} OR email = {ph}',
            (username, username)
        )
        if row:
            user = self._row_to_user(row)
            user._authenticated = True
            rbac.load_user(user)
            return user
        return None

    def authenticate(self, username: str, password: str) -> Optional[User]:
        user = self.get_user_by_username(username)
        if user and user.is_active and user.check_password(password):
            user._authenticated = True
            self._update_last_login(user)
            return user
        return None

    def create_session(self, user: User) -> str:
        session_key = secrets.token_urlsafe(32)
        expires_at  = _now() + timedelta(hours=SESSION_EXPIRE_HOURS)
        ph          = self._ph()
        self.db.execute(
            f'INSERT INTO pycore_sessions (session_key, user_id, expires_at) VALUES ({ph}, {ph}, {ph})',
            [session_key, user.id, expires_at.isoformat()]
        )
        return session_key

    def get_user_from_session(self, session_key: str) -> Optional[User]:
        if not session_key:
            return None
        ph  = self._ph()
        row = self.db.fetchone(
            f'SELECT user_id, expires_at FROM pycore_sessions WHERE session_key = {ph}',
            (session_key,)
        )
        if not row:
            return None
        expires_at = _parse_dt(row['expires_at'])
        if expires_at is None or _now() > expires_at:
            self.destroy_session(session_key)
            return None
        user = self.get_user(row['user_id'])
        if user:
            user._authenticated = True
        return user

    def destroy_session(self, session_key: str):
        ph = self._ph()
        self.db.execute(
            f'DELETE FROM pycore_sessions WHERE session_key = {ph}', (session_key,)
        )

    def destroy_all_sessions(self, user: User):
        """Remove todas as sessões de um usuário (logout em todos os dispositivos)"""
        ph = self._ph()
        self.db.execute(
            f'DELETE FROM pycore_sessions WHERE user_id = {ph}', (user.id,)
        )

    def cleanup_expired_sessions(self):
        """Remove sessões expiradas do banco manualmente"""
        ph = self._ph()
        self.db.execute(
            f'DELETE FROM pycore_sessions WHERE expires_at < {ph}',
            (_now().isoformat(),)
        )

    def update_password(self, user: User, new_password: str):
        user.set_password(new_password)
        ph = self._ph()
        self.db.execute(
            f'UPDATE pycore_users SET password_hash = {ph}, updated_at = {ph} WHERE id = {ph}',
            [user.password_hash, _now().isoformat(), user.id]
        )

    def deactivate_user(self, user: User):
        ph    = self._ph()
        value = False if self.db.driver == 'postgresql' else 0
        self.db.execute(
            f'UPDATE pycore_users SET is_active = {ph}, updated_at = {ph} WHERE id = {ph}',
            [value, _now().isoformat(), user.id]
        )

    def get_or_create_oauth_user(self, provider: str, oauth_id: str,
                                  email: str, username: str) -> User:
        ph = self._ph()
        row = self.db.fetchone(
            f'SELECT * FROM pycore_users WHERE oauth_provider = {ph} AND oauth_id = {ph}',
            (provider, oauth_id)
        )
        if row:
            user = self._row_to_user(row)
            user._authenticated = True
            self._update_last_login(user)
            return user

        row = self.db.fetchone(
            f'SELECT * FROM pycore_users WHERE email = {ph}', (email,)
        )
        if row:
            self.db.execute(
                f'UPDATE pycore_users SET oauth_provider = {ph}, oauth_id = {ph}, updated_at = {ph} WHERE id = {ph}',
                [provider, oauth_id, _now().isoformat(), row['id']]
            )
            user = self._row_to_user(row)
            user.oauth_provider = provider
            user.oauth_id       = oauth_id
            user._authenticated = True
            self._update_last_login(user)
            return user

        safe_username = self._ensure_unique_username(username)
        self.db.execute(
            f'INSERT INTO pycore_users (username, email, oauth_provider, oauth_id) VALUES ({ph}, {ph}, {ph}, {ph})',
            [safe_username, email, provider, oauth_id]
        )
        user = self.get_user_by_username(safe_username)
        user._authenticated = True
        self._update_last_login(user)
        return user

    def _ensure_unique_username(self, username: str) -> str:
        """
        Garante username único.
        CORREÇÃO: busca todos os usernames com o prefixo de uma vez
        para evitar N queries em loop.
        """
        ph   = self._ph()
        rows = self.db.fetchall(
            f"SELECT username FROM pycore_users WHERE username = {ph} OR username LIKE {ph}",
            (username, f"{username}%")
        )
        existing = {row['username'] for row in rows}
        if username not in existing:
            return username
        counter = 1
        while f"{username}{counter}" in existing:
            counter += 1
        return f"{username}{counter}"

    def _update_last_login(self, user: User):
        ph  = self._ph()
        now = _now()
        self.db.execute(
            f'UPDATE pycore_users SET last_login = {ph} WHERE id = {ph}',
            [now.isoformat(), user.id]
        )
        user.last_login = now

    def _row_to_user(self, row: dict) -> User:
        return User(
            id             = row['id'],
            username       = row['username'],
            email          = row['email'],
            password_hash  = row.get('password_hash', ''),
            is_active      = bool(row['is_active']),
            is_staff       = bool(row['is_staff']),
            is_superuser   = bool(row['is_superuser']),
            oauth_provider = row.get('oauth_provider'),
            oauth_id       = row.get('oauth_id'),
            last_login     = _parse_dt(row.get('last_login')),
        )

    def __repr__(self):
        return f'<DatabaseAuthBackend backend={self.db.driver}>'


# ─────────────────────────────────────────
# OAuth Providers
# ─────────────────────────────────────────

class OAuthProvider:
    """Classe base para provedores OAuth 2.0"""

    name         = ''
    auth_url     = ''
    token_url    = ''
    userinfo_url = ''
    scopes       = []

    def __init__(self):
        prefix             = self.name.upper()
        self.client_id     = os.getenv(f'{prefix}_CLIENT_ID', '')
        self.client_secret = os.getenv(f'{prefix}_CLIENT_SECRET', '')
        self.redirect_uri  = os.getenv(f'{prefix}_REDIRECT_URI', '')
        if not self.client_id or not self.client_secret:
            print(f'⚠ OAuth {self.name}: {prefix}_CLIENT_ID ou {prefix}_CLIENT_SECRET não configurado')

    def get_auth_url(self, state: str = None) -> str:
        params = {
            'client_id':     self.client_id,
            'redirect_uri':  self.redirect_uri,
            'response_type': 'code',
            'scope':         ' '.join(self.scopes),
        }
        if state:
            params['state'] = state
        return f"{self.auth_url}?{urllib.parse.urlencode(params)}"

    def exchange_code(self, code: str) -> dict:
        data = urllib.parse.urlencode({
            'client_id':     self.client_id,
            'client_secret': self.client_secret,
            'code':          code,
            'redirect_uri':  self.redirect_uri,
            'grant_type':    'authorization_code',
        }).encode()
        req = urllib.request.Request(
            self.token_url, data=data,
            headers={
                'Accept':       'application/json',
                'Content-Type': 'application/x-www-form-urlencoded',
            }
        )
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())

    def get_user_info(self, access_token: str) -> dict:
        req = urllib.request.Request(
            self.userinfo_url,
            headers={'Authorization': f'Bearer {access_token}'}
        )
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())

    def get_pycore_user_data(self, user_info: dict) -> dict:
        raise NotImplementedError

    def authenticate(self, code: str) -> Optional[User]:
        try:
            token_data   = self.exchange_code(code)
            access_token = token_data.get('access_token')
            if not access_token:
                raise ValueError(f'Token não retornado: {token_data}')
            user_info = self.get_user_info(access_token)
            data      = self.get_pycore_user_data(user_info)
            return auth_backend.get_or_create_oauth_user(
                provider = self.name,
                oauth_id = str(data['id']),
                email    = data['email'],
                username = data['username'],
            )
        except Exception as e:
            print(f'Erro OAuth {self.name}: {e}')
            return None


class GoogleOAuth(OAuthProvider):
    name         = 'google'
    auth_url     = 'https://accounts.google.com/o/oauth2/v2/auth'
    token_url    = 'https://oauth2.googleapis.com/token'
    userinfo_url = 'https://www.googleapis.com/oauth2/v3/userinfo'
    scopes       = ['openid', 'email', 'profile']

    def get_auth_url(self, state: str = None) -> str:
        params = {
            'client_id':     self.client_id,
            'redirect_uri':  self.redirect_uri,
            'response_type': 'code',
            'scope':         ' '.join(self.scopes),
            'access_type':   'offline',
        }
        if state:
            params['state'] = state
        return f"{self.auth_url}?{urllib.parse.urlencode(params)}"

    def get_pycore_user_data(self, user_info: dict) -> dict:
        return {
            'id':       user_info['sub'],
            'email':    user_info['email'],
            'username': user_info.get('name', user_info['email'].split('@')[0]),
        }


class GitHubOAuth(OAuthProvider):
    name         = 'github'
    auth_url     = 'https://github.com/login/oauth/authorize'
    token_url    = 'https://github.com/login/oauth/access_token'
    userinfo_url = 'https://api.github.com/user'
    scopes       = ['user:email', 'read:user']

    def get_user_info(self, access_token: str) -> dict:
        req = urllib.request.Request(
            self.userinfo_url,
            headers={'Authorization': f'Bearer {access_token}', 'User-Agent': 'Velox-OAuth'}
        )
        with urllib.request.urlopen(req) as resp:
            user_info = json.loads(resp.read())
        if not user_info.get('email'):
            req = urllib.request.Request(
                'https://api.github.com/user/emails',
                headers={'Authorization': f'Bearer {access_token}', 'User-Agent': 'Velox-OAuth'}
            )
            with urllib.request.urlopen(req) as resp:
                emails = json.loads(resp.read())
            user_info['email'] = next((e['email'] for e in emails if e.get('primary')), None)
        return user_info

    def get_pycore_user_data(self, user_info: dict) -> dict:
        return {
            'id':       user_info['id'],
            'email':    user_info.get('email', f"{user_info['login']}@github.com"),
            'username': user_info['login'],
        }


class FacebookOAuth(OAuthProvider):
    name         = 'facebook'
    auth_url     = 'https://www.facebook.com/v18.0/dialog/oauth'
    token_url    = 'https://graph.facebook.com/v18.0/oauth/access_token'
    userinfo_url = 'https://graph.facebook.com/me?fields=id,name,email'
    scopes       = ['email', 'public_profile']

    def get_pycore_user_data(self, user_info: dict) -> dict:
        return {
            'id':       user_info['id'],
            'email':    user_info.get('email', f"{user_info['id']}@facebook.com"),
            'username': user_info.get('name', f"fb_{user_info['id']}"),
        }


class DiscordOAuth(OAuthProvider):
    name         = 'discord'
    auth_url     = 'https://discord.com/api/oauth2/authorize'
    token_url    = 'https://discord.com/api/oauth2/token'
    userinfo_url = 'https://discord.com/api/users/@me'
    scopes       = ['identify', 'email']

    def get_pycore_user_data(self, user_info: dict) -> dict:
        return {
            'id':       user_info['id'],
            'email':    user_info.get('email', f"{user_info['username']}@discord.com"),
            'username': user_info['username'],
        }


_oauth_providers = {
    'google':   GoogleOAuth,
    'github':   GitHubOAuth,
    'facebook': FacebookOAuth,
    'discord':  DiscordOAuth,
}

def get_oauth_provider(name: str) -> Optional[OAuthProvider]:
    cls = _oauth_providers.get(name.lower())
    if not cls:
        raise ValueError(f'Provedor OAuth "{name}" não suportado. Use: {list(_oauth_providers.keys())}')
    return cls()


# ─────────────────────────────────────────
# RBAC — Roles e Permissões
# ─────────────────────────────────────────

class RBACManager:
    """
    Gerenciador de papéis e permissões em memória.
    Usado pelo SessionBasedAuthBackend e como cache pelo DatabaseAuthBackend.

    NOTA: Quando usar DatabaseAuthBackend, o RBACManager em memória serve
    apenas como cache de roles já definidos. A fonte verdadeira é o banco.
    Os dados são carregados via _sync_user_roles_permissions() a cada get_user().
    """

    def __init__(self):
        self._roles:            Dict[str, Set[str]] = {}   # role_name -> permissions
        self._user_roles:       Dict[int, Set[str]] = {}   # user_id -> role names
        self._user_extra_perms: Dict[int, Set[str]] = {}   # user_id -> extra permissions

    def create_role(self, name: str, permissions: List[str] = None) -> None:
        if name not in self._roles:
            self._roles[name] = set()
        if permissions:
            self._roles[name].update(permissions)
        print(f"✓ RBAC: role '{name}' criado com {len(self._roles[name])} permissões")

    def add_permission_to_role(self, role: str, permission: str) -> None:
        if role not in self._roles:
            raise ValueError(f"Role '{role}' não existe. Crie com create_role() primeiro.")
        self._roles[role].add(permission)

    def remove_permission_from_role(self, role: str, permission: str) -> None:
        if role in self._roles:
            self._roles[role].discard(permission)

    def get_role_permissions(self, role: str) -> Set[str]:
        return self._roles.get(role, set()).copy()

    def list_roles(self) -> List[str]:
        return list(self._roles.keys())

    def assign_role(self, user: 'User', role: str) -> None:
        if role not in self._roles:
            raise ValueError(f"Role '{role}' não existe. Crie com create_role() primeiro.")
        if user.id not in self._user_roles:
            self._user_roles[user.id] = set()
        self._user_roles[user.id].add(role)
        self._sync_user(user)

    def revoke_role(self, user: 'User', role: str) -> None:
        if user.id in self._user_roles:
            self._user_roles[user.id].discard(role)
        self._sync_user(user)

    def get_user_roles(self, user: 'User') -> List[str]:
        return list(self._user_roles.get(user.id, set()))

    def grant_permission(self, user: 'User', permission: str) -> None:
        if user.id not in self._user_extra_perms:
            self._user_extra_perms[user.id] = set()
        self._user_extra_perms[user.id].add(permission)
        self._sync_user(user)

    def revoke_permission(self, user: 'User', permission: str) -> None:
        if user.id in self._user_extra_perms:
            self._user_extra_perms[user.id].discard(permission)
        self._sync_user(user)

    def _sync_user(self, user: 'User') -> None:
        roles     = self._user_roles.get(user.id, set())
        extra     = self._user_extra_perms.get(user.id, set())
        all_perms = set(extra)
        for role in roles:
            all_perms.update(self._roles.get(role, set()))
        user.roles       = list(roles)
        user.permissions = all_perms

    def load_user(self, user: 'User') -> 'User':
        """
        Carrega roles e permissions em um usuário.
        No DatabaseAuthBackend, o banco sobrescreve este cache via
        _sync_user_roles_permissions(), então este método serve apenas
        para o backend de memória.
        """
        self._sync_user(user)
        return user

    def __repr__(self):
        return f'<RBACManager roles={len(self._roles)} users={len(self._user_roles)}>'


# Instância global do RBAC
rbac = RBACManager()


# ─────────────────────────────────────────
# Cleanup Automático de Sessões
# ─────────────────────────────────────────

SESSION_CLEANUP_INTERVAL_HOURS = float(os.getenv('SESSION_CLEANUP_INTERVAL_HOURS', 1))

class SessionCleanup:
    """
    Thread daemon em background que remove sessões expiradas do banco.
    Evita crescimento infinito da tabela pycore_sessions.
    Inicia automaticamente junto com o DatabaseAuthBackend.
    """

    def __init__(self, backend: 'DatabaseAuthBackend', interval_hours: float = None):
        self.backend        = backend
        self.interval       = (interval_hours or SESSION_CLEANUP_INTERVAL_HOURS) * 3600
        self._stop_event    = threading.Event()
        self._thread        = None
        self._removed_total = 0

    def _run(self):
        print(f"✓ SessionCleanup: iniciado (intervalo={SESSION_CLEANUP_INTERVAL_HOURS}h)")
        while not self._stop_event.wait(self.interval):
            self.run_once()

    def run_once(self) -> int:
        """Executa uma limpeza imediata. Retorna o número de sessões removidas."""
        try:
            ph     = self.backend._ph()
            result = self.backend.db.execute(
                f'DELETE FROM pycore_sessions WHERE expires_at < {ph}',
                (_now().isoformat(),)
            )
            removed = getattr(result, 'rowcount', 0) or 0
            self._removed_total += removed
            if removed:
                print(f"✓ SessionCleanup: {removed} removidas (total={self._removed_total})")
            return removed
        except Exception as e:
            print(f"⚠ SessionCleanup erro: {e}")
            return 0

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run, daemon=True, name='Velox-SessionCleanup'
        )
        self._thread.start()

    def stop(self, timeout: int = 5):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=timeout)
        print("✓ SessionCleanup: parado")

    def __repr__(self):
        alive = self._thread and self._thread.is_alive()
        return f'<SessionCleanup running={alive} interval={SESSION_CLEANUP_INTERVAL_HOURS}h removed={self._removed_total}>'


# ─────────────────────────────────────────
# Usuário Anônimo
# ─────────────────────────────────────────

class AnonymousUser(User):
    """
    Representa um usuário não autenticado.
    Sempre presente em request.user quando AuthMiddleware está ativo.
    Nunca é None — elimina a necessidade de checar `if request.user`.
    """
    def __init__(self):
        super().__init__(username='anonymous', is_active=False)
        self._authenticated = False

    @property
    def is_authenticated(self) -> bool:
        return False

    @property
    def is_anonymous(self) -> bool:
        return True

    def __repr__(self):
        return '<AnonymousUser>'


# ─────────────────────────────────────────
# Middleware de Autenticação Global
# ─────────────────────────────────────────

class AuthMiddleware:
    """
    Middleware que autentica automaticamente toda requisição.
    Injeta request.user em todas as rotas sem precisar de @login_required.

    Uso:
        from pycore.auth import AuthMiddleware
        app.use(AuthMiddleware())

    Nas rotas:
        def minha_rota(req, res):
            if req.user.is_authenticated:
                ...
            if req.user.has_role('admin'):
                ...
    """

    def process_request(self, request):
        session_key = (
            request.cookies.get('session_key') or
            request.headers.get('Authorization', '').replace('Bearer ', '').strip() or
            None
        )
        user = auth_backend.get_user_from_session(session_key) if session_key else None
        request.user = user or AnonymousUser()


# ─────────────────────────────────────────
# Seleção automática do backend
# ─────────────────────────────────────────

def _create_auth_backend() -> AuthBackend:
    backend = os.getenv('AUTH_BACKEND', 'memory').lower()
    if backend == 'database':
        return DatabaseAuthBackend()
    print('✓ Auth backend: memória')
    return SessionBasedAuthBackend()


# Instância global
auth_backend = _create_auth_backend()


# ─────────────────────────────────────────
# Helpers internos dos decoradores
# ─────────────────────────────────────────

def _get_session_key(request) -> Optional[str]:
    return (
        request.cookies.get('session_key') or
        request.headers.get('Authorization', '').replace('Bearer ', '').strip() or
        None
    )

def _make_error_response(status: int, message: str):
    from .response import Response
    response = Response()
    response.status_code = status
    response.json({'error': message})
    return response


# ─────────────────────────────────────────
# Decoradores  (todos com @wraps)
# ─────────────────────────────────────────

def login_required(func):
    """Decorador que exige login para acessar a rota."""
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        user = auth_backend.get_user_from_session(_get_session_key(request))
        if not user or not user.is_authenticated:
            return _make_error_response(401, 'Login required')
        request.user = user
        return func(request, *args, **kwargs)
    return wrapper


def staff_required(func):
    """Decorador que exige que o usuário seja staff."""
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        user = auth_backend.get_user_from_session(_get_session_key(request))
        if not user or not user.is_staff:
            return _make_error_response(403, 'Staff access required')
        request.user = user
        return func(request, *args, **kwargs)
    return wrapper


def superuser_required(func):
    """Decorador que exige que o usuário seja superuser."""
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        user = auth_backend.get_user_from_session(_get_session_key(request))
        if not user or not user.is_superuser:
            return _make_error_response(403, 'Superuser access required')
        request.user = user
        return func(request, *args, **kwargs)
    return wrapper


def role_required(*roles: str):
    """
    Decorador que exige que o usuário tenha pelo menos um dos papéis.

    Uso:
        @role_required('motorista')
        @role_required('admin', 'operador')   # qualquer um dos dois
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            user = auth_backend.get_user_from_session(_get_session_key(request))
            if not user or not user.has_any_role(*roles):
                return _make_error_response(403, f'Papel necessário: {list(roles)}')
            request.user = user
            return func(request, *args, **kwargs)
        return wrapper
    return decorator


def permission_required(*perms: str):
    """
    Decorador que exige que o usuário tenha TODAS as permissões listadas.

    Uso:
        @permission_required('rotas.criar')
        @permission_required('rotas.criar', 'viagens.ver')
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            user = auth_backend.get_user_from_session(_get_session_key(request))
            if not user or not user.has_all_permissions(*perms):
                return _make_error_response(403, f'Permissão necessária: {list(perms)}')
            request.user = user
            return func(request, *args, **kwargs)
        return wrapper
    return decorator


# ─────────────────────────────────────────
# Funções de conveniência — Auth
# ─────────────────────────────────────────

def login(request, user: User) -> str:
    """Faz login — retorna session_key"""
    return auth_backend.create_session(user)


def logout(request):
    """Faz logout — destrói a sessão"""
    session_key = _get_session_key(request)
    if session_key:
        auth_backend.destroy_session(session_key)


def get_current_user(request) -> Optional[User]:
    """Retorna o usuário autenticado ou None"""
    return auth_backend.get_user_from_session(_get_session_key(request))


def create_user(username: str, email: str, password: str) -> User:
    """Cria um novo usuário. Ponto único de log para criação."""
    user = auth_backend.create_user(username, email, password)
    print(f"✓ Usuário criado: {username} ({user.id})")
    return user


def authenticate(username: str, password: str) -> Optional[User]:
    """
    Autentica usuário com rate limiting.
    Retorna None se bloqueado por excesso de tentativas.
    """
    allowed, remaining = rate_limiter.check_attempt(username)
    if not allowed:
        print(f"⚠ Rate limit: {username} bloqueado por {remaining}s")
        return None

    user = auth_backend.authenticate(username, password)

    if user:
        rate_limiter.reset_attempts(username)
        print(f"✓ Login: {username}")
    else:
        rate_limiter.record_attempt(username)
        print(f"⚠ Login falhou: {username}")

    return user


def oauth_authenticate(provider: str, code: str) -> Optional[User]:
    """
    Autentica via OAuth.

    Uso:
        user = oauth_authenticate('google', request.query.get('code'))
        if user:
            session_key = login(request, user)
    """
    return get_oauth_provider(provider).authenticate(code)


def generate_oauth_state() -> str:
    """Gera state token para proteção CSRF no OAuth"""
    return secrets.token_urlsafe(16)


# ─────────────────────────────────────────
# Funções de conveniência — RBAC
# ─────────────────────────────────────────

def create_role(name: str, permissions: List[str] = None):
    """Cria um papel com permissões opcionais"""
    rbac.create_role(name, permissions)

def assign_role(user: User, role: str):
    """Atribui um papel ao usuário"""
    rbac.assign_role(user, role)

def revoke_role(user: User, role: str):
    """Remove um papel do usuário"""
    rbac.revoke_role(user, role)

def grant_permission(user: User, permission: str):
    """Concede uma permissão extra ao usuário"""
    rbac.grant_permission(user, permission)

def revoke_permission(user: User, permission: str):
    """Remove uma permissão extra do usuário"""
    rbac.revoke_permission(user, permission)