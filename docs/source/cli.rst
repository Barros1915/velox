CLI - Interface de Linha de Comando
====================================

Todos os comandos disponíveis no ``velox`` com exemplos práticos.

Instalação
----------

.. code-block:: bash

   pip install velox-web

---

``velox init`` — Cria um novo projeto
-------------------------------------

.. code-block:: bash

   velox init meu-projeto

**Saída:**

::

   ✔   meu-projeto/app.py
   ✔   meu-projeto/.env
   ✔   meu-projeto/.gitignore
   ✔   meu-projeto/requirements.txt
   ✔   meu-projeto/templates/index.html
   ✔   meu-projeto/templates/404.html
   ✔   meu-projeto/static/css/style.css
   ✔   meu-projeto/static/img/velox-logo.png

   ✅ Projeto criado com sucesso!

     → cd meu-projeto
     → velox run

---

``velox startapp`` — Cria um app modular
------------------------------------------

.. code-block:: bash

   # App completo (com templates)
   velox startapp blog

   # App API-only (sem templates)
   velox startapp api --api

   # Sobrescreve se já existir
   velox startapp blog --force

**Saída (app completo):**

::

   ✔   blog/__init__.py
   ✔   blog/models.py
   ✔   blog/views.py
   ✔   blog/admin.py
   ✔   blog/tests.py
   ✔   blog/templates/blog/list.html
   ✔   blog/templates/blog/form.html

   App 'blog' criado!

     Adicione em app.py:
       from blog.views import router
       app.include(router)

---

``velox run`` — Inicia o servidor
---------------------------------

.. code-block:: bash

   # Servidor padrão (localhost:8000)
   velox run

   # Porta customizada
   velox run --port 5000

   # Com auto-reload (recomendado em desenvolvimento)
   velox run --reload

   # Exposto na rede local
   velox run --host 0.0.0.0 --port 8080

   # Arquivo de app diferente
   velox run minha_app.py --port 3000 --reload

**Saída:**

::

   🌐 http://localhost:8000
   ↺ Auto-reload ativado
   Ctrl+C para parar

---

``velox routes`` — Lista as rotas registradas
---------------------------------------------

.. code-block:: bash

   velox routes

   # Arquivo de app diferente
   velox routes minha_app.py

**Saída:**

::

   Rotas registradas:

   GET       /
   GET       /sobre
   GET       /api/posts
   POST      /api/posts
   GET       /api/posts/<id>
   PUT       /api/posts/<id>
   DELETE    /api/posts/<id>
   GET       /admin/
   POST      /admin/login

   Total: 9 rota(s)

---

``velox create`` — Cria arquivos no projeto
-------------------------------------------

.. code-block:: bash

   # Criar um model
   velox create model produto

   # Criar uma view
   velox create view home

   # Criar um middleware
   velox create middleware autenticacao

   # Criar um template HTML
   velox create template contato

**Saída:**

::

   ✔ Criado: models/produto.py
   ✔ Criado: views/home.py
   ✔ Criado: middlewares/autenticacao.py
   ✔ Criado: templates/contato.html

---

``velox makemigration`` — Cria um arquivo de migration
------------------------------------------------------

.. code-block:: bash

   velox makemigration create_posts
   velox makemigration add_autor_to_posts
   velox makemigration create_tags

**Saída:**

::

   ✔ Migration criada: migrations/20260329120000_create_posts.py
   → Edite o arquivo e rode: velox migrate

**Arquivo gerado** (``migrations/20260329120000_create_posts.py``):

.. code-block:: python

   """
   Migration: create_posts
   Created: 2026-03-29 12:00:00
   """
   from velox.migrations import Migration


   class CreateMigration(Migration):
       def __init__(self):
           super().__init__("create_posts")

       def forward(self):
           self.create_table('posts', {
               'id':         'INTEGER PRIMARY KEY AUTOINCREMENT',
               'titulo':     'TEXT NOT NULL',
               'conteudo':   'TEXT',
               'criado_em':  'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
           })

       def backward(self):
           self.drop_table('posts')

---

``velox migrate`` — Aplica as migrations pendentes
----------------------------------------------------

.. code-block:: bash

   velox migrate

**Saída (primeira vez):**

::

   ✔ Aplicada: create_posts
   ✔ Aplicada: add_autor_to_posts
   ✔ Aplicada: create_tags

   3 migration(s) aplicada(s).

**Saída (já aplicadas):**

::

     Já aplicada: create_posts
     Já aplicada: add_autor_to_posts
     Já aplicada: create_tags
   → Nenhuma migration pendente.

---

``velox createuser`` — Cria um usuário admin
---------------------------------------------

.. code-block:: bash

   # Modo interativo (recomendado)
   velox createuser

   # Passando username e email diretamente
   velox createuser --username joao --email joao@email.com

**Saída (modo interativo):**

::

   Criar usuário admin

     Username: admin
     Email: admin@meusite.com
     Senha: ••••••••
     Confirmar senha: ••••••••

   ✔ Usuário 'admin' criado com sucesso!
   → Acesse /admin/ com suas credenciais.

---

``velox version`` — Exibe a versão
----------------------------------

.. code-block:: bash

   velox version

**Saída:**

::

   Velox Framework v1.0.0
   Python 3.12.0

---

Fluxo completo — do zero ao projeto rodando
-------------------------------------------

.. code-block:: bash

   # 1. Criar projeto
   velox init minha-loja
   cd minha-loja

   # 2. Criar apps
   velox startapp produtos
   velox startapp usuarios
   velox startapp api --api

   # 3. Criar migration e aplicar
   velox makemigration create_produtos
   # (edite o arquivo em migrations/)
   velox migrate

   # 4. Criar usuário admin
   velox createuser

   # 5. Rodar o servidor
   velox run --reload

---

Links
------

- PyPI: https://pypi.org/project/velox-web/
- GitHub: https://github.com/Barros1915/velox
- Docs: https://velox.readthedocs.io/
- Site: https://barros1915.github.io/velox/