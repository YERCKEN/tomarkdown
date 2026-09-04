"""Pruebas de `app.queue_runner.QueueRunner`: orden, aislamiento de errores y cancelación."""

from __future__ import annotations

import threading

from app.converter import ConversionError


def _zip_entry(zip_contents):
    return {
        "id-0": {
            "id": "id-0",
            "name": "muestra.zip",
            "path": "/tmp/muestra.zip",
            "ext": "zip",
            "size_bytes": 100,
            "status": "pending",
            "error": None,
            "saved_to": None,
            "zip_contents": zip_contents,
        }
    }


def test_procesa_en_orden_y_aisla_errores(make_entries, run_queue):
    entries = make_entries(4)
    order: list[str] = []

    def fake_convert(path: str) -> str:
        order.append(path)
        if path.endswith("archivo-2.pdf"):
            raise ConversionError("No se pudo leer el archivo")
        return "# contenido\n"

    _runner, events, markdown = run_queue(entries, fake_convert)

    assert order == [f"/tmp/archivo-{i}.pdf" for i in range(4)]

    statuses = [entries[f"id-{i}"]["status"] for i in range(4)]
    assert statuses == ["done", "done", "error", "done"]

    assert len(markdown) == 3
    assert entries["id-2"]["error"] == "No se pudo leer el archivo"

    progress = [e["completed"] for e in events if e["event"] == "queue:progress"]
    assert progress == [1, 2, 3, 4]

    assert events[-1] == {
        "event": "queue:done",
        "completed": 3,
        "failed": 1,
        "cancelled": 0,
    }


def test_cancelacion(make_entries, run_queue):
    entries = make_entries(5)
    started = threading.Event()
    release = threading.Event()

    def fake_convert(path: str) -> str:
        if path.endswith("archivo-0.pdf"):
            started.set()
            release.wait(timeout=10)
        return "# contenido\n"

    def cancel_midway(runner):
        started.wait(timeout=10)
        runner.cancel()
        release.set()

    runner, events, _ = run_queue(entries, fake_convert, during=cancel_midway)

    assert entries["id-0"]["status"] == "done"
    assert [entries[f"id-{i}"]["status"] for i in range(1, 5)] == ["cancelled"] * 4
    assert events[-1] == {
        "event": "queue:done",
        "completed": 1,
        "failed": 0,
        "cancelled": 4,
    }
    assert not runner.is_running


def test_no_reconvierte_lo_ya_hecho(make_entries, run_queue):
    entries = make_entries(3)
    entries["id-1"]["status"] = "done"
    seen: list[str] = []

    def fake_convert(path: str) -> str:
        seen.append(path)
        return "# contenido\n"

    _runner, events, _markdown = run_queue(entries, fake_convert)

    assert "/tmp/archivo-1.pdf" not in seen
    assert events[0] == {"event": "queue:start", "total": 2}


# ------------------------------------------------------- reconciliar zip_contents


def test_reconcilia_zip_contents_con_exito(run_queue):
    entries = _zip_entry(
        [
            {"path": "notas.txt", "status": "pending"},
            {"path": "foto.png", "status": "unsupported"},
            {"path": "roto.pdf", "status": "pending"},
        ]
    )

    def fake_convert(_path: str) -> str:
        return "## File: notas.txt\n\ncontenido\n"

    run_queue(entries, fake_convert)

    contents = {m["path"]: m["status"] for m in entries["id-0"]["zip_contents"]}
    assert contents == {"notas.txt": "done", "foto.png": "unsupported", "roto.pdf": "error"}


def test_reconcilia_zip_contents_si_falla_el_zip_entero(run_queue):
    entries = _zip_entry(
        [
            {"path": "notas.txt", "status": "pending"},
            {"path": "foto.png", "status": "unsupported"},
        ]
    )

    def fake_convert(_path: str) -> str:
        raise ConversionError("no se pudo leer el archivo")

    run_queue(entries, fake_convert)

    contents = {m["path"]: m["status"] for m in entries["id-0"]["zip_contents"]}
    # El no-soportado sigue así: nunca se intentó, no falló.
    assert contents == {"notas.txt": "error", "foto.png": "unsupported"}
