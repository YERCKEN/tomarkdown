"""Pruebas de `app.converter`: conversión real por formato y traducción de errores."""

from __future__ import annotations

import json

import pytest
from markitdown import (
    FileConversionException,
    MissingDependencyException,
    UnsupportedFormatException,
)

from app import converter
from app.converter import ConversionError, convert

# ----------------------------------------------------------- conversión real

TEXT_SAMPLES = {
    "txt": "Primera línea\nSegunda con acentos: ñ á é\n",
    "md": "# Título\n\nUn párrafo con **negrita**.\n",
    "csv": "nombre,cantidad\nlápiz,3\ncuaderno,7\n",
    "json": json.dumps({"nombre": "ToMarkdown", "versión": 1}, ensure_ascii=False),
    "html": "<html><body><h1>Encabezado</h1><p>Texto <b>marcado</b>.</p></body></html>",
    "xml": "<root><item>uno</item><item>dos</item></root>",
}


@pytest.mark.parametrize("ext", sorted(TEXT_SAMPLES))
def test_formato_de_texto_convierte(ext, tmp_path):
    sample = tmp_path / f"muestra.{ext}"
    sample.write_text(TEXT_SAMPLES[ext], encoding="utf-8")

    assert convert(str(sample)).strip()


def test_ipynb_convierte(tmp_path):
    notebook = {
        "cells": [
            {"cell_type": "markdown", "metadata": {}, "source": ["# Cuaderno\n"]},
            {
                "cell_type": "code",
                "metadata": {},
                "execution_count": 1,
                "outputs": [],
                "source": ["print('hola')\n"],
            },
        ],
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    sample = tmp_path / "análisis.ipynb"
    sample.write_text(json.dumps(notebook), encoding="utf-8")

    assert "Cuaderno" in convert(str(sample))


def test_xlsx_convierte(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")

    book = openpyxl.Workbook()
    sheet = book.active
    sheet.append(["producto", "stock"])
    sheet.append(["cuaderno", 12])
    sample = tmp_path / "inventario.xlsx"
    book.save(sample)

    assert "cuaderno" in convert(str(sample))


def test_pptx_convierte(tmp_path):
    pptx = pytest.importorskip("pptx")

    deck = pptx.Presentation()
    slide = deck.slides.add_slide(deck.slide_layouts[0])
    slide.shapes.title.text = "Diapositiva de prueba"
    sample = tmp_path / "presentación.pptx"
    deck.save(sample)

    assert "Diapositiva de prueba" in convert(str(sample))


def test_pdf_valido_convierte(tmp_path, make_pdf):
    sample = tmp_path / "informe.pdf"
    sample.write_bytes(make_pdf("Informe anual de prueba"))

    assert "Informe anual" in convert(str(sample))


def test_pdf_truncado_da_conversion_error(tmp_path, make_pdf):
    data = make_pdf("Informe anual de prueba")
    sample = tmp_path / "roto.pdf"
    sample.write_bytes(data[: len(data) // 2])

    with pytest.raises(ConversionError):
        convert(str(sample))


# ------------------------------------------------------ traducción de errores


class _FailingEngine:
    """Motor falso cuyo `convert_local` siempre levanta la excepción dada."""

    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    def convert_local(self, target):  # noqa: ARG002 - firma de MarkItDown
        raise self._exc


@pytest.mark.parametrize(
    "exc, fragmento",
    [
        (FileNotFoundError(), "ya no está"),
        (PermissionError(), "permiso"),
        (IsADirectoryError(), "carpeta"),
        (UnsupportedFormatException(), "no reconoce"),
        (MissingDependencyException(), "Falta el componente"),
        (FileConversionException(), "dañado"),
    ],
)
def test_traduce_las_excepciones_conocidas(monkeypatch, exc, fragmento):
    monkeypatch.setattr(converter, "_engine", lambda: _FailingEngine(exc))

    with pytest.raises(ConversionError) as err:
        convert("/x/archivo.pdf")

    assert fragmento in str(err.value)


def test_error_inesperado_se_traduce_con_el_tipo(monkeypatch):
    monkeypatch.setattr(converter, "_engine", lambda: _FailingEngine(RuntimeError("boom")))

    with pytest.raises(ConversionError, match="RuntimeError"):
        convert("/x/archivo.pdf")


def test_resultado_sin_texto_da_error(monkeypatch):
    class _EmptyResult:
        markdown = ""
        text_content = ""

    class _EmptyEngine:
        def convert_local(self, target):  # noqa: ARG002 - firma de MarkItDown
            return _EmptyResult()

    monkeypatch.setattr(converter, "_engine", lambda: _EmptyEngine())

    with pytest.raises(ConversionError, match="no tiene texto"):
        convert("/x/vacío.txt")
