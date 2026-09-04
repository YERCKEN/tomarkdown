"""Pruebas de `app.api`.

Los helpers puros van directo. Lo que necesita ventana (`on_native_drop`, el
ciclo de la cola, `save_all`) usa la fixture `fake_window` de `conftest.py`.
"""

from __future__ import annotations

import pytest

from app import config
from app.api import Api, _all_paths, _extension, _first_path, _unique_md_path
from app.converter import ConversionError


def _drop_event(paths: list[str]) -> dict:
    """Arma el `event` que pywebview pasa a `on_native_drop` para esas rutas."""
    files = [{"name": path.rsplit("/", 1)[-1], "pywebviewFullPath": path} for path in paths]
    return {"dataTransfer": {"files": files}}


def test_get_app_info():
    info = Api().get_app_info()

    assert info == {"name": config.APP_NAME, "version": config.__version__}


@pytest.mark.parametrize(
    "path, expected",
    [
        ("/x/informe.pdf", "pdf"),
        ("/x/INFORME.PDF", "pdf"),
        ("/x/backup.tar.gz", "gz"),
        ("/x/sin_extension", ""),
        ("/x/.gitignore", ""),
    ],
)
def test_extension(path, expected):
    assert _extension(path) == expected


@pytest.mark.parametrize(
    "raw, expected",
    [
        (None, None),
        ("", None),
        ((), None),
        ("/a/b.md", "/a/b.md"),
        (["/a/b.md"], "/a/b.md"),
        (("/a/b.md", "/c/d.md"), "/a/b.md"),
    ],
)
def test_first_path(raw, expected):
    assert _first_path(raw) == expected


@pytest.mark.parametrize(
    "raw, expected",
    [
        (None, []),
        ("", []),
        ("/a/b.md", ["/a/b.md"]),
        (["/a/b.md", "/c/d.md"], ["/a/b.md", "/c/d.md"]),
    ],
)
def test_all_paths(raw, expected):
    assert _all_paths(raw) == expected


def test_unique_md_path_sin_colision(tmp_path):
    assert _unique_md_path(tmp_path, "informe") == tmp_path / "informe.md"


def test_unique_md_path_con_colision(tmp_path):
    (tmp_path / "informe.md").write_text("x", encoding="utf-8")
    (tmp_path / "informe-2.md").write_text("x", encoding="utf-8")

    assert _unique_md_path(tmp_path, "informe") == tmp_path / "informe-3.md"


# --------------------------------------------------------------- on_native_drop


def test_on_native_drop_agrega_las_entradas(tmp_path, fake_window):
    archivo = tmp_path / "informe.pdf"
    archivo.write_bytes(b"%PDF-1.4\n")
    api = Api()
    api.attach(fake_window)

    api.on_native_drop(_drop_event([str(archivo)]))

    (entry,) = api._entries.values()
    assert entry["name"] == "informe.pdf"
    assert entry["ext"] == "pdf"
    assert entry["status"] == "pending"

    added = fake_window.events_named("files:added")
    assert added and added[0]["files"][0]["name"] == "informe.pdf"


def test_on_native_drop_rechaza_formato_no_soportado(tmp_path, fake_window):
    malo = tmp_path / "programa.exe"
    malo.write_bytes(b"MZ")
    api = Api()
    api.attach(fake_window)

    api.on_native_drop(_drop_event([str(malo)]))

    assert api._entries == {}
    rejected = fake_window.events_named("files:rejected")
    assert rejected and "programa.exe" in rejected[0]["names"]


def test_on_native_drop_avisa_al_soltar_una_carpeta(tmp_path, fake_window):
    carpeta = tmp_path / "mis documentos"
    carpeta.mkdir()
    api = Api()
    api.attach(fake_window)

    api.on_native_drop(_drop_event([str(carpeta)]))

    assert api._entries == {}
    rejected = fake_window.events_named("files:rejected")
    assert rejected and "mis documentos" in rejected[0]["folders"]
    assert rejected[0]["names"] == []


def test_on_native_drop_ignora_los_duplicados(tmp_path, fake_window):
    archivo = tmp_path / "informe.pdf"
    archivo.write_bytes(b"%PDF-1.4\n")
    api = Api()
    api.attach(fake_window)

    api.on_native_drop(_drop_event([str(archivo)]))
    api.on_native_drop(_drop_event([str(archivo)]))

    assert len(api._entries) == 1


# ------------------------------------------------------------- zip_contents


def test_on_native_drop_lista_el_contenido_de_un_zip(fake_window, make_zip):
    archivo = make_zip({"notas.txt": b"hola", "foto.png": b"\x89PNG", "vacia/": b""})
    api = Api()
    api.attach(fake_window)

    api.on_native_drop(_drop_event([str(archivo)]))

    (entry,) = api._entries.values()
    assert entry["ext"] == "zip"
    contents = {member["path"]: member["status"] for member in entry["zip_contents"]}
    assert contents == {"notas.txt": "pending", "foto.png": "unsupported"}


def test_zip_corrupto_no_tiene_zip_contents(tmp_path, fake_window):
    malo = tmp_path / "roto.zip"
    malo.write_bytes(b"esto no es un zip")
    api = Api()
    api.attach(fake_window)

    api.on_native_drop(_drop_event([str(malo)]))

    (entry,) = api._entries.values()
    assert entry["zip_contents"] is None


def test_archivo_normal_no_lleva_zip_contents(tmp_path, fake_window):
    archivo = tmp_path / "informe.pdf"
    archivo.write_bytes(b"%PDF-1.4\n")
    api = Api()
    api.attach(fake_window)

    api.on_native_drop(_drop_event([str(archivo)]))

    (entry,) = api._entries.values()
    assert entry["zip_contents"] is None


# --------------------------------------------------------------- paste_files


def test_paste_files_agrega_lo_que_hay_en_el_portapapeles(tmp_path, fake_window, monkeypatch):
    archivo = tmp_path / "informe.pdf"
    archivo.write_bytes(b"%PDF-1.4\n")
    api = Api()
    api.attach(fake_window)
    monkeypatch.setattr("app.api.clipboard.files_in_clipboard", lambda: [str(archivo)])

    accepted = api.paste_files()

    assert accepted and accepted[0]["name"] == "informe.pdf"
    assert list(api._entries.values()) == accepted


def test_paste_files_rechaza_formato_no_soportado(tmp_path, fake_window, monkeypatch):
    malo = tmp_path / "programa.exe"
    malo.write_bytes(b"MZ")
    api = Api()
    api.attach(fake_window)
    monkeypatch.setattr("app.api.clipboard.files_in_clipboard", lambda: [str(malo)])

    accepted = api.paste_files()

    assert accepted == []
    rejected = fake_window.events_named("files:rejected")
    assert rejected and "programa.exe" in rejected[0]["names"]


def test_paste_files_sin_nada_copiado(fake_window, monkeypatch):
    api = Api()
    api.attach(fake_window)
    monkeypatch.setattr("app.api.clipboard.files_in_clipboard", lambda: [])

    assert api.paste_files() == []
    assert fake_window.events_named("files:rejected") == []


def test_clipboard_has_files_delega_en_el_modulo_clipboard(monkeypatch):
    monkeypatch.setattr("app.api.clipboard.has_files_in_clipboard", lambda: True)

    assert Api().clipboard_has_files() is True


# ---------------------------------------------------- start_conversion (ciclo)


def test_start_conversion_lleva_a_done(tmp_path, fake_window, monkeypatch):
    archivo = tmp_path / "a.pdf"
    archivo.write_bytes(b"%PDF-1.4\n")
    api = Api()
    api.attach(fake_window)
    api.on_native_drop(_drop_event([str(archivo)]))
    (file_id,) = api._entries

    monkeypatch.setattr("app.queue_runner.convert", lambda path: "# Título\n\ncuerpo")
    api.start_conversion([file_id])
    api._runner.join(timeout=10)

    assert api._entries[file_id]["status"] == "done"
    assert api._markdown[file_id] == "# Título\n\ncuerpo"
    assert fake_window.events_named("item:done")
    assert fake_window.events_named("queue:done")


def test_start_conversion_marca_error_y_sigue(tmp_path, fake_window, monkeypatch):
    archivo = tmp_path / "a.pdf"
    archivo.write_bytes(b"%PDF-1.4\n")
    api = Api()
    api.attach(fake_window)
    api.on_native_drop(_drop_event([str(archivo)]))
    (file_id,) = api._entries

    def boom(path):
        raise ConversionError("el archivo está dañado")

    monkeypatch.setattr("app.queue_runner.convert", boom)
    api.start_conversion([file_id])
    api._runner.join(timeout=10)

    assert api._entries[file_id]["status"] == "error"
    assert api._entries[file_id]["error"] == "el archivo está dañado"
    assert file_id not in api._markdown
    errors = fake_window.events_named("item:error")
    assert errors and errors[0]["error"] == "el archivo está dañado"


# ------------------------------------------------------------------- save_all


def _done_entry(api, file_id, name):
    api._entries[file_id] = {
        "id": file_id,
        "name": name,
        "path": f"/origen/{name}",
        "ext": name.rsplit(".", 1)[-1],
        "size_bytes": 0,
        "status": "done",
        "error": None,
        "saved_to": None,
    }
    api._markdown[file_id] = f"# {file_id}"


def test_save_all_escribe_md_con_nombres_unicos(tmp_path, fake_window):
    api = Api()
    api.attach(fake_window)
    _done_entry(api, "id1", "informe.pdf")
    _done_entry(api, "id2", "informe.docx")
    fake_window.dialog_result = str(tmp_path)

    result = api.save_all(["id1", "id2"])

    assert result["written"] == 2
    assert (tmp_path / "informe.md").exists()
    assert (tmp_path / "informe-2.md").exists()
    assert set(result["saved"]) == {"id1", "id2"}
    assert api._entries["id1"]["saved_to"] == result["saved"]["id1"]


def test_save_all_sin_dialogo_no_escribe_nada(tmp_path, fake_window):
    api = Api()
    api.attach(fake_window)
    _done_entry(api, "id1", "informe.pdf")
    fake_window.dialog_result = None  # el usuario canceló

    result = api.save_all(["id1"])

    assert result["written"] == 0
    assert list(tmp_path.iterdir()) == []


def test_save_all_recuerda_la_carpeta(tmp_path, fake_window):
    destino = tmp_path / "salida"
    destino.mkdir()

    api = Api()
    api.attach(fake_window)
    _done_entry(api, "id1", "informe.pdf")
    fake_window.dialog_result = str(destino)
    api.save_all(["id1"])

    # Segunda vez (otra instancia): el diálogo arranca en la carpeta anterior.
    otra = Api()
    otra.attach(fake_window)
    _done_entry(otra, "id9", "otro.pdf")
    fake_window.dialog_calls.clear()
    otra.save_all(["id9"])

    _, kwargs = fake_window.dialog_calls[0]
    assert kwargs["directory"] == str(destino)
