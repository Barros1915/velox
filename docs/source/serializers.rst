Serializers - Serializadores
=============================

Converter objetos Python para JSON e vice-versa.

Uso Básico
----------

.. code-block:: python

   from velox.serializers import serializer, deserialize

   # Serializar objeto
   data = {'id': 1, 'name': 'João', 'email': 'joao@email.com'}
   json_str = serializer(data)

   # Desserializar
   obj = deserialize(json_str)

---

Serializar Model
----------------

.. code-block:: python

   from velox.database import Model

   class User(Model):
       table = 'users'

       def to_dict(self):
           return {
               'id': self.id,
               'name': self.name,
               'email': self.email,
           }

   # Usar no Model
   user = User.get(1)
   data = user.to_dict()
   json_str = serializer(data)

---

Serializar Lista
----------------

.. code-block:: python

   users = User.all()
   data = [u.to_dict() for u in users]
   json_str = serializer(data)

---

Campos Específicos
------------------

.. code-block:: python

   def to_dict(self, fields=None, exclude=None):
       d = self.__dict__.copy()
       d.pop('_state', None)

       if fields:
           d = {k: v for k, v in d.items() if k in fields}

       if exclude:
           d = {k: v for k, v in d.items() if k not in exclude}

       return d

---

Serializadores Customizados
---------------------------

.. code-block:: python

   from velox.serializers import Serializer

   class UserSerializer:
       @staticmethod
       def serialize(user):
           return {
               'id': user.id,
               'name': user.name,
               'email': user.email,
               'created_at': user.created_at.isoformat() if user.created_at else None,
           }

       @staticmethod
       def deserialize(data):
           return User(
               id=data.get('id'),
               name=data.get('name'),
               email=data.get('email'),
           )

   # Usar
   json_str = UserSerializer.serialize(user)
   user = UserSerializer.deserialize(data)

---

Serialização com Relationships
------------------------------

.. code-block:: python

   class PostSerializer:
       @staticmethod
       def serialize(post):
           return {
               'id': post.id,
               'title': post.title,
               'author': {
                   'id': post.author.id,
                   'name': post.author.name,
               },
               'tags': [t.name for t in post.related('tags')],
           }

---

JSON Response
-------------

.. code-block:: python

   @app.get('/api/users')
   def list_users(req, res):
       users = User.all()
       data = [u.to_dict() for u in users]
       res.json(data)

   @app.get('/api/users/<int:id>')
   def get_user(req, res, id):
       user = User.get(id)
       if not user:
           res.json({'error': 'Not found'}, status=404)
           return
       res.json(user.to_dict())

---

Validação com Serializer
------------------------

.. code-block:: python

   class UserInputSerializer:
       @staticmethod
       def validate(data):
           errors = {}

           if 'name' not in data or len(data['name']) < 2:
               errors['name'] = 'Nome deve ter no mínimo 2 caracteres'

           if 'email' not in data or '@' not in data['email']:
               errors['email'] = 'Email inválido'

           if errors:
               raise ValueError(errors)

           return data

   # Usar
   validated = UserInputSerializer.validate(req.json)