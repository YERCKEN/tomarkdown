"""Hilo de conversión serial y emisión de eventos hacia el front.

La conversión corre en un `threading.Thread` porque hacerlo en el hilo principal
congelaría la ventana entera. Se procesa un archivo a la vez: markitdown puede
ser pesado en memoria con PDFs grandes, y la cola tiene que avanzar en orden.
"""

from __future__ import annotations

import logging
import threading
from typing import Callable

from app.converter import ConversionError, convert

logger = logging.getLogger(__name__)

#: Firma del emisor de eventos que inyecta `Api`: (nombre, payload) -> None
Emitter = Callable[[str, dict], None]


class QueueRunner:
    """Recorre la cola en segundo plano y reporta el avance por eventos."""

    def __init__(
        self,
        entries: dict[str, dict],
        markdown: dict[str, str],
        emit: Emitter,
    ) -> None:
        """
        :param entries: Store de `FileEntry` indexado por id, compartido con `Api`.
        :param markdown: Store del Markdown convertido, indexado por id.
        :param emit: Función que empuja un evento al front.
        """
        self._entries = entries
        self._markdown = markdown
        self._emit = emit
        self._thread: threading.Thread | None = None
        self._cancel = threading.Event()

    @property
    def is_running(self) -> bool:
        """Indica si hay una cola en curso."""
        return self._thread is not None and self._thread.is_alive()

    def start(self, file_ids: list[str]) -> None:
        """Arranca la conversión y retorna de inmediato.

        :param file_ids: Ids a procesar, en el orden en que se mostrarán.
        """
        if self.is_running:
            logger.warning("⚠️ Se pidió arrancar la cola con otra ya en curso")
            return

        pending = [
            fid
            for fid in file_ids
            if fid in self._entries and self._entries[fid]["status"] != "done"
        ]
        if not pending:
            return

        self._cancel.clear()
        self._thread = threading.Thread(
            target=self._run, args=(pending,), name="tomarkdown-queue", daemon=True
        )
        self._thread.start()

    def cancel(self) -> None:
        """Marca la bandera de cancelación.

        El archivo en curso termina; los pendientes pasan a `cancelled`.
        """
        if self.is_running:
            logger.info("⚠️ Cancelación solicitada, la cola se detiene tras el archivo actual")
            self._cancel.set()

    def _run(self, file_ids: list[str]) -> None:
        """Bucle serial de conversión. Corre en el hilo secundario."""
        total = len(file_ids)
        done = failed = cancelled = 0
        self._emit("queue:start", {"total": total})

        for index, file_id in enumerate(file_ids):
            entry = self._entries.get(file_id)
            if entry is None:
                continue

            if self._cancel.is_set():
                cancelled += len(file_ids) - index
                for remaining in file_ids[index:]:
                    if remaining in self._entries:
                        self._entries[remaining]["status"] = "cancelled"
                        self._entries[remaining]["error"] = None
                break

            entry["status"] = "converting"
            entry["error"] = None
            self._emit("item:start", {"id": file_id})

            try:
                markdown = convert(entry["path"])
            except ConversionError as exc:
                failed += 1
                entry["status"] = "error"
                entry["error"] = str(exc)
                self._markdown.pop(file_id, None)
                logger.warning("⚠️ %s: %s", entry["name"], exc)
                self._emit("item:error", {"id": file_id, "error": str(exc)})
            else:
                done += 1
                entry["status"] = "done"
                entry["error"] = None
                self._markdown[file_id] = markdown
                logger.info("✅ %s convertido (%d caracteres)", entry["name"], len(markdown))
                self._emit("item:done", {"id": file_id, "chars": len(markdown)})

            # `completed` acá es "procesados" (convertidos + fallidos), que es lo
            # que hace avanzar la barra general hasta el final.
            self._emit("queue:progress", {"completed": done + failed, "total": total})

        self._emit(
            "queue:done",
            {"completed": done, "failed": failed, "cancelled": cancelled},
        )
