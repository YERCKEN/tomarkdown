"""Genera THIRD-PARTY-LICENSES.md a partir de las distribuciones instaladas.

Recorre todo lo que hay en el entorno (menos las herramientas de desarrollo) y,
para cada paquete, junta el identificador de licencia y el texto que trae su
`*.dist-info`. Solo stdlib: `build.spec` lo corre antes de empaquetar.
"""

from __future__ import annotations

from importlib import metadata
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "THIRD-PARTY-LICENSES.md"

LICENSE_FILE_HINTS = ("licen", "copying", "notice", "patents")

#: Se instalan solo para construir/probar y **no** entran al bundle, así que sus
#: avisos no hacen falta en el binario que se distribuye.
DEV_ONLY = {
    "tomarkdown",
    "pyinstaller",
    "pyinstaller-hooks-contrib",
    "altgraph",
    "macholib",
    "pytest",
    "iniconfig",
    "pluggy",
    "pygments",
}

#: Paquetes cuyo wheel no incluye el texto de la licencia. Se completa a mano con
#: el texto canónico del proyecto (mismo SPDX que declara su metadata).
SUPPLEMENT = {
    "markitdown": (
        "LICENSE (MIT)",
        "MIT License\n\n"
        "Copyright (c) Microsoft Corporation.\n\n"
        'Permission is hereby granted, free of charge, to any person obtaining a copy\n'
        'of this software and associated documentation files (the "Software"), to deal\n'
        "in the Software without restriction, including without limitation the rights\n"
        "to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n"
        "copies of the Software, and to permit persons to whom the Software is\n"
        "furnished to do so, subject to the following conditions:\n\n"
        "The above copyright notice and this permission notice shall be included in all\n"
        "copies or substantial portions of the Software.\n\n"
        'THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n'
        "IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n"
        "FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n"
        "AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n"
        "LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n"
        "OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE\n"
        "SOFTWARE.\n",
    ),
}


def runtime_packages() -> list[str]:
    """Todo lo instalado menos las herramientas de desarrollo (ver `DEV_ONLY`)."""
    names = {
        dist.metadata["Name"]
        for dist in metadata.distributions()
        if dist.metadata["Name"]
    }
    return sorted(
        (n for n in names if n.lower().replace("_", "-") not in DEV_ONLY),
        key=str.lower,
    )


def license_id(dist: metadata.Distribution) -> str:
    md = dist.metadata
    expr = md.get("License-Expression")
    if expr:
        return expr.strip()
    classifiers = [
        c.split("::")[-1].strip()
        for c in md.get_all("Classifier", [])
        if c.startswith("License ::") and "OSI Approved ::" in c
    ]
    if classifiers:
        return " / ".join(dict.fromkeys(classifiers))
    lic = (md.get("License") or "").strip()
    if lic and "\n" not in lic and len(lic) < 60:
        return lic
    if lic:
        return "ver texto abajo"
    return "sin declarar"


def license_texts(dist: metadata.Distribution) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    files = dist.files or []
    for entry in files:
        parts = str(entry).lower()
        in_licenses_dir = "/licenses/" in parts or parts.startswith("licenses/")
        looks_like = any(h in Path(parts).name for h in LICENSE_FILE_HINTS)
        if not (in_licenses_dir or looks_like):
            continue
        if Path(parts).suffix in {".py", ".pyc", ".so", ".dll", ".dylib"}:
            continue
        try:
            text = entry.locate().read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            continue
        if text:
            found.append((Path(str(entry)).name, text))
    # sin duplicados por contenido
    seen: set[str] = set()
    unique: list[tuple[str, str]] = []
    for name, text in found:
        if text in seen:
            continue
        seen.add(text)
        unique.append((name, text))
    return unique


def _pending_block(incomplete: list[str]) -> str:
    if not incomplete:
        return ""
    items = "\n".join(f"- {p}" for p in incomplete)
    return (
        "> [!IMPORTANT]\n"
        "> Estos paquetes no traen el texto de su licencia en el wheel. Antes de\n"
        "> publicar un release hay que pegar el `LICENSE` de su repositorio de origen\n"
        "> (todas son licencias permisivas):\n>\n"
        + "\n".join(f"> {line}" for line in items.splitlines())
        + "\n\n"
    )


def main() -> None:
    rows: list[tuple[str, str, str]] = []
    bodies: list[str] = []
    incomplete: list[str] = []

    for name in runtime_packages():
        try:
            dist = metadata.distribution(name)
        except metadata.PackageNotFoundError:
            continue
        version = dist.version
        lic = license_id(dist)
        rows.append((name, version, lic))

        texts = license_texts(dist)
        if not texts and name not in SUPPLEMENT:
            incomplete.append(f"{name} ({lic})")
        bodies.append(f"### {name} {version}\n")
        bodies.append(f"Licencia: **{lic}**\n")
        home = dist.metadata.get("Home-page") or ""
        for url in dist.metadata.get_all("Project-URL", []):
            if "source" in url.lower() or "repository" in url.lower() or "homepage" in url.lower():
                home = url.split(", ", 1)[-1]
                break
        if home:
            bodies.append(f"Origen: {home}\n")
        if not texts and name in SUPPLEMENT:
            texts = [SUPPLEMENT[name]]
        if texts:
            for fname, text in texts:
                bodies.append(f"<details><summary><code>{fname}</code></summary>\n")
                bodies.append("\n```\n" + text + "\n```\n\n</details>\n")
        else:
            bodies.append(
                "_El wheel no incluye el texto de la licencia; aplica el identificador "
                "SPDX de arriba, ver el repositorio de origen._\n"
            )
        bodies.append("\n---\n")

    header = [
        "# Licencias de terceros",
        "",
        "ToMarkdown se distribuye como un binario de PyInstaller que **incluye** las",
        "librerías de Python de las que depende. Cada una conserva su propia licencia;",
        "este archivo reúne los avisos que esas licencias piden mantener al redistribuir.",
        "",
        "El código de ToMarkdown en sí está bajo MIT (ver [`LICENSE`](LICENSE)).",
        "",
        "Archivo generado: `build.spec` corre `scripts/gen_licenses.py` antes de",
        "empaquetar. No se versiona.",
        "",
        _pending_block(incomplete),
        "## Resumen",
        "",
        "| Paquete | Versión | Licencia |",
        "|---|---|---|",
    ]
    for name, version, lic in rows:
        header.append(f"| {name} | {version} | {lic} |")
    header.append("")
    header.append("---")
    header.append("")

    OUT.write_text("\n".join(header) + "\n".join(bodies) + "\n", encoding="utf-8")
    print(f"{OUT}  ({OUT.stat().st_size // 1024} KB, {len(rows)} paquetes)")


if __name__ == "__main__":
    main()
