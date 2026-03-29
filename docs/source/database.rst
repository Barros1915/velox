Banco de Dados
==============

O Velox inclui um ORM completo com suporte a SQLite, PostgreSQL, **MySQL** e **MariaDB**.

Configuração
------------

Escolha o banco de dados via variável de ambiente:

.. code-block:: bash

   # SQLite (padrão)
   DATABASE_URI=db/app.db

   # PostgreSQL
   DATABASE_URI=postgresql://user:pass@localhost:5432/mydb

   # MySQL
   DATABASE_URI=mysql://user:pass@localhost:3306/mydb

   # MariaDB
   DATABASE_URI=mariadb://user:pass@localhost:3306/mydb

Instalação dos Drivers
----------------------

.. code-block:: bash

   # SQLite (padrão, zero dependências)
   pip install velox-web

   # PostgreSQL
   pip install velox-web[postgres]
   # ou: pip install psycopg2-binary

   # MySQL
   pip install velox-web[mysql]
   # ou: pip install mysql-connector-python

   # MariaDB (usa o mesmo driver do MySQL)
   pip install velox-web[mariadb]

   # Tudo (async completo)
   pip install velox-web[full]
   # aiosqlite + asyncpg + aiomysql

---

Criando uma Conexão
-------------------

.. code-block:: python

   from velox.database import Database

   # SQLite (padrão)
   db = Database('db/app.db')

   # PostgreSQL
   db = Database('postgresql://user:pass@localhost:5432/mydb')

   # MySQL / MariaDB
   db = Database('mysql://user:pass@localhost:3306/mydb')
   db = Database('mariadb://user:pass@localhost:3306/mydb')

   # Use contexto
   with db:
       rows = db.fetchall('SELECT * FROM users')

---

Operações Básicas
------------------

.. code-block:: python

   from velox.database import Database

   db = Database('mysql://user:pass@localhost/mydb')

   # INSERT
   db.execute('INSERT INTO users (name, email) VALUES (?, ?)', ('João', 'joao@test.com'))

   # SELECT one
   user = db.fetchone('SELECT * FROM users WHERE id = ?', (1,))

   # SELECT all
   users = db.fetchall('SELECT * FROM users')

**Nota:** O Velox converte automaticamente ``?`` para ``%s`` quando usa MySQL/MariaDB.

---

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

   # Criar tabela (detecta o banco automaticamente)
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

---

Suporte MySQL/MariaDB no ORM
----------------------------

O Velox adapta automaticamente a sintaxe SQL para cada banco:

.. code-block:: python

   class Post(Model):
       table = 'posts'
       schema = {
           'title': str,
           'content': str,
           'published': bool,
       }

   # O Velox gera a query correta automaticamente:
   # - SQLite:  AUTOINCREMENT, INSERT OR IGNORE
   # - MySQL:   AUTO_INCREMENT, INSERT IGNORE, VARCHAR(255) para índices
   # - PostgreSQL: SERIAL, ON CONFLICT DO NOTHING

   Post.create_table()  # Cria com CHARACTER SET utf8mb4 no MySQL

---

Queries Encadeadas
-------------------

.. code-block:: python

   from velox.database import Model

   class Post(Model):
       table = 'posts'
       schema = {'title': str, 'content': str, 'published': bool}

   # WHERE + ORDER + LIMIT
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

---

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

   # Adicionar/remover relacionamento ManyToMany
   author.add_related('books', book)
   author.remove_related('books', book)

---

Async Database
--------------

Para modo ASGI, use banco assíncrono:

.. code-block:: python

   from velox.database import AsyncDatabase, AsyncModel

   # MySQL / MariaDB async
   db = AsyncDatabase('mysql://user:pass@localhost/mydb')

   class Post(AsyncModel):
       table  = 'posts'
       schema = {'title': str, 'content': str, 'published': bool}

   async def handler(req, res):
       # Queries assíncronas
       rows = await db.fetchall('SELECT * FROM posts')

       # Ou use AsyncModel
       posts = await Post.all()
       post  = await Post.create(title='Olá', content='...')

       res.json(rows)

Instale os drivers async:

.. code-block:: bash

   pip install aiosqlite     # SQLite async
   pip install asyncpg       # PostgreSQL async
   pip install aiomysql      # MySQL/MariaDB async

---

Configuração de Conexão
-----------------------

Para MySQL/MariaDB, o Velox usa:

.. code-block:: text

   host=localhost (ou parsed.hostname)
   port=3306 (padrão MySQL)
   database=<path>
   user=<username>
   password=<password>
   charset=utf8mb4
   collation=utf8mb4_unicode_ci
   autocommit=False

O pool é thread-local com auto-reconexão (ping com reconnect=True).

---

Migrations
----------

A tabela de migrations (``velox_migrations``) é criada automaticamente com a sintaxe correta para cada banco:

- **SQLite:** TEXT para name, AUTOINCREMENT
- **MySQL:** VARCHAR(255) para name (índices em TEXT não são permitidos), AUTO_INCREMENT, utf8mb4
- **PostgreSQL:** TEXT para name, SERIAL

---

Resumo de Drivers
-----------------

+------------------+------------------+------------------+
| Banco            | Driver Sync      | Driver Async     |
+==================+==================+==================+
| SQLite           | built-in         | aiosqlite        |
+------------------+------------------+------------------+
| PostgreSQL       | psycopg2-binary  | asyncpg          |
+------------------+------------------+------------------+
| MySQL            | mysql-connector  | aiomysql         |
+------------------+------------------+------------------+
| MariaDB          | mysql-connector  | aiomysql         |
+------------------+------------------+------------------+