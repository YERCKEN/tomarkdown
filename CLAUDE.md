# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Qué es

App de escritorio nativa (una ventana) que convierte documentos a Markdown con
[microsoft/markitdown](https://github.com/microsoft/markitdown). Un proceso
Python abre un WebView con **pywebview** y expone la clase `Api` directamente al
JavaScript. **No hay HTTP, ni framework de front, ni backend, ni telemetría.**
Tiene que funcionar sin conexión.

## Comandos

### Desarrollo

```bash
uv sync --extra dev                            # dependencias Python (uv, no pip)
uv run python -m app.main                       # abre la ventana
TOMARKDOWN_DEBUG=1 uv run python -m app.main    # + devtools del WebView + logs DEBUG
```

### Pruebas

`pytest`, deterministas, sin GUI. En `tests/`: un `test_<módulo>.py` por módulo
de `app/` + `conftest.py` con los fixtures compartidos (`make_pdf`,
`make_entries`, `run_queue`).

```bash
uv run pytest                                       # todo
uv run pytest tests/test_queue_runner.py            # un archivo
uv run pytest tests/test_queue_runner.py::test_cancelacion   # un caso
uv run pytest -k cancel                             # por nombre
uv run pytest -x --lf                               # frena en el primer fallo / solo los que fallaron
```

`ci.yml` corre `pytest` en cada push a `develop`/`main` y en cada PR.

Aparte, `--self-check` importa los módulos de los converters (`CONVERTER_IMPORTS`
en `config.py`, lo que va a `hiddenimports`) y convierte una muestra sin abrir la
ventana; `scripts/gen_selfcheck_samples.py` arma una carpeta con un archivo
mínimo de cada formato pesado. CI lo corre sobre el binario ya empaquetado.
`build.yml` en un tag: validar versión → `pytest` → empaquetar → generar
muestras → `--self-check <carpeta>`.

### Front (solo si tocas el CSS)

`web/dist/output.css` y `web/fonts/` **se versionan**, así empaquetar no necesita
Node. Regenerar solo tras cambiar el CSS:

```bash
npm install
npm run fonts        # copia los woff2 (subset latin) de @fontsource a web/fonts/
npm run css          # compila Tailwind v4
npm run css:watch    # idem en watch
```

### Empaquetado

```bash
uv run pyinstaller --noconfirm build.spec
```

macOS → `dist/ToMarkdown.app` (onedir dentro de un `.app`). Windows →
`dist/ToMarkdown.exe` (onefile). PyInstaller no hace cross-compile: cada binario
sale de su plataforma, por eso CI usa matriz `macos-latest` + `windows-latest` y
dispara con tags `v*`. El runner de macOS es Apple Silicon: no hay build Intel.

Para el release, `build.yml` empaqueta el `.app` en un `.dmg` (`hdiutil` + alias
a `/Applications`) y el `.exe` en un instalador de Inno Setup
(`packaging/windows/installer.iss`), más un zip portable del `.exe`.

### Verificar un bundle

```bash
/Applications/ToMarkdown.app/Contents/MacOS/ToMarkdown --self-check [archivo | carpeta ...]
```

Sin abrir la ventana: importa `CONVERTER_IMPORTS` y convierte. Sin argumentos usa
una muestra de texto interna (ejercita la carga del modelo ONNX de magika); con
una carpeta convierte cada archivo que tenga dentro.

## Arquitectura

### Las piezas y el puente

```
web/ (index.html + app.js)  --pywebview.api.metodo()-->  app/api.py (clase Api)
                            <--window.run_js(onEvent)---
                                                              |
                                          app/queue_runner.py (hilo serial)
                                                              |
                                          app/converter.py --> markitdown
```

| Módulo | Responsabilidad |
|---|---|
| `app/config.py` | **Fuente única de verdad**: nombre, `__version__`, tamaños de ventana, `SUPPORTED_EXTENSIONS`. Lo leen `main.py`, `api.py`, `build.spec` y `pyproject.toml` (hatchling). |
| `app/converter.py` | Único punto que conoce markitdown. Instancia única de `MarkItDown`, `convert_local()` (no `convert()`), traduce excepciones a `ConversionError` con mensaje en español. |
| `app/queue_runner.py` | Hilo de conversión serial y emisión de eventos al front. |
| `app/api.py` | Superficie expuesta al JS. Dueña del estado de la cola. |
| `app/main.py` | Crea la ventana, enlaza el drop nativo, ofrece `--self-check`. |

El **contrato completo** (métodos de `Api`, eventos, forma de `FileEntry`) está
en [`docs/arquitectura/contrato-api.md`](docs/arquitectura/contrato-api.md).
La arquitectura y el modelo de hilos, en
[`docs/arquitectura/overview.md`](docs/arquitectura/overview.md). Esos dos son
la referencia vigente.

### Modelo de hilos

- **Principal**: bucle nativo de la ventana. Nunca darle trabajo pesado.
- **Hilos `js_api`**: pywebview corre cada método de `Api` en su propio hilo.
  `start_conversion` lanza el hilo de la cola y retorna de inmediato.
- **Hilo de la cola** (`QueueRunner._run`): convierte un archivo a la vez y
  empuja eventos con `window.run_js()` — **no** `evaluate_js` (ese envuelve en
  `eval`, devuelve valor y da problemas desde hilos secundarios).

### Dirección única del estado

El store de Python (`Api._entries`, `Api._markdown`) es el dueño. El front
mantiene una copia que se actualiza **solo por eventos** (`onEvent`). Todo el
estado del front vive en un objeto `state`; el DOM se deriva de él, nunca al
revés. El **Markdown convertido no viaja al front**: vive en memoria de Python
indexado por `id` (un PDF grande convertido son varios MB de texto y no hay
preview).

`status` de un archivo: `pending → converting → done|error`, o
`pending → cancelled`.

### Drag & drop (la parte con trampa)

El objeto `File` del DOM no expone la ruta en disco. pywebview la inyecta del
lado nativo como `pywebviewFullPath` al suscribirse al evento `drop` desde
Python. Ese enlace va en `window.events.loaded` (**no** en el callable de
`webview.start()`, que corre antes de que exista el WebView). El `dragover` hace
`preventDefault()` en el handler de Python **y** en JS: sin eso el WebView abre
el archivo soltado y el usuario se sale de la app.

## Convenciones y restricciones

- **Offline, sin excepción.** Nada de CDN, Google Fonts ni Tailwind Play. Todo se
  sirve desde disco. Fuentes self-hosted en `web/fonts/`, iconos inline en
  `web/icons.js`.
- **`web/dist/output.css` y `web/fonts/` se commitean.** El build de PyInstaller
  no debe depender de Node.
- **Tailwind v4** con `@import "tailwindcss" source(none)` + `@source`
  explícitos en `web/src/input.css`, para que el CSS compilado sea reproducible
  y no cambie según los `.md` que haya en el repo.
- **markitdown con extras acotados**: `[pdf,docx,pptx,xlsx,xls,outlook]`, nunca
  `[all]` (arrastra audio/transcripción, cientos de MB).
- **Agregar un formato** = editar el dict `SUPPORTED_EXTENSIONS` en `config.py`
  (y, si el converter trae una dep nueva, sumarla a `CONVERTER_IMPORTS` en
  `config.py` y, si se puede generar, a `scripts/gen_selfcheck_samples.py`). El
  front pide la lista al arrancar con `get_supported_extensions()`.
- **`build.spec`**: bundlea el modelo ONNX de `magika` y las dylibs de
  `onnxruntime`; `hiddenimports = [*CONVERTER_IMPORTS, "magika", "onnxruntime"]`
  (la lista de converters vive en `config.py`, la comparte `--self-check`);
  `excludes` corta audio, notebooks y librería científica que se cuela por pandas.
- **Logging**: usar `logging` (ya configurado en `_setup_logging`), nunca
  `print` en código de app. `_setup_logging` cae a `NullHandler` cuando
  `sys.stderr is None` (el `.exe` de Windows es windowed). Mensajes con prefijo
  emoji (🚀 arranque, ✅ éxito, ⚠️ warning, 🔴 error, 🗄️ disco).
- **Front sin build de framework**: JS vanilla, `icons.js` se carga antes que
  `app.js` y expone `Icons`/`icon()` global. Las filas de la cola se cachean por
  firma (`rowSignature`) para no reiniciar la animación de barrido en cada evento
  de progreso.
- **`web/icons.js` y `web/images/YERCKEN_LOGO.svg`** son assets de runtime
  requeridos por código ya commiteado (`index.html` carga `icons.js`;
  `input.css`/`output.css` usan el SVG como máscara). Si aparecen sin trackear,
  commitearlos.
- **UI dark-only** por diseño, sin toggle de tema. Copy en español, tono directo,
  los errores explican y no se disculpan.
- **Idioma**: encabezados de docs y comentarios en español; código,
  identificadores y etiquetas de diagramas en inglés. Diagramas en Mermaid,
  ≤ 10 entidades.
- **Toda funcionalidad nueva lleva test.** Un cambio en `app/` (feature o fix)
  agrega o extiende un `test_*` en `tests/`. Para un bug, primero el test que
  reproduce el fallo (rojo), después el arreglo. Correr `uv run pytest` antes de
  cada commit. Los helpers puros se testean directo; lo que necesita ventana o
  markitdown real va con fixture o `monkeypatch` (ver `tests/conftest.py`).
- **Commits**: Conventional Commits con scope (`feat(web)`, `fix(api)`, `docs`,
  `build`, `test`, `chore`). Proyecto personal: mensajes simples, sin ISSUE-KEY,
  **sin trailer de co-autor**.
- **Changelog**: cada cambio relevante suma una línea a `[Unreleased]` en
  [`CHANGELOG.md`](CHANGELOG.md) (Keep a Changelog + SemVer). `scripts/bump_version.py`
  crea el commit y el tag de release; mover `[Unreleased]` a la sección con
  número queda a mano.
