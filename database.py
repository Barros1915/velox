"""
Módulo de Banco de Dados (ORM) do Velox

Suporta SQLite e PostgreSQL.
Instale psycopg2 para usar PostgreSQL:
    pip install psycopg2-binary

Recursos:
- ORM completo com Model
- Relacionamentos (ForeignKey, ManyToMany)
- Paginação nativa
- Queries encadeadas
- Migrations
"""

import os
import re
import sqlite3
import json
import threading
from datetime import datetime
from urllib.parse import urlparse
from typing import Any, Optional, List, Dict, TypeVar

T = TypeVar('T')

_SAFE_COL = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')

def _safe_col(name: str) -> str:
    """Valida nome de coluna para prevenir SQL injection."""
    if not _SAFE_COL.match(name):
        raise ValueError(f"Nome de coluna inválido: {name!r}")
    return name


# ─────────────────────────────────────────
# Connection Pool (SQLite thread-local)
# ─────────────────────────────────────────

class _SQLitePool:
    """
    Pool thread-local para SQLite.
    Cada thread tem sua própria conexão — evita conflitos de concorrência
    e elimina o overhead de abrir/fechar conexão por request.
    """
    def __init__(self, db_path: str):
        self._path  = db_path
        self._local = threading.local()

    def get(self) -> sqlite3.Connection:
        if not getattr(self._local, 'conn', None):
            conn = sqlite3.connect(self._path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute('PRAGMA journal_mode=WAL')   # melhor concorrência
            conn.execute('PRAGMA foreign_keys=ON')
            self._local.conn = conn
        return self._local.conn

    def close(self):
        conn = getattr(self._local, 'conn', None)
        if conn:
            conn.close()
            self._local.conn = None


class Database:
    """
    Gerenciador de banco de dados com connection pooling.
    SQLite: pool thread-local (uma conexão por thread, reutilizada).
    PostgreSQL: conexão única por instância (use pgBouncer para pool externo).
    """

    def __init__(self, db_name='app.db'):
        self.db_name      = db_name
        self._is_postgres = db_name.startswith(('postgresql://', 'postgres://'))
        self._pg_conn     = None          # PostgreSQL: conexão única
        self._pool        = None          # SQLite: pool thread-local
        if not self._is_postgres:
            self._pool = _SQLitePool(db_name)

    def _get_connection_string(self):
        parsed = urlparse(self.db_name)
        return {
            'host':     parsed.hostname or 'localhost',
            'port':     parsed.port or 5432,
            'database': parsed.path.lstrip('/') if parsed.path else '',
            'user':     parsed.username or 'postgres',
            'password': parsed.password or '',
        }

    def connect(self):
        if self._is_postgres:
            if self._pg_conn is None:
                try:
                    import psycopg2
                    self._pg_conn = psycopg2.connect(**self._get_connection_string())
                    self._pg_conn.autocommit = False
                except ImportError:
                    raise ImportError(
                        "psycopg2 não instalado. Execute:\n  pip install psycopg2-binary"
                    )
            return self._pg_conn
        return self._pool.get()

    # Alias para compatibilidade
    @property
    def connection(self):
        return self.connect()

    def close(self):
        if self._is_postgres and self._pg_conn:
            self._pg_conn.close()
            self._pg_conn = None
        elif self._pool:
            self._pool.close()

    def execute(self, query, params=None):
        conn   = self.connect()
        cursor = conn.cursor()
        try:
            cursor.execute(query, params) if params else cursor.execute(query)
            conn.commit()
            return cursor
        except Exception as e:
            conn.rollback()
            raise e

    def fetchone(self, query, params=None):
        row = self.execute(query, params).fetchone()
        return dict(row) if row else None

    def fetchall(self, query, params=None):
        return [dict(r) for r in self.execute(query, params).fetchall()]

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @property
    def driver(self) -> str:
        return 'postgresql' if self._is_postgres else 'sqlite'


# ─────────────────────────────────────────
# Relacionamentos
# ─────────────────────────────────────────

class ForeignKey:
    """Define um relacionamento ForeignKey"""
    
    def __init__(self, to: str, on_delete: str = 'CASCADE', related_name: str = None):
        self.to = to  # Nome do Model ou 'tabela.id'
        self.on_delete = on_delete  # CASCADE, SET_NULL, SET_DEFAULT, RESTRICT
        self.related_name = related_name


class ManyToMany:
    """Define um relacionamento ManyToMany"""
    
    def __init__(self, to: str, through: str = None, related_name: str = None):
        self.to = to
        self.through = through  # Tabela intermediária
        self.related_name = related_name


# ─────────────────────────────────────────
# Model Base
# ─────────────────────────────────────────

class Model:
    """
    Classe base para modelos do ORM.
    
    Uso:
        class User(Model):
            table = 'users'
            schema = {
                'username': str,
                'email': str,
                'password_hash': str,
                'is_active': bool,
                'created_at': datetime,
            }
            
            # Relacionamentos
            posts = ForeignKey('Post', on_delete='CASCADE', related_name='author')
            tags = ManyToMany('Tag', through='post_tags')
        
        # CRUD básico
        user = User.create(username='joao', email='joao@test.com')
        user = User.get(1)
        users = User.all()
        user.update(email='novo@test.com')
        user.delete()
        
        # Queries encadeadas
        users = User.where('is_active', '=', True).order_by('created_at', 'DESC').limit(10).get()
        
        # Paginação
        page = User.paginate(page=1, per_page=20)
        
        # Relacionamentos
        posts = user.posts
        user.posts.add(post)
        user.posts.remove(post)
    """
    
    table = None
    schema: Dict[str, type] = {}
    _relationships: Dict[str, Any] = {}
    _db = None
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    @classmethod
    def set_database(cls, db: Database):
        cls._db = db
    
    @classmethod
    def _get_db(cls) -> 'Database':
        if cls._db is None:
            db_uri = os.environ.get('DATABASE_URI', 'db/app.db')
            # Garante que a pasta existe para SQLite
            if not db_uri.startswith(('postgresql://', 'postgres://')):
                import pathlib
                pathlib.Path(db_uri).parent.mkdir(parents=True, exist_ok=True)
            cls._db = Database(db_uri)
        return cls._db
    
    @classmethod
    def _get_driver(cls) -> str:
        db = cls._get_db()
        return db.driver
    
    @classmethod
    def _placeholder(cls) -> str:
        """Retorna o placeholder correto para o banco"""
        return '?' if cls._get_driver() == 'sqlite' else '%s'
    
    @classmethod
    def _column_type(cls, col_type) -> str:
        """Converte tipo Python para tipo SQL"""
        if col_type == str:
            return "TEXT"
        elif col_type == int:
            return "INTEGER"
        elif col_type == float:
            return "REAL"
        elif col_type == bool:
            return "INTEGER"
        elif col_type == datetime:
            return "TIMESTAMP"
        elif col_type == dict:
            return "TEXT"  # JSON
        elif col_type == list:
            return "TEXT"  # JSON
        else:
            return "TEXT"
    
    @classmethod
    def create_table(cls):
        if not cls.table:
            raise ValueError("Nome da tabela não definido")
        
        driver = cls._get_driver()
        
        # Colunas do schema
        columns = []
        for col, col_type in cls.schema.items():
            col_def = f"{col} {cls._column_type(col_type)}"
            columns.append(col_def)
        
        # Criar tabela principal
        if driver == 'postgresql':
            query = f"CREATE TABLE IF NOT EXISTS {cls.table} (id SERIAL PRIMARY KEY, {', '.join(columns)})"
        else:
            query = f"CREATE TABLE IF NOT EXISTS {cls.table} (id INTEGER PRIMARY KEY AUTOINCREMENT, {', '.join(columns)})"
        
        cls._get_db().execute(query)
        
        # Criar tabelas de relacionamento ManyToMany
        for rel_name, rel in cls._relationships.items():
            if isinstance(rel, ManyToMany):
                through = rel.through or f"{cls.table}_{rel_name}"
                other_table = rel.to.lower() if rel.to[0].isupper() else rel.to
                
                if driver == 'postgresql':
                    query = f'''
                        CREATE TABLE IF NOT EXISTS {through} (
                            id SERIAL PRIMARY KEY,
                            {cls.table}_id INTEGER REFERENCES {cls.table}(id) ON DELETE CASCADE,
                            {other_table}_id INTEGER REFERENCES {other_table}(id) ON DELETE CASCADE,
                            UNIQUE({cls.table}_id, {other_table}_id)
                        )
                    '''
                else:
                    query = f'''
                        CREATE TABLE IF NOT EXISTS {through} (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            {cls.table}_id INTEGER,
                            {other_table}_id INTEGER,
                            FOREIGN KEY ({cls.table}_id) REFERENCES {cls.table}(id) ON DELETE CASCADE,
                            FOREIGN KEY ({other_table}_id) REFERENCES {other_table}(id) ON DELETE CASCADE,
                            UNIQUE({cls.table}_id, {other_table}_id)
                        )
                    '''
                cls._get_db().execute(query)
    
    @classmethod
    def _prepare_value(cls, value: Any) -> Any:
        """Prepara valor para inserção no banco"""
        if isinstance(value, (dict, list)):
            return json.dumps(value)
        elif isinstance(value, bool):
            return 1 if value else 0
        elif isinstance(value, datetime):
            return value.isoformat()
        return value
    
    @classmethod
    def create(cls, **kwargs) -> 'Model':
        if not cls.table:
            raise ValueError("Nome da tabela não definido")

        kwargs = {_safe_col(k): cls._prepare_value(v) for k, v in kwargs.items()}
        ph = cls._placeholder()
        columns = ', '.join(kwargs.keys())
        placeholders = ', '.join([ph for _ in kwargs])
        
        db = cls._get_db()
        if db.driver == 'postgresql':
            query = f"INSERT INTO {cls.table} ({columns}) VALUES ({placeholders}) RETURNING id"
            cursor = db.execute(query, list(kwargs.values()))
            row = cursor.fetchone()
            last_id = row[0] if row else None
        else:
            query = f"INSERT INTO {cls.table} ({columns}) VALUES ({placeholders})"
            cursor = db.execute(query, list(kwargs.values()))
            last_id = cursor.lastrowid
        
        return cls.get(last_id)
    
    @classmethod
    def get(cls, id) -> Optional['Model']:
        if not cls.table:
            raise ValueError("Nome da tabela não definido")
        
        ph = cls._placeholder()
        query = f"SELECT * FROM {cls.table} WHERE id = {ph}"
        row = cls._get_db().fetchone(query, (id,))
        
        if row:
            return cls(**row)
        return None
    
    @classmethod
    def first(cls, **kwargs) -> Optional['Model']:
        results = cls.where(**kwargs).limit(1).get()
        return results[0] if results else None
    
    @classmethod
    def find(cls, **kwargs) -> Optional['Model']:
        return cls.first(**kwargs)
    
    @classmethod
    def all(cls) -> List['Model']:
        if not cls.table:
            raise ValueError("Nome da tabela não definido")
        
        query = f"SELECT * FROM {cls.table}"
        rows = cls._get_db().fetchall(query)
        return [cls(**row) for row in rows]
    
    @classmethod
    def count(cls, **kwargs) -> int:
        """Conta registros"""
        if not cls.table:
            raise ValueError("Nome da tabela não definido")
        
        if kwargs:
            ph = cls._placeholder()
            conditions = ' AND '.join([f"{k} = {ph}" for k in kwargs.keys()])
            query = f"SELECT COUNT(*) as cnt FROM {cls.table} WHERE {conditions}"
            result = cls._get_db().fetchone(query, list(kwargs.values()))
        else:
            query = f"SELECT COUNT(*) as cnt FROM {cls.table}"
            result = cls._get_db().fetchone(query)
        
        return result['cnt'] if result else 0
    
    @classmethod
    def exists(cls, **kwargs) -> bool:
        """Verifica se existe algum registro"""
        return cls.count(**kwargs) > 0
    
    @classmethod
    def query(cls, sql: str, params=None) -> List[Dict]:
        db = cls._get_db()
        if params:
            return db.fetchall(sql, params)
        return db.fetchall(sql)
    
    @classmethod
    def where(cls, column: str, operator: str = None, value: Any = None) -> 'QueryBuilder':
        """Inicia uma query encadeada"""
        qb = QueryBuilder(cls.table)
        qb.set_database(cls._get_db())
        
        if value is None and operator is not None:
            qb._where.append((column, '=', operator))
        elif value is not None:
            qb._where.append((column, operator, value))
        else:
            qb._where.append((column, '=', column))
        
        return qb
    
    @classmethod
    def paginate(cls, page: int = 1, per_page: int = 20, **kwargs) -> Dict:
        """
        Retorna página de resultados.
        
        Returns:
            {
                'items': [...],
                'total': 100,
                'page': 1,
                'per_page': 20,
                'pages': 5,
                'has_next': True,
                'has_prev': False,
                'next_page': 2,
                'prev_page': None,
            }
        """
        page = max(1, page)
        per_page = max(1, min(per_page, 100))  # Limita a 100 por página
        
        # Contar total
        total = cls.count(**kwargs)
        
        # Calcular offset
        offset = (page - 1) * per_page
        total_pages = (total + per_page - 1) // per_page if total > 0 else 1
        
        # Buscar items
        qb = QueryBuilder(cls.table)
        qb.set_database(cls._get_db())
        
        for key, value in kwargs.items():
            qb._where.append((key, '=', value))
        
        qb.limit(per_page).offset(offset)
        
        return {
            'items': qb.get(),
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': total_pages,
            'has_next': page < total_pages,
            'has_prev': page > 1,
            'next_page': page + 1 if page < total_pages else None,
            'prev_page': page - 1 if page > 1 else None,
        }
    
    @classmethod
    def raw(cls, sql: str, *params) -> List[Dict]:
        """Executa SQL raw e retorna resultados"""
        return cls._get_db().fetchall(sql, params)
    
    @classmethod
    def truncate(cls):
        """Remove todos os registros da tabela"""
        if not cls.table:
            raise ValueError("Nome da tabela não definido")
        cls._get_db().execute(f"DELETE FROM {cls.table}")
    
    def update(self, **kwargs) -> 'Model':
        if not self.table:
            raise ValueError("Nome da tabela não definido")
        if not self.id:
            raise ValueError("Registro não existe")

        kwargs = {_safe_col(k): self._prepare_value(v) for k, v in kwargs.items()}
        ph = self._placeholder()
        set_clause = ', '.join([f"{k} = {ph}" for k in kwargs.keys()])
        query = f"UPDATE {self.table} SET {set_clause} WHERE id = {ph}"
        
        params = list(kwargs.values()) + [self.id]
        self._get_db().execute(query, params)
        
        for key, value in kwargs.items():
            setattr(self, key, value)
        
        return self
    
    def delete(self) -> 'Model':
        if not self.table:
            raise ValueError("Nome da tabela não definido")
        
        if not self.id:
            raise ValueError("Registro não existe")
        
        ph = self._placeholder()
        query = f"DELETE FROM {self.table} WHERE id = {ph}"
        self._get_db().execute(query, (self.id,))
        
        self.id = None
        return self
    
    def save(self) -> 'Model':
        if self.id:
            return self.update(**self._get_data())
        else:
            return self.__class__.create(**self._get_data())

    def _get_data(self) -> Dict:
        data = {}
        for key in self.schema.keys():
            if hasattr(self, key):
                data[key] = getattr(self, key)
        return data

    def related(self, field_name: str) -> List['Model']:
        """
        Retorna objetos relacionados via ForeignKey ou ManyToMany.

        Uso:
            class Post(Model):
                table = 'posts'
                schema = {'title': str, 'author_id': int}

            class Tag(Model):
                table = 'tags'
                schema = {'name': str}
                posts = ManyToMany('Post', through='post_tags')

            post = Post.get(1)
            tags = post.related('tags')   # ManyToMany
        """
        rel = self._relationships.get(field_name)
        if rel is None:
            raise AttributeError(f"Relacionamento '{field_name}' não definido em {self.__class__.__name__}")

        db = self._get_db()
        ph = self._placeholder()

        if isinstance(rel, ForeignKey):
            # Busca registros onde <tabela>_id = self.id
            target_table = rel.to.lower() + 's' if rel.to[0].isupper() else rel.to
            fk_col       = f"{self.table}_id"
            rows = db.fetchall(
                f"SELECT * FROM {target_table} WHERE {fk_col} = {ph}", (self.id,)
            )
            return rows

        if isinstance(rel, ManyToMany):
            through      = rel.through or f"{self.table}_{field_name}"
            other_table  = rel.to.lower() + 's' if rel.to[0].isupper() else rel.to
            other_id_col = f"{other_table[:-1] if other_table.endswith('s') else other_table}_id"
            self_id_col  = f"{self.table[:-1] if self.table.endswith('s') else self.table}_id"
            rows = db.fetchall(
                f"""SELECT t.* FROM {other_table} t
                    INNER JOIN {through} j ON j.{other_id_col} = t.id
                    WHERE j.{self_id_col} = {ph}""",
                (self.id,)
            )
            return rows

        return []

    def add_related(self, field_name: str, other: 'Model'):
        """Adiciona relacionamento ManyToMany."""
        rel = self._relationships.get(field_name)
        if not isinstance(rel, ManyToMany):
            raise AttributeError(f"'{field_name}' não é um ManyToMany")
        through     = rel.through or f"{self.table}_{field_name}"
        other_table = rel.to.lower() + 's' if rel.to[0].isupper() else rel.to
        self_col    = f"{self.table[:-1] if self.table.endswith('s') else self.table}_id"
        other_col   = f"{other_table[:-1] if other_table.endswith('s') else other_table}_id"
        ph = self._placeholder()
        if self._get_driver() == 'postgresql':
            self._get_db().execute(
                f"INSERT INTO {through} ({self_col}, {other_col}) VALUES ({ph}, {ph}) ON CONFLICT DO NOTHING",
                (self.id, other.id)
            )
        else:
            self._get_db().execute(
                f"INSERT OR IGNORE INTO {through} ({self_col}, {other_col}) VALUES ({ph}, {ph})",
                (self.id, other.id)
            )

    def remove_related(self, field_name: str, other: 'Model'):
        """Remove relacionamento ManyToMany."""
        rel = self._relationships.get(field_name)
        if not isinstance(rel, ManyToMany):
            raise AttributeError(f"'{field_name}' não é um ManyToMany")
        through     = rel.through or f"{self.table}_{field_name}"
        other_table = rel.to.lower() + 's' if rel.to[0].isupper() else rel.to
        self_col    = f"{self.table[:-1] if self.table.endswith('s') else self.table}_id"
        other_col   = f"{other_table[:-1] if other_table.endswith('s') else other_table}_id"
        ph = self._placeholder()
        self._get_db().execute(
            f"DELETE FROM {through} WHERE {self_col} = {ph} AND {other_col} = {ph}",
            (self.id, other.id)
        )
    
    def to_dict(self) -> Dict:
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
    
    def __repr__(self):
        return f"<{self.__class__.__name__} id={self.id}>"


# ─────────────────────────────────────────
# Query Builder
# ─────────────────────────────────────────

class QueryBuilder:
    """
    Query Builder para construção de queries encadeadas.
    
    Uso:
        users = User.where('is_active', '=', True) \\
                    .order_by('created_at', 'DESC') \\
                    .limit(10) \\
                    .offset(0) \\
                    .get()
        
        user = User.where('email', '=', 'test@test.com').first()
    """
    
    def __init__(self, table: str):
        self.table = table
        self._select = ['*']
        self._where = []
        self._order_by = []
        self._limit = None
        self._offset = None
        self._join = []
        self._group_by = []
        self._having = []
        self._db: Database = None
    
    def set_database(self, db: Database):
        self._db = db
        return self
    
    def select(self, *columns) -> 'QueryBuilder':
        """Seleciona colunas específicas"""
        if columns:
            self._select = list(columns)
        return self
    
    def where(self, column: str, operator: str = '=', value: Any = None) -> 'QueryBuilder':
        """Adiciona condição WHERE"""
        _safe_col(column)
        if value is None:
            self._where.append((column, '=', operator))
        else:
            self._where.append((column, operator, value))
        return self
    
    def or_where(self, column: str, operator: str = '=', value: Any = None) -> 'QueryBuilder':
        """Adiciona condição OR WHERE"""
        if value is None:
            self._where.append((column, '=', operator, 'OR'))
        else:
            self._where.append((column, operator, value, 'OR'))
        return self
    
    def where_in(self, column: str, values: List) -> 'QueryBuilder':
        """WHERE column IN (values)"""
        ph = '?' if self._db and self._db.driver == 'sqlite' else '%s'
        placeholders = ', '.join([ph for _ in values])
        self._where.append((column, 'IN', f"({placeholders})", 'AND', values))
        return self
    
    def where_like(self, column: str, pattern: str) -> 'QueryBuilder':
        """WHERE column LIKE pattern"""
        self._where.append((column, 'LIKE', pattern))
        return self
    
    def where_null(self, column: str) -> 'QueryBuilder':
        """WHERE column IS NULL"""
        self._where.append((column, 'IS', 'NULL'))
        return self
    
    def where_not_null(self, column: str) -> 'QueryBuilder':
        """WHERE column IS NOT NULL"""
        self._where.append((column, 'IS NOT', 'NULL'))
        return self
    
    def join(self, table: str, on: str, how: str = 'INNER') -> 'QueryBuilder':
        """Adiciona JOIN"""
        self._join.append((table, on, how))
        return self
    
    def left_join(self, table: str, on: str) -> 'QueryBuilder':
        return self.join(table, on, 'LEFT')
    
    def right_join(self, table: str, on: str) -> 'QueryBuilder':
        return self.join(table, on, 'RIGHT')
    
    def order_by(self, column: str, direction: str = 'ASC') -> 'QueryBuilder':
        """Ordena resultados"""
        self._order_by.append((column, direction.upper()))
        return self
    
    def group_by(self, *columns) -> 'QueryBuilder':
        """Agrupa resultados"""
        self._group_by.extend(columns)
        return self
    
    def having(self, column: str, operator: str, value: Any) -> 'QueryBuilder':
        """Condição HAVING"""
        self._having.append((column, operator, value))
        return self
    
    def limit(self, limit: int) -> 'QueryBuilder':
        """Limita quantidade de resultados"""
        self._limit = limit
        return self
    
    def offset(self, offset: int) -> 'QueryBuilder':
        """Desloca resultados"""
        self._offset = offset
        return self
    
    def page(self, page: int, per_page: int = 20) -> 'QueryBuilder':
        """Paginação"""
        self._offset = (page - 1) * per_page
        self._limit = per_page
        return self
    
    def _build_query(self) -> tuple:
        """Constrói a query SQL"""
        ph = '?' if self._db and self._db.driver == 'sqlite' else '%s'
        
        columns = ', '.join(self._select) if self._select else '*'
        query = f"SELECT {columns} FROM {self.table}"
        params = []
        
        # Joins
        for table, on, how in self._join:
            query += f" {how} JOIN {table} ON {on}"
        
        # Where
        if self._where:
            conditions = []
            for cond in self._where:
                if len(cond) >= 4 and cond[3] == 'OR':
                    col, op, val = cond[0], cond[1], cond[2]
                    if isinstance(val, (list, tuple)):
                        placeholders = ', '.join([ph for _ in val])
                        conditions.append(f"{col} {op} ({placeholders})")
                        params.extend(val)
                    else:
                        conditions.append(f"{col} {op} {ph}")
                        params.append(val)
                elif len(cond) >= 5:
                    col, op, val = cond[0], cond[1], cond[4]
                    placeholders = ', '.join([ph for _ in val])
                    conditions.append(f"{col} {op} ({placeholders})")
                    params.extend(val)
                elif cond[1] == 'IS' and cond[2] == 'NULL':
                    conditions.append(f"{cond[0]} {cond[1]} {cond[2]}")
                elif cond[1] == 'IS NOT' and cond[2] == 'NULL':
                    conditions.append(f"{cond[0]} {cond[1]} {cond[2]}")
                else:
                    conditions.append(f"{cond[0]} {cond[1]} {ph}")
                    params.append(cond[2])
            
            query += " WHERE " + " AND ".join(conditions)
        
        # Group by
        if self._group_by:
            query += " GROUP BY " + ", ".join(self._group_by)
        
        # Having
        if self._having:
            havings = []
            for col, op, val in self._having:
                havings.append(f"{col} {op} {ph}")
                params.append(val)
            query += " HAVING " + " AND ".join(havings)
        
        # Order by
        if self._order_by:
            orders = [f"{col} {dir}" for col, dir in self._order_by]
            query += " ORDER BY " + ", ".join(orders)
        
        # Limit
        if self._limit is not None:
            query += f" LIMIT {self._limit}"
        
        # Offset
        if self._offset is not None:
            query += f" OFFSET {self._offset}"
        
        return query, params
    
    def get(self) -> List[Dict]:
        """Executa a query e retorna resultados"""
        db = self._db or Database(os.environ.get('DATABASE_URI', 'db/app.db'))
        query, params = self._build_query()
        return [dict(r) for r in db.fetchall(query, params if params else None)]

    def first(self) -> Optional[Dict]:
        """Retorna o primeiro resultado"""
        results = self.limit(1).get()
        return results[0] if results else None

    def count(self) -> int:
        """Conta resultados"""
        db = self._db or Database(os.environ.get('DATABASE_URI', 'db/app.db'))
        original_select = self._select
        self._select    = ['COUNT(*) as cnt']
        query, params   = self._build_query()
        self._select    = original_select
        result = db.fetchone(query, params if params else None)
        return result['cnt'] if result else 0
    
    def paginate(self, page: int = 1, per_page: int = 20) -> Dict:
        """Retorna página de resultados"""
        page = max(1, page)
        per_page = max(1, min(per_page, 100))
        
        total = self.count()
        offset = (page - 1) * per_page
        total_pages = (total + per_page - 1) // per_page if total > 0 else 1
        
        self.limit(per_page).offset(offset)
        
        return {
            'items': self.get(),
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': total_pages,
            'has_next': page < total_pages,
            'has_prev': page > 1,
            'next_page': page + 1 if page < total_pages else None,
            'prev_page': page - 1 if page > 1 else None,
        }


# ─────────────────────────────────────────
# Funções de conveniência
# ─────────────────────────────────────────

def create_database(db_name: str = None) -> Database:
    """Cria uma instância do banco de dados"""
    if db_name is None:
        db_name = os.environ.get('DATABASE_URI', 'db/app.db')
    # Garante que a pasta existe para SQLite
    if not db_name.startswith(('postgresql://', 'postgres://')):
        import pathlib
        pathlib.Path(db_name).parent.mkdir(parents=True, exist_ok=True)
    return Database(db_name)


# ─────────────────────────────────────────
# Migrations
# ─────────────────────────────────────────

class Migration:
    """Classe base para migrations"""
    
    def up(self):
        """Aplica a migration"""
        raise NotImplementedError
    
    def down(self):
        """Reverte a migration"""
        raise NotImplementedError


class Migrations:
    """Gerenciador de migrations"""
    
    def __init__(self, db: Database = None):
        self.db = db or create_database()
        self._ensure_table()
    
    def _ensure_table(self):
        """Cria tabela de migrations se não existir"""
        if self.db.driver == 'postgresql':
            self.db.execute('''
                CREATE TABLE IF NOT EXISTS pycore_migrations (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
        else:
            self.db.execute('''
                CREATE TABLE IF NOT EXISTS pycore_migrations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
    
    def get_applied(self) -> List[str]:
        """Retorna lista de migrations aplicadas"""
        rows = self.db.fetchall("SELECT name FROM pycore_migrations ORDER BY id")
        return [row['name'] for row in rows]
    
    def is_applied(self, name: str) -> bool:
        """Verifica se uma migration foi aplicada"""
        return name in self.get_applied()
    
    def apply(self, name: str, migration: Migration):
        """Aplica uma migration"""
        if not self.is_applied(name):
            migration.up()
            ph = '?' if self.db.driver == 'sqlite' else '%s'
            self.db.execute(f"INSERT INTO pycore_migrations (name) VALUES ({ph})", (name,))
            print(f"[Migration] Applied: {name}")
    
    def rollback(self, name: str, migration: Migration):
        """Reverte uma migration"""
        if self.is_applied(name):
            migration.down()
            ph = '?' if self.db.driver == 'sqlite' else '%s'
            self.db.execute(f"DELETE FROM pycore_migrations WHERE name = {ph}", (name,))
            print(f"[Migration] Rolled back: {name}")


# ─────────────────────────────────────────
# Banco de dados ASSÍNCRONO
# ─────────────────────────────────────────

class AsyncDatabase:
    """
    Banco de dados assíncrono — não bloqueia o event loop no modo ASGI.

    SQLite:     pip install aiosqlite
    PostgreSQL: pip install asyncpg

    Uso:
        db = AsyncDatabase('db/app.db')

        async def handler(req, res):
            rows = await db.fetchall('SELECT * FROM posts')
            res.json(rows)

    Ou via AsyncModel:
        class Post(AsyncModel):
            table  = 'posts'
            schema = {'title': str, 'content': str}

        posts = await Post.all()
        post  = await Post.get(1)
        post  = await Post.create(title='Olá', content='...')
    """

    def __init__(self, db_name: str = 'db/app.db'):
        self.db_name      = db_name
        self._is_postgres = db_name.startswith(('postgresql://', 'postgres://'))
        self._pg_pool     = None   # asyncpg pool
        self._sqlite_conn = None   # aiosqlite connection

    def _pg_dsn(self) -> str:
        return self.db_name

    async def connect(self):
        if self._is_postgres:
            if self._pg_pool is None:
                try:
                    import asyncpg
                    self._pg_pool = await asyncpg.create_pool(self._pg_dsn())
                except ImportError:
                    raise ImportError(
                        "asyncpg não instalado. Execute:\n  pip install asyncpg"
                    )
            return self._pg_pool
        else:
            if self._sqlite_conn is None:
                try:
                    import aiosqlite
                    import pathlib
                    pathlib.Path(self.db_name).parent.mkdir(parents=True, exist_ok=True)
                    self._sqlite_conn = await aiosqlite.connect(self.db_name)
                    self._sqlite_conn.row_factory = aiosqlite.Row
                    await self._sqlite_conn.execute('PRAGMA journal_mode=WAL')
                    await self._sqlite_conn.execute('PRAGMA foreign_keys=ON')
                except ImportError:
                    raise ImportError(
                        "aiosqlite não instalado. Execute:\n  pip install aiosqlite"
                    )
            return self._sqlite_conn

    async def close(self):
        if self._is_postgres and self._pg_pool:
            await self._pg_pool.close()
            self._pg_pool = None
        elif self._sqlite_conn:
            await self._sqlite_conn.close()
            self._sqlite_conn = None

    async def execute(self, query: str, params=None):
        conn = await self.connect()
        if self._is_postgres:
            async with conn.acquire() as c:
                if params:
                    return await c.execute(query, *params)
                return await c.execute(query)
        else:
            cursor = await conn.execute(query, params or ())
            await conn.commit()
            return cursor

    async def fetchone(self, query: str, params=None) -> Optional[Dict]:
        conn = await self.connect()
        if self._is_postgres:
            async with conn.acquire() as c:
                row = await c.fetchrow(query, *(params or ()))
                return dict(row) if row else None
        else:
            cursor = await conn.execute(query, params or ())
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def fetchall(self, query: str, params=None) -> List[Dict]:
        conn = await self.connect()
        if self._is_postgres:
            async with conn.acquire() as c:
                rows = await c.fetch(query, *(params or ()))
                return [dict(r) for r in rows]
        else:
            cursor = await conn.execute(query, params or ())
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    @property
    def driver(self) -> str:
        return 'postgresql' if self._is_postgres else 'sqlite'

    def _ph(self) -> str:
        return '$1' if self._is_postgres else '?'

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, *_):
        await self.close()


class AsyncModel:
    """
    Model assíncrono — mesma API do Model síncrono, mas com await.

    Uso:
        class Post(AsyncModel):
            table  = 'posts'
            schema = {'title': str, 'content': str, 'published': bool}

        # No handler async:
        @app.get('/posts')
        async def list_posts(req, res):
            posts = await Post.all()
            res.json([p.to_dict() for p in posts])

        @app.post('/posts')
        async def create_post(req, res):
            data = req.json or {}
            post = await Post.create(**data)
            res.json(post.to_dict(), status=201)

    Configuração:
        Post.set_database(AsyncDatabase('db/app.db'))
        # ou via env: DATABASE_URI=db/app.db
    """

    table:  str              = None
    schema: Dict[str, type]  = {}
    _relationships: Dict     = {}
    _async_db: 'AsyncDatabase' = None

    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        for k, v in kwargs.items():
            setattr(self, k, v)

    @classmethod
    def set_database(cls, db: 'AsyncDatabase'):
        cls._async_db = db

    @classmethod
    def _get_db(cls) -> 'AsyncDatabase':
        if cls._async_db is None:
            cls._async_db = AsyncDatabase(os.environ.get('DATABASE_URI', 'db/app.db'))
        return cls._async_db

    @classmethod
    def _ph(cls) -> str:
        return '%s' if cls._get_db()._is_postgres else '?'

    @classmethod
    def _col_type(cls, t) -> str:
        return {str: 'TEXT', int: 'INTEGER', float: 'REAL',
                bool: 'INTEGER', datetime: 'TIMESTAMP',
                dict: 'TEXT', list: 'TEXT'}.get(t, 'TEXT')

    @classmethod
    def _prep(cls, value: Any) -> Any:
        if isinstance(value, (dict, list)):
            return json.dumps(value)
        if isinstance(value, bool):
            return 1 if value else 0
        if isinstance(value, datetime):
            return value.isoformat()
        return value

    @classmethod
    async def create_table(cls):
        db     = cls._get_db()
        cols   = ', '.join(f"{c} {cls._col_type(t)}" for c, t in cls.schema.items())
        if db._is_postgres:
            q = f"CREATE TABLE IF NOT EXISTS {cls.table} (id SERIAL PRIMARY KEY, {cols})"
        else:
            q = f"CREATE TABLE IF NOT EXISTS {cls.table} (id INTEGER PRIMARY KEY AUTOINCREMENT, {cols})"
        await db.execute(q)

    @classmethod
    async def create(cls, **kwargs) -> 'AsyncModel':
        db   = cls._get_db()
        data = {_safe_col(k): cls._prep(v) for k, v in kwargs.items()}
        ph   = cls._ph()
        cols = ', '.join(data.keys())
        if db._is_postgres:
            holders = ', '.join(f'${i+1}' for i in range(len(data)))
            q   = f"INSERT INTO {cls.table} ({cols}) VALUES ({holders}) RETURNING id"
            row = await db.fetchone(q, list(data.values()))
            return await cls.get(row['id'])
        else:
            holders = ', '.join([ph] * len(data))
            q = f"INSERT INTO {cls.table} ({cols}) VALUES ({holders})"
            cursor = await db.execute(q, list(data.values()))
            return await cls.get(cursor.lastrowid)

    @classmethod
    async def get(cls, id) -> Optional['AsyncModel']:
        ph  = cls._ph()
        row = await cls._get_db().fetchone(
            f"SELECT * FROM {cls.table} WHERE id = {ph}", (id,)
        )
        return cls(**row) if row else None

    @classmethod
    async def all(cls) -> List['AsyncModel']:
        rows = await cls._get_db().fetchall(f"SELECT * FROM {cls.table}")
        return [cls(**r) for r in rows]

    @classmethod
    async def where(cls, column: str, operator: str = '=', value: Any = None) -> List['AsyncModel']:
        """Filtro simples. Para queries complexas use AsyncDatabase diretamente."""
        _safe_col(column)
        ph  = cls._ph()
        val = value if value is not None else operator
        rows = await cls._get_db().fetchall(
            f"SELECT * FROM {cls.table} WHERE {column} {operator if value is not None else '='} {ph}",
            (val,)
        )
        return [cls(**r) for r in rows]

    @classmethod
    async def count(cls) -> int:
        result = await cls._get_db().fetchone(f"SELECT COUNT(*) as cnt FROM {cls.table}")
        return result['cnt'] if result else 0

    @classmethod
    async def paginate(cls, page: int = 1, per_page: int = 20) -> Dict:
        page     = max(1, page)
        per_page = max(1, min(per_page, 100))
        total    = await cls.count()
        offset   = (page - 1) * per_page
        pages    = max(1, (total + per_page - 1) // per_page)
        ph       = cls._ph()
        rows     = await cls._get_db().fetchall(
            f"SELECT * FROM {cls.table} LIMIT {ph} OFFSET {ph}", (per_page, offset)
        )
        return {
            'items':     [cls(**r) for r in rows],
            'total':     total,
            'page':      page,
            'per_page':  per_page,
            'pages':     pages,
            'has_next':  page < pages,
            'has_prev':  page > 1,
            'next_page': page + 1 if page < pages else None,
            'prev_page': page - 1 if page > 1 else None,
        }

    async def save(self) -> 'AsyncModel':
        if self.id:
            return await self.update(**self._get_data())
        return await self.__class__.create(**self._get_data())

    async def update(self, **kwargs) -> 'AsyncModel':
        db   = self._get_db()
        data = {_safe_col(k): self._prep(v) for k, v in kwargs.items()}
        ph   = self._ph()
        if db._is_postgres:
            sets = ', '.join(f"{k} = ${i+1}" for i, k in enumerate(data.keys()))
            q    = f"UPDATE {self.table} SET {sets} WHERE id = ${len(data)+1}"
        else:
            sets = ', '.join(f"{k} = {ph}" for k in data.keys())
            q    = f"UPDATE {self.table} SET {sets} WHERE id = {ph}"
        await db.execute(q, list(data.values()) + [self.id])
        for k, v in kwargs.items():
            setattr(self, k, v)
        return self

    async def delete(self) -> None:
        ph = self._ph()
        await self._get_db().execute(
            f"DELETE FROM {self.table} WHERE id = {ph}", (self.id,)
        )
        self.id = None

    def _get_data(self) -> Dict:
        return {k: getattr(self, k) for k in self.schema if hasattr(self, k)}

    def to_dict(self) -> Dict:
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}

    def __repr__(self):
        return f"<{self.__class__.__name__} id={self.id}>"
