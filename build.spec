# -*- mode: python ; coding: utf-8 -*-
"""Configuración de PyInstaller para ToMarkdown.

Un solo spec para las dos plataformas. PyInstaller no hace cross compile: el
`.app` sale de macOS y el `.exe` de Windows, por eso el workflow de CI usa una
matriz con los dos runners.

  macOS   -> one folder dentro de un `.app` (arranca más rápido y es lo que
             hace falta para poder firmar bien)
  Windows -> one file

Uso: uv run pyinstaller build.spec
"""

import subprocess
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

ROOT = Path(SPECPATH)  # noqa: F821 - PyInstaller lo inyecta
sys.path.insert(0, str(ROOT))

from app.config import APP_ID, APP_NAME, CONVERTER_IMPORTS, __version__  # noqa: E402

IS_MACOS = sys.platform == "darwin"

# Icono propio del binario. Se toma solo si el archivo existe, así el build
# sigue funcionando sin `assets/` (usa el icono por defecto de PyInstaller).
# Cómo generarlos: docs/guias/cambiar-el-icono.md
_icns = ROOT / "assets" / "icon.icns"
_ico = ROOT / "assets" / "icon.ico"
ICON_MAC = str(_icns) if _icns.exists() else None
ICON_WIN = str(_ico) if _ico.exists() else None

# El front completo: index.html, el CSS compilado y las fuentes woff2. Sin esto
# la ventana abre en blanco.
datas = [(str(ROOT / "web"), "web")]

# Avisos de licencia de las librerías que el bundle incluye (MIT / BSD /
# Apache-2.0 / PSF piden mantener el aviso al redistribuir). Se genera acá y no
# se versiona: refleja lo que hay instalado al momento de empaquetar.
_licenses = ROOT / "THIRD-PARTY-LICENSES.md"
subprocess.run([sys.executable, str(ROOT / "scripts" / "gen_licenses.py")], check=True)
datas += [(str(_licenses), ".")]

# markitdown usa magika para detectar el tipo de archivo, y magika carga un
# modelo ONNX desde el paquete. Sin estos datos la conversión falla en runtime
# dentro del bundle aunque funcione perfecto en desarrollo.
datas += collect_data_files("magika")

binaries = collect_dynamic_libs("onnxruntime")

# Dependencias que los converters de markitdown importan dentro de try/except.
# Se declaran a mano para que el análisis estático no las descarte. La lista de
# converters vive en app/config.py (la comparte --self-check); magika y
# onnxruntime son del núcleo de markitdown.
hiddenimports = [*CONVERTER_IMPORTS, "magika", "onnxruntime"]

# markitdown[all] arrastraría audio y transcripción; acá además se cortan las
# librerías científicas y de notebooks que se cuelan por pandas.
excludes = [
    "tkinter",
    "matplotlib",
    "IPython",
    "jupyter",
    "notebook",
    "pytest",
    "sphinx",
    "pydub",
    "speech_recognition",
    "youtube_transcript_api",
]

analysis = Analysis(  # noqa: F821
    [str(ROOT / "app" / "main.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(analysis.pure)  # noqa: F821

if IS_MACOS:
    exe = EXE(  # noqa: F821
        pyz,
        analysis.scripts,
        [],
        exclude_binaries=True,
        name=APP_NAME,
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )

    collected = COLLECT(  # noqa: F821
        exe,
        analysis.binaries,
        analysis.datas,
        strip=False,
        upx=False,
        upx_exclude=[],
        name=APP_NAME,
    )

    app = BUNDLE(  # noqa: F821
        collected,
        name=f"{APP_NAME}.app",
        icon=ICON_MAC,
        bundle_identifier=APP_ID,
        version=__version__,
        info_plist={
            "CFBundleName": APP_NAME,
            "CFBundleDisplayName": APP_NAME,
            "CFBundleShortVersionString": __version__,
            "CFBundleVersion": __version__,
            "LSMinimumSystemVersion": "11.0",
            "NSHighResolutionCapable": True,
            # La interfaz es dark only por diseño, pero la ventana nativa tiene
            # que seguir al sistema en vez de forzar apariencia clara.
            "NSRequiresAquaSystemAppearance": False,
        },
    )
else:
    exe = EXE(  # noqa: F821
        pyz,
        analysis.scripts,
        analysis.binaries,
        analysis.datas,
        [],
        name=APP_NAME,
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=ICON_WIN,
    )
