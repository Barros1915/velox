Painel Admin
============

Painel administrativo completo inspirado no Django Admin. CRUD completo com busca, filtros, paginação e exportação CSV.

Configuração
------------

No arquivo ``.env``:

.. code-block:: text

   VELOX_ADMIN_USER=admin
   VELOX_ADMIN_PASSWORD=senha123
   VELOX_ADMIN_PREFIX=/admin
   VELOX_SECRET_KEY=sua-chave-secreta

---

Registrar Modelos
-----------------

.. code-block:: python

   from velox import Velox
   from velox.admin import site, ModelAdmin

   app = Velox(__name__)

   # Registrar no admin
   @site.register(Post)
   class PostAdmin(ModelAdmin):
       list_display    = ['id', 'title', 'published', 'created_at']
       list_filter     = ['published']
       search_fields   = ['title', 'content']
       ordering        = [('created_at', 'desc')]
       per_page        = 20

   # Registrar rotas
   site.register_routes(app)

Acesse: http://localhost:8000/admin/

---

Configurações do ModelAdmin
----------------------------

list_display
~~~~~~~~~~~~

Colunas exibidas na listagem:

.. code-block:: python

   class PostAdmin(ModelAdmin):
       list_display = ['id', 'title', 'author', 'published', 'created_at']

list_filter
~~~~~~~~~~~

Filtros laterais na listagem:

.. code-block:: python

   class PostAdmin(ModelAdmin):
       list_filter = ['published', 'category', 'author']

search_fields
~~~~~~~~~~~~~

Campos pesquisáveis:

.. code-block:: python

   class PostAdmin(ModelAdmin):
       search_fields = ['title', 'content', 'author__name']

ordering
~~~~~~~~

Ordenação padrão:

.. code-block:: python

   class PostAdmin(ModelAdmin):
       ordering = [('created_at', 'desc'), ('title', 'asc')]

fieldsets
~~~~~~~~~

Campos agrupados no formulário:

.. code-block:: python

   class PostAdmin(ModelAdmin):
       fieldsets = [
           ('Conteúdo', {
               'fields': ['title', 'slug', 'content']
           }),
           ('Publicação', {
               'fields': ['published', 'published_at']
           }),
           ('Meta', {
               'fields': ['author', 'category'],
               'classes': ['collapse']
           }),
       ]

readonly_fields
~~~~~~~~~~~~~~~

Campos somente leitura:

.. code-block:: python

   class PostAdmin(ModelAdmin):
       readonly_fields = ['created_at', 'updated_at']

exclude
~~~~~~~

Campos excluídos do formulário:

.. code-block:: python

   class PostAdmin(ModelAdmin):
       exclude = ['internal_notes']

per_page
~~~~~~~~

Registros por página (padrão 25):

.. code-block:: python

   class PostAdmin(ModelAdmin):
       per_page = 50

actions
~~~~~~~

Ações em lote customizadas:

.. code-block:: python

   class PostAdmin(ModelAdmin):
       actions = ['publish', 'unpublish']

       def publish(self, request, queryset):
           for obj in queryset:
               obj.update(published=True)
           return 'Publicados com sucesso!'

---

Exibição Customizada
--------------------

Use métodos ``display_<campo>`` para formatar colunas:

.. code-block:: python

   class PostAdmin(ModelAdmin):
       list_display = ['id', 'title', 'is_published', 'created_at']

       def is_published(self, obj):
           if obj.published:
               return '✓'
           return '✗'

---

Permissões
----------

.. code-block:: python

   class PostAdmin(ModelAdmin):
       def has_add_permission(self, request):
           return request.user.is_staff

       def has_change_permission(self, request):
           return request.user.is_staff

       def has_delete_permission(self, request):
           return request.user.is_superuser

---

Exportação CSV
--------------

Acesse ``/admin/post/export/`` para baixar CSV dos registros.

---

Hooks de Save/Delete
--------------------

.. code-block:: python

   class PostAdmin(ModelAdmin):
       def save_model(self, request, obj, form_data, change):
           if not change:
               # Novo registro
               obj.created_by = request.user.username
           obj.save()

       def delete_model(self, request, obj):
           # Log antes de deletar
           print(f'Deletando: {obj}')
           obj.delete()