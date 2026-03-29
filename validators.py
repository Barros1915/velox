"""
Sistema de Validação de Dados - Velox
Similar ao django.core.validators
"""

import re
from typing import Any, List, Optional


class ValidationError(Exception):
    """Exceção de validação"""
    def __init__(self, message, code=None):
        self.message = message
        self.code = code
        super().__init__(message)


class Validator:
    """Validador base"""
    def __call__(self, value):
        return self.validate(value)

    def validate(self, value):
        raise NotImplementedError


class RegexValidator(Validator):
    """Valida usando regex"""
    def __init__(self, regex=None, message=None, code=None):
        self.regex = re.compile(regex or r'.+')
        self.message = message or "Valor inválido"
        self.code = code or 'invalid'

    def validate(self, value):
        if not self.regex.match(str(value)):
            raise ValidationError(self.message, self.code)


class EmailValidator(Validator):
    """Valida email"""
    regex = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )
    message = "Email inválido"
    code = 'invalid_email'

    def validate(self, value):
        if not self.regex.match(str(value)):
            raise ValidationError(self.message, self.code)


class URLValidator(Validator):
    """Valida URL"""
    regex = re.compile(
        r'^https?://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
    )
    message = "URL inválida"
    code = 'invalid_url'

    def validate(self, value):
        if not self.regex.match(str(value)):
            raise ValidationError(self.message, self.code)


class MinLengthValidator(Validator):
    """Valida comprimento mínimo"""
    def __init__(self, min_length, message=None):
        self.min_length = min_length
        self.message = message or f"Mínimo de {min_length} caracteres"

    def validate(self, value):
        if len(str(value)) < self.min_length:
            raise ValidationError(self.message, 'min_length')


class MaxLengthValidator(Validator):
    """Valida comprimento máximo"""
    def __init__(self, max_length, message=None):
        self.max_length = max_length
        self.message = message or f"Máximo de {max_length} caracteres"

    def validate(self, value):
        if len(str(value)) > self.max_length:
            raise ValidationError(self.message, 'max_length')


class MinValueValidator(Validator):
    """Valida valor mínimo"""
    def __init__(self, min_value, message=None):
        self.min_value = min_value
        self.message = message or f"Valor mínimo é {min_value}"

    def validate(self, value):
        if value < self.min_value:
            raise ValidationError(self.message, 'min_value')


class MaxValueValidator(Validator):
    """Valida valor máximo"""
    def __init__(self, max_value, message=None):
        self.max_value = max_value
        self.message = message or f"Valor máximo é {max_value}"

    def validate(self, value):
        if value > self.max_value:
            raise ValidationError(self.message, 'max_value')


class ChoicesValidator(Validator):
    """Valida opções"""
    def __init__(self, choices, message=None):
        self.choices = choices
        self.message = message or "Opção inválida"

    def validate(self, value):
        if value not in self.choices:
            raise ValidationError(self.message, 'invalid_choice')


# Validadores prontos
validate_email = EmailValidator()
validate_url = URLValidator()


def validate(value, validators: List[Validator]) -> List[ValidationError]:
    """Executa múltiplos validadores"""
    errors = []
    for validator in validators:
        try:
            validator(value)
        except ValidationError as e:
            errors.append(e)
    return errors


def clean_email(email: str) -> str:
    """Valida e limpa email"""
    validate_email(email)
    return email.lower().strip()


def clean_url(url: str) -> str:
    """Valida e limpa URL"""
    validate_url(url)
    return url.strip()
