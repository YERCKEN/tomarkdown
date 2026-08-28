"""Prueba de humo del hilo de la cola, sin abrir la ventana.

Verifica el contrato de `QueueRunner` con un convertidor falso controlado por
eventos, de modo que la cancelación se pruebe de forma determinista y no
dependiendo de cuánto tarde un archivo real.

Uso: uv run python scripts/smoke_queue.py
"""

from __future__ import annotations

import sys
import threading
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import queue_runner  # noqa: E402
from app.converter import ConversionError  # noqa: E402
from app.queue_runner import QueueRunner  # noqa: E402

RESULTS: list[tuple[bool, str]] = []


def check(ok: bool, label: str, detail: str = "") -> None:
    """Registra una comprobación con su detalle."""
    RESULTS.append((ok, f"{label}{(' -> ' + detail) if detail else ''}"))


def make_entries(count: int) -> dict[str, dict]:
    """Crea entradas de cola sintéticas, ya normalizadas."""
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


@contextmanager
def running(entries: dict[str, dict], convert_fn):
    """Arranca la cola con un convertidor inyectado y recoge los eventos.

    El parche se mantiene hasta que el bloque termina: restaurarlo antes de que
    el hilo cierre haría que la cola usara el convertidor real a mitad de camino.
    """
    events: list[dict] = []
    markdown: dict[str, str] = {}
    lock = threading.Lock()

    def emit(name: str, payload: dict) -> None:
        with lock:
            events.append({"event": name, **payload})

    original = queue_runner.convert
    queue_runner.convert = convert_fn
    try:
        runner = QueueRunner(entries, markdown, emit)
        runner.start(list(entries))
        yield runner, events, markdown
    finally:
        queue_runner.convert = original


def test_orden_y_errores() -> None:
    """La cola procesa en orden, un archivo corrupto no la tumba."""
    entries = make_entries(4)
    order: list[str] = []

    def fake_convert(path: str) -> str:
        order.append(path)
        if path.endswith("archivo-2.pdf"):
            raise ConversionError("No se pudo leer el archivo")
        return "# contenido\n"

    with running(entries, fake_convert) as (runner, events, markdown):
        runner.join(timeout=10)

    check(
        order == [f"/tmp/archivo-{i}.pdf" for i in range(4)],
        "procesa en orden, uno a la vez",
        str([Path(p).name for p in order]),
    )

    statuses = [entries[f"id-{i}"]["status"] for i in range(4)]
    check(
        statuses == ["done", "done", "error", "done"],
        "un archivo con error no detiene la cola",
        str(statuses),
    )

    check(len(markdown) == 3, "solo se guarda el markdown de los convertidos", str(len(markdown)))
    check(
        entries["id-2"]["error"] == "No se pudo leer el archivo",
        "el mensaje de error queda en la entrada",
    )

    progress = [e for e in events if e["event"] == "queue:progress"]
    check(
        [e["completed"] for e in progress] == [1, 2, 3, 4],
        "la barra general avanza en cada archivo",
        str([e["completed"] for e in progress]),
    )

    final = events[-1]
    check(
        final == {"event": "queue:done", "completed": 3, "failed": 1, "cancelled": 0},
        "queue:done reporta el recuento correcto",
        str(final),
    )


def test_cancelacion() -> None:
    """Cancelar deja terminar el archivo en curso y cancela los pendientes."""
    entries = make_entries(5)
    started = threading.Event()
    release = threading.Event()

    def fake_convert(path: str) -> str:
        if path.endswith("archivo-0.pdf"):
            started.set()
            release.wait(timeout=10)
        return "# contenido\n"

    with running(entries, fake_convert) as (runner, events, _markdown):
        # Cancelar mientras el primer archivo está a mitad de conversión.
        started.wait(timeout=10)
        runner.cancel()
        release.set()
        runner.join(timeout=10)

    check(
        entries["id-0"]["status"] == "done",
        "el archivo en curso alcanza a terminar",
        entries["id-0"]["status"],
    )

    rest = [entries[f"id-{i}"]["status"] for i in range(1, 5)]
    check(
        rest == ["cancelled"] * 4,
        "los pendientes pasan a cancelled",
        str(rest),
    )

    final = events[-1]
    check(
        final == {"event": "queue:done", "completed": 1, "failed": 0, "cancelled": 4},
        "queue:done informa cuántos se cancelaron",
        str(final),
    )

    check(
        not runner.is_running,
        "el hilo termina limpio, sin excepciones",
    )


def test_no_reconvierte() -> None:
    """Los archivos ya convertidos no se vuelven a procesar."""
    entries = make_entries(3)
    entries["id-1"]["status"] = "done"
    seen: list[str] = []

    def fake_convert(path: str) -> str:
        seen.append(path)
        return "# contenido\n"

    with running(entries, fake_convert) as (runner, events, _markdown):
        runner.join(timeout=10)

    check(
        "/tmp/archivo-1.pdf" not in seen,
        "no reconvierte lo que ya estaba listo",
        str([Path(p).name for p in seen]),
    )
    check(
        events[0] == {"event": "queue:start", "total": 2},
        "el total de la cola descuenta los ya convertidos",
        str(events[0]),
    )


def main() -> int:
    """Corre las pruebas e informa. Devuelve el código de salida."""
    print("\nProbando el hilo de la cola\n")
    test_orden_y_errores()
    test_cancelacion()
    test_no_reconvierte()

    failed = 0
    for ok, label in RESULTS:
        print(f"  {'✓' if ok else '✗'} {label}")
        if not ok:
            failed += 1

    print()
    if failed:
        print(f"🔴 {failed} de {len(RESULTS)} comprobaciones fallaron")
        return 1

    print(f"✅ {len(RESULTS)} comprobaciones pasaron")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
