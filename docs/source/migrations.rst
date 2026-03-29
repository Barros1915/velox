Migrations
==========

Sistema de migrations para banco de dados.

Uso
---

.. code-block:: python

   from velox.migrations import MigrationManager

   migrations = MigrationManager(db='db/app.db')

---

Criar Tabela
------------

.. code-block:: python

   migrations.create_table(
       'users',
       {
           'id': 'INTEGER PRIMARY KEY AUTOINCREMENT',
           'username': 'TEXT NOT NULL UNIQUE',
           'email': 'TEXT NOT NULL UNIQUE',
           'password_hash': 'TEXT',
           'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
       }
   )

---

Drop Table
-----------

.. code-block:: python

   migrations.drop_table('users')

---

Add Column
----------

.. code-block:: python

   migrations.add_column('users', 'avatar_url', 'TEXT')

---

Drop Column
-----------

.. code-block:: python

   migrations.drop_column('users', 'avatar_url')

---

Rename Column
-------------

.. code-block:: python

   migrations.rename_column('users', 'old_name', 'new_name')

---

Create Index
------------

.. code-block:: python

   migrations.create_index('users', 'username')
   migrations.create_index('users', 'email', unique=True)

---

Drop Index
---------

.. code-block:: python

   migrations.drop_index('idx_users_username')

---

Execute SQL Customizado
-----------------------

.. code-block:: python

   migrations.execute('''
       CREATE TABLE IF NOT EXISTS posts (
           id INTEGER PRIMARY KEY AUTOINCREMENT,
           title TEXT NOT NULL,
           content TEXT
       )
   ''')

---

Listar Tabelas
--------------

.. code-block:: python

   tables = migrations.list_tables()
   print(tables)  # ['users', 'posts', 'comments']

---

Verificar Tabela
-----------------

.. code-block:: python

   if migrations.table_exists('users'):
       print('Tabela users existe')

---

Exportar Schema
--------------

.. code-block:: python

   schema = migrations.export_schema()
   print(schema)

---

Migrations com Model
--------------------

.. code-block:: python

   from velox.database import Model

   class User(Model):
       table = 'users'
       schema = {
           'username': str,
           'email': str,
           'created_at': datetime,
       }

   # Criar tabela automaticamente
   User.create_table()