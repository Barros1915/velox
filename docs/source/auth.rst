Autenticação e Autorização
==========================

O Velox possui um sistema completo de autenticação com suporte a:

- **Login tradicional** (usuário/senha)
- **OAuth** (Google, GitHub, Facebook, Discord)
- **RBAC** (Roles e Permissões)
- **Rate Limiting** (proteção contra brute force)
- **Sessions server-side** (seguro, escalável)

---

Configuração
------------

Configure via ``.env``:

.. code-block:: text

   # Backend: memory (dev) ou database (produção)
   AUTH_BACKEND=memory

   # Sessões
   SESSION_EXPIRE_HOURS=24

   # Rate Limiting
   MAX_LOGIN_ATTEMPTS=5
   LOGIN_WINDOW_SECONDS=900

   # OAuth Google
   GOOGLE_CLIENT_ID=seu-client-id
   GOOGLE_CLIENT_SECRET=seu-client-secret
   GOOGLE_REDIRECT_URI=https://seusite.com/auth/google/callback

   # OAuth GitHub
   GITHUB_CLIENT_ID=seu-client-id
   GITHUB_CLIENT_SECRET=seu-client-secret
   GITHUB_REDIRECT_URI=https://seusite.com/auth/github/callback

---

Autenticação Tradicional
------------------------

Importar funções:

.. code-block:: python

   from velox.auth import (
       authenticate, login, logout, login_required,
       create_user, get_current_user
   )

Criar Usuário
~~~~~~~~~~~~

.. code-block:: python

   from velox.auth import create_user

   # Cria usuário e faz hash da senha automaticamente
   user = create_user('joao', 'joao@email.com', 'senha123')
   # ✓ Usuário criado: joao (1)

Login
~~~~~

.. code-block:: python

   @app.post('/login')
   def do_login(req, res):
       username = req.form.get('username')
       password = req.form.get('password')

       user = authenticate(username, password)

       if user:
           # Cria sessão e retorna session_key
           session_key = login(req, user)
           # Define cookie com a sessão
           res.set_cookie('session_key', session_key, httponly=True)
           res.redirect('/dashboard')
       else:
           res.json({'error': 'Credenciais inválidas'}, status=401)

Logout
~~~~~~

.. code-block:: python

   @app.post('/logout')
   def do_logout(req, res):
       logout(req)
       res.delete_cookie('session_key')
       res.redirect('/')

Proteger Rotas
~~~~~~~~~~~~~~

Use o decorador ``@login_required``:

.. code-block:: python

   from velox.auth import login_required

   @app.get('/perfil')
   @login_required
   def perfil(req, res):
       res.json(req.user.to_dict())

   # Resultado:
   # {
   #   "id": 1,
   #   "username": "joao",
   #   "email": "joao@email.com",
   #   "is_active": true,
   #   "roles": [],
   #   "permissions": []
   # }

Middleware Global
~~~~~~~~~~~~~~~~~

Em vez de usar ``@login_required`` em cada rota, use o middleware:

.. code-block:: python

   from velox.auth import AuthMiddleware

   app = Velox(__name__)
   app.use(AuthMiddleware())

   @app.get('/dashboard')
   def dashboard(req, res):
       # req.user sempre disponível
       if req.user.is_authenticated:
           res.json({'user': req.user.username})
       else:
           res.json({'user': 'visitante'})

---

OAuth (Google, GitHub, Facebook, Discord)
-----------------------------------------

Google OAuth
~~~~~~~~~~~~

.. code-block:: python

   from velox.auth import get_oauth_provider, oauth_authenticate, login

   @app.get('/auth/google')
   def google_login(req, res):
       provider = get_oauth_provider('google')
       # Gera URL de autorização
       auth_url = provider.get_auth_url()
       res.redirect(auth_url)

   @app.get('/auth/google/callback')
   def google_callback(req, res):
       code = req.args.get('code')
       if not code:
           res.json({'error': 'Código não fornecido'}, status=400)
           return

       user = oauth_authenticate('google', code)

       if user:
           session_key = login(req, user)
           res.set_cookie('session_key', session_key)
           res.redirect('/')
       else:
           res.json({'error': 'Falha na autenticação OAuth'}, status=400)

GitHub OAuth
~~~~~~~~~~~~

.. code-block:: python

   @app.get('/auth/github')
   def github_login(req, res):
       provider = get_oauth_provider('github')
       res.redirect(provider.get_auth_url())

   @app.get('/auth/github/callback')
   def github_callback(req, res):
       user = oauth_authenticate('github', req.args.get('code'))
       if user:
           session_key = login(req, user)
           res.set_cookie('session_key', session_key)
           res.redirect('/')

Facebook OAuth
~~~~~~~~~~~~~~

.. code-block:: python

   @app.get('/auth/facebook')
   def facebook_login(req, res):
       provider = get_oauth_provider('facebook')
       res.redirect(provider.get_auth_url())

Discord OAuth
~~~~~~~~~~~~~

.. code-block:: python

   @app.get('/auth/discord')
   def discord_login(req, res):
       provider = get_oauth_provider('discord')
       res.redirect(provider.get_auth_url())

---

RBAC (Controle de Acesso por Papel)
------------------------------------

O Velox suporta roles e permissões granulares.

Criar Roles
~~~~~~~~~~~

.. code-block:: python

   from velox.auth import create_role, assign_role, revoke_role

   # Criar papel com permissões
   create_role('admin', [
       'posts.criar', 'posts.editar', 'posts.excluir',
       'usuarios.ver', 'usuarios.editar'
   ])

   # Criar papel sem permissões iniciais
   create_role('editor', ['posts.criar', 'posts.editar'])

   create_role('moderador')

Atribuir Roles a Usuários
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from velox.auth import assign_role, revoke_role

   user = User.get(1)

   # Atribuir role
   assign_role(user, 'admin')

   # Remover role
   revoke_role(user, 'editor')

Verificar Roles
~~~~~~~~~~~~~~~

.. code-block:: python

   @app.get('/admin')
   @login_required
   def admin_panel(req, res):
       if req.user.has_role('admin'):
           res.json({'admin': True})
       else:
           res.json({'error': 'Acesso negado'}, status=403)

Decoradores de Role
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from velox.auth import role_required

   @app.get('/painel')
   @role_required('admin', 'editor')  # qualquer um dos dois
   def painel(req, res):
       res.json({'access': 'granted'})

---

Permissões Granulares
---------------------

Conceder Permissão Extra
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from velox.auth import grant_permission, revoke_permission

   user = User.get(1)

   # Conceder permissão específica
   grant_permission(user, 'relatorios.exportar')

   # Remover permissão
   revoke_permission(user, 'relatorios.exportar')

Verificar Permissões
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   @app.get('/exportar')
   @login_required
   def exportar(req, res):
       if req.user.has_permission('relatorios.exportar'):
           # código de exportação
           res.json({'exported': True})
       else:
           res.json({'error': 'Sem permissão'}, status=403)

Decorador de Permissão
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from velox.auth import permission_required

   @app.post('/usuarios/excluir')
   @permission_required('usuarios.excluir')
   def excluir_usuario(req, res):
       # código para excluir
       res.json({'deleted': True})

---

Proteger Rotas por Tipo de Usuário
-----------------------------------

.. code-block:: python

   from velox.auth import (
       login_required, staff_required, superuser_required
   )

   # Requer usuário logado
   @app.get('/conta')
   @login_required
   def conta(req, res):
       res.json(req.user.to_dict())

   # Requer usuário com is_staff=True
   @app.get('/admin/relatorios')
   @staff_required
   def relatorios(req, res):
       res.json({'reports': []})

   # Requer usuário com is_superuser=True
   @app.get('/admin/config')
   @superuser_required
   def config(req, res):
       res.json({'config': {}})

---

Banco de Dados vs Memória
-------------------------

**Memory (padrão):**
- Rápido para desenvolvimento
- Não persiste entre reinicializações
- Ideal para testes

.. code-block:: text

   AUTH_BACKEND=memory

**Database:**
- Persiste usuários e sessões
- Suporta múltiplos workers (com Redis)
- Recomendado para produção

.. code-block:: text

   AUTH_BACKEND=database
   DATABASE_URI=db/app.db
   # ou PostgreSQL:
   DATABASE_URI=postgresql://user:pass@localhost:5432/mydb

---

Rate Limiting (Proteção contra Brute Force)
--------------------------------------------

O Velox bloqueia tentativas de login excessivas automaticamente:

.. code-block:: text

   # Padrão: 5 tentativas em 900 segundos (15 minutos)
   MAX_LOGIN_ATTEMPTS=5
   LOGIN_WINDOW_SECONDS=900

Se exceder o limite, ``authenticate()`` retorna ``None``:

.. code-block:: python

   user = authenticate(username, password)
   if user is None:
       # Pode ser senha errada OU bloqueado por rate limit
       res.json({'error': 'Tentativas excedidas, tente mais tarde'}, status=429)

---

Modelo User
-----------

.. code-block:: python

   from velox.auth import User

   user = User(
       id=1,
       username='joao',
       email='joao@email.com',
       is_active=True,
       is_staff=False,
       is_superuser=False,
       oauth_provider=None,  # 'google', 'github', etc.
       last_login=datetime.now(),
       roles=['admin'],
       permissions={'posts.criar'}
   )

   # Verificar senha
   user.check_password('senha123')  # True/False

   # Alterar senha
   user.set_password('nova_senha')

   # Converter para dict
   user.to_dict()

---

Logout em Todos os Dispositivos
--------------------------------

Para o backend de banco, você pode destruir todas as sessões de um usuário:

.. code-block:: python

   from velox.auth import auth_backend

   @app.post('/logout-everywhere')
   @login_required
   def logout_everywhere(req, res):
       auth_backend.destroy_all_sessions(req.user)
       res.json({'message': 'Deslogado de todos os dispositivos'})

---

Próximos Passos
---------------

- Configure **HTTPS** em produção (``SESSION_COOKIE_SECURE=true``)
- Use **Redis** como cache para múltiplos workers
- Adicione ** двухфакторную autenticação** (2FA)
- Implemente **recuperação de senha** por email