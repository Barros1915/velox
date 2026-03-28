# Changelog

## [1.0.0] - 2026-03-28

### Lançamento inicial

- WSGI threading e ASGI uvicorn no mesmo app
- ORM com SQLite e PostgreSQL
- Sistema de autenticação: sessions, OAuth (Google, GitHub, Facebook, Discord), RBAC
- Template engine com escape XSS automático, sem eval()
- Painel admin dark theme com CRUD completo
- Cache: memory, SQLite, Redis
- CSRF protection com middleware funcional
- WebSocket nativo (modo ASGI)
- CLI: `velox init`, `velox startapp`, `velox run`, `velox routes`
- Zero dependências obrigatórias
