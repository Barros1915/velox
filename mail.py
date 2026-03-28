"""
Sistema de Envio de Emails - Velox
Similar ao django.core.mail
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional


class EmailMessage:
    """Mensagem de email"""
    
    def __init__(
        self,
        subject: str = '',
        body: str = '',
        from_email: str = None,
        to: List[str] = None,
        cc: List[str] = None,
        bcc: List[str] = None,
        html: bool = False
    ):
        self.subject = subject
        self.body = body
        self.from_email = from_email or 'noreply@localhost'
        self.to = to or []
        self.cc = cc or []
        self.bcc = bcc or []
        self.html = html
        self.attachments = []
    
    def send(self, smtp_host: str = 'localhost', smtp_port: int = 25, 
             username: str = None, password: str = None,
             use_tls: bool = False) -> bool:
        """Envia o email"""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = self.subject
            msg['From'] = self.from_email
            msg['To'] = ', '.join(self.to)
            
            if self.cc:
                msg['Cc'] = ', '.join(self.cc)
            
            if self.html:
                part = MIMEText(self.body, 'html')
            else:
                part = MIMEText(self.body, 'plain')
            
            msg.attach(part)
            
            # Enviar
            all_recipients = self.to + self.cc + self.bcc
            
            server = smtplib.SMTP(smtp_host, smtp_port)
            if use_tls:
                server.starttls()
            if username and password:
                server.login(username, password)
            
            server.sendmail(self.from_email, all_recipients, msg.as_string())
            server.quit()
            
            return True
        except Exception as e:
            print(f"Erro ao enviar email: {e}")
            return False


def send_mail(
    subject: str,
    message: str,
    from_email: str = None,
    recipient_list: List[str] = None,
    html: bool = False,
    smtp_host: str = 'localhost',
    smtp_port: int = 25,
    username: str = None,
    password: str = None,
    use_tls: bool = False
) -> bool:
    """Função de conveniência para enviar email"""
    msg = EmailMessage(
        subject=subject,
        body=message,
        from_email=from_email,
        to=recipient_list,
        html=html
    )
    return msg.send(smtp_host, smtp_port, username, password, use_tls)


def send_html_mail(
    subject: str,
    html_content: str,
    from_email: str = None,
    recipient_list: List[str] = None,
    **kwargs
) -> bool:
    """Envia email HTML"""
    return send_mail(subject, html_content, from_email, recipient_list, True, **kwargs)
