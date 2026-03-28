"""
Velox - Fast Python Web Framework
"""

# ── Core (obrigatorio) ────────────────────────────────────────────
from .core import Velox, create_app, Router, Blueprint
from .request import Request
from .response import Response
from .template import TemplateEngine

# ── Modulos opcionais (nao quebram o framework se falharem) ───────
try:
    from .template import render_template
except Exception:
    pass

try:
    from .session import Session, SessionManager
except Exception:
    pass

try:
    from .middleware import (
        Middleware, CORSMiddleware, LoggingMiddleware,
        AuthMiddleware, RateLimitMiddleware, cors, login_required,
    )
except Exception:
    pass

try:
    from .database import Database, Model, QueryBuilder, create_database
except Exception:
    pass

try:
    from .config import Config, get_config, DevelopmentConfig, ProductionConfig, TestingConfig
except Exception:
    pass

try:
    from .log import Logger, get_logger, RequestLogger
except Exception:
    pass

try:
    from .exceptions import (
        VeloxException, HTTPException,
        NotFoundError, ForbiddenError, UnauthorizedError,
        BadRequestError, ValidationError, DatabaseError,
        TemplateError, ConfigurationError,
    )
except Exception:
    pass

try:
    from .cache import Cache, cache, get_cache, set_cache, delete_cache, clear_cache
except Exception:
    pass

try:
    from .mail import EmailMessage, send_mail, send_html_mail
except Exception:
    pass

try:
    from .paginator import Paginator, Page, paginate
except Exception:
    pass

try:
    from .serializers import Serializer, JSONSerializer, to_json, from_json, to_dict
except Exception:
    pass

try:
    from .validators import (
        Validator, RegexValidator, EmailValidator, URLValidator,
        MinLengthValidator, MaxLengthValidator, MinValueValidator,
        MaxValueValidator, validate_email, validate_url, validate,
    )
except Exception:
    pass

try:
    from .files import File, UploadedFile, FileField, save_upload, delete_file, read_file, write_file
except Exception:
    pass

try:
    from .signals import Signal, receiver, emit, create_signal
except Exception:
    pass

try:
    from .auth import (
        User, AuthBackend, login, logout,
        get_current_user, create_user, authenticate,
    )
except Exception:
    pass

try:
    from .forms import (
        Form, CharField, EmailField, IntegerField,
        BooleanField, ContactForm, LoginForm, RegisterForm,
    )
except Exception:
    pass

try:
    from .admin import AdminSite, ModelAdmin, site
    from .admin import register as register_model
except Exception:
    pass

try:
    from .migrations import Migration, MigrationManager, migrate, makemigration, rollback
except Exception:
    pass

try:
    from .websocket import (
        WebSocketManager, WebSocketHandler, WebSocketMessage,
        ws_route, get_manager,
    )
except Exception:
    pass

# ── Testing (testes automatizados) ───────────────────────────────
from .testing import (
    VeloxTestClient, TestRequest, TestResponse, TestCase,
)

# ── Swagger/OpenAPI (documentação automática) ──────────────────
from .swagger import (
    SwaggerRouter, add_swagger_docs, api_doc, APIDoc,
)

__version__ = "1.0.0"
