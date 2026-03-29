# Velox Framework

[![Tests](https://github.com/Barros1915/velox/actions/workflows/tests.yml/badge.svg)](https://github.com/Barros1915/velox/actions/workflows/tests.yml)
[![codecov](https://codecov.io/gh/Barros1915/velox/branch/main/graph/badge.svg)](https://codecov.io/gh/Barros1915/velox)
[![Python Versions](https://img.shields.io/pypi/pyversions/velox-framework.svg)](https://pypi.org/project/velox-framework/)
[![License](https://img.shields.io/pypi/l/velox-framework.svg)](https://pypi.org/project/velox-framework/)
[![Docs](https://img.shields.io/badge/Docs-GitHub%20Pages-blue)](https://barros1915.github.io/velox/)

**O framework Python que cresce com você — de um arquivo único até uma aplicação completa.**

📚 **[Documentação completa no GitHub Pages](https://barros1915.github.io/velox/)**

```bash
pip install velox-web
```

---

## Um arquivo. Zero configuração. Pronto.

Assim como o Flask, você pode criar um servidor completo em um único arquivo:

```python
from velox import Velox

app = Velox(__name__)

@app.get('/')
def home(req, res):
    return '<h1>Hello, Velox!</h1>'

@app.get('/api/users')
async def users(req, res):
    res.json({'users': [{'id': 1, 'name': 'João'}]})

if __name__ == '__main__':
    app.run()
```

```bash
python app.py
# ✓  Velox [WSGI/threading]  http://localhost:8000
```

Não precisa de estrutura de pastas, não precisa de configuração, não precisa instalar nada além do próprio Velox.

---

## Ou um projeto completo com CLI

```bash
velox init meu-projeto
cd meu-projeto
velox run
```

Estrutura gerada:
```
meu-projeto/
├── app.py              # ponto de entrada
├── templates/          # templates HTML
├── static/
│   ├── css/style.css
│   └── img/velox-logo.png
├── db/                 # banco de dados (dentro do projeto)
├── .env                # configurações
└── requirements.txt
```

---

## O que torna o Velox diferente

| | Velox | Flask | Django | FastAPI |
|---|---|---|---|---|
| Um arquivo só | ✅ | ✅ | ❌ | ✅ |
| ORM embutido | ✅ | ❌ | ✅ | ❌ |
| Admin estilo Django | ✅ | ❌ | ✅ | ❌ |
| WSGI + ASGI no mesmo app | ✅ | ❌ | ❌ | ❌ |
| Sync + Async no mesmo app | ✅ | ❌ | ❌ | ✅ |
| WebSocket nativo | ✅ | ❌ | ❌ | ✅ |
| Zero dependências obrigatórias | ✅ | ❌ | ❌ | ❌ |
| CLI com scaffolding | ✅ | ❌ | ✅ | ❌ |
| Auth + OAuth embutido | ✅ | ❌ | ✅ | ❌ |
| Sessions server-side | ✅ | ❌ | ✅ | ❌ |
| Cache multi-backend embutido | ✅ | ❌ | ✅ | ❌ |
| CSRF automático nos forms | ✅ | ❌ | ✅ | ❌ |

---

## Flexível do jeito que você quiser

### Modo minimalista (um arquivo)
```python
from velox import Velox

app = Velox(__name__)

@app.get('/ping')
def ping(req, res):
    res.json({'pong': True})

app.run(port=3000)
```

### Modo modular (apps separados)
```bash
velox startapp blog
velox startapp usuarios
```

```python
# app.py
from velox import Velox
from blog.views import router as blog_router
from usuarios.views import router as user_router

app = Velox(__name__)
app.include(blog_router)
app.include(user_router)
app.run()
```

### Modo ASGI com async e WebSocket
```python
from velox import Velox

app = Velox(__name__)

@app.get('/api/dados')
async def dados(req, res):
    resultado = await buscar_dados()
    res.json(resultado)

@app.websocket('/ws/chat')
async def chat(ws):
    while True:
        msg = await ws.receive()
        if not msg:
            break
        await ws.send(f'echo: {msg}')

# uvicorn app:app
app.run(asgi=True)
```

---

## ORM assíncrono (modo ASGI)

No modo ASGI com `async def`, use `AsyncModel` para não bloquear o event loop:

```python
from velox.database import AsyncModel, AsyncDatabase

class Post(AsyncModel):
    table  = 'posts'
    schema = {'title': str, 'content': str, 'published': bool}

# Configurar banco (ou via DATABASE_URI no .env)
Post.set_database(AsyncDatabase('db/app.db'))

@app.get('/posts')
async def list_posts(req, res):
    posts = await Post.all()
    res.json([p.to_dict() for p in posts])

@app.post('/posts')
async def create_post(req, res):
    post = await Post.create(**(req.json or {}))
    res.json(post.to_dict(), status=201)

@app.get('/posts/<id:int>')
async def get_post(req, res, id):
    post = await Post.get(id)
    if not post:
        res.json({'error': 'não encontrado'}, status=404)
        return
    res.json(post.to_dict())
```

Instale os drivers async:
```bash
pip install velox-web[async]
# aiosqlite (SQLite) + asyncpg (PostgreSQL)
```

---



```python
from velox.database import Model, ForeignKey, ManyToMany

class Post(Model):
    table  = 'posts'
    schema = {
        'title':     str,
        'content':   str,
        'published': bool,
    }
    _relationships = {
        'tags': ManyToMany('Tag', through='post_tags'),
    }

Post.create_table()

# CRUD
post  = Post.create(title='Olá Mundo', content='...', published=True)
post  = Post.get(1)
posts = Post.where('published', '=', True).order_by('id', 'DESC').limit(10).get()
page  = Post.paginate(page=1, per_page=20)

post.update(title='Novo título')
post.delete()

# Relacionamentos
tags = post.related('tags')       # ManyToMany
post.add_related('tags', tag)
post.remove_related('tags', tag)
```

SQLite por padrão. Drivers para outros bancos:
```env
DATABASE_URI=db/app.db
# DATABASE_URI=postgresql://user:pass@localhost/mydb
# DATABASE_URI=mysql://user:pass@localhost/mydb
# DATABASE_URI=mariadb://user:pass@localhost/mydb
```

---

## Autenticação completa

```python
from velox.auth import authenticate, login, login_required, create_user

# Criar usuário
create_user('joao', 'joao@email.com', 'senha123')

@app.post('/login')
def do_login(req, res):
    user = authenticate(req.form.get('username'), req.form.get('password'))
    if user:
        session_key = login(req, user)
        res.set_cookie('session_key', session_key)
        res.redirect('/')
    else:
        res.json({'error': 'Credenciais inválidas'}, status=401)

@app.get('/perfil')
@login_required
def perfil(req, res):
    res.json(req.user.to_dict())
```

OAuth com Google, GitHub, Facebook e Discord:
```python
from velox.auth import get_oauth_provider, oauth_authenticate, login

@app.get('/auth/google')
def google_login(req, res):
    provider = get_oauth_provider('google')
    res.redirect(provider.get_auth_url())

@app.get('/auth/google/callback')
def google_callback(req, res):
    user = oauth_authenticate('google', req.args.get('code'))
    if user:
        session_key = login(req, user)
        res.set_cookie('session_key', session_key)
        res.redirect('/')
```

---

## Sessions server-side

Por padrão, o Velox usa sessions server-side — os dados ficam no cache (memory, Redis ou SQLite), apenas o ID da sessão viaja no cookie:

```python
from velox.session import SessionManager

sessions = SessionManager()  # server_side=True por padrão

@app.get('/dashboard')
def dashboard(req, res):
    session = sessions.get_session(req, res)
    user_id = session.get('user_id')
    if not user_id:
        res.redirect('/login')
        return
    session['last_visit'] = '2026-03-28'
    session.save()
    res.json({'user_id': user_id})
```

Com Redis (múltiplos workers):
```env
CACHE_BACKEND=redis
CACHE_REDIS_URL=redis://localhost:6379/0
```

---

## Painel Admin (estilo Django)

```python
from velox.admin import site, ModelAdmin

@site.register(Post)
class PostAdmin(ModelAdmin):
    list_display    = ['id', 'title', 'published', 'created_at']
    list_filter     = ['published']
    search_fields   = ['title', 'content']
    ordering        = [('created_at', 'desc')]
    readonly_fields = ['created_at']
    fieldsets       = [
        ('Conteúdo',      ['title', 'content']),
        ('Configurações', ['published', 'created_at']),
    ]
    per_page = 20

    def display_published(self, obj):
        return '✓ Publicado' if obj.published else '✗ Rascunho'

site.register_routes(app)
# Acesse /admin/ — configure via .env: VELOX_ADMIN_USER, VELOX_ADMIN_PASSWORD
```

Funcionalidades incluídas:
- Busca por campos (`search_fields`)
- Filtros laterais (`list_filter`)
- Ordenação clicável por coluna
- Paginação com navegação
- Ações em lote (excluir selecionados + customizáveis)
- Exportação CSV
- Fieldsets agrupados
- Log de atividade
- Botões: Salvar / Salvar e adicionar outro / Salvar e continuar editando

---

## Templates com herança e escape XSS automático

```html
<!-- templates/base.html -->
<!DOCTYPE html>
<html>
<head><title>{% block title %}Velox{% endblock %}</title></head>
<body>{% block content %}{% endblock %}</body>
</html>
```

```html
<!-- templates/index.html -->
{% extends "base.html" %}
{% block title %}{{ titulo }}{% endblock %}
{% block content %}
  <h1>{{ titulo }}</h1>
  {% for post in posts %}
    <article>
      <h2>{{ post.title }}</h2>
      {{ post.content|safe }}
    </article>
  {% endfor %}
{% endblock %}
```

Variáveis são escapadas automaticamente contra XSS. Use `|safe` para HTML confiável.

---

## Forms com CSRF automático

```python
from velox.forms import Form, CharField, EmailField, Textarea

class ContactForm(Form):
    nome     = CharField(label='Nome', required=True, min_length=2)
    email    = EmailField(label='Email', required=True)
    mensagem = CharField(label='Mensagem', required=True, widget=Textarea())

@app.get('/contato')
def contato_get(req, res):
    form = ContactForm()
    # render(request) injeta o CSRF token automaticamente
    return app.render('contato.html', {'form': form.render(req)})

@app.post('/contato')
def contato_post(req, res):
    form = ContactForm(data=req.form)
    if form.is_valid():
        res.json({'ok': True, 'dados': form.cleaned_data})
    else:
        res.json({'errors': form.errors}, status=400)
```

---

## Cache multi-backend

```python
from velox.cache import cache, cache_on

# Manual
cache.set('chave', {'dados': 123}, timeout=300)
valor = cache.get('chave')

# Decorador
@cache_on(lambda *a: f'user:{a[0]}', timeout=60)
def get_user(user_id):
    return User.get(user_id)
```

Configure via `.env`:
```env
CACHE_BACKEND=memory   # padrão (dev)
CACHE_BACKEND=file     # SQLite persistente
CACHE_BACKEND=redis    # Redis (produção, múltiplos workers)
CACHE_REDIS_URL=redis://localhost:6379/0
```

---

## Logging

```python
from velox.log import Logger, get_logger

# Setup
Logger.setup('meu-app', level='INFO', log_file='logs/app.log')

# Uso
log = get_logger('meu-app')
log.info('Servidor iniciado')
log.error('Erro ao conectar ao banco')
```

---

## Instalação

```bash
# Básico (zero dependências)
pip install velox-web

# Com ASGI (uvicorn)
pip install velox-web[asgi]

# Com PostgreSQL
pip install velox-web[postgres]

# Com MySQL
pip install velox-web[mysql]

# Com MariaDB (mesmo driver do MySQL)
pip install velox-web[mariadb]

# Com async (todos os drivers)
pip install velox-web[async]

# Tudo
pip install velox-web[full]
```

---

## CLI

```bash
velox init meu-projeto        # Cria projeto completo
velox startapp blog           # Cria app modular
velox startapp api --api      # App API-only (sem templates)
velox run                     # Inicia servidor
velox run --port 5000         # Porta customizada
velox routes                  # Lista todas as rotas
velox version                 # Versão
```

---

## Configuração via .env

```env
APP_HOST=0.0.0.0
APP_PORT=8000
APP_DEBUG=true

VELOX_SECRET_KEY=sua-chave-secreta
VELOX_ADMIN_USER=admin
VELOX_ADMIN_PASSWORD=senha-segura
VELOX_ADMIN_PREFIX=/admin

DATABASE_URI=db/app.db
# DATABASE_URI=postgresql://user:pass@localhost/mydb

CACHE_BACKEND=memory
# CACHE_BACKEND=redis
# CACHE_REDIS_URL=redis://localhost:6379/0

SESSION_COOKIE_NAME=velox_sid
SESSION_EXPIRE_SECONDS=86400
SESSION_COOKIE_SECURE=false
SESSION_COOKIE_SAMESITE=Lax

WS_MAX_MESSAGE_SIZE=1048576

AUTH_BACKEND=memory
# AUTH_BACKEND=database
MAX_LOGIN_ATTEMPTS=5
LOGIN_WINDOW_SECONDS=900
```

---

## Assets

O Velox inclui o logo oficial acessível programaticamente:

```python
from velox.assets import logo_svg, logo_path, LOGO_PNG

# SVG inline para HTML
svg = logo_svg('icon')        # 'default' | 'icon' | 'horizontal' | 'dark'

# Caminho absoluto do PNG
path = logo_path('velox-logo.png')
```

---

## Licença

MIT — use como quiser.