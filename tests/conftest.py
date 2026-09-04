"""Fixtures compartidos por la suíte.

Reúne lo que los scripts de humo tenían suelto: el armador de PDF mínimo, las
entradas de cola sintéticas, el arranque instrumentado de `QueueRunner` y una
ventana de pywebview de mentira para probar `Api`.
"""

from __future__ import annotations

import json
import re
import threading
from collections.abc import Callable

import pytest

from app.queue_runner import QueueRunner
from scripts.gen_selfcheck_samples import minimal_pdf

#: `Api._emit` empuja eventos con `window.run_js("window.toMarkdown.onEvent(<json>)")`.
_ON_EVENT_RE = re.compile(r"window\.toMarkdown\.onEvent\((?P<payload>.*)\)$", re.DOTALL)


class FakeWindow:
    """Ventana de pywebview de mentira: lo mínimo que `Api` le pide.

    `Api` solo usa dos cosas de la ventana: `run_js` (para empujar eventos al
    front) y `create_file_dialog` (los diálogos nativos de abrir/guardar).
    """

    def __init__(self) -> None:
        #: Cada string que pasó por run_js, tal cual.
        self.js_calls: list[str] = []
        #: Payloads de `onEvent(...)` ya parseados de JSON, en orden.
        self.events: list[dict] = []
        #: (dialog_type, kwargs) de cada create_file_dialog.
        self.dialog_calls: list[tuple[int, dict]] = []
        #: Lo que devuelve el próximo create_file_dialog: str, lista de str o None.
        self.dialog_result: object = None

    def run_js(self, code: str) -> None:
        self.js_calls.append(code)
        match = _ON_EVENT_RE.search(code)
        if match:
            self.events.append(json.loads(match.group("payload")))

    def create_file_dialog(self, dialog_type: int, **kwargs: object) -> object:
        self.dialog_calls.append((dialog_type, kwargs))
        return self.dialog_result

    def events_named(self, name: str) -> list[dict]:
        """Los eventos con ese `event`, en orden de llegada."""
        return [event for event in self.events if event.get("event") == name]


@pytest.fixture
def fake_window() -> FakeWindow:
    """Una `FakeWindow` nueva para enchufarle a `Api.attach`."""
    return FakeWindow()


@pytest.fixture(autouse=True)
def _isolate_settings(tmp_path, monkeypatch):
    """Ningún test escribe en el `settings.json` real del sistema.

    Redirige `app.settings._settings_file` a `tmp_path`; `_config_dir` queda
    intacto para que `test_settings.py` pueda probar su lógica de plataforma.
    """
    monkeypatch.setattr("app.settings._settings_file", lambda: tmp_path / "settings.json")


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
