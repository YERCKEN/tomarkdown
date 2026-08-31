"""Clase `Api` expuesta al JavaScript a través del puente `js_api` de pywebview.

Desde el front cada método se llama como `await pywebview.api.nombre_metodo(...)`.
No hay HTTP de por medio: pywebview serializa la llamada y la resuelve como promesa.

El Markdown convertido vive acá, en memoria, indexado por id. **No viaja al front**:
un PDF grande convertido puede ser de varios MB de texto y el front no lo necesita
mientras no haya preview.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import threading
import uuid
from pathlib import Path

import webview

from app.config import (
    APP_NAME,
    SUPPORTED_EXTENSIONS,
    __version__,
    file_dialog_filter,
    supported_extensions,
)
from app.queue_runner import QueueRunner

logger = logging.getLogger(__name__)


def _extension(path: str) -> str:
    """Extensión en minúsculas y sin punto. Cadena vacía si no tiene."""
    return Path(path).suffix.lstrip(".").lower()


def _first_path(result) -> str | None:
    """Normaliza lo que devuelve `create_file_dialog` a una sola ruta.

    Según la plataforma y el tipo de diálogo puede llegar `None`, una cadena o
    una secuencia de cadenas.
    """
    if not result:
        return None
    if isinstance(result, str):
        return result
    return str(result[0])


def _all_paths(result) -> list[str]:
    """Normaliza lo que devuelve `create_file_dialog` a una lista de rutas."""
    if not result:
        return []
    if isinstance(result, str):
        return [result]
    return [str(item) for item in result]


class Api:
    """Superficie que el front puede invocar."""

    def __init__(self) -> None:
        self._window: webview.Window | None = None
        self._entries: dict[str, dict] = {}
        self._markdown: dict[str, str] = {}
        self._known_paths: set[str] = set()
        self._lock = threading.Lock()
        self._runner = QueueRunner(self._entries, self._markdown, self._emit)

    # ------------------------------------------------------------------ interno

    def attach(self, window: webview.Window) -> None:
        """Guarda la ventana para poder emitir eventos y abrir diálogos nativos."""
        self._window = window

    def _emit(self, name: str, payload: dict) -> None:
        """Empuja un evento al front.

        Usa `run_js` en vez de `evaluate_js`: no devuelve valor ni usa callback,
        que es justo lo que hace falta para llamarlo desde el hilo de la cola.
        `json.dumps` con escapado ASCII resuelve las comillas y los acentos de los
        nombres de archivo.
        """
        window = self._window
        if window is None:
            return

        message = json.dumps({"event": name, **payload})
        try:
            window.run_js(f"window.toMarkdown.onEvent({message})")
        except Exception:  # noqa: BLE001 - un fallo del puente no puede tumbar la cola
            logger.exception("🔴 No se pudo emitir el evento %s", name)

    def _make_entry(self, path: str) -> dict:
        """Construye un `FileEntry` normalizado a partir de una ruta absoluta."""
        try:
            size = os.path.getsize(path)
        except OSError:
            size = 0

        return {
            "id": str(uuid.uuid4()),
            "name": os.path.basename(path),
            "path": path,
            "ext": _extension(path),
            "size_bytes": size,
            "status": "pending",
            "error": None,
            "saved_to": None,
        }

    def _accept(self, paths: list[str]) -> tuple[list[dict], list[str]]:
        """Filtra rutas y crea las entradas aceptadas.

        :returns: (entradas aceptadas, nombres rechazados por formato)
        """
        accepted: list[dict] = []
        rejected: list[str] = []

        with self._lock:
            for raw in paths:
                if not raw:
                    continue

                path = os.path.realpath(os.path.expanduser(str(raw)))
                if not os.path.isfile(path):
                    continue
                if path in self._known_paths:
                    continue
                if _extension(path) not in SUPPORTED_EXTENSIONS:
                    rejected.append(os.path.basename(path))
                    continue

                entry = self._make_entry(path)
                self._entries[entry["id"]] = entry
                self._known_paths.add(path)
                accepted.append(entry)

        return accepted, rejected

    def on_native_drop(self, event: dict) -> None:
        """Handler del drop nativo de pywebview.

        pywebview inyecta la ruta absoluta real en cada archivo soltado como
        `pywebviewFullPath`; el objeto `File` del DOM no la expone por seguridad
        del navegador. Verificado contra pywebview 6.2.1 (`webview/util.py`).
        """
        transfer = event.get("dataTransfer") or {}
        files = transfer.get("files") or []
        paths = [f.get("pywebviewFullPath") for f in files if f.get("pywebviewFullPath")]

        if not paths:
            if files:
                logger.warning("⚠️ El drop no trajo rutas absolutas, %d archivos ignorados", len(files))
                self._emit("files:rejected", {"names": [f.get("name", "?") for f in files]})
            return

        accepted, rejected = self._accept(paths)
        if accepted:
            self._emit("files:added", {"files": accepted})
        if rejected:
            self._emit("files:rejected", {"names": rejected})

    # --------------------------------------------------- selección de archivos

    def get_app_info(self) -> dict:
        """Nombre y versión de la app, para la pantalla «Qué hace ToMarkdown»."""
        return {"name": APP_NAME, "version": __version__}

    def get_supported_extensions(self) -> list[str]:
        """Lista viva de extensiones soportadas, para el filtro visual del front."""
        return supported_extensions()

    def pick_files(self) -> list[dict]:
        """Abre el diálogo nativo con selección múltiple.

        :returns: Las entradas aceptadas, o lista vacía si el usuario canceló.
        """
        window = self._window
        if window is None:
            return []

        result = window.create_file_dialog(
            webview.FileDialog.OPEN,
            allow_multiple=True,
            file_types=file_dialog_filter(),
        )
        accepted, rejected = self._accept(_all_paths(result))
        if rejected:
            self._emit("files:rejected", {"names": rejected})
        return accepted

    def add_paths(self, paths: list[str]) -> list[dict]:
        """Agrega rutas absolutas, descartando duplicados y formatos no soportados.

        :returns: Solo las entradas aceptadas.
        """
        accepted, rejected = self._accept(list(paths or []))
        if rejected:
            self._emit("files:rejected", {"names": rejected})
        return accepted

    def clear(self) -> list[str]:
        """Vacía la cola. Cancela primero si hay una conversión en curso.

        :returns: Lista vacía, para que el front reinicie su estado.
        """
        self._runner.cancel()
        with self._lock:
            self._entries.clear()
            self._markdown.clear()
            self._known_paths.clear()
        return []

    # -------------------------------------------------------------- conversión

    def start_conversion(self, file_ids: list[str]) -> None:
        """Arranca el hilo de conversión. Retorna de inmediato, no bloquea."""
        self._runner.start(list(file_ids or []))

    def cancel_conversion(self) -> None:
        """Marca la cancelación: el archivo en curso termina, el resto se cancela."""
        self._runner.cancel()

    # ---------------------------------------------------------------- guardado

    def save_one(self, file_id: str) -> str | None:
        """Abre «guardar como» para un archivo convertido.

        :returns: La ruta escrita, o `None` si el usuario canceló.
        """
        window = self._window
        entry = self._entries.get(file_id)
        if window is None or entry is None or entry["status"] != "done":
            return None

        markdown = self._markdown.get(file_id)
        if markdown is None:
            return None

        result = window.create_file_dialog(
            webview.FileDialog.SAVE,
            save_filename=f"{Path(entry['name']).stem}.md",
            file_types=("Markdown (*.md)", "Todos los archivos (*.*)"),
        )
        target = _first_path(result)
        if not target:
            return None

        try:
            Path(target).write_text(markdown, encoding="utf-8")
        except OSError:
            logger.exception("🔴 No se pudo escribir %s", target)
            self._emit("save:error", {"id": file_id, "error": "No se pudo escribir el archivo"})
            return None

        entry["saved_to"] = target
        logger.info("✅ Guardado %s", target)
        return target

    def save_all(self, file_ids: list[str]) -> dict:
        """Pide una carpeta y escribe ahí todos los archivos convertidos.

        Si ya existe un `.md` con ese nombre agrega sufijo numérico
        (`informe.md`, `informe-2.md`), así guardar dos veces no pisa nada.

        :returns: `{"folder": str, "written": int, "failed": list[str], "saved": dict[str, str]}`.
            `saved` mapea id a la ruta escrita: el nombre final puede llevar
            sufijo numérico, así que el front no puede deducirlo desde la carpeta.
        """
        window = self._window
        empty = {"folder": "", "written": 0, "failed": [], "saved": {}}
        if window is None:
            return empty

        ids = list(file_ids or []) or list(self._entries)
        ready = [
            fid
            for fid in ids
            if fid in self._entries
            and self._entries[fid]["status"] == "done"
            and fid in self._markdown
        ]
        if not ready:
            return empty

        folder = _first_path(window.create_file_dialog(webview.FileDialog.FOLDER))
        if not folder:
            return empty

        destination = Path(folder)
        written = 0
        failed: list[str] = []
        saved: dict[str, str] = {}

        for file_id in ready:
            entry = self._entries[file_id]
            target = _unique_md_path(destination, Path(entry["name"]).stem)
            try:
                target.write_text(self._markdown[file_id], encoding="utf-8")
            except OSError:
                logger.exception("🔴 No se pudo escribir %s", target)
                failed.append(entry["name"])
                continue

            entry["saved_to"] = str(target)
            saved[file_id] = str(target)
            written += 1

        logger.info("✅ Guardados %d archivos en %s", written, destination)
        return {
            "folder": str(destination),
            "written": written,
            "failed": failed,
            "saved": saved,
        }

    def reveal(self, file_id: str) -> bool:
        """Muestra en el explorador del sistema el `.md` ya guardado.

        La ruta se lee de la entrada del lado Python, que guarda la ruta exacta
        tanto en `save_one` como en `save_all`. El front no la necesita.

        :returns: True si se lanzó el explorador.
        """
        entry = self._entries.get(file_id)
        if entry is None:
            return False

        target = entry.get("saved_to")
        if not target or not os.path.isfile(target):
            self._emit(
                "save:error",
                {"id": file_id, "error": "El archivo guardado ya no está en esa ruta"},
            )
            return False

        # Lista de argumentos y nunca `shell=True`: los nombres vienen del disco
        # del usuario y traen espacios, comillas y acentos.
        if sys.platform == "darwin":
            command = ["open", "-R", target]
        elif os.name == "nt":
            # `explorer` devuelve código 1 incluso cuando abre bien, por eso el
            # resultado no se chequea en ninguna plataforma.
            command = ["explorer", f"/select,{os.path.normpath(target)}"]
        else:
            command = ["xdg-open", os.path.dirname(target)]

        try:
            subprocess.run(command, check=False)
        except OSError:
            logger.exception("🔴 No se pudo abrir el explorador en %s", target)
            self._emit(
                "save:error",
                {"id": file_id, "error": "No se pudo abrir el explorador de archivos"},
            )
            return False

        logger.info("🗄️ Revelado %s", target)
        return True


def _unique_md_path(folder: Path, stem: str) -> Path:
    """Devuelve una ruta `.md` libre dentro de `folder`, con sufijo numérico si hace falta."""
    candidate = folder / f"{stem}.md"
    counter = 2
    while candidate.exists():
        candidate = folder / f"{stem}-{counter}.md"
        counter += 1
    return candidate
