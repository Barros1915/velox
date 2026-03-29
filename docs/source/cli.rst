CLI - Interface de Linha de Comando
====================================

Comandos disponíveis para criar projetos, apps e gerenciar o servidor.

Instalação
----------

O CLI é instalado junto com o Velox:

.. code-block:: bash

   pip install velox-web

Comandos
--------

init - Criar Projeto
~~~~~~~~~~~~~~~~~~~~

Cria um novo projeto com estrutura completa:

.. code-block:: bash

   velox init meu-projeto

Estrutura gerada:

::

   meu-projeto/
   ├── app.py              # ponto de entrada
   ├── .env                # configurações
   ├── .gitignore
   ├── requirements.txt
   ├── db/.gitkeep
   ├── static/
   │   ├── css/style.css
   │   └── img/velox-logo.png
   └── templates/
       ├── index.html
       └── 404.html

startapp - Criar App Modular
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Cria um app modular (como Django):

.. code-block:: bash

   velox startapp blog

   # Para API-only (sem templates)
   velox startapp api --api

Estrutura gerada:

::

   blog/
   ├── __init__.py
   ├── models.py     # models do app
   ├── views.py      # rotas/handlers
   ├── admin.py      # interface admin
   ├── tests.py      # testes
   └── templates/
       └── blog/
           ├── list.html
           └── form.html

Registrar no app.py:

.. code-block:: python

   from velox import Velox
   from blog.views import router

   app = Velox(__name__)
   app.include(router)

run - Iniciar Servidor
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Padrão (porta 8000)
   velox run

   # Porta customizada
   velox run --port 5000

   # Com auto-reload
   velox run --reload

create - Criar Arquivos
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Criar model
   velox create model User

   # Criar views
   velox create view profile

   # Criar middleware
   velox create middleware cors

   # Criar template
   velox create template dashboard

routes - Listar Rotas
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   velox routes

   # GET     /
   # GET     /api/users
   # POST    /api/users
   # WS      /ws/chat

version - Versão
~~~~~~~~~~~~~~~~

.. code-block:: bash

   velox version

   # Velox Framework v1.0.0
   # Python 3.12.0

---

Auto-reload
-----------

O servidor monitora arquivos e reinicia automaticamente quando detecta mudanças.

Arquivos monitorados: ``.py``, ``.html``, ``.css``, ``.js``, ``.env``

Arquivos ignorados: ``__pycache__``, ``.git``, ``node_modules``

---

Cores no Terminal
-----------------

O CLI usa cores ANSI para melhor legibilidade:

- **Verde** ✓ Sucesso
- **Amarelo** ⚠ Aviso
- **Vermelho** ✘ Erro
- **Ciano** → Informação