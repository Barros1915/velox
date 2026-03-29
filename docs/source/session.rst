Sessions
========

Gerenciamento de sessões de usuário.

Configuração
------------

.. code-block:: text

   SESSION_COOKIE_NAME=velox_sid
   SESSION_EXPIRE_SECONDS=86400
   SESSION_COOKIE_SECURE=false
   SESSION_COOKIE_SAMESITE=Lax

---

Server-Side Sessions (Recomendado)
-----------------------------------

Dados armazenados no cache, apenas o ID no cookie:

.. code-block:: python

   from velox.session import SessionManager

   sessions = SessionManager(server_side=True)

   @app.get('/perfil')
   def perfil(req, res):
       session = sessions.get_session(req, res)

       if not session.get('user_id'):
           res.redirect('/login')
           return

       res.json({'user_id': session.get('user_id')})

---

Uso da Sessão
-------------

.. code-block:: python

   @app.get('/login')
   def login(req, res):
       session = sessions.get_session(req, res)

       # Salvar dados
       session['user_id'] = 123
       session['username'] = 'joao'
       session.save()

       res.json({'status': 'logged in'})

   @app.get('/logout')
   def logout(req, res):
       session = sessions.get_session(req, res)
       session.destroy()
       res.redirect('/')

---

Métodos da Session
------------------

.. code-block:: python

   session = sessions.get_session(req, res)

   # Obter valor
   user_id = session.get('user_id')
   user_id = session['user_id']

   # Definir valor
   session.set('key', 'value')
   session['key'] = 'value'

   # Remover valor
   session.pop('key')
   del session['key']

   # Verificar existência
   if 'key' in session:
       print('Existe')

   # Salvar no cookie
   session.save()

   # Destruir sessão
   session.destroy()

   # Rotacionar sessão (novo ID, mesmos dados)
   session.rotate()

---

Client-Side Sessions (Legado)
------------------------------

Dados assinados no próprio cookie:

.. code-block:: python

   from velox.session import SessionManager

   sessions = SessionManager(server_side=False)

---

SessionManager
--------------

.. code-block:: python

   from velox.session import SessionManager

   # Server-side (padrão) - recomendado
   sessions = SessionManager(server_side=True)

   # Client-side (legado)
   sessions = SessionManager(server_side=False, secret_key='sua-chave')

---

Combine com Auth
----------------

.. code-block:: python

   from velox.auth import authenticate, login, logout
   from velox.session import SessionManager

   sessions = SessionManager()

   @app.post('/login')
   def do_login(req, res):
       user = authenticate(req.form.get('username'), req.form.get('password'))

       if user:
           # Login + salvar na sessão
           login(req, user)
           session = sessions.get_session(req, res)
           session['user_id'] = user.id
           session['roles'] = user.roles
           session.save()

           res.redirect('/dashboard')
       else:
           res.json({'error': 'Credenciais inválidas'}, status=401)