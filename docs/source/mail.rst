Sistema de Emails
==================

Envio de emails SMTP simples.

Uso Básico
----------

.. code-block:: python

   from velox.mail import send_mail

   # Email simples
   send_mail(
       subject='Olá',
       message='Conteúdo do email',
       from_email='noreply@meusite.com',
       recipient_list=['destino@email.com'],
       smtp_host='smtp.meusite.com',
       smtp_port=587,
       username='user@meusite.com',
       password='senha',
       use_tls=True
   )

---

Email HTML
----------

.. code-block:: python

   from velox.mail import send_html_mail

   html_content = '''
   <html>
   <body>
       <h1>Bem-vindo!</h1>
       <p>Seu cadastro foi realizado com sucesso.</p>
   </body>
   </html>
   '''

   send_html_mail(
       subject='Bem-vindo ao MeuSite',
       html_content=html_content,
       from_email='noreply@meusite.com',
       recipient_list=['usuario@email.com'],
       smtp_host='smtp.meusite.com',
       smtp_port=587,
       username='user@meusite.com',
       password='senha',
       use_tls=True
   )

---

Classe EmailMessage
--------------------

Para emails mais complexos:

.. code-block:: python

   from velox.mail import EmailMessage

   msg = EmailMessage(
       subject='Assunto',
       body='Conteúdo em texto plano',
       from_email='remetente@email.com',
       to=['destino@email.com'],
       cc=['copia@email.com'],
       bcc=['copia_oculta@email.com']
   )

   # Enviar
   msg.send(
       smtp_host='smtp.meusite.com',
       smtp_port=587,
       username='user@meusite.com',
       password='senha',
       use_tls=True
   )

---

Configuração via .env
---------------------

.. code-block:: text

   # SMTP
   SMTP_HOST=smtp.meusite.com
   SMTP_PORT=587
   SMTP_USERNAME=user@meusite.com
   SMTP_PASSWORD=senha
   SMTP_USE_TLS=true

---

Funções de Conveniência
-----------------------

``send_mail()``
   Envia email texto simples

``send_html_mail()``
   Envia email HTML

Ambas retornam ``True`` em caso de sucesso ou ``False`` em caso de erro.