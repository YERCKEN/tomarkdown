"""Lee archivos copiados en el portapapeles del sistema operativo.

pywebview no expone ninguna API de portapapeles (verificado contra
`webview/window.py` de la librería instalada): el truco de `pywebviewFullPath`
que resuelve rutas reales en el drag & drop es específico de ese evento y no
aplica acá. Para "pegar" archivos hay que hablar con el portapapeles nativo
directamente, por eso este módulo aísla esa parte específica de cada
plataforma.

Los imports de `AppKit`/`win32clipboard` van adentro de cada función y no al
tope del módulo: son dependencias condicionadas por plataforma
(`pyproject.toml`), así que importar este módulo tiene que funcionar en
cualquier sistema operativo aunque la plataforma actual no tenga instalada la
librería nativa correspondiente.
"""

from __future__ import annotations

import logging
import sys

logger = logging.getLogger(__name__)


def files_in_clipboard() -> list[str]:
    """Rutas absolutas de los archivos copiados en el portapapeles del SO.

    Lista vacía si no hay archivos copiados, si la plataforma no está
    soportada, o si la lectura nativa falla por cualquier motivo.
    """
    if sys.platform == "darwin":
        return _files_from_macos()
    if sys.platform == "win32":
        return _files_from_windows()
    return []


def has_files_in_clipboard() -> bool:
    """Peek barato: hay archivos pegables, sin extraer las rutas todavía.

    Pensado para sondear seguido (p. ej. cada pocos cientos de ms desde el
    front) sin pagar el costo de resolver rutas en cada chequeo.
    """
    if sys.platform == "darwin":
        return _has_files_macos()
    if sys.platform == "win32":
        return _has_files_windows()
    return False


def _files_from_macos() -> list[str]:
    try:
        from AppKit import NSURL, NSPasteboard, NSPasteboardURLReadingFileURLsOnlyKey

        pasteboard = NSPasteboard.generalPasteboard()
        urls = pasteboard.readObjectsForClasses_options_(
            [NSURL], {NSPasteboardURLReadingFileURLsOnlyKey: True}
        )
        return [str(url.path()) for url in urls or [] if url.path()]
    except Exception:
        logger.warning("⚠️ No se pudo leer el portapapeles de macOS", exc_info=True)
        return []


def _has_files_macos() -> bool:
    try:
        from AppKit import NSPasteboard, NSPasteboardTypeFileURL

        pasteboard = NSPasteboard.generalPasteboard()
        types = pasteboard.types() or []
        return bool(NSPasteboardTypeFileURL in types or "NSFilenamesPboardType" in types)
    except Exception:
        logger.warning("⚠️ No se pudo consultar el portapapeles de macOS", exc_info=True)
        return False


def _files_from_windows() -> list[str]:
    try:
        import win32clipboard

        win32clipboard.OpenClipboard()
        try:
            if not win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_HDROP):
                return []
            return list(win32clipboard.GetClipboardData(win32clipboard.CF_HDROP))
        finally:
            win32clipboard.CloseClipboard()
    except Exception:
        logger.warning("⚠️ No se pudo leer el portapapeles de Windows", exc_info=True)
        return []


def _has_files_windows() -> bool:
    try:
        import win32clipboard

        return bool(win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_HDROP))
    except Exception:
        logger.warning("⚠️ No se pudo consultar el portapapeles de Windows", exc_info=True)
        return False
