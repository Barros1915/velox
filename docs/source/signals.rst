Signals (Eventos)
=================

Sistema de sinais para executar callbacks quando eventos ocorrem.

Sinais Padrão
-------------

.. code-block:: python

   from velox.signals import (
       request_started,
       request_finished,
       request_error,
       template_rendered,
       database_query,
       user_logged_in,
       user_logged_out,
   )

---

Conectar Callback
-----------------

.. code-block:: python

   def meu_callback(sender, **kwargs):
       print(f'Evento em {sender}')

   # Conectar ao sinal
   request_started.connect(meu_callback)

---

Decorador @receiver
--------------------

Forma mais limpa de conectar:

.. code-block:: python

   from velox.signals import receiver, request_finished

   @receiver(request_finished)
   def after_request(sender, request, **kwargs):
       print(f'Requisição {request.path} finalizada')

---

Desconectar
-----------

.. code-block:: python

   # Por função
   request_finished.disconnect(meu_callback)

   # Por dispatch_uid
   request_finished.disconnect(dispatch_uid='meu_uid')

---

Emitir Sinal
------------

.. code-block:: python

   from velox.signals import emit

   # Emitir sinal padrão
   emit('request_finished', sender=app, request=request)

   # Criar sinal customizado primeiro
   from velox.signals import create_signal

   meu_sinal = create_signal('meu_evento')
   emit('meu_evento', sender=self, data='valor')

---

Criar Sinais Customizados
-------------------------

.. code-block:: python

   from velox.signals import Signal

   # Criar sinal
   post_saved = Signal(['post', 'created'])

   # Conectar
   @receiver(post_saved)
   def on_post_saved(sender, post, created, **kwargs):
       if created:
           print(f'Novo post: {post.title}')
       else:
           print(f'Post atualizado: {post.title}')

   # Emitir
   post_saved.send(sender=model, post=post_obj, created=True)

---

Emitir com Robustez
-------------------

``send_robust()`` captura exceções nos receivers:

.. code-block:: python

   responses = post_saved.send_robust(sender=self, post=post)

   for func, response in responses:
       if isinstance(response, Exception):
           print(f'Erro em {func}: {response}')
       else:
           print(f'Sucesso: {response}')

---

Exemplo Completo
----------------

.. code-block:: python

   from velox.signals import receiver, request_started, request_finished

   @receiver(request_started)
   def log_request(sender, request, **kwargs):
       print(f'Iniciando: {request.method} {request.path}')

   @receiver(request_finished)
   def after_request(sender, request, **kwargs):
       print(f'Finalizado: {request.method} {request.path}')