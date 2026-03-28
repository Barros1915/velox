Arquivos Estáticos
================

O Veloxserve automaticamente arquivos estáticos.

Configuração
------------

.. code-block:: python

   from velox import Velox

   app = Velox(__name__)

   # Definir pasta de arquivos estáticos
   app.static('static')

Estrutura de Arquivos
--------------------

Coloque seus arquivos em ``static/``:

.. code-block:: text

   static/
   ├── css/
   │   ├── style.css
   │   └── components.css
   ├── js/
   │   ├── main.js
   │   └── components.js
   └── images/
       ├── logo.png
       └── banner.jpg

Acessando Arquivos
-----------------

Na HTML, use o caminho a partir de ``static/``:

.. code-block:: html

   <link rel="stylesheet" href="/static/css/style.css">
   <script src="/static/js/main.js"></script>
   <img src="/static/images/logo.png">

Pastas Múltiplas
-----------------

Você pode configurar múltiplas pastas:

.. code-block:: python

   # Não há suporte nativo, mas pode servir manualmente
   @app.get('/static/<path:path>')
   def serve_static(req, res, path):
       # Seu código de servidor de arquivos
       pass

Cache de Arquivos Estáticos
------------------------

Para produção, considere usar um servidor web (nginx, Apache) ou CDN.

Próximos Passos
-------------

- Configure um servidor web para servir estáticos em produção
- Use CDN para imagens e assets comuns