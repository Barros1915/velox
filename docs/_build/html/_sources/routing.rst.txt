Rotas e Routing
=================

Definindo Rotas
--------------

O Velox usa decoradores para definir rotas:

.. code-block:: python

   from velox import Velox

   app = Velox(__name__)

   @app.get('/')
   def index(req, res):
       res.text('Olá mundo!')

   @app.post('/api/data')
   def create_data(req, res):
       res.json({'status': 'ok'})

Métodos HTTP Suportados
-----------------------

.. code-block:: python

   @app.get('/path')      # GET
   @app.post('/path')     # POST
   @app.put('/path')     # PUT
   @app.delete('/path')  # DELETE
   @app.patch('/path')   # PATCH

Parâmetros de Rota
-----------------

Capture segmentos da URL:

.. code-block:: python

   @app.get('/user/<int:user_id>')
   def get_user(req, res, user_id):
       res.json({'id': user_id})

Converters Disponíveis
~~~~~~~~~~~~~~~~~~~~

====================  ====================  ======================================
Converter             Exemplo             Descrição
====================  ====================  ======================================
``<int:id>``          ``/user/123``        Inteiro
``<float:value>``      ``/price/19.99``    Número decimal
``<str:name>``        ``/user/joao``      String (padrão)
``<slug:slug>``       ``/post/my-post``   Slug URL
``<uuid:id>``         ``/file/abc...``   UUID
``<path:path>``       ``/files/a/b``     Caminho
====================  ====================  ======================================

Múltiplos Métodos
----------------

.. code-block:: python

   @app.route('/resource', methods=['GET', 'POST'])
   def resource_handler(req, res):
       if req.method == 'GET':
           res.json({})
       else:
           res.json({'created': True})

Resource (Classe)
-----------------

Use uma classe para múltiplos métodos:

.. code-block:: python

   @app.resource('/api/posts')
   class PostResource:
       def get(req, res):
           res.json({'posts': []})
           return res

       def post(req, res):
           data = req.json
           res.json({'created': True})
           return res

       def put(req, res):
           res.json({'updated': True})
           return res

       def delete(req, res):
           res.json({'deleted': True})
           return res

Blueprints
---------

Organize rotas com Blueprints:

.. code-block:: python

   from velox import Velox, Router

   app = Velox(__name__)

   # Criar Blueprint
   api = Router()

   @api.get('/users')
   def list_users(req, res):
       res.json([])

   @api.get('/users/<int:user_id>')
   def get_user(req, res, user_id):
       res.json({'id': user_id})

   # Registrar com prefixo
   app.include(api, prefix='/api')

Agora as rotas são ``/api/users`` e ``/api/users/<id>``.

Próximos Passos
-------------

- Leia :doc:`named_routes` para rotas nomeadas
- Explore :doc:`database` para banco de dados