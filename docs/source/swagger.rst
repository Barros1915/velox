Swagger/OpenAPI - Documentação Automática
==========================================

Gera documentação estilo Swagger UI para sua API.

Instalação
----------

.. code-block:: bash

   pip install velox-web

Uso
---

.. code-block:: python

   from velox import Velox
   from velox.swagger import add_swagger_docs

   app = Velox(__name__)

   # Suas rotas API
   @app.get('/api/users')
   def list_users(req, res):
       res.json({'users': [{'id': 1, 'name': 'João'}]})

   @app.post('/api/users')
   def create_user(req, res):
       data = req.json
       res.json({'created': data}, status=201)

   @app.get('/api/users/<int:id>')
   def get_user(req, res, id):
       res.json({'id': id, 'name': 'João'})

   # Adicionar documentação
   add_swagger_docs(app)

   app.run()

Acesse:

- UI Swagger: http://localhost:8000/docs/
- JSON OpenAPI: http://localhost:8000/docs/openapi.json

---

Configuração
------------

.. code-block:: python

   add_swagger_docs(
       app,
       path='/api-docs',      # caminho da documentação
       title='Minha API',    # título
       version='2.0.0'       # versão
   )

---

Decorador @api_doc
------------------

Documente suas rotas com metadados:

.. code-block:: python

   from velox.swagger import api_doc

   @app.get('/api/posts')
   @api_doc(
       summary='Lista posts',
       description='Retorna lista de posts paginados',
       tags=['Posts'],
       responses={
           '200': {'description': 'Lista de posts'},
           '401': {'description': 'Não autorizado'},
       }
   )
   def list_posts(req, res):
       res.json({'posts': []})

---

Rotas Manuais
-------------

Adicione rotas manualmente para melhor documentação:

.. code-block:: python

   from velox.swagger import SwaggerRouter

   app = Velox(__name__)
   swagger = SwaggerRouter(app, title='API Documentation')

   # Adicionar rota manualmente
   swagger.add_route(
       '/api/products',
       'GET',
       list_products_handler,
       summary='Lista produtos',
       tags=['Products']
   )

   app.include(swagger, prefix='/docs')

---

SwaggerRouter
-------------

.. code-block:: python

   from velox.swagger import SwaggerRouter

   swagger = SwaggerRouter(
       app,
       title='API Documentation',
       version='1.0.0',
       description='API do meu sistema',
       openapi_version='3.0.0'
   )

   # Obter especificação OpenAPI
   spec = swagger.get_openapi_spec()

---

Classe APIDoc
-------------

Documente classes de recursos:

.. code-block:: python

   from velox.swagger import APIDoc

   @app.resource('/api/users')
   @APIDoc('Gerencia usuários', tags=['Users'])
   class Users:
       def get(req, res):
           '''Lista todos os usuários'''
           return res.json({'users': []})

       def post(req, res):
           '''Cria um novo usuário'''
           data = req.json
           return res.json({'user': data}, status=201)