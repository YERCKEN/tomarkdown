# Changelog

Todos los cambios relevantes de ToMarkdown se anotan acá.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el
versionado sigue [SemVer](https://semver.org/lang/es/). Cada cambio que se
mergea a `develop` suma una línea en `[Unreleased]`; al publicar un release esas
líneas pasan a una sección con número y fecha.

## [Unreleased]

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

[Unreleased]: https://github.com/YERCKEN/tomarkdown/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/YERCKEN/tomarkdown/releases/tag/v0.1.0
