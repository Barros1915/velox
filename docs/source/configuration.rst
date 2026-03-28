Configuração
=============

Variáveis de Ambiente
------------------

O Velox usa variáveis de ambiente para configuração.

Arquivo .env
~~~~~~~~~~~~

Crie um arquivo ``.env`` na raiz do projeto:

.. code-block:: text

   # Servidor
   APP_HOST=localhost
   APP_PORT=8000
   APP_DEBUG=true

   # Banco de dados
   DATABASE_URI=db/app.db

   # Para PostgreSQL:
   DATABASE_URI=postgresql://user:pass@localhost:5432/mydb

   # Segurança
   SECRET_KEY=your-secret-key-here

   # Cache (opcional)
   CACHE_BACKEND=redis
   REDIS_URL=redis://localhost:6379/0

   # Sessão
   SESSION_SECRET=session-secret-key

Variáveis Disponíveis
~~~~~~~~~~~~~~~~~~~~~

=========================  =======================  ==============================================
Variável                  Padrão                  Descrição
=========================  =======================  ==============================================
``APP_HOST``              ``localhost``            Host do servidor
``APP_PORT``              ``8000``                 Porta do servidor
``APP_DEBUG``            ``false``                Modo debug
``DATABASE_URI``          ``db/app.db``            URI do banco de dados
``SECRET_KEY``           (gerado)                Chave para sessões/CSRF
``CACHE_BACKEND``        ``memory``              Backend de cache (memory/redis)
``REDIS_URL``            ``redis://localhost``     URL do Redis
``SESSION_SECRET``       (SECRET_KEY)            Chave para sessões
``TEMPLATE_CACHE``       ``true``                Cache de templates
``WS_MAX_MESSAGE_SIZE``  ``1048576``             Tamanho máx. mensagem WebSocket
=========================  =======================  ==============================================

Configuração Programática
------------------------

Você também pode configurar programaticamente:

.. code-block:: python

   from velox import Velox

   app = Velox(__name__)

   # Pastas
   app.template('templates')  # pasta de templates
   app.static('static')      # pasta de arquivos estáticos

   # Configurar servidor
   # app.run(host='0.0.0.0', port=8080, debug=True)

Modo ASGI
--------

Para usar async com uvicorn:

.. code-block:: bash

   pip install velox-framework[asgi]

Execute:

.. code-block:: bash

   uvicorn app:app --reload --host 0.0.0.0 --port 8080

Ou programaticamente:

.. code-block:: python

   app.run(asgi=True)  # usa uvicorn internamente

Próximos Passos
-------------

- Leia :doc:`database` para configurar banco de dados
