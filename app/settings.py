"""Preferencias mínimas que sobreviven al cierre de la app.

Un único archivo JSON (`settings.json`) en el directorio de configuración del
sistema operativo. Hoy guarda un solo valor: la última carpeta de guardado, para
que el diálogo no arranque siempre de cero.

Es la primera grieta deliberada en «sin configuración persistente» (ver el
README). El alcance se mantiene chico a propósito: un archivo, valores planos, y
toda lectura tolera que el archivo no exista o esté corrupto.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

from app.config import APP_NAME

logger = logging.getLogger(__name__)

_LAST_SAVE_DIR = "last_save_dir"


def _config_dir() -> Path:
    """Directorio de configuración del SO para ToMarkdown.

    Se decide por `sys.platform` (no `os.name`): `pathlib` lee `os.name` al
    construir un `Path`, así que un test no puede fingir Windows tocándolo.
    """
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or str(Path.home())
        return Path(base) / APP_NAME
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / APP_NAME.lower()


def _settings_file() -> Path:
    return _config_dir() / "settings.json"


def load() -> dict:
    """Lee el archivo de preferencias. `{}` si no existe o no se puede leer."""
    try:
        data = json.loads(_settings_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save(data: dict) -> None:
    """Escribe las preferencias. Best-effort: un fallo se loguea y no propaga.

    Guardar un `.md` no puede fallar porque no se pudo escribir la preferencia.
    """
    try:
        path = _settings_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as exc:
        logger.warning("⚠️ No se pudo guardar la configuración: %s", exc)


def last_save_dir() -> str | None:
    """La última carpeta usada para guardar, si todavía existe."""
    value = load().get(_LAST_SAVE_DIR)
    if isinstance(value, str) and os.path.isdir(value):
        return value
    return None


def remember_save_dir(path: str) -> None:
    """Guarda `path` como la última carpeta de guardado."""
    if not path:
        return
    data = load()
    data[_LAST_SAVE_DIR] = path
    save(data)
