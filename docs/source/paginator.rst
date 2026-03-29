Paginator - Paginação
=====================

Sistema de paginação para listagens.

Uso Básico
----------

.. code-block:: python

   from velox.paginator import Paginator

   @app.get('/posts')
   def list_posts(req, res):
       page = int(req.args.get('page', 1))
       per_page = 10

       posts = Post.all()
       paginator = Paginator(posts, per_page=per_page)
       page_obj = paginator.get_page(page)

       res.json({
           'posts': page_obj.items,
           'total': page_obj.total,
           'page': page_obj.number,
           'pages': page_obj.pages,
       })

---

Paginator com QuerySet
----------------------

.. code-block:: python

   # Paginar resultado do banco
   paginator = Paginator(queryset, per_page=20)

   page1 = paginator.get_page(1)
   page2 = paginator.get_page(2)

---

Page Object
-----------

.. code-block:: python

   page = paginator.get_page(2)

   page.number        # número da página atual
   page.items         # itens da página
   page.total         # total de itens
   page.pages         # total de páginas
   page.has_prev      # existe página anterior?
   page.has_next      # existe próxima página?
   page.prev_number   # número da página anterior
   page.next_number   # número da próxima página
   page.range         # lista de números de página para exibir

---

Template
---------

.. code-block:: html

   <div class="pagination">
       {% if page.has_prev %}
           <a href="?page={{ page.prev_number }}">‹ Anterior</a>
       {% endif %}

       {% for p in page.range %}
           {% if p == page.number %}
               <span class="current">{{ p }}</span>
           {% else %}
               <a href="?page={{ p }}">{{ p }}</a>
           {% endif %}
       {% endfor %}

       {% if page.has_next %}
           <a href="?page={{ page.next_number }}">Próximo ›</a>
       {% endif %}
   </div>

---

Paginator com Model
-------------------

.. code-block:: python

   from velox.database import Model

   class Post(Model):
       table = 'posts'

   # Método paginate no Model
   result = Post.paginate(page=1, per_page=10)
   # Retorna: {'items': [...], 'total': 100, 'page': 1, 'pages': 10}

---

Parâmetros
----------

.. code-block:: python

   paginator = Paginator(
       items,
       per_page=10,       # itens por página
       orphans=3,         # itens órfãos na última página
       allow_empty_first_page=True
   )

---

Navegação de Páginas
--------------------

.. code-block:: python

   # Obter primeira página
   first = paginator.get_page(1)

   # Obter última página
   last = paginator.get_page(paginator.num_pages)

   # Verificar se página existe
   if paginator.page_exists(5):
       page5 = paginator.get_page(5)