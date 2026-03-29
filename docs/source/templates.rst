Templates
=========

O Velox usa um sistema de templates similar ao Jinja2, com escape XSS automático.

Renderizar Templates
-------------------

**1. Usando app.render() (recomendado):**

.. code-block:: python

   from velox import Velox

   app = Velox(__name__)
   app.template('templates')  # Define a pasta de templates

   @app.get('/')
   def home(req, res):
       # Renderiza template com contexto
       return app.render('index.html', {
           'title': 'Minha Página',
           'name': 'João',
           'users': [{'name': 'Alice'}, {'name': 'Bob'}]
       })

**2. Usando res.html() com template:**

.. code-block:: python

   @app.get('/pagina')
   def pagina(req, res):
       html = app.render('pagina.html', {'msg': 'Olá!'})
       res.html(html)

**3. Sem template (HTML direto):**

.. code-block:: python

   @app.get('/')
   def home(req, res):
       res.html('<h1>Olá Mundo!</h1>')

---

Variáveis no Template
---------------------

No arquivo ``templates/index.html``:

.. code-block:: html

   <!DOCTYPE html>
   <html>
   <head>
       <title>{{ title }}</title>
   </head>
   <body>
       <h1>Olá, {{ name }}!</h1>
       
       <!-- Acessar objetos -->
       <p>Primeiro usuário: {{ users.0.name }}</p>
       
       <!-- Acessar atributos -->
       <p>Email: {{ user.email }}</p>
   </body>
   </html>

Variáveis são **escapadas automaticamente** contra XSS. Use ``|safe`` para HTML confiável:

.. code-block:: html

   <!-- Escape automático (safe) -->
   {{ conteudo_html }}  <!-- escapa <script> -->

   <!-- HTML seguro (não escapa) -->
   {{ conteudo_html|safe }}

---

Condicionais
------------

.. code-block:: html

   {% if user %}
       <p>Bem-vindo, {{ user.name }}!</p>
   {% else %}
       <p>Bem-vindo, visitante!</p>
   {% endif %}

   {% if count > 10 %}
       <span class="badge">Mais de 10 itens</span>
   {% elif count > 5 %}
       <span class="badge">Entre 5 e 10</span>
   {% else %}
       <span class="badge">Poucos itens</span>
   {% endif %}

---

Loops (For)
-----------

.. code-block:: html

   <ul>
   {% for user in users %}
       <li>{{ user.name }} - {{ user.email }}</li>
   {% endfor %}
   </ul>

   <!-- Com índice -->
   {% for user in users %}
       <p>{{ forloop.index }}: {{ user.name }}</p>
   {% endfor %}

Variáveis disponíveis no loop:
- ``forloop.index`` - posição atual (1-based)
- ``forloop.index0`` - posição atual (0-based)
- ``forloop.first`` - True se primeiro
- ``forloop.last`` - True se último
- ``forloop.length`` - total de items

---

Herança de Templates
--------------------

**templates/base.html:**

.. code-block:: html

   <!DOCTYPE html>
   <html>
   <head>
       <title>{% block title %}Velox{% endblock %}</title>
       <link rel="stylesheet" href="/static/css/style.css">
   </head>
   <body>
       <header>
           <nav>
               <a href="/">Home</a>
               <a href="/sobre">Sobre</a>
           </nav>
       </header>
       
       <main>
           {% block content %}{% endblock %}
       </main>
       
       <footer>
           © 2026 Meu Site
       </footer>
   </body>
   </html>

**templates/index.html:**

.. code-block:: html

   {% extends "base.html" %}

   {% block title %}Página Inicial{% endblock %}

   {% block content %}
       <h1>Bem-vindo!</h1>
       <p>Esta é a página inicial.</p>
   {% endblock %}

---

Includes
--------

**header.html:**

.. code-block:: html

   <header>
       <h1>Meu Site</h1>
       <nav>
           <a href="/">Home</a>
           <a href="/sobre">Sobre</a>
       </nav>
   </header>

**footer.html:**

.. code-block:: html

   <footer>
       <p>© 2026 - Todos os direitos reservados</p>
   </footer>

**index.html (com includes):**

.. code-block:: html

   {% include "header.html" %}

   <main>
       <h1>Página Principal</h1>
       {% include "components/alerta.html" with msg="Olá!" %}
   </main>

   {% include "footer.html" %}

---

Filtros
-------

.. code-block:: html

   <!-- Textos -->
   {{ name|upper }}           <!-- JOÃO -->
   {{ name|lower }}           <!-- joão -->
   {{ name|title }}           <!-- João -->

   <!-- Strings -->
   {{ text|truncate:50 }}     <!-- Primeiros 50 chars... -->
   {{ text|striptags }}       <!-- Remove tags HTML -->
   {{ text|default:"N/A" }}   <!-- Valor padrão -->

   <!-- Listas -->
   {{ items|length }}         <!-- Total de items -->
   {{ items|first }}          <!-- Primeiro item -->
   {{ items|last }}           <!-- Último item -->
   {{ items|join:", " }}      <!-- item1, item2 -->

   <!-- Números -->
   {{ price|currency:"R$" }}  <!-- R$ 10,50 -->
   {{ num|format:"%.2f" }}     <!-- 10.50 -->

   <!-- Datas -->
   {{ date|date:"%d/%m/%Y" }}  <!-- 25/03/2026 -->

   <!-- HTML -->
   {{ html|safe }}            <!-- Não escapa -->

---

Static Files (CSS/JS)
----------------------

Configure no app.py:

.. code-block:: python

   from velox import Velox

   app = Velox(__name__)
   app.template('templates')
   app.static('static')  # Pasta de arquivos estáticos

No template:

.. code-block:: html

   <link rel="stylesheet" href="/static/css/style.css">
   <script src="/static/js/app.js"></script>
   <img src="/static/img/logo.png">

Estrutura:

::

   projeto/
   ├── app.py
   ├── static/
   │   ├── css/
   │   │   └── style.css
   │   ├── js/
   │   │   └── app.js
   │   └── img/
   │       └── logo.png
   └── templates/
       └── index.html

---

Exemplo Completo
----------------

**app.py:**

.. code-block:: python

   from velox import Velox

   app = Velox(__name__)
   app.template('templates')
   app.static('static')

   @app.get('/')
   def home(req, res):
       users = [
           {'name': 'Alice', 'email': 'alice@email.com'},
           {'name': 'Bob', 'email': 'bob@email.com'},
       ]
       return app.render('index.html', {
           'title': 'Home',
           'users': users,
           'count': len(users),
       })

   @app.get('/sobre')
   def sobre(req, res):
       res.html('<h1>Sobre Nós</h1><p>Página sobre.</p>')

   if __name__ == '__main__':
       app.run()

**templates/index.html:**

.. code-block:: html

   {% extends "base.html" %}

   {% block title %}{{ title }}{% endblock %}

   {% block content %}
       <h1>Bem-vindo!</h1>
       
       <p>Total de usuários: {{ count }}</p>
       
       <ul>
       {% for user in users %}
           <li>
               <strong>{{ user.name|title }}</strong> -
               <a href="mailto:{{ user.email }}">{{ user.email }}</a>
           </li>
       {% empty %}
           <li>Nenhum usuário cadastrado.</li>
       {% endfor %}
       </ul>
       
       {% if count > 0 %}
           <p>Há usuários registrados!</p>
       {% endif %}
   {% endblock %}