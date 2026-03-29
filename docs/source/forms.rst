Forms - Formulários
===================

Sistema de formulários com validação automática e proteção CSRF.

Campos Disponíveis
------------------

.. code-block:: python

   from velox.forms import (
       Form, CharField, EmailField, TextField,
       IntegerField, FloatField, BooleanField,
       DateField, DateTimeField, ChoiceField,
       PasswordField, Textarea, Select, Checkbox,
   )

---

Formulário Básico
-----------------

.. code-block:: python

   from velox.forms import Form, CharField, EmailField, Textarea

   class ContactForm(Form):
       nome     = CharField(label='Nome', required=True, min_length=2)
       email    = EmailField(label='Email', required=True)
       mensagem = CharField(label='Mensagem', required=True, widget=Textarea())

   @app.get('/contato')
   def contato_get(req, res):
       form = ContactForm()
       html = app.render('contato.html', {'form': form.render(req)})
       res.html(html)

   @app.post('/contato')
   def contato_post(req, res):
       form = ContactForm(data=req.form)

       if form.is_valid():
           # Processar dados
           data = form.cleaned_data
           print(f'Nome: {data["nome"]}, Email: {data["email"]}')
           res.json({'success': True})
       else:
           res.json({'errors': form.errors}, status=400)

---

Campos Comuns
-------------

CharField
~~~~~~~~~

.. code-block:: python

   nome = CharField(
       label='Nome completo',
       required=True,
       min_length=3,
       max_length=100,
       placeholder='Seu nome'
   )

EmailField
~~~~~~~~~~

.. code-block:: python

   email = EmailField(
       label='Endereço de email',
       required=True
   )

Textarea
~~~~~~~~

.. code-block:: python

   mensagem = CharField(
       label='Mensagem',
       widget=Textarea(attrs={'rows': 5, 'cols': 40})
   )

Select
~~~~~~

.. code-block:: python

   from velox.forms import ChoiceField

   categoria = ChoiceField(
       label='Categoria',
       choices=[
           ('tech', 'Tecnologia'),
           ('games', 'Games'),
           ('music', 'Música'),
       ],
       required=True
   )

Checkbox
~~~~~~~~

.. code-block:: python

   from velox.forms import BooleanField

   aceitar_termos = BooleanField(
       label='Aceito os termos',
       required=True
   )

IntegerField
~~~~~~~~~~~~

.. code-block:: python

   idade = IntegerField(
       label='Idade',
       min_value=0,
       max_value=150
   )

---

Validação Personalizada
------------------------

.. code-block:: python

   class CadastroForm(Form):
       username = CharField(label='Username', required=True)

       def validate_username(self, value):
           if len(value) < 3:
               raise ValueError('Mínimo 3 caracteres')
           if not value.isalnum():
               raise ValueError('Apenas letras e números')

---

Renderizar HTML
---------------

.. code-block:: html

   <!-- contato.html -->
   <form method="POST">
       {{{ form.nome }}}
       {{{ form.email }}}
       {{{ form.mensagem }}}
       <button type="submit">Enviar</button>
   </form>

O token CSRF é injetado automaticamente no render.

---

Accessors no Template
---------------------

.. code-block:: html

   <div class="form-group">
       <label>{{{ form.nome.label }}}</label>
       {{{ form.nome.widget }}}
       <span class="error">{{{ form.nome.error }}}</span>
   </div>

---

Validação Extra
---------------

.. code-block:: python

   class RegistroForm(Form):
       email = EmailField(label='Email', required=True)
       confirm_email = EmailField(label='Confirmar email', required=True)

       def validate(self):
           super().validate()
           if self.cleaned_data.get('email') != self.cleaned_data.get('confirm_email'):
               self.errors['confirm_email'] = 'Emails não coincidem'

---

Configuração
------------

O CSRF é gerado automaticamente. Configure no .env:

.. code-block:: text

   VELOX_SECRET_KEY=sua-chave-secreta
   CSRF_COOKIE_SECURE=true  # em produção
   CSRF_COOKIE_SAMESITE=Lax