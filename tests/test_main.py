"""Pruebas de `app.main`: expansión de rutas y `--self-check`."""

from __future__ import annotations

import importlib

import pytest

from app.config import CONVERTER_IMPORTS
from app.main import _echo, _expand_paths, _self_check
from scripts.gen_selfcheck_samples import write_samples

# ------------------------------------------------------ CONVERTER_IMPORTS


@pytest.mark.parametrize("name", CONVERTER_IMPORTS)
def test_cada_modulo_de_converter_importa(name):
    """La lista que va a `hiddenimports` no puede tener un nombre mal escrito."""
    importlib.import_module(name)


# ------------------------------------------------------------ _expand_paths


def test_expand_paths_carpeta_devuelve_archivos_ordenados(tmp_path):
    (tmp_path / "b.txt").write_text("b", encoding="utf-8")
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    (tmp_path / "sub").mkdir()

    assert _expand_paths([str(tmp_path)]) == [
        str(tmp_path / "a.txt"),
        str(tmp_path / "b.txt"),
    ]


def test_expand_paths_deja_los_archivos_como_estan(tmp_path):
    sample = tmp_path / "x.txt"
    sample.write_text("x", encoding="utf-8")

    assert _expand_paths([str(sample)]) == [str(sample)]


# --------------------------------------------------------------- _self_check


def test_self_check_sin_argumentos_convierte_la_muestra():
    assert _self_check([]) == 0


def test_self_check_ok_con_una_carpeta_de_muestras(tmp_path):
    write_samples(tmp_path)

    assert _self_check([str(tmp_path)]) == 0


def test_self_check_falla_con_un_archivo_roto(tmp_path, make_pdf):
    data = make_pdf("Informe de prueba")
    (tmp_path / "roto.pdf").write_bytes(data[: len(data) // 2])

    assert _self_check([str(tmp_path)]) == 1


def test_self_check_falla_si_la_carpeta_no_tiene_archivos(tmp_path):
    assert _self_check([str(tmp_path)]) == 1


def test_self_check_no_revienta_sin_stdout(monkeypatch):
    """El .exe windowed de Windows puede tener `sys.stdout` en None."""
    monkeypatch.setattr("sys.stdout", None)

    assert _self_check([]) == 0


def test_echo_sin_stdout_no_lanza(monkeypatch):
    monkeypatch.setattr("sys.stdout", None)

    _echo("descartado")


def test_echo_degrada_a_ascii_si_la_consola_no_soporta_unicode(monkeypatch):
    import io

    class AsciiOnly(io.StringIO):
        def write(self, s):
            s.encode("ascii")  # UnicodeEncodeError con no-ASCII, como cp1252
            return super().write(s)

    fake = AsciiOnly()
    monkeypatch.setattr("sys.stdout", fake)

    _echo("✓ hola")

    assert "hola" in fake.getvalue()
    assert "✓" not in fake.getvalue()
