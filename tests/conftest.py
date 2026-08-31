"""Fixtures compartidos por la suíte.

Reúne lo que los scripts de humo tenían suelto: el armador de PDF mínimo, las
entradas de cola sintéticas y el arranque instrumentado de `QueueRunner`.
"""

from __future__ import annotations

import threading
from typing import Callable

import pytest

from app.queue_runner import QueueRunner
from scripts.gen_selfcheck_samples import minimal_pdf


@pytest.fixture
def make_pdf() -> Callable[[str], bytes]:
    """Devuelve la función que arma un PDF válido mínimo con una línea de texto.

    Es `minimal_pdf` de `scripts/gen_selfcheck_samples.py`: la misma que usa
    `--self-check`, para no mantener dos armadores de PDF.
    """
    return minimal_pdf


@pytest.fixture
def make_entries() -> Callable[[int], dict[str, dict]]:
    """Devuelve un generador de entradas de cola sintéticas, ya normalizadas."""

    def _build(count: int) -> dict[str, dict]:
        return {
            f"id-{i}": {
                "id": f"id-{i}",
                "name": f"archivo-{i}.pdf",
                "path": f"/tmp/archivo-{i}.pdf",
                "ext": "pdf",
                "size_bytes": 100,
                "status": "pending",
                "error": None,
                "saved_to": None,
            }
            for i in range(count)
        }

    return _build


@pytest.fixture
def run_queue(monkeypatch):
    """Arranca `QueueRunner` con un `convert` inyectado y recoge sus eventos.

    Parchea `app.queue_runner.convert` con el falso que se le pase. `during` corre
    entre el `start` y el `join`: sirve para cancelar en un punto exacto sin
    depender de cuánto tarde un archivo real.

    :returns: función `(entries, fake_convert, *, ids=None, during=None)`
        que devuelve `(runner, events, markdown)`.
    """

    def _run(entries, fake_convert, *, ids=None, during=None):
        events: list[dict] = []
        markdown: dict[str, str] = {}
        lock = threading.Lock()

        def emit(name: str, payload: dict) -> None:
            with lock:
                events.append({"event": name, **payload})

        monkeypatch.setattr("app.queue_runner.convert", fake_convert)

        runner = QueueRunner(entries, markdown, emit)
        runner.start(list(ids if ids is not None else entries))
        if during is not None:
            during(runner)
        runner.join(timeout=10)
        return runner, events, markdown

    return _run
