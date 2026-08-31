"""Pruebas de `app.api` que no necesitan ventana ni diálogos nativos."""

from __future__ import annotations

import pytest

from app import config
from app.api import Api, _all_paths, _extension, _first_path, _unique_md_path


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
