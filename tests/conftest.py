"""Fixtures compartidos por la suíte.

Reúne lo que los scripts de humo tenían suelto: el armador de PDF mínimo, las
entradas de cola sintéticas y el arranque instrumentado de `QueueRunner`.
"""

from __future__ import annotations

import threading
from typing import Callable

import pytest

from app.queue_runner import QueueRunner


def _minimal_pdf(text: str) -> bytes:
    """Arma un PDF válido mínimo con una línea de texto.

    Evita depender de una librería de escritura de PDF solo para las pruebas. La
    tabla xref lleva los desplazamientos reales, así pdfminer lo lee sin
    reconstruirla.
    """
    stream = f"BT /F1 14 Tf 24 120 Td ({text}) Tj ET".encode("latin-1")
    objects = [
        b"<</Type/Catalog/Pages 2 0 R>>",
        b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]"
        b"/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>",
        b"<</Length " + str(len(stream)).encode() + b">>stream\n" + stream + b"\nendstream",
        b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    ]

    out = bytearray(b"%PDF-1.4\n")
    offsets: list[int] = []
    for index, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{index} 0 obj\n".encode() + body + b"\nendobj\n"

    xref_at = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += (
        f"trailer<</Size {len(objects) + 1}/Root 1 0 R>>\n"
        f"startxref\n{xref_at}\n%%EOF\n"
    ).encode()

    return bytes(out)


@pytest.fixture
def make_pdf() -> Callable[[str], bytes]:
    """Devuelve la función que arma un PDF válido mínimo con una línea de texto."""
    return _minimal_pdf


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
