"""Sube la version de ToMarkdown y deja el commit y el tag listos.

`__version__` vive en `app/config.py` (lo lee hatchling). Subir version a mano es
editar esa linea y taggear, sin garantia de que coincidan; `build.yml` aborta un
tag que no case con `__version__`. Este script hace las dos cosas de una:

1. Reescribe `__version__` en `app/config.py` con el salto pedido.
2. `git commit` de esa linea + `git tag vX.Y.Z`.

**No hace push**: eso lo decide la persona. Tampoco mueve `[Unreleased]` en
`CHANGELOG.md`, solo lo recuerda.

Uso:

    uv run python scripts/bump_version.py {major|minor|patch}

Solo stdlib. El nucleo (`parse_version`, `bump`, `replace_version`) es puro y
esta cubierto en `tests/test_bump_version.py`.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CONFIG = REPO / "app" / "config.py"

#: La linea exacta que busca hatchling (`[tool.hatch.version] path = app/config.py`).
_VERSION_RE = re.compile(r'^__version__ = "(\d+)\.(\d+)\.(\d+)"$', re.MULTILINE)

PARTS = ("major", "minor", "patch")


def parse_version(text: str) -> tuple[int, int, int]:
    """Extrae `(major, minor, patch)` de la linea `__version__` de `config.py`."""
    match = _VERSION_RE.search(text)
    if match is None:
        raise ValueError('No se encontro la linea `__version__ = "X.Y.Z"` en app/config.py')
    return int(match[1]), int(match[2]), int(match[3])


def bump(version: tuple[int, int, int], part: str) -> str:
    """Devuelve la version siguiente como `"X.Y.Z"` para el salto `part`."""
    major, minor, patch = version
    if part == "major":
        return f"{major + 1}.0.0"
    if part == "minor":
        return f"{major}.{minor + 1}.0"
    if part == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise ValueError(f"Salto invalido: {part!r} (esperaba uno de {PARTS})")


def replace_version(text: str, new: str) -> str:
    """Reescribe solo la linea `__version__`, sin tocar el resto del archivo."""
    if not _VERSION_RE.search(text):
        raise ValueError('No se encontro la linea `__version__ = "X.Y.Z"` en app/config.py')
    return _VERSION_RE.sub(f'__version__ = "{new}"', text, count=1)


def _git(*args: str) -> str:
    """Corre git en la raiz del repo y devuelve su stdout."""
    result = subprocess.run(
        ["git", *args],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _ensure_clean_tree() -> None:
    if _git("status", "--porcelain"):
        raise SystemExit("🔴 El arbol de trabajo tiene cambios sin commitear. Limpialo primero.")


def _ensure_tag_free(tag: str) -> None:
    existing = _git("tag", "--list", tag)
    if existing:
        raise SystemExit(f"🔴 El tag {tag} ya existe.")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Sube la version y deja commit + tag.")
    parser.add_argument("part", choices=PARTS, help="Que parte de la version subir.")
    args = parser.parse_args(argv)

    _ensure_clean_tree()

    text = CONFIG.read_text(encoding="utf-8")
    current = parse_version(text)
    new = bump(current, args.part)
    tag = f"v{new}"

    _ensure_tag_free(tag)

    CONFIG.write_text(replace_version(text, new), encoding="utf-8")
    _git("add", str(CONFIG.relative_to(REPO)))
    _git("commit", "-m", f"chore: release {tag}")
    _git("tag", tag)

    old = ".".join(str(n) for n in current)
    print(f"✅ {old} → {new}")
    print(f"   commit: chore: release {tag}")
    print(f"   tag:    {tag}")
    print()
    print("Falta a mano:")
    print(f"  · mover los cambios de [Unreleased] a [{new}] en CHANGELOG.md")
    print(f"  · git push origin HEAD --follow-tags   (el tag {tag} dispara build.yml)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
