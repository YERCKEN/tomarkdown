"""Pruebas de `app.config`: lista de extensiones y filtro del diálogo de archivos."""

from __future__ import annotations

from app.config import SUPPORTED_EXTENSIONS, file_dialog_filter, supported_extensions


def test_supported_extensions_ordenadas_y_sin_duplicados():
    exts = supported_extensions()

    assert exts == sorted(set(exts))
    assert set(exts) == set(SUPPORTED_EXTENSIONS)
    assert "pdf" in exts


def test_file_dialog_filter():
    filtro = file_dialog_filter()

    assert len(filtro) == 2
    assert filtro[0].startswith("Documentos soportados (")
    assert "*.pdf" in filtro[0]
    assert filtro[1] == "Todos los archivos (*.*)"
