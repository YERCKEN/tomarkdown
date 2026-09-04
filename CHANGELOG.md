# Changelog

Todos los cambios relevantes de ToMarkdown se anotan acá.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el
versionado sigue [SemVer](https://semver.org/lang/es/). Cada cambio que se
mergea a `develop` suma una línea en `[Unreleased]`; al publicar un release esas
líneas pasan a una sección con número y fecha.

## [Unreleased]

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
