"""
Sistema de Migrations - Velox
Similar ao Django migrations
"""

import os
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional


class Migration:
    """Representa uma migration"""
    
    def __init__(self, name: str, dependencies: List[str] = None):
        self.name = name
        self.dependencies = dependencies or []
        self.applied = False
    
    def forward(self):
        """Aplica a migration"""
        raise NotImplementedError
    
    def backward(self):
        """Reverte a migration"""
        raise NotImplementedError


class MigrationManager:
    """Gerenciador de migrations"""
    
    def __init__(self, db_path: str = 'db.sqlite3'):
        self.db_path = db_path
        self.migrations = []
        self._ensure_table()
    
    def _ensure_table(self):
        """Cria tabela de migrations se não existir"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pycore_migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
    
    def register(self, migration: Migration):
        """Registra uma migration"""
        self.migrations.append(migration)
    
    def create_table(self, table_name: str, fields: Dict[str, str]):
        """Cria uma tabela"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        columns = ', '.join([f'{name} {dtype}' for name, dtype in fields.items()])
        
        cursor.execute(f'CREATE TABLE IF NOT EXISTS {table_name} ({columns})')
        conn.commit()
        conn.close()
    
    def drop_table(self, table_name: str):
        """Deleta uma tabela"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(f'DROP TABLE IF EXISTS {table_name}')
        conn.commit()
        conn.close()
    
    def add_column(self, table_name: str, column_name: str, dtype: str):
        """Adiciona coluna"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(f'ALTER TABLE {table_name} ADD COLUMN {column_name} {dtype}')
            conn.commit()
        except sqlite3.OperationalError:
            pass  # Coluna já existe
        finally:
            conn.close()
    
    def drop_column(self, table_name: str, column_name: str):
        """Remove coluna"""
        # SQLite não suporta DROP COLUMN diretamente
        # Necesita recriar a tabela
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Pegar schema atual
        cursor.execute(f'PRAGMA table_info({table_name})')
        columns = cursor.fetchall()
        
        # Filtrar coluna a ser removida
        new_columns = [col for col in columns if col[1] != column_name]
        
        if len(new_columns) != len(columns):
            # Criar nova tabela
            col_defs = ', '.join([f'{c[1]} {c[2]}' for c in new_columns])
            cursor.execute(f'CREATE TABLE {table_name}_new ({col_defs})')
            
            # Copiar dados
            col_names = ', '.join([c[1] for c in new_columns])
            cursor.execute(f'INSERT INTO {table_name}_new SELECT {col_names} FROM {table_name}')
            
            # Remover tabela antiga e renomear
            cursor.execute(f'DROP TABLE {table_name}')
            cursor.execute(f'ALTER TABLE {table_name}_new RENAME TO {table_name}')
            
            conn.commit()
        
        conn.close()
    
    def apply_all(self):
        """Aplica todas as migrations pendentes"""
        applied = self.get_applied()
        
        for migration in self.migrations:
            if migration.name not in applied:
                print(f'Applying migration: {migration.name}')
                migration.forward()
                self._record_migration(migration.name)
                print(f'Applied: {migration.name}')
    
    def get_applied(self) -> List[str]:
        """Retorna migrations já aplicadas"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT name FROM pycore_migrations ORDER BY applied_at')
        migrations = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        return migrations
    
    def _record_migration(self, name: str):
        """Registra que uma migration foi aplicada"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('INSERT INTO pycore_migrations (name) VALUES (?)', (name,))
        conn.commit()
        conn.close()
    
    def rollback(self, migration_name: str):
        """Reverte até uma migration específica"""
        applied = self.get_applied()
        
        # Encontrar a migration
        for migration in reversed(self.migrations):
            if migration.name in applied and migration.name != migration_name:
                print(f'Rolling back: {migration.name}')
                migration.backward()
                self._remove_migration_record(migration.name)
    
    def _remove_migration_record(self, name: str):
        """Remove registro de migration"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM pycore_migrations WHERE name = ?', (name,))
        conn.commit()
        conn.close()
    
    def make_migration(self, name: str):
        """Cria um arquivo de migration"""
        migrations_dir = Path('migrations')
        migrations_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        filename = f'{timestamp}_{name}.py'
        
        content = f'''"""
Migration: {name}
Created: {datetime.now()}
"""

from velox.migrations import Migration


class CreateMigration(Migration):
    def __init__(self):
        super().__init__("{name}")

    def forward(self):
        # Adicione suas operações aqui
        # Exemplo:
        # self.create_table('minha_tabela', {{
        #     'id':   'INTEGER PRIMARY KEY AUTOINCREMENT',
        #     'nome': 'TEXT NOT NULL',
        # }})
        pass

    def backward(self):
        # Adicione operações de rollback
        # Exemplo: self.drop_table('minha_tabela')
        pass
'''
        
        with open(migrations_dir / filename, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f'Migration created: {filename}')


# Instância global
manager = MigrationManager()


# Decorador para migrations
def migration(name: str):
    """Decora uma classe como migration"""
    def decorator(cls):
        manager.register(cls(name))
        return cls
    return decorator


# Funções de conveniência
def create_table(table_name: str, fields: Dict[str, str]):
    """Cria tabela"""
    manager.create_table(table_name, fields)

def drop_table(table_name: str):
    """Deleta tabela"""
    manager.drop_table(table_name)

def add_column(table_name: str, column_name: str, dtype: str):
    """Adiciona coluna"""
    manager.add_column(table_name, column_name, dtype)

def migrate():
    """Aplica migrations"""
    manager.apply_all()

def rollback(target: str = None):
    """Reverte migrations"""
    manager.rollback(target or '')

def makemigration(name: str):
    """Cria arquivo de migration"""
    manager.make_migration(name)
