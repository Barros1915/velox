Banco de Dados
=============

O Velox inclui um ORM completo com suporte a SQLite e PostgreSQL.

Configuração
-----------

Escolha o banco de dados via variável de ambiente:

.. code-block:: bash

   # SQLite (padrão)
   DATABASE_URI=db/app.db

   # PostgreSQL
   DATABASE_URI=postgresql://user:pass@localhost:5432/mydb

Criando umaConexão
------------------

.. code-block:: python

   from velox.database import Database

   # SQLite (padrão)
   db = Database('db/app.db')

   # PostgreSQL
   db = Database('postgresql://user:pass@localhost:5432/mydb')

   # Use contexto
   with db:
       rows = db.fetchall('SELECT * FROM users')

Operações Básicas
----------------

.. code-block:: python

   from velox.database import Database

   db = Database('db/app.db')

   # INSERT
   db.execute('INSERT INTO users (name) VALUES (?)', ('João',))

   # SELECT one
   user = db.fetchone('SELECT * FROM users WHERE id = ?', (1,))

   # SELECT all
   users = db.fetchall('SELECT * FROM users')

Modelo (ORM)
------------

.. code-block:: python

   from velox.database import Model

   class User(Model):
       table = 'users'
       schema = {
           'name': str,
           'email': str,
           'is_active': bool,
       }

   # Criar tabela
   User.create_table()

   # CREATE
   user = User.create(name='João', email='joao@test.com')

   # READ
   user = User.get(1)
   all_users = User.all()

   # UPDATE
   user.update(name='João atualizado')

   # DELETE
   user.delete()

Queries Encadeadas
--------------

.. code-block:: python

   from velox.database import Model

   class Post(Model):
       table = 'posts'
       schema = {'title': str, 'content': str, 'published': bool}

   #WHERE + ORDER + LIMIT
   posts = (Post
       .where('published', '=', True)
       .order_by('created_at', 'DESC')
       .limit(10)
       .get())

   # Paginação
   result = Post.paginate(page=1, per_page=20)

   # Contagem
   count = Post.count(published=True)
   exists = Post.exists(email='joao@test.com')

Relacionamentos
---------------

.. code-block:: python

   from velox.database import Model, ForeignKey, ManyToMany

   class Author(Model):
       table = 'authors'
       schema = {'name': str}
       books = ManyToMany('Book', through='author_books')

   class Book(Model):
       table = 'books'
       schema = {'title': str}
       author = ForeignKey('Author', on_delete='CASCADE')

   # Acessar relacionados
   author = Author.get(1)
   books = author.related('books')

PostgreSQL
-----------

Instale o driver:

.. code-block:: bash

   pip install psycopg2-binary

Configuração:

.. code-block:: python

   import os
   os.environ['DATABASE_URI'] = 'postgresql://user:pass@localhost:5432/mydb'

Async Database
-------------

Para modo ASGI, use banco assíncrono:

.. code-block:: python

   from velox.database import AsyncDatabase

   db = AsyncDatabase('db/app.db')

   # PostgreSQL
   db = AsyncDatabase('postgresql://user:pass@localhost:5432/mydb')

   async def handler(req, res):
       rows = await db.fetchall('SELECT * FROM posts')
       res.json(rows)

Instale os drivers:

.. code-block:: bash

   pip install aiosqlite     # SQLite async
   pip install asyncpg       # PostgreSQL async

Próximos Passos
---------------

- Leia :doc:`models` para modelos avançados
- Explore :doc:`queries` para queries complexas