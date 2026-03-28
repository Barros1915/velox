"""
velox.assets — Recursos estáticos do Velox Framework

Uso:
    from velox.assets import LOGO_SVG, LOGO_PNG, ICON_SVG, logo_path

    # Caminho absoluto para o logo principal
    path = logo_path('velox-logo.svg')

    # Conteúdo SVG inline (para embutir em HTML)
    svg_content = LOGO_SVG
"""

from pathlib import Path

_ASSETS_DIR = Path(__file__).parent

# Caminhos absolutos
LOGO_SVG            = _ASSETS_DIR / 'velox-logo.svg'
LOGO_PNG            = _ASSETS_DIR / 'velox-logo.png'
ICON_SVG            = _ASSETS_DIR / 'velox-icon.svg'
LOGO_HORIZONTAL_SVG = _ASSETS_DIR / 'velox-logo-horizontal.svg'
LOGO_DARK_SVG       = _ASSETS_DIR / 'velox-logo-dark.svg'


def logo_path(filename: str = 'velox-logo.svg') -> Path:
    """Retorna o caminho absoluto para um asset pelo nome do arquivo."""
    return _ASSETS_DIR / filename


def logo_svg(variant: str = 'default') -> str:
    """
    Retorna o conteúdo SVG do logo para embutir diretamente em HTML.

    Variantes:
        'default'    -> velox-logo.svg      (círculo completo, fundo escuro)
        'icon'       -> velox-icon.svg      (versão 64x64 compacta)
        'horizontal' -> velox-logo-horizontal.svg (logo + texto)
        'dark'       -> velox-logo-dark.svg (para fundo claro)

    Uso no template:
        {{ logo_svg }}  (com filtro |safe)

    Uso no Python:
        from velox.assets import logo_svg
        html = f'<div>{logo_svg("icon")}</div>'
    """
    files = {
        'default':    LOGO_SVG,
        'icon':       ICON_SVG,
        'horizontal': LOGO_HORIZONTAL_SVG,
        'dark':       LOGO_DARK_SVG,
    }
    path = files.get(variant, LOGO_SVG)
    try:
        return path.read_text(encoding='utf-8')
    except FileNotFoundError:
        return ''


def list_assets() -> list:
    """Lista todos os arquivos de assets disponíveis."""
    return [f.name for f in _ASSETS_DIR.iterdir()
            if f.is_file() and not f.name.startswith('_')]
