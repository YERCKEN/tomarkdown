"""Pruebas de `app.clipboard`.

El dispatch por plataforma se prueba en las tres, monkeypatcheando las
funciones internas (no la librería nativa real), para no depender de que
`pyobjc`/`pywin32` estén instalados en el runner equivocado.

Las pruebas de manejo de errores de `_files_from_macos`/`_has_files_macos`
inyectan un `AppKit` de mentira en `sys.modules` en vez de tocar las clases
reales de PyObjC: son objetos puente a Objective-C y `monkeypatch` no puede
deshacer un `setattr` sobre ellas (`delattr` falla al finalizar el test), así
que un módulo de mentira es además más simple que necesitar `pyobjc` instalado
en este runner.
"""

from __future__ import annotations

import sys
import types

import pytest

from app import clipboard


def test_files_in_clipboard_darwin(monkeypatch):
    monkeypatch.setattr(clipboard.sys, "platform", "darwin")
    monkeypatch.setattr(clipboard, "_files_from_macos", lambda: ["/a/b.pdf"])

    assert clipboard.files_in_clipboard() == ["/a/b.pdf"]


def test_files_in_clipboard_windows(monkeypatch):
    monkeypatch.setattr(clipboard.sys, "platform", "win32")
    monkeypatch.setattr(clipboard, "_files_from_windows", lambda: ["C:\\a\\b.pdf"])

    assert clipboard.files_in_clipboard() == ["C:\\a\\b.pdf"]


def test_files_in_clipboard_otra_plataforma(monkeypatch):
    monkeypatch.setattr(clipboard.sys, "platform", "linux")

    assert clipboard.files_in_clipboard() == []


def test_has_files_in_clipboard_darwin(monkeypatch):
    monkeypatch.setattr(clipboard.sys, "platform", "darwin")
    monkeypatch.setattr(clipboard, "_has_files_macos", lambda: True)

    assert clipboard.has_files_in_clipboard() is True


def test_has_files_in_clipboard_windows(monkeypatch):
    monkeypatch.setattr(clipboard.sys, "platform", "win32")
    monkeypatch.setattr(clipboard, "_has_files_windows", lambda: True)

    assert clipboard.has_files_in_clipboard() is True


def test_has_files_in_clipboard_otra_plataforma(monkeypatch):
    monkeypatch.setattr(clipboard.sys, "platform", "linux")

    assert clipboard.has_files_in_clipboard() is False


def _fake_appkit_module(pasteboard) -> types.ModuleType:
    fake = types.ModuleType("AppKit")
    fake.NSPasteboard = types.SimpleNamespace(generalPasteboard=lambda: pasteboard)
    fake.NSURL = object()
    fake.NSPasteboardURLReadingFileURLsOnlyKey = "readingFileURLsOnly"
    fake.NSPasteboardTypeFileURL = "public.file-url"
    return fake


def test_files_from_macos_atrapa_sus_excepciones(monkeypatch):
    class BoomPasteboard:
        def readObjectsForClasses_options_(self, *_args, **_kwargs):
            raise RuntimeError("portapapeles no disponible")

    monkeypatch.setitem(sys.modules, "AppKit", _fake_appkit_module(BoomPasteboard()))

    assert clipboard._files_from_macos() == []


def test_files_from_macos_lee_las_rutas(monkeypatch):
    class URL:
        def __init__(self, ruta):
            self._ruta = ruta

        def path(self):
            return self._ruta

    class Pasteboard:
        def readObjectsForClasses_options_(self, *_args, **_kwargs):
            return [URL("/a/informe.pdf"), URL("/a/notas.docx")]

    monkeypatch.setitem(sys.modules, "AppKit", _fake_appkit_module(Pasteboard()))

    assert clipboard._files_from_macos() == ["/a/informe.pdf", "/a/notas.docx"]


def test_has_files_macos_atrapa_sus_excepciones(monkeypatch):
    class BoomPasteboard:
        def types(self):
            raise RuntimeError("portapapeles no disponible")

    monkeypatch.setitem(sys.modules, "AppKit", _fake_appkit_module(BoomPasteboard()))

    assert clipboard._has_files_macos() is False


def test_has_files_macos_detecta_archivos(monkeypatch):
    class Pasteboard:
        def types(self):
            return ["public.file-url"]

    monkeypatch.setitem(sys.modules, "AppKit", _fake_appkit_module(Pasteboard()))

    assert clipboard._has_files_macos() is True


def test_files_from_windows_real_atrapa_sus_excepciones(monkeypatch):
    win32clipboard = pytest.importorskip("win32clipboard")

    def boom():
        raise RuntimeError("portapapeles no disponible")

    monkeypatch.setattr(win32clipboard, "OpenClipboard", boom)

    assert clipboard._files_from_windows() == []


def test_has_files_windows_real_atrapa_sus_excepciones(monkeypatch):
    win32clipboard = pytest.importorskip("win32clipboard")

    def boom(_fmt):
        raise RuntimeError("portapapeles no disponible")

    monkeypatch.setattr(win32clipboard, "IsClipboardFormatAvailable", boom)

    assert clipboard._has_files_windows() is False
