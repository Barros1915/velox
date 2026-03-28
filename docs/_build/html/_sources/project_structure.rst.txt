Estrutura do Projeto
================

Este guia mostra como criar e organizar seu projeto Velox.

Criando um Novo Projeto
--------------------

Use o comando CLI para criar um novo projeto:

.. code-block:: bash

   velox init meu_projeto

Isso cria a estrutura completa:

.. code-block:: text

   meu_projeto/
   ├── app.py              # Aplicação principal
   ├── .env               # Variáveis de ambiente
   ├── .gitignore
   ├── requirements.txt
   ├── db/                # Arquivos SQLite
   ├── static/
   │   ├── css/
   │   │   └── style.css
   │   └── img/
   │       └── velox-logo.png
   └── templates/
       ├── index.html
       └── 404.html

Executando o Projeto
--------------------

.. code-block:: bash

   cd meu_projeto
   velox run

Ou:

.. code-block:: bash

   cd meu_projeto
   python app.py

O servidor roda em http://localhost:8000

Criando Apps Modulares
--------------------

O Velox permite criar apps modulares (como Django):

.. code-block:: bash

   velox startapp blog

Estrutura de um app:

.. code-block:: text

   blog/
   ├── __init__.py
   ├── models.py      # Models do banco
   ├── views.py      # Rotas/Handlers
   ├── admin.py      # Registro no admin
   ├── tests.py     # Testes
   └── templates/
       ├── blog/
       │   ├── list.html
       │   └── form.html

Usando o App
-------------

No ``app.py``, inclua o router do app:

.. code-block:: python

   from velox import Velox
   from blog.views import router

   app = Velox(__name__)

   # Incluir app com prefixo
   app.include(router, prefix='/blog')

   # Ou use autodiscovery:
   # app.load_apps(['blog'])

Rotas do app ficam em ``/blog/``, ``/blog/<id>``, etc.

App API-Only
-------------

Para criar um app sem templates:

.. code-block:: bash

   velox startapp api --api

Estrutura minimalista:

.. code-block:: text

   api/
   ├── __init__.py
   ├── models.py
   ├── views.py
   ├── admin.py
   └── tests.py

Próximos Passos
--------------

- Leia :doc:`routing` para rotas
- Explore :doc:`database` para banco de dados
- Aprenda :doc:`templates` para templates