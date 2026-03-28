"""
Sistema de SerializaÃ§Ã£o de Dados - Velox
Similar ao django.core.serializers

Recursos:
- SerializaÃ§Ã£o JSON com validaÃ§Ã£o
- SerializaÃ§Ã£o de modelos
- ValidaÃ§Ã£o de dados
- TransformaÃ§Ã£o de campos
"""

import json
import re
from typing import Any, List, Dict, Optional, Callable, Type
from datetime import datetime, date
from decimal import Decimal


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Serializadores
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class Serializer:
    """Serializador base"""
    
    def serialize(self, obj: Any) -> str:
        raise NotImplementedError
    
    def deserialize(self, data: str) -> Any:
        raise NotImplementedError


class JSONSerializer(Serializer):
    """Serializador JSON com opÃ§Ãµes avanÃ§adas"""
    
    def __init__(
        self,
        indent: int = 2,
        ensure_ascii: bool = False,
        sort_keys: bool = False,
        default: Callable = None
    ):
        self.indent = indent
        self.ensure_ascii = ensure_ascii
        self.sort_keys = sort_keys
        self.default = default or self._default_handler
    
    def serialize(self, obj: Any) -> str:
        return json.dumps(
            obj,
            indent=self.indent,
            ensure_ascii=self.ensure_ascii,
            sort_keys=self.sort_keys,
            default=self.default
        )
    
    def deserialize(self, data: str) -> Any:
        return json.loads(data)
    
    def _default_handler(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        if hasattr(obj, '__dict__'):
            d = obj.__dict__.copy()
            d.pop('_authenticated', None)
            d.pop('_cache', None)
            return d
        if hasattr(obj, 'to_dict'):
            return obj.to_dict()
        return str(obj)


class ModelSerializer:
    """
    Serializador de modelos com validação e transformação.

    Uso:
        class UserSerializer(ModelSerializer):
            fields = ['id', 'username', 'email']
            read_only_fields = ['id']
            extra_kwargs = {'password': {'write_only': True}}

        serializer = UserSerializer(data={'username': 'joao', 'password': '123'})
        if serializer.is_valid():
            user = serializer.save()
        else:
            print(serializer.errors)
    """

    model:             type       = None
    fields:            List[str]  = None
    exclude:           List[str]  = None
    read_only_fields:  List[str]  = []
    write_only_fields: List[str]  = []
    extra_kwargs:      Dict       = {}
    validators:        Dict       = {}

    def __init__(self, instance=None, data=None):
        self.instance       = instance
        self._input_data    = data          # dados de entrada (evita conflito com @property data)
        self.errors:         Dict[str, List[str]] = {}
        self.validated_data: Dict = {}
        self._fields_cache:  Dict = {}

    @property
    def data(self) -> Dict:
        """Retorna dados serializados da instância, ou os dados de entrada."""
        if self.instance:
            return self.to_representation(self.instance)
        return self._input_data or {}

    def to_internal_value(self, data: Dict) -> Dict:
        result = {}
        for field_name in self._get_fields():
            if field_name in self.read_only_fields:
                continue
            kwargs = self.extra_kwargs.get(field_name, {})
            if kwargs.get('read_only'):
                continue
            value = data.get(field_name)
            for validator in self.validators.get(field_name, []):
                try:
                    value = validator(value)
                except ValidationError as e:
                    self._add_error(field_name, str(e))
            result[field_name] = value
        return result

    def _get_fields(self) -> List[str]:
        if self.fields is not None:
            return self.fields
        if self.model and hasattr(self.model, 'schema'):
            return list(self.model.schema.keys())
        if self.instance:
            return [k for k in self.instance.__dict__ if not k.startswith('_')]
        return []

    def validate(self, data: Dict) -> Dict:
        return data

    def is_valid(self) -> bool:
        if self._input_data is None:
            return True
        self.errors = {}
        internal  = self.to_internal_value(self._input_data)
        validated = self.validate(internal)
        if self.errors:
            return False
        self.validated_data = validated
        return True

    def save(self, **kwargs):
        if not self.is_valid():
            raise ValueError("Dados inválidos")
        data = {**self.validated_data, **kwargs}
        if self.instance:
            for key, value in data.items():
                setattr(self.instance, key, value)
            return self.instance.update() if hasattr(self.instance, 'update') else self.instance
        if self.model:
            return self.model.create(**data)
        raise ValueError("Model não definido")

    def to_representation(self, instance) -> Dict:
        result = {}
        for field_name in self._get_fields():
            if field_name in self.write_only_fields:
                continue
            value = getattr(instance, field_name, None)
            fn    = getattr(self, f'serialize_{field_name}', None)
            if fn:
                value = fn(value, instance)
            result[field_name] = self._serialize_value(value)
        return result

    def _serialize_value(self, value: Any) -> Any:
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, Decimal):
            return float(value)
        return value

    def _add_error(self, field: str, message: str):
        self.errors.setdefault(field, []).append(message)


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Validadores
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class ValidationError(Exception):
    """Erro de validaÃ§Ã£o"""
    
    def __init__(self, message, field=None):
        self.message = message
        self.field = field
        super().__init__(message)


class Validator:
    """Classe base para validadores"""
    
    def __call__(self, value):
        return self.validate(value)
    
    def validate(self, value):
        raise NotImplementedError


class RequiredValidator(Validator):
    """Valida que o campo Ã© obrigatÃ³rio"""
    
    def validate(self, value):
        if value is None or value == '':
            raise ValidationError('Este campo Ã© obrigatÃ³rio')


class MinLengthValidator(Validator):
    """Valida tamanho mÃ­nimo"""
    
    def __init__(self, min_length: int):
        self.min_length = min_length
    
    def validate(self, value):
        if value and len(str(value)) < self.min_length:
            raise ValidationError(f'Deve ter pelo menos {self.min_length} caracteres')


class MaxLengthValidator(Validator):
    """Valida tamanho mÃ¡ximo"""
    
    def __init__(self, max_length: int):
        self.max_length = max_length
    
    def validate(self, value):
        if value and len(str(value)) > self.max_length:
            raise ValidationError(f'Deve ter no mÃ¡ximo {self.max_length} caracteres')


class MinValueValidator(Validator):
    """Valida valor mÃ­nimo"""
    
    def __init__(self, min_value: int):
        self.min_value = min_value
    
    def validate(self, value):
        if value is not None and value < self.min_value:
            raise ValidationError(f'Deve ser pelo menos {self.min_value}')


class MaxValueValidator(Validator):
    """Valida valor mÃ¡ximo"""
    
    def __init__(self, max_value: int):
        self.max_value = max_value
    
    def validate(self, value):
        if value is not None and value > self.max_value:
            raise ValidationError(f'Deve ser no mÃ¡ximo {self.max_value}')





class EmailValidator(Validator):
    """Valida formato de email"""

    EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    def validate(self, value):
        if value and not re.match(self.EMAIL_REGEX, str(value)):
            raise ValidationError('Email inválido')


class URLValidator(Validator):
    """Valida formato de URL"""

    URL_REGEX = r'^https?://[^\s/$.?#].[^\s]*$'

    def validate(self, value):
        if value and not re.match(self.URL_REGEX, str(value)):
            raise ValidationError('URL inválida')


class RegexValidator(Validator):
    """Valida com expressão regular"""

    def __init__(self, pattern: str, message: str = None):
        self.pattern = re.compile(pattern)
        self.message = message or 'Formato inválido'

    def validate(self, value):
        if value and not self.pattern.match(str(value)):
            raise ValidationError(self.message)


class ChoiceValidator(Validator):
    """Valida que o valor está entre as escolhas"""

    def __init__(self, choices: List):
        self.choices = choices

    def validate(self, value):
        if value and value not in self.choices:
            raise ValidationError(f'Valor deve ser um dos seguintes: {", ".join(str(c) for c in self.choices)}')


# ─────────────────────────────────────────
# Funções de conveniência
# ─────────────────────────────────────────

def serialize_json(obj: Any, **kwargs) -> str:
    """Serializa para JSON"""
    return JSONSerializer(**kwargs).serialize(obj)


def deserialize_json(data: str) -> Any:
    """Desserializa JSON"""
    return json.loads(data)


def to_dict(obj: Any) -> Dict:
    """Converte objeto para dicionário"""
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, 'to_dict'):
        return obj.to_dict()
    if hasattr(obj, '__dict__'):
        return {k: v for k, v in obj.__dict__.items() if not k.startswith('_')}
    if isinstance(obj, (list, tuple)):
        return {'_type': 'list', 'data': list(obj)}
    return {'value': str(obj)}


def to_json(obj: Any, **kwargs) -> str:
    """Serializa objeto para JSON"""
    return JSONSerializer(**kwargs).serialize(obj)


def from_json(data: str) -> Any:
    """Desserializa JSON"""
    return json.loads(data)


def validate_email(email: str) -> bool:
    """Valida email"""
    return bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email))


def validate_cpf(cpf: str) -> bool:
    """Valida CPF"""
    cpf = re.sub(r'\D', '', cpf)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    for i in range(9, 11):
        total = sum(int(cpf[j]) * ((i + 1) - j) for j in range(i))
        digit = ((total * 10) % 11) % 10
        if int(cpf[i]) != digit:
            return False
    return True


def validate_cnpj(cnpj: str) -> bool:
    """Valida CNPJ"""
    cnpj = re.sub(r'\D', '', cnpj)
    if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
        return False
    weights1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    weights2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    d1 = (11 - (sum(int(cnpj[i]) * weights1[i] for i in range(12)) % 11)) % 11
    d1 = 0 if d1 >= 10 else d1
    d2 = (11 - (sum(int(cnpj[i]) * weights2[i] for i in range(13)) % 11)) % 11
    d2 = 0 if d2 >= 10 else d2
    return int(cnpj[12]) == d1 and int(cnpj[13]) == d2


def validate_phone(phone: str) -> bool:
    """Valida telefone brasileiro"""
    phone = re.sub(r'\D', '', phone)
    return len(phone) in [10, 11]


def mask_sensitive(value: str, visible: int = 4) -> str:
    """Mascara dados sensíveis"""
    if not value or len(value) <= visible:
        return '*' * len(value)
    return value[:visible] + '*' * (len(value) - visible)
