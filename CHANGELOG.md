# Changelog

Todos los cambios relevantes de ToMarkdown se anotan acá.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el
versionado sigue [SemVer](https://semver.org/lang/es/). Cada cambio que se
mergea a `develop` suma una línea en `[Unreleased]`; al publicar un release esas
líneas pasan a una sección con número y fecha.

## [Unreleased]

### Added

- Soltar (o elegir) una **carpeta** ahora avisa en vez de ignorarla en silencio;
  el aviso distingue carpetas de formatos no soportados.
- El diálogo de **guardar** arranca en la última carpeta usada y la recuerda
  (`settings.json`, un solo valor, en el dir de config del SO). Nuevo módulo
  `app/settings.py`.
- `ruff` (lint + formato) configurado y corriendo en CI (`ci.yml`).
- Pegar archivos con **`Cmd+V`/`Ctrl+V`**, además de arrastrar o «Examinar».
  Nuevo módulo `app/clipboard.py` (lee el portapapeles nativo del SO, ya que
  pywebview no expone esto), con `pyobjc`/`pywin32` como dependencias
  condicionadas por plataforma. Un hint junto al cursor avisa cuando hay algo
  pegable.
- Cada fila de la cola muestra un **chip de color** según su estado, y las
  filas terminadas suman un lavado verde tenue.
- Una vez guardado, el botón de **volver a guardar** queda disponible junto a
  «Mostrar en el explorador», en vez de reemplazarlo.
- Con algo copiado en el portapapeles, la zona de arrastre muestra un
  **spotlight** rojo sutil que sigue al cursor; el hint y el spotlight solo
  aparecen mientras el cursor está sobre la zona.
- **Tooltip** para todos los botones icon-only (ayuda, limpiar cola, cerrar,
  guardar/revelar de cada fila), con el mismo texto que ya tenían como
  `aria-label`.
- La ayuda («¿Qué hace ToMarkdown?») aclara que un `.zip` termina en un
  **único** `.md`, no en uno por archivo interno.
- La fila de un `.zip` puede desplegar el **árbol de su contenido** (carpetas y
  archivos), con el estado de cada archivo interno: `en espera`/`no soportado`
  antes de convertir (según su extensión), y `listo`/`error` una vez que el
  zip entero termina (markitdown no expone progreso por archivo interno, así
  que es un salto de estado, no una barra en vivo).

### Changed

- El aviso de archivos rechazados suma margen respecto del footer y un tinte
  rojo sutil (antes quedaba pegado, sin ningún acento visual).

### Tests

- `test_api.py` cubre `on_native_drop`, el ciclo de estado de `start_conversion`
  y `save_all` (fixture `fake_window`). Nuevo `test_settings.py`.
- Nuevo `test_clipboard.py`: dispatch por plataforma y manejo de errores del
  portapapeles nativo.

## [0.2.0] - 2026-09-03

Pipeline de publicación endurecido. Verificado en Windows 11 y en dos Macs con
Apple Silicon (ver issue #4).

### Added

- Workflow `ci.yml`: `pytest` en cada push a `develop`/`main` y en cada pull
  request.
- `build.yml` valida, en un tag, que `vX.Y.Z` coincide con `__version__`.
- `--self-check` importa los módulos de los converters (`CONVERTER_IMPORTS`) y
  acepta carpetas; `scripts/gen_selfcheck_samples.py` arma una muestra mínima de
  cada formato pesado y CI corre `--self-check` del binario contra ella.
- `scripts/bump_version.py`: sube `__version__`, y deja el commit y el tag de
  release listos (sin push).
- Guía [Publicar y verificar un release](docs/guias/verificar-el-release.md) con
  el checklist de instalación en máquina limpia.

### Changed

- El release de macOS es un `.dmg` (con alias a `/Applications`) en vez de un zip
  con el `.app` suelto.
- El release de Windows suma un instalador de Inno Setup
  (`packaging/windows/installer.iss`) junto al zip portable del `.exe`.

## [0.1.0] - 2026-08-31

Primera versión publicada.

### Added

- Conversión de documentos a Markdown con
  [microsoft/markitdown](https://github.com/microsoft/markitdown), en una app de
  escritorio nativa de una sola ventana (pywebview), sin HTTP, sin backend y sin
  telemetría.
- Arrastrar y soltar archivos con rutas reales del disco, más un diálogo nativo
  de selección múltiple.
- Cola de conversión serial: un archivo a la vez, con barra general determinada
  y animación indeterminada en la fila activa. Un archivo con error no detiene
  la cola; la cancelación deja terminar el archivo en curso.
- Guardado de los `.md`: uno por uno («guardar como») o todos juntos en una
  carpeta, con sufijo numérico para no pisar archivos. «Mostrar en el
  explorador» del archivo guardado.
- Formatos soportados: `pdf`, `docx`, `pptx`, `xlsx`, `xls`, `msg`, `epub`,
  `html`, `htm`, `xml`, `json`, `csv`, `txt`, `md`, `markdown`, `ipynb`, `zip`.
- Interfaz dark, copy en español, mensajes de error que explican y no se
  disculpan. Pantalla «Qué hace ToMarkdown».
- `--self-check`: convierte una muestra sin abrir la ventana, para verificar un
  bundle empaquetado.
- Empaquetado con PyInstaller: `.app` para macOS (Apple Silicon) y `.exe` para
  Windows, publicados por GitHub Actions al taggear `v*`.
- Icono propio del binario y `THIRD-PARTY-LICENSES.md` generado al empaquetar.

### Known limitations

- El binario de macOS es solo para Apple Silicon.
- Ni el `.app` ni el `.exe` están firmados con una cuenta de desarrollador.

[Unreleased]: https://github.com/YERCKEN/tomarkdown/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/YERCKEN/tomarkdown/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/YERCKEN/tomarkdown/releases/tag/v0.1.0
