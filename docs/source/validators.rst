Validators - Validadores
=========================

Funções de validação reutilizáveis.

Validadores Disponíveis
-----------------------

.. code-block:: python

   from velox.validators import (
       validate_email,
       validate_url,
       validate_phone,
       validate_cpf,
       validate_cnpj,
       validate_min_length,
       validate_max_length,
       validate_range,
       validate_regex,
       validate_file_extension,
       validate_file_size,
   )

---

validate_email
--------------

.. code-block:: python

   from velox.validators import validate_email

   try:
       validate_email('user@domain.com')
       print('Email válido')
   except ValueError as e:
       print(f'Erro: {e}')

---

validate_cpf
------------

.. code-block:: python

   from velox.validators import validate_cpf

   try:
       validate_cpf('123.456.789-09')
       print('CPF válido')
   except ValueError:
       print('CPF inválido')

---

validate_cnpj
-------------

.. code-block:: python

   from velox.validators import validate_cnpj

   try:
       validate_cnpj('12.345.678/0001-90')
       print('CNPJ válido')
   except ValueError:
       print('CNPJ inválido')

---

validate_phone
---------------

.. code-block:: python

   from velox.validators import validate_phone

   # Aceita vários formatos
   validate_phone('(11) 99999-9999')
   validate_phone('11999999999')
   validate_phone('+55 11 99999 9999')

---

validate_url
------------

.. code-block:: python

   from velox.validators import validate_url

   validate_url('https://example.com')
   validate_url('http://test.com/path')  # URL completa

---

validate_min_length / validate_max_length
-----------------------------------------

.. code-block:: python

   from velox.validators import validate_min_length, validate_max_length

   validate_min_length('abc', 2)  # ✓
   validate_min_length('a', 2)    # ✗ ValueError

   validate_max_length('abc', 5)  # ✓
   validate_max_length('abcdef', 5)  # ✗ ValueError

---

validate_range
--------------

.. code-block:: python

   from velox.validators import validate_range

   validate_range(10, min=0, max=100)  # ✓
   validate_range(-1, min=0, max=100)   # ✗ ValueError

---

validate_regex
--------------

.. code-block:: python

   from velox.validators import validate_regex

   validate_regex('abc123', r'^[a-z]+\d+$')  # ✓
   validate_regex('123', r'^[a-z]+\d+$')     # ✗ ValueError

---

validate_file_extension
------------------------

.. code-block:: python

   from velox.validators import validate_file_extension

   validate_file_extension('photo.jpg', ['jpg', 'png', 'gif'])
   validate_file_extension('document.pdf', ['jpg', 'png', 'gif'])  # ✗

---

validate_file_size
------------------

.. code-block:: python

   from velox.validators import validate_file_size

   # max_size em bytes
   validate_file_size(file_size=1024 * 1024, max_size=5 * 1024 * 1024)  # ✓
   validate_file_size(file_size=10 * 1024 * 1024, max_size=5 * 1024 * 1024)  # ✗

---

Validação Combinada
-------------------

.. code-block:: python

   from velox.validators import validate_email, validate_min_length

   def validate_user_data(data):
       errors = []

       try:
           validate_email(data['email'])
       except ValueError:
           errors.append('Email inválido')

       try:
           validate_min_length(data['name'], 2)
       except ValueError:
           errors.append('Nome muito curto')

       return errors

---

Validadores Customizados
------------------------

.. code-block:: python

   def validate_username(username):
       if not username.replace('_', '').isalnum():
           raise ValueError('Username deve ter apenas letras, números e underscore')
       if len(username) < 3:
           raise ValueError('Username deve ter no mínimo 3 caracteres')
       if len(username) > 30:
           raise ValueError('Username deve ter no máximo 30 caracteres')