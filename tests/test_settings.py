"""Pruebas de `app.settings`: dónde vive el archivo y que leer nunca rompa."""

from __future__ import annotations

from pathlib import Path

import pytest

from app import settings

# --------------------------------------------------------------- _config_dir


def test_config_dir_macos(monkeypatch):
    monkeypatch.setattr(settings.sys, "platform", "darwin")

    assert settings._config_dir() == Path.home() / "Library" / "Application Support" / "ToMarkdown"


def test_config_dir_windows(monkeypatch, tmp_path):
    monkeypatch.setattr(settings.sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    assert settings._config_dir() == tmp_path / "ToMarkdown"


def test_config_dir_linux(monkeypatch, tmp_path):
    monkeypatch.setattr(settings.sys, "platform", "linux")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    assert settings._config_dir() == tmp_path / "tomarkdown"


# ------------------------------------------------------------- load / save


def test_save_y_load_es_ida_y_vuelta():
    settings.save({"last_save_dir": "/tmp/salida", "otro": 1})

    assert settings.load() == {"last_save_dir": "/tmp/salida", "otro": 1}


def test_load_sin_archivo_da_vacio():
    assert settings.load() == {}


def test_load_json_corrupto_da_vacio(monkeypatch, tmp_path):
    archivo = tmp_path / "settings.json"
    archivo.write_text("{ esto no es json", encoding="utf-8")
    monkeypatch.setattr(settings, "_settings_file", lambda: archivo)

    assert settings.load() == {}


def test_save_que_falla_no_lanza(monkeypatch, tmp_path):
    bloqueador = tmp_path / "bloqueador"
    bloqueador.write_text("soy un archivo, no una carpeta", encoding="utf-8")
    monkeypatch.setattr(settings, "_settings_file", lambda: bloqueador / "settings.json")

    settings.save({"x": 1})  # no debe propagar el OSError


# --------------------------------------------- last_save_dir / remember_save_dir


def test_remember_y_last_save_dir(tmp_path):
    carpeta = tmp_path / "salida"
    carpeta.mkdir()

    settings.remember_save_dir(str(carpeta))

    assert settings.last_save_dir() == str(carpeta)


def test_last_save_dir_none_si_la_carpeta_ya_no_existe(tmp_path):
    settings.remember_save_dir(str(tmp_path / "borrada"))

    assert settings.last_save_dir() is None


def test_remember_save_dir_ignora_cadena_vacia():
    settings.remember_save_dir("")

    assert "last_save_dir" not in settings.load()


@pytest.mark.parametrize("bad", [None, 123, ["/x"]])
def test_last_save_dir_tolera_valores_raros(monkeypatch, bad):
    monkeypatch.setattr(settings, "load", lambda: {"last_save_dir": bad})

    assert settings.last_save_dir() is None
