Templates
==========

O Velox inclui um motor de templates poderoso.

Configuração
------------

.. code-block:: python

   from velox import Velox

   app = Velox(__name__)

   # Definir pasta de templates (padrão: templates)
   app.template('templates')

   @app.get('/')
   def index(req, res):
       return app.render('index.html', {'nome': 'João'})

Variáveis
---------

Use ``{{ variavel }}`` para imprimir variáveis:

.. code-block:: html

   <h1>Olá, {{ nome }}!</h1>

   {# Comentário #}

Condicionais
-------------

.. code-block:: html

   {% if user %}
       <p>Bem-vindo, {{ user.name }}!</p>
   {% else %}
       <p>Por favor, faça login.</p>
   {% endif %}

Loops
----

.. code-block:: html

   <ul>
   {% for item in items %}
       <li>{{ item.name }}</li>
   {% endfor %}
   </ul>

Variáveis de Loop
~~~~~~~~~~~~~~~~

No loop, você tem acesso a:

- ``items`` - o item atual
- ``items_index`` - índice (0-based)
- ``items_first`` - True se primeiro
- ``items_last`` - True se último
- ``items_length`` - total de itens

Filtros
-------

Use filtros com ``|``:

.. code-block:: html

   {{ nome|upper }}           {# JOÃO #}
   {{ nome|lower }}           {# joão #}
   {{ nome|title }}           {# João #}
   {{ texto|truncate:30 }}   {# texto truncado #}
   {{ preco|currency:"R$" }}  {# R$ 10,00 #}
   {{ items|join:", " }}       {# item1, item2 #}

Herança de Templates
--------------------

base.html:

.. code-block:: html

   <!DOCTYPE html>
   <html>
   <head>
       <title>{% block title %}Meu Site{% endblock %}</title>
       {% block extra %}{% endblock %}
   </head>
   <body>
       {% block content %}{% endblock %}
   </body>
   </html>

 Extend:

.. code-block:: html

   {% extends "base.html" %}

   {% block title %}Página Inicial{% endblock %}

   {% block content %}
       <h1>Olá!</h1>
   {% endblock %}

Macros
-----

Defina macros reutilizáveis:

.. code-block:: html

   {% macro button(text, type='primary') %}
       <button class="btn btn-{{ type }}">{{ text }}</button>
   {% endmacro %}

Use:

.. code-block:: html

   {{ button('Salvar') }}
   {{ button('Cancelar', 'secondary') }}

Includes
---------

Inclua outros templates:

.. code-block:: html

   {% include "header.html" %}
   {% include "footer.html" %}

Próximos Passos
-------------

- Explore :doc:`template_filters` para todos os filtros
- Leia :doc:`template_inheritance` para herança avançada