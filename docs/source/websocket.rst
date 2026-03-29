WebSocket
=========

Comunicação em tempo real bidirecional.

Requer modo ASGI:

.. code-block:: bash

   pip install velox-web[asgi]

---

Uso Básico
----------

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

   app.run(asgi=True)

Client JavaScript:

.. code-block:: javascript

   const ws = new WebSocket('ws://localhost:8000/ws/chat');

   ws.onopen = () => console.log('Conectado');
   ws.onmessage = (e) => console.log('Recebeu:', e.data);
   ws.send('Olá');

   ws.close();

---

WebSocketManager
----------------

Gerencie conexões, rooms e broadcast:

.. code-block:: python

   from velox.websocket import WebSocketManager

   manager = WebSocketManager()

   @app.websocket('/ws/chat')
   async def chat(ws):
       await manager.connect(ws, room='chat')

       try:
           while True:
               msg = await ws.receive()
               if msg is None:
                   break

               # Broadcast para sala
               await manager.broadcast({'msg': msg}, room='chat')
       finally:
           manager.disconnect(ws)

---

Rooms/Canais
------------

Separe conexões em salas diferentes:

.. code-block:: python

   @app.websocket('/ws/<room>')
   async def room_chat(ws, room):
       await manager.connect(ws, room=room)

       try:
           while True:
               msg = await ws.receive()
               if msg is None:
                   break

               # Enviar para sala específica
               await manager.send_to_room({
                   'type': 'message',
                   'data': msg,
                   'room': room
               }, room=room)
       finally:
           manager.disconnect(ws)

---

Enviar para Usuário Específico
-------------------------------

.. code-block:: python

   # Enviar mensagem para usuário específico
   await manager.send_to_user(
       {'notification': 'Nova mensagem'},
       user_id='user123'
   )

---

Callbacks de Eventos
--------------------

.. code-block:: python

   @manager.on_connect
   async def on_connected(ws, info):
       print(f'Cliente conectado na sala: {info["room"]}')

   @manager.on_disconnect
   async def on_disconnected(ws, info):
       print(f'Cliente desconectado')

   @manager.on_message
   async def on_message(ws, msg_type, data):
       print(f'{msg_type}: {data}')

---

Broadcast Global
----------------

.. code-block:: python

   # Enviar para TODOS os clientes conectados
   await manager.broadcast({
       'type': 'announcement',
       'data': 'Manutenção programada para amanhã'
   })

---

Estatísticas
------------

.. code-block:: python

   stats = manager.get_stats()
   print(f"Conexões: {stats['connections']}")
   print(f"Rooms: {stats['rooms']}")
   print(f"Detalhes: {stats['room_details']}")

---

WebSocketHandler
-----------------

Helper para processar mensagens estruturadas:

.. code-block:: python

   from velox.websocket import WebSocketHandler

   handler = WebSocketHandler(manager)

   @handler.register('chat_message')
   async def handle_chat(ws, data):
       await manager.send_to_room({
           'type': 'chat',
           'from': ws.user_id,
           'message': data
       }, room=ws.room)

   @handler.register('typing')
   async def handle_typing(ws, data):
       # Notificar outros na sala
       pass

---

Configuração
------------

.. code-block:: text

   # Tamanho máximo da mensagem (1MB padrão)
   WS_MAX_MESSAGE_SIZE=1048576

---

Singleton
---------

Use o gerenciador padrão:

.. code-block:: python

   from velox.websocket import get_manager

   manager = get_manager()  # retorna instância única