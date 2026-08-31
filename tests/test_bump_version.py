"""Pruebas del núcleo puro de `scripts/bump_version.py`.

La parte de git (`commit`, `tag`) no se prueba: acá solo el parseo, el salto de
SemVer y el reemplazo de la línea.
"""

from __future__ import annotations

import pytest

from scripts.bump_version import bump, parse_version, replace_version

CONFIG_SNIPPET = '''from __future__ import annotations

__version__ = "1.4.2"

APP_NAME = "ToMarkdown"
'''


def test_parse_version_lee_la_linea():
    assert parse_version(CONFIG_SNIPPET) == (1, 4, 2)


def test_parse_version_sin_linea_falla():
    with pytest.raises(ValueError):
        parse_version("APP_NAME = 'x'\n")


@pytest.mark.parametrize(
    "part, expected",
    [
        ("major", "2.0.0"),
        ("minor", "1.5.0"),
        ("patch", "1.4.3"),
    ],
)
def test_bump(part, expected):
    assert bump((1, 4, 2), part) == expected


def test_bump_salto_invalido():
    with pytest.raises(ValueError):
        bump((1, 4, 2), "mayor")


def test_replace_version_solo_toca_esa_linea():
    result = replace_version(CONFIG_SNIPPET, "1.5.0")

    assert '__version__ = "1.5.0"' in result
    assert '__version__ = "1.4.2"' not in result
    assert 'APP_NAME = "ToMarkdown"' in result
    assert result.count("__version__") == 1


def test_replace_version_sin_linea_falla():
    with pytest.raises(ValueError):
        replace_version("nada que ver\n", "1.5.0")
