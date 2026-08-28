"""Envoltorio de markitdown.

Aísla el resto de la app de la librería: expone una sola función `convert` que
devuelve el Markdown o levanta `ConversionError` con un mensaje legible.
"""

from __future__ import annotations

import logging
from pathlib import Path

from markitdown import (
    FileConversionException,
    MarkItDown,
    MissingDependencyException,
    UnsupportedFormatException,
)

logger = logging.getLogger(__name__)

#: Instancia única. Crear un `MarkItDown` por archivo reconstruye el registro de
#: converters y el modelo de magika en cada llamada.
_markitdown: MarkItDown | None = None


class ConversionError(Exception):
    """Fallo de conversión con un mensaje ya listo para mostrar al usuario."""


def _engine() -> MarkItDown:
    """Devuelve la instancia compartida de MarkItDown, creándola la primera vez."""
    global _markitdown
    if _markitdown is None:
        logger.info("🚀 Inicializando MarkItDown (plugins deshabilitados)")
        _markitdown = MarkItDown(enable_plugins=False)
    return _markitdown


def convert(path: str) -> str:
    """Convierte un archivo local a Markdown.

    Usa `convert_local()` en vez de `convert()`: este último es permisivo y
    también acepta URIs remotos, y acá solo se manejan archivos en disco.

    :param path: Ruta absoluta del archivo a convertir.
    :returns: El Markdown resultante.
    :raises ConversionError: Con un mensaje en español apto para la interfaz.
    """
    target = Path(path)
    try:
        result = _engine().convert_local(target)
    except FileNotFoundError:
        raise ConversionError("El archivo ya no está en esa ruta") from None
    except PermissionError:
        raise ConversionError("No hay permiso para leer el archivo") from None
    except IsADirectoryError:
        raise ConversionError("Eso es una carpeta, no un archivo") from None
    except UnsupportedFormatException:
        raise ConversionError("El convertidor no reconoce este formato") from None
    except MissingDependencyException:
        ext = target.suffix.lstrip(".").lower() or "este tipo"
        raise ConversionError(f"Falta el componente para leer archivos {ext}") from None
    except FileConversionException:
        raise ConversionError(
            "No se pudo leer el archivo, puede estar dañado o protegido con contraseña"
        ) from None
    except Exception as exc:  # noqa: BLE001 - la cola no puede caerse por un archivo
        logger.exception("🔴 Error inesperado convirtiendo %s", target.name)
        raise ConversionError(
            f"No se pudo convertir el archivo ({type(exc).__name__})"
        ) from None

    # `markdown` es el atributo real desde markitdown 0.1.x; `text_content` quedó
    # como alias suave. Se leen los dos por si cambia el orden de deprecación.
    markdown = getattr(result, "markdown", None)
    if markdown is None:
        markdown = getattr(result, "text_content", None)

    if not markdown:
        raise ConversionError("El archivo se leyó pero no tiene texto que convertir")

    return markdown
