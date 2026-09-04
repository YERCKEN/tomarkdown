"""Configuracion central de ToMarkdown.

Este modulo es la unica fuente de verdad para el nombre, la version, el tamano
de la ventana y la lista de extensiones soportadas. Lo leen `main.py`, `api.py`,
`build.spec` y el propio `pyproject.toml` (via hatchling).
"""

from __future__ import annotations

import sys
from pathlib import Path

__version__ = "0.2.0"

APP_NAME = "ToMarkdown"
APP_ID = "com.yercken.tomarkdown"

WINDOW_WIDTH = 960
WINDOW_HEIGHT = 700
MIN_SIZE = (720, 560)
BACKGROUND = "#0B0C0E"

#: Extensiones que markitdown resuelve con los extras que instalamos
#: (pdf, docx, pptx, xlsx, xls, outlook) mas los formatos de texto que trae
#: en el nucleo. El valor es la etiqueta que ve el usuario.
SUPPORTED_EXTENSIONS: dict[str, str] = {
    "pdf": "PDF",
    "docx": "Word",
    "pptx": "PowerPoint",
    "xlsx": "Excel",
    "xls": "Excel 97-2003",
    "msg": "Outlook",
    "epub": "EPUB",
    "html": "HTML",
    "htm": "HTML",
    "csv": "CSV",
    "json": "JSON",
    "xml": "XML",
    "txt": "Texto",
    "md": "Markdown",
    "markdown": "Markdown",
    "ipynb": "Notebook",
    "zip": "ZIP",
}


#: Modulos que los converters de markitdown importan de forma diferida (dentro
#: de try/except). El analisis estatico de PyInstaller no los ve, por eso van
#: como `hiddenimports` en `build.spec`, y `--self-check` verifica que el bundle
#: los incluye. Fuente unica: la lee `build.spec` y `app/main.py`.
CONVERTER_IMPORTS: tuple[str, ...] = (
    "mammoth",
    "olefile",
    "openpyxl",
    "pandas",
    "pdfminer",
    "pdfminer.high_level",
    "pdfplumber",
    "pptx",
    "xlrd",
)


def supported_extensions() -> list[str]:
    """Devuelve las extensiones soportadas, ordenadas y sin duplicados."""
    return sorted(SUPPORTED_EXTENSIONS)


def file_dialog_filter() -> tuple[str, ...]:
    """Construye el filtro de `create_file_dialog` con las extensiones soportadas."""
    patterns = ";".join(f"*.{ext}" for ext in supported_extensions())
    return (f"Documentos soportados ({patterns})", "Todos los archivos (*.*)")


def base_path() -> Path:
    """Raiz desde la que se resuelven los recursos.

    Bajo PyInstaller (onefile y onedir) los datos viven en `sys._MEIPASS`.
    En desarrollo, en la raiz del repo.
    """
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent


def resource_path(relative: str) -> str:
    """Ruta absoluta a un recurso empaquetado, por ejemplo `web/index.html`."""
    return str(base_path() / relative)
