Instalação
==========

Formas de Usar o Velox
-----------------------

O Velox oferece **duas modalidades** de desenvolvimento:

1. **Arquivo único** - Para projetos rápidos e APIs simples
2. **Projeto completo** - Para aplicações modulares com estrutura organizada

---

Modo 1: Arquivo Único (Single File)
-----------------------------------

O Velox permite criar uma aplicação completa em **um único arquivo Python**. Ideal para:
- APIs simples
- Microserviços
- Protótipos rápidos
- Scripts automatizados

### Instalação

.. code-block:: bash

   pip install velox-web

### Criar arquivo ``app.py``:

.. code-block:: python

   from velox import Velox

   app = Velox(__name__)

   @app.get('/')
   def home(req, res):
       res.html('<h1>Olá Mundo!</h1>')

   @app.get('/api/users')
   def users(req, res):
       res.json([
           {'id': 1, 'name': 'Alice'},
           {'id': 2, 'name': 'Bob'},
       ])

   @app.post('/api/create')
   def create(req, res):
       data = req.json
       res.json({'created': data}, status=201)

   if __name__ == '__main__':
       app.run()

### Executar:

.. code-block:: bash

   # Modo simples
   python app.py

   # Com auto-reload (reinicia ao salvar)
   velox run --reload

   # Porta customizada
   velox run --port 5000 --reload

**Resultado:**

.. code-block:: text

   ✓  Velox [WSGI/threading]  http://localhost:8000

### Estrutura gerada:

::

   projeto/
   └── app.py

---

Modo 2: Projeto Completo (CLI)
------------------------------

Para projetos maiores, use o CLI do Velox para scaffolding automático.

### Criar projeto:

.. code-block:: bash

   # Cria projeto completo com estrutura
   velox init meu-projeto

   # Entrar na pasta
   cd meu-projeto

   # Rodar servidor com auto-reload
   velox run --reload

### Estrutura gerada:

::

   meu-projeto/
   ├── app.py              # ponto de entrada
   ├── templates/          # templates HTML
   │   └── base.html
   ├── static/             # arquivos estáticos
   │   ├── css/style.css
   │   └── js/app.js
   ├── db/                 # banco de dados
   │   └── app.db
   ├── views/              # suas rotas
   │   └── __init__.py
   ├── models/             # modelos ORM
   │   └── __init__.py
   ├── .env                # configurações
   └── requirements.txt

### Arquivo ``app.py``:

.. code-block:: python

   from velox import Velox
   from views import router

   app = Velox(__name__)
   app.template('templates')
   app.static('static')

   # Incluir rotas modulares
   app.include(router)

   if __name__ == '__main__':
       app.run()

### Criar apps modulares:

.. code-block:: bash

   # Criar módulo blog
   velox startapp blog

   # Criar módulo API
   velox startapp api --api

### Estrutura com apps:

::

   meu-projeto/
   ├── app.py
   ├── blog/
   │   ├── __init__.py
   │   ├── views.py
   │   └── models.py
   ├── api/
   │   ├── __init__.py
   │   └── views.py
   ├── templates/
   └── static/

---

Comparativo: Arquivo Único vs Projeto
-------------------------------------

+------------------------+-------------------+-------------------+
| Aspecto                | Arquivo Único     | Projeto Completo   |
+========================+===================+===================+
| Uso ideal              | APIs simples      | Apps modulares    |
+------------------------+-------------------+-------------------+
| Estrutura             | 1 arquivo         | Múltiplos módulos |
+------------------------+-------------------+-------------------+
| Rotas                  | No mesmo arquivo  | Arquivos separada |
+------------------------+-------------------+-------------------+
| Models                 | No mesmo arquivo  | Pasta models/     |
+------------------------+-------------------+-------------------+
| Templates              | Opcional          | Recomendado       |
+------------------------+-------------------+-------------------+
| Deploy                 | Rápido            | Organizado        |
+------------------------+-------------------+-------------------+

---

Instalação de Drivers de Banco
------------------------------

.. code-block:: bash

   # SQLite (padrão, zero dependências)
   pip install velox-web

   # PostgreSQL
   pip install velox-web[postgres]
   # ou: pip install psycopg2-binary

   # MySQL
   pip install velox-web[mysql]
   # ou: pip install mysql-connector-python

   # MariaDB (mesmo driver do MySQL)
   pip install velox-web[mariadb]

   # Async (todos os drivers)
   pip install velox-web[async]
   # aiosqlite + asyncpg + aiomysql

   # Tudo
   pip install velox-web[full]

---

Configuração via .env
---------------------

Crie um arquivo ``.env`` no projeto:

.. code-block:: text

   # Servidor
   APP_HOST=0.0.0.0
   APP_PORT=8000
   APP_DEBUG=true

   # Segurança
   VELOX_SECRET_KEY=sua-chave-secreta-aleatoria

   # Admin
   VELOX_ADMIN_USER=admin
   VELOX_ADMIN_PASSWORD=senha-segura
   VELOX_ADMIN_PREFIX=/admin

   # Banco de dados
   DATABASE_URI=db/app.db
   # DATABASE_URI=postgresql://user:pass@localhost/mydb
   # DATABASE_URI=mysql://user:pass@localhost/mydb

   # Cache
   CACHE_BACKEND=memory
   # CACHE_BACKEND=redis
   # CACHE_REDIS_URL=redis://localhost:6379/0

   # Sessions
   SESSION_COOKIE_NAME=velox_sid
   SESSION_EXPIRE_SECONDS=86400

---

Deploy em Produção
------------------

### Gunicorn (WSGI):

.. code-block:: bash

   pip install gunicorn
   gunicorn app:app -w 4 -b 0.0.0.0:8000

### uvicorn (ASGI):

.. code-block:: bash

   pip install uvicorn
   uvicorn app:app --workers 4 --host 0.0.0.0 --port 8000

### Docker:

.. code-block:: dockerfile

   FROM python:3.11
   WORKDIR /app
   RUN pip install velox-web gunicorn
   COPY . .
   EXPOSE 8000
   CMD ["gunicorn", "app:app", "-b", "0.0.0.0:8000"]

### Platforms testadas:

- ✅ Railway, Render, Heroku
- ✅ DigitalOcean App Platform
- ✅ AWS Elastic Beanstalk
- ✅ VPS (Ubuntu/CentOS)