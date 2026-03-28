"""
Sistema de Forms - Velox
Similar ao Django forms
"""

from .validators import (
    ValidationError, EmailValidator, MinLengthValidator, MaxLengthValidator,
    MinValueValidator, MaxValueValidator,
)
from typing import Any, Dict, List, Optional


class Widget:
    """Widget base para campos de formulário"""
    def __init__(self, attrs: Dict = None):
        self.attrs = attrs or {}
    
    def render(self, name: str, value: Any = None) -> str:
        """Renderiza o widget"""
        return f'<input name="{name}" {self._render_attrs()}>'
    
    def _render_attrs(self) -> str:
        attrs = ' '.join(f'{k}="{v}"' for k, v in self.attrs.items())
        return attrs


class TextInput(Widget):
    """Input de texto"""
    def render(self, name: str, value: Any = None) -> str:
        val = f' value="{value}"' if value else ''
        return f'<input type="text" name="{name}"{val} {self._render_attrs()}>'


class EmailInput(Widget):
    """Input de email"""
    def render(self, name: str, value: Any = None) -> str:
        val = f' value="{value}"' if value else ''
        return f'<input type="email" name="{name}"{val} {self._render_attrs()}>'


class PasswordInput(Widget):
    """Input de senha"""
    def render(self, name: str, value: Any = None) -> str:
        return f'<input type="password" name="{name}" {self._render_attrs()}>'


class Textarea(Widget):
    """Textarea"""
    def render(self, name: str, value: Any = None) -> str:
        val = value or ''
        return f'<textarea name="{name}" {self._render_attrs()}>{val}</textarea>'


class Select(Widget):
    """Select dropdown"""
    def __init__(self, choices: List[tuple] = None, attrs: Dict = None):
        super().__init__(attrs)
        self.choices = choices or []
    
    def render(self, name: str, value: Any = None) -> str:
        options = ''
        for choice_value, choice_label in self.choices:
            selected = ' selected' if choice_value == value else ''
            options += f'<option value="{choice_value}"{selected}>{choice_label}</option>'
        return f'<select name="{name}" {self._render_attrs()}>{options}</select>'


class CheckboxInput(Widget):
    """Checkbox"""
    def render(self, name: str, value: Any = None) -> str:
        checked = ' checked' if value else ''
        return f'<input type="checkbox" name="{name}"{checked} {self._render_attrs()}>'


class Field:
    """Campo de formulário"""
    
    def __init__(
        self,
        label: str = None,
        required: bool = True,
        initial: Any = None,
        validators: List = None,
        widget: Widget = None,
        error_messages: Dict = None
    ):
        self.label = label
        self.required = required
        self.initial = initial
        self.validators = validators or []
        self.widget = widget or TextInput()
        self.error_messages = error_messages or {}
        self.errors = []
    
    def clean(self, value: Any) -> Any:
        """Valida o campo"""
        self.errors = []
        
        # Verifica se é obrigatório
        if self.required and (value is None or value == ''):
            self.errors.append(self.error_messages.get('required', 'Este campo é obrigatório'))
            return None
        
        if value is None or value == '':
            return value
        
        # Executa validadores
        for validator in self.validators:
            try:
                validator(value)
            except ValidationError as e:
                self.errors.append(e.message)
        
        return value
    
    def render(self, name: str, value: Any = None) -> str:
        """Renderiza o campo"""
        return self.widget.render(name, value or self.initial)
    
    def __str__(self):
        return self.label or ''


class CharField(Field):
    """Campo de texto"""
    def __init__(self, min_length: int = None, max_length: int = None, **kwargs):
        widget = kwargs.pop('widget', None) or TextInput()
        super().__init__(widget=widget, **kwargs)
        
        if min_length:
            self.validators.append(MinLengthValidator(min_length))
        if max_length:
            self.validators.append(MaxLengthValidator(max_length))


class EmailField(Field):
    """Campo de email"""
    def __init__(self, **kwargs):
        super().__init__(widget=EmailInput(), **kwargs)
        self.validators.append(EmailValidator())


class IntegerField(Field):
    """Campo de inteiro"""
    def __init__(self, min_value: int = None, max_value: int = None, **kwargs):
        super().__init__(**kwargs)
        
        if min_value is not None:
            self.validators.append(MinValueValidator(min_value))
        if max_value is not None:
            self.validators.append(MaxValueValidator(max_value))
    
    def clean(self, value: Any) -> Any:
        """Valida como inteiro"""
        if value is None or value == '':
            return None
        
        try:
            return int(value)
        except ValueError:
            self.errors.append('Valor deve ser um inteiro')
            return None


class BooleanField(Field):
    """Campo booleano"""
    def __init__(self, **kwargs):
        super().__init__(widget=CheckboxInput(), **kwargs)
    
    def clean(self, value: Any) -> bool:
        """Valida como booleano"""
        return bool(value)


class Form:
    """Formulário"""
    
    def __init__(self, data: Dict = None, files: Dict = None):
        self.data = data or {}
        self.files = files or {}
        self.errors = {}
        self.cleaned_data = {}
    
    def __getitem__(self, field_name: str) -> Field:
        """Obtém campo pelo nome"""
        return getattr(self, field_name)
    
    def is_valid(self) -> bool:
        """Valida o formulário"""
        self.errors = {}
        self.cleaned_data = {}
        
        for name in self.fields:
            field = getattr(self, name)
            value = self.data.get(name)
            
            # Limpa e valida
            cleaned_value = field.clean(value)
            
            if field.errors:
                self.errors[name] = field.errors
            else:
                self.cleaned_data[name] = cleaned_value
        
        return len(self.errors) == 0
    
    @property
    def fields(self) -> List[str]:
        """Lista de campos do formulário"""
        return [attr for attr in dir(self) if isinstance(getattr(self, attr), Field)]
    
    def render(self, request=None) -> str:
        """
        Renderiza o formulário completo.
        Injeta CSRF token automaticamente se request for fornecido.

        Uso:
            html = form.render(request)   # com CSRF
            html = form.render()          # sem CSRF (APIs, testes)
        """
        csrf_field = ''
        if request is not None:
            try:
                from .csrf import csrf_input
                csrf_field = csrf_input(request)
            except Exception:
                pass

        html = f'<form method="post">{csrf_field}'

        for name in self.fields:
            field = getattr(self, name)
            value = self.data.get(name)
            if field.label:
                html += f'<label>{field.label}</label><br>'
            html += field.render(name, value)
            if name in self.errors:
                for error in self.errors[name]:
                    html += f'<span style="color:red">{error}</span><br>'
            html += '<br>'

        html += '<button type="submit">Enviar</button></form>'
        return html


# Formulários prontos
class ContactForm(Form):
    """Formulário de contato"""
    nome = CharField(label='Nome', required=True, min_length=2)
    email = EmailField(label='Email', required=True)
    mensagem = CharField(label='Mensagem', required=True, widget=Textarea())


class LoginForm(Form):
    """Formulário de login"""
    username = CharField(label='Usuário', required=True)
    password = CharField(label='Senha', required=True, widget=PasswordInput())


class RegisterForm(Form):
    """Formulário de cadastro"""
    username = CharField(label='Usuário', required=True, min_length=3, max_length=20)
    email = EmailField(label='Email', required=True)
    password = CharField(label='Senha', required=True, min_length=6, widget=PasswordInput())
    password_confirm = CharField(label='Confirmar Senha', required=True, widget=PasswordInput())
    
    def clean(self):
        """Validação extra"""
        cleaned = super().cleaned_data
        
        if 'password' in cleaned and 'password_confirm' in cleaned:
            if cleaned['password'] != cleaned['password_confirm']:
                self.errors.setdefault('password_confirm', []).append('Senhas não conferem')
        
        return cleaned
