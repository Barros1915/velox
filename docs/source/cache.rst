Sistema de Cache
================

Cache multi-backend com suporte a memória, SQLite (arquivo) e Redis.

Configuração
------------

.. code-block:: text

   # Backend: memory (padrão), file, redis
   CACHE_BACKEND=memory

   # Para SQLite
   CACHE_DB=cache.db

   # Para Redis
   CACHE_REDIS_URL=redis://localhost:6379/0

   CACHE_PREFIX=velox
   CACHE_DEFAULT_TIMEOUT=300

---

Uso Básico
----------

.. code-block:: python

   from velox.cache import cache

   # Definir valor
   cache.set('user:1', {'name': 'João', 'email': 'joao@email.com'}, timeout=300)

   # Obter valor
   user = cache.get('user:1')

   # Verificar existência
   if cache.has('user:1'):
       print('Usuário está em cache')

   # Deletar
   cache.delete('user:1')

   # Limpar tudo
   cache.clear()

---

Decorador cache_on
------------------

Cacheia resultado de funções:

.. code-block:: python

   from velox.cache import cache_on

   @cache_on(lambda user_id: f'user:{user_id}', timeout=60)
   def get_user(user_id):
       # Simula busca no banco
       return db.query(f'SELECT * FROM users WHERE id = {user_id}')

   # Primeira chamada: executa função
   user = get_user(1)

   # Segunda chamada: retorna do cache
   user = get_user(1)

---

Operações em Massa
------------------

.. code-block:: python

   # Obter múltiplas chaves
   dados = cache.get_many(['user:1', 'user:2', 'user:3'])

   # Definir múltiplas chaves
   cache.set_many({
       'config:site': 'Meu Site',
       'config:theme': 'dark',
   }, timeout=3600)

   # Deletar múltiplas chaves
   cache.delete_many(['user:1', 'user:2', 'user:3'])

---

Estatísticas
------------

.. code-block:: python

   stats = cache.stats
   print(f"Hits: {stats['hits']}")
   print(f"Misses: {stats['misses']}")
   print(f"Hit rate: {stats['hit_rate']}%")
   print(f"Chaves: {stats['keys']}")

---

Backends
--------

Memory (desenvolvimento)
~~~~~~~~~~~~~~~~~~~~~~~~

Padrão, rápido, não persiste entre reinicializações.

.. code-block:: text

   CACHE_BACKEND=memory

FileCache (produção simples)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Persiste em SQLite, sobrevive a reinicializações.

.. code-block:: text

   CACHE_BACKEND=file
   CACHE_DB=cache.db

RedisCache (alta performance)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Recomendado para produção com múltiplos workers.

.. code-block:: text

   CACHE_BACKEND=redis
   CACHE_REDIS_URL=redis://localhost:6379/0

Requer: ``pip install redis``

---

Template Cache
--------------

.. code-block:: python

   from velox.cache import template_cache

   # Habilitar cache de templates
   TEMPLATE_CACHE=true

   # Obter template compilado
   compiled = template_cache.get('index.html')

   # Limpar cache de templates
   template_cache.clear()