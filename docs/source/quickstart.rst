Quickstart
==========

This guide will get you up and running with Velox in minutes.

Basic App
----------

Create a file ``app.py``:

.. code-block:: python

   from velox import Velox

   app = Velox(__name__)

   @app.get('/')
   def home(req, res):
       res.text('Hello, World!')

   if __name__ == '__main__':
       app.run()

Run it:

.. code-block:: bash

   # Modo simples
   python app.py

   # Com auto-reload (reinicia ao salvar arquivos)
   velox run --reload

   # Porta customizada
   velox run --port 5000 --reload

Server running at http://localhost:8000

O Velox monitora alterações em ``.py``, ``.html``, ``.css``, ``.js`` e ``.env``.

Rendering Templates
------------------

Create a template file ``templates/index.html``:

.. code-block:: html

   <!DOCTYPE html>
   <html>
   <head>
       <title>{{ title }}</title>
   </head>
   <body>
       <h1>Hello, {{ name }}!</h1>
   </body>
   </html>

Update your app:

.. code-block:: python

   from velox import Velox

   app = Velox(__name__)
   app.template('templates')

   @app.get('/')
   def home(req, res):
       return app.render('index.html', {'title': 'Home', 'name': 'World'})

   if __name__ == '__main__':
       app.run()

JSON API
-------

.. code-block:: python

   from velox import Velox

   app = Velox(__name__)

   @app.get('/api/users')
   def list_users(req, res):
       users = [
           {'id': 1, 'name': 'Alice'},
           {'id': 2, 'name': 'Bob'},
       ]
       res.json(users)

   if __name__ == '__main__':
       app.run()

Route Parameters
----------------

.. code-block:: python

   from velox import Velox

   app = Velox(__name__)

   @app.get('/user/<int:user_id>')
   def get_user(req, res, user_id):
       res.json({'id': user_id, 'name': f'User {user_id}'})

   if __name__ == '__main__':
       app.run()

Supported converters:

- ``<int:id>`` — Integer
- ``<float:value>`` — Float
- ``<str:name>`` — String
- ``<slug:slug>`` — URL slug
- ``<uuid:id>`` — UUID
- ``<path:path>`` — File path

POST Requests
-----------

.. code-block:: python

   from velox import Velox

   app = Velox(__name__)

   @app.post('/api/data')
   def handle_post(req, res):
       data = req.json
       res.json({'received': data})

   if __name__ == '__main__':
       app.run()

Async Handlers
-------------

Velox supports both sync and async handlers in the same app:

.. code-block:: python

   from velox import Velox

   app = Velox(__name__)

   # Sync handler
   @app.get('/sync')
   def sync_handler(req, res):
       res.text('Sync response')

   # Async handler
   @app.get('/async')
   async def async_handler(req, res):
       import asyncio
       await asyncio.sleep(0.1)
       res.text('Async response')

   if __name__ == '__main__':
       app.run()

Blueprints
---------

Organize routes with Blueprints:

.. code-block:: python

   from velox import Velox, Router

   app = Velox(__name__)

   # Create a Blueprint
   api = Router()

   @api.get('/users')
   def list_users(req, res):
       res.json(['alice', 'bob'])

   @api.get('/posts')
   def list_posts(req, res):
       res.json(['post1', 'post2'])

   # Register with prefix
   app.include(api, prefix='/api')

   if __name__ == '__main__':
       app.run()

Now routes are:

- ``/api/users``
- ``/api/posts``

Middleware
----------

Add global middleware:

.. code-block:: python

   from velox import Velox

   app = Velox(__name__)

   @app.use
   async def log_middleware(next_handler, req, res, **kw):
       print(f'Request: {req.method} {req.path}')
       result = await next_handler(req, res, **kw)
       return result

   @app.get('/')
   def home(req, res):
       res.text('Home')

   if __name__ == '__main__':
       app.run()

ASGI Mode
---------

Run with uvicorn for async support:

.. code-block:: bash

pip install velox-web[asgi]

Then run:

.. code-block:: bash

   uvicorn app:app --reload

Or in your app:

.. code-block:: python

   from velox import Velox

   app = Velox(__name__)

   @app.get('/')
   def home(req, res):
       res.text('Hello!')

   if __name__ == '__main__':
       app.run(asgi=True)  # Uses uvicorn

WebSocket
--------

WebSocket routes (ASGI only):

.. code-block:: python

   from velox import Velox

   app = Velox(__name__)

   @app.websocket('/ws/chat')
   async def chat(ws):
       await ws.accept()
       while True:
           msg = await ws.receive()
           if msg is None:
               break
           await ws.send(f'echo: {msg}')

   if __name__ == '__main__':
       app.run(asgi=True)

Client example:

.. code-block:: javascript

   const ws = new WebSocket('ws://localhost:8000/ws/chat');
   ws.onmessage = (event) => console.log(event.data);
   ws.send('Hello');

Error Handlers
-------------

Custom error pages:

.. code-block:: python

   from velox import Velox

   app = Velox(__name__)

   @app.not_found
   def not_found(req, res):
       res.status_code = 404
       res.html('<h1>404 - Page not found</h1>')

   @app.server_error
   def error(req, res):
       res.status_code = 500
       res.html('<h1>500 - Internal error</h1>')

   if __name__ == '__main__':
       app.run()

Static Files
-----------

Serve static files:

.. code-block:: python

   from velox import Velox

   app = Velox(__name__)
   app.static('static')  # Serve from 'static' folder

   @app.get('/')
   def home(req, res):
       res.text('Go to /static/style.css')

   if __name__ == '__main__':
       app.run()

Files in ``static/`` are served at ``/static/filename``.

Environment Variables
-------------------

Create a ``.env`` file:

.. code-block:: text

   APP_HOST=localhost
   APP_PORT=8000
   APP_DEBUG=true

Load it automatically:

.. code-block:: python

   # .env is loaded automatically

   from velox import Velox

   app = Velox(__name__)

   @app.get('/')
   def home(req, res):
       res.text('Hello!')

   app.run()  # Uses .env values

Next Steps
----------

- Read the :doc:`api` reference
- Learn about :doc:`templates`
- Explore :doc:`middleware` and :doc:`websocket`