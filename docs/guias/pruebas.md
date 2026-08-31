# Pruebas

La lógica se prueba con **`pytest`**; el binario empaquetado, con el flag
**`--self-check`** del ejecutable. Ambos corren en CI antes de publicar un
release.

```mermaid
graph TD;
    PT["pytest · tests/"] --> CONV["converter<br/>(errores + formatos reales)"];
    PT --> QR["queue_runner<br/>(orden, error, cancelación)"];
    PT --> HELP["helpers de api / config / main"];
    SELF["--self-check<br/>(sobre el binario)"] --> IMP["importa CONVERTER_IMPORTS"];
    SELF --> SAMPLES["convierte una muestra<br/>de cada formato"];
    CI["CI"] --> PT;
    CI --> SELF;
```

Los tests son deterministas: generan sus propios datos en un `tmp_path` y no
tocan la red ni la ventana.

---

## Correr los tests

| Comando | Qué hace |
|---|---|
| `uv run pytest` | Toda la suíte |
| `uv run pytest -v` | Una línea por test |
| `uv run pytest tests/test_queue_runner.py` | Un archivo |
| `uv run pytest tests/test_queue_runner.py::test_cancelacion` | Un solo test |
| `uv run pytest -k cancel` | Todos los que tengan `cancel` en el nombre |
| `uv run pytest -x` | Frena en el primer fallo |
| `uv run pytest --lf` | Solo los que fallaron la última vez |

Un test **pasa** si termina sin lanzar excepción; **falla** si un `assert` da
falso o algo revienta. No hace falta registrar ni devolver nada.

---

## Estructura de `tests/`

Un `test_<módulo>.py` por módulo de `app/`, más `conftest.py` con los fixtures
compartidos. Sin `__init__.py` (pytest los descubre por nombre).

| Archivo | Cubre |
|---|---|
| `test_converter.py` | Conversión real formato por formato (texto, `ipynb`, `xlsx`, `pptx`, PDF), un PDF roto que debe dar `ConversionError`, y la traducción de cada excepción de markitdown a su mensaje en español. |
| `test_queue_runner.py` | `QueueRunner`: procesa en orden y un archivo con error no detiene la cola; cancelar deja terminar el archivo en curso y marca el resto `cancelled`; no reprocesa lo que ya estaba `done`. |
| `test_api.py` | Helpers puros de `api.py`: `_extension`, `_first_path`, `_all_paths`, `_unique_md_path`. |
| `test_config.py` | `supported_extensions()` y `file_dialog_filter()`. |
| `test_main.py` | `_expand_paths` (carpeta → archivos ordenados) y `_self_check` (ok con una carpeta de muestras, falla con un archivo roto o una carpeta vacía); que cada nombre de `CONVERTER_IMPORTS` importe. |

### Fixtures (`conftest.py`)

| Fixture | Da |
|---|---|
| `make_pdf` | La función `minimal_pdf` de `scripts/gen_selfcheck_samples.py`: `(texto) -> bytes` con un PDF válido mínimo, sin depender de una librería de PDF. |
| `make_entries` | Una función `(n) -> dict` con `n` entradas de cola sintéticas ya normalizadas. |
| `run_queue` | Arranca `QueueRunner` con un `convert` falso (parchea `app.queue_runner.convert` con `monkeypatch`), recoge los eventos y permite un callback `during` entre el `start` y el `join` — así la cancelación se prueba en un punto exacto. |

Los builtin de pytest que más se usan acá: `tmp_path` (carpeta temporal por
test, se borra sola), `monkeypatch` (reemplaza algo y lo deshace al terminar),
`pytest.raises` (afirma que algo levanta una excepción), `pytest.importorskip`
(salta el test si falta una dependencia opcional).

---

## Agregar un test

Regla del proyecto: **toda funcionalidad nueva lleva test** (ver
[`CLAUDE.md`](../../CLAUDE.md)).

1. Abrí (o creá) `tests/test_<módulo>.py` para el módulo de `app/` que tocaste.
2. Escribí una función `def test_...():` con un nombre que describa el contrato,
   no el mecanismo.
3. Preparás el escenario, ejecutás, y `assert` sobre el resultado.
4. Si estás arreglando un bug: **primero** el test que reproduce el fallo (tiene
   que quedar en rojo), después el arreglo.
5. `uv run pytest` antes de commitear.

Ejemplo mínimo:

```python
def test_extension_ignora_mayusculas():
    from app.api import _extension

    assert _extension("/x/INFORME.PDF") == "pdf"
```

---

## `--self-check`

```bash
uv run python -m app.main --self-check
# o, sobre un bundle ya construido:
./dist/ToMarkdown.app/Contents/MacOS/ToMarkdown --self-check [archivo | carpeta ...]
```

Sin abrir la ventana, hace dos cosas:

1. **Importa** cada módulo de `CONVERTER_IMPORTS` (`app/config.py`), que son los
   que `build.spec` declara como `hiddenimports` porque los converters de
   markitdown los cargan dentro de un `try/except`. Cubre `.msg` / `olefile`,
   que no se puede generar como muestra.
2. **Convierte** archivos. Sin argumentos, una muestra de texto interna (que ya
   ejercita la carga del modelo ONNX de `magika`). Con una carpeta, cada archivo
   que tenga dentro.

Su valor está en el **binario empaquetado**: todo esto funciona siempre en
desarrollo y es lo que se rompe en un `.app` mal armado.
`scripts/gen_selfcheck_samples.py <carpeta>` arma una muestra mínima de cada
formato pesado (`pdf`, `docx`, `xlsx`, `xls`, `pptx`, …); CI genera esa carpeta
y corre `--self-check` del binario contra ella.

En Windows el ejecutable es de tipo ventana y no escribe en consola: ahí solo
cuenta el código de salida.

```bash
echo $LASTEXITCODE   # PowerShell
```

---

## En CI

[`.github/workflows/ci.yml`](../../.github/workflows/ci.yml) corre `uv run pytest`
en cada push a `develop`/`main` y en cada pull request: un test roto queda en
rojo antes de mergear.

[`.github/workflows/build.yml`](../../.github/workflows/build.yml) corre, en cada
tag `v*` y en cada runner de la matriz (`macos-latest`, `windows-latest`):

1. En un tag, valida que el nombre (sin la `v`) coincide con
   `app.config.__version__`.
2. `uv run pytest` — antes de empaquetar.
3. `pyinstaller --noconfirm build.spec`.
4. `--self-check` del binario recién construido contra la carpeta de muestras
   que arma `scripts/gen_selfcheck_samples.py`.

Si cualquiera falla, no se publica el release.

---

Anterior: [Cambiar el icono de la app](cambiar-el-icono.md) · Siguiente: [Índice](../index.md)
