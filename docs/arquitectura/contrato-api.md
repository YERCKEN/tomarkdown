# Contrato de la API

Todo lo que el front puede pedirle a Python, y todo lo que Python le informa al
front. Los métodos viven en la clase `Api` de [`app/api.py`](../../app/api.py) y
se llaman como `await pywebview.api.nombre_metodo(args)`.

No hay HTTP de por medio: pywebview serializa la llamada por su puente `js_api`
y la resuelve como promesa.

---

## Selección de archivos

| Método | Devuelve | Qué hace |
|---|---|---|
| `pick_files()` | `list[FileEntry]` | Abre el diálogo nativo con selección múltiple, filtrado por las extensiones soportadas. Lista vacía si se cancela. |
| `paste_files()` | `list[FileEntry]` | Agrega los archivos copiados en el portapapeles del sistema (`Cmd+V`/`Ctrl+V` en el front). Lee el portapapeles nativo vía `app/clipboard.py`, ya que pywebview no tiene una API propia para esto. |
| `clipboard_has_files()` | `bool` | Peek barato: si el portapapeles tiene archivos ahora mismo, sin extraer las rutas. Lo usa el front para mostrar el hint del atajo, sondeando cada pocos cientos de ms. |
| `add_paths(paths)` | `list[FileEntry]` | Recibe rutas absolutas, descarta duplicados, carpetas y formatos no soportados, y devuelve **solo las aceptadas**. |
| `get_supported_extensions()` | `list[str]` | La lista viva de extensiones. El front la usa para el estado vacío y para el mensaje de rechazo. |
| `get_app_info()` | `dict` | `{"name", "version"}` desde `app/config.py`. Lo usa la pantalla «Qué hace ToMarkdown». |

Los duplicados se detectan por `os.path.realpath`, no por nombre: dos archivos
con el mismo nombre en carpetas distintas son dos entradas.

> [!NOTE]
> `add_paths` devuelve solo lo aceptado, así que lo rechazado se informa aparte
> por el evento `files:rejected`. Si no, el arrastre nativo —que nace en Python—
> no tendría forma de contarle al front qué quedó afuera.

---

## Conversión

| Método | Devuelve | Qué hace |
|---|---|---|
| `start_conversion(file_ids)` | `None` | Arranca el hilo y retorna de inmediato. El progreso viaja por eventos. |
| `cancel_conversion()` | `None` | Marca la bandera. El archivo en curso **termina**; los pendientes pasan a `cancelled`. |
| `clear()` | `list` | Vacía la cola. Cancela primero si hay una conversión en curso. |

Los archivos que ya están en `done` no se vuelven a convertir aunque se manden
en `file_ids`.

---

## Guardado

| Método | Devuelve | Qué hace |
|---|---|---|
| `save_one(file_id)` | `str \| None` | Diálogo «guardar como» con el nombre sugerido `<original>.md`. Devuelve la ruta escrita o `None` si se canceló. Se puede llamar más de una vez por archivo: el front deja el botón disponible incluso después de guardarlo. |
| `save_all(file_ids)` | `dict` | Diálogo de carpeta y escritura de todos los convertidos. |

Los dos diálogos arrancan en la última carpeta usada para guardar, si todavía
existe (`app/settings.py`). Tras guardar, esa carpeta queda recordada.
| `reveal(file_id)` | `bool` | Abre el explorador del sistema con el `.md` ya guardado seleccionado. |

`save_all` devuelve
`{"folder": str, "written": int, "failed": list[str], "saved": dict[str, str]}`.

Si ya existe un `.md` con ese nombre agrega sufijo numérico, así guardar dos
veces en la misma carpeta no pisa nada:

```
informe.md
informe-2.md
informe-3.md
```

> [!IMPORTANT]
> Por ese sufijo el front **no puede deducir** la ruta final a partir de la
> carpeta, y por eso existe `saved`: mapea cada `id` a la ruta realmente escrita.

> [!IMPORTANT]
> Solo se pueden guardar archivos en estado `done`. El resto se ignora en
> silencio en vez de fallar.

### Revelar en el explorador

`reveal` no recibe la ruta: la lee de `saved_to` en la entrada del lado Python,
que ya guarda la ruta exacta tanto en `save_one` como en `save_all`. El front
solo manda el `id`.

| Sistema | Comando |
|---|---|
| macOS | `open -R <archivo>` |
| Windows | `explorer /select,<archivo>` |
| Otros | `xdg-open <carpeta>` |

Se lanza con una lista de argumentos y nunca con `shell=True`: los nombres
vienen del disco del usuario y traen espacios, comillas y acentos.

> [!NOTE]
> El resultado del proceso no se comprueba en ninguna plataforma, porque
> `explorer` devuelve código 1 incluso cuando abre bien. Si el archivo ya no
> está en la ruta guardada, `reveal` emite `save:error` y devuelve `False`.

---

## Forma de `FileEntry`

```json
{
  "id": "uuid4",
  "name": "informe anual.pdf",
  "path": "/Users/x/Documents/informe anual.pdf",
  "ext": "pdf",
  "size_bytes": 2481923,
  "status": "pending",
  "error": null,
  "saved_to": null,
  "zip_contents": null
}
```

`status` es uno de: `pending`, `converting`, `done`, `error`, `cancelled`.

### `zip_contents`

`null` salvo que `ext` sea `"zip"`. En ese caso, o bien `null` (el zip no se
pudo abrir con `zipfile`, está corrupto) o una lista de
`{"path": str, "status": str}`, una por cada archivo dentro del zip
(las carpetas no llevan entrada propia, se deducen de los `/` en `path`).

`status` de un miembro es uno de: `pending`, `done`, `error`, `unsupported`.
Se arma en dos tiempos, porque markitdown convierte el `.zip` entero en una
sola llamada y no expone progreso por archivo interno:

1. Al crear la entrada (`pick_files`, `on_native_drop`, `add_paths`,
   `paste_files`): cada archivo del zip queda `pending` si su extensión está
   en `SUPPORTED_EXTENSIONS`, o `unsupported` si no — sin abrir el zip de
   verdad, solo lista sus nombres.
2. Cuando el `.zip` (como entrada única) termina de convertirse: los eventos
   `item:done`/`item:error` traen `zip_contents` ya reconciliado. markitdown
   arma cada archivo incluido como una sección `## File: <nombre>`
   (`ZipConverter`); lo que sigue `pending` y no aparece ahí pasa a `error`
   (era soportado por extensión pero markitdown lo saltó igual, o el zip
   entero falló). `unsupported` no cambia: nunca se intentó.

---

## Eventos hacia el front

`queue_runner.py` los empuja con `window.run_js()`, llamando a
`window.toMarkdown.onEvent(payload)`. Se serializan con `json.dumps`, que
resuelve el escapado de las comillas y los acentos que traen los nombres de
archivo.

| Evento | Payload | Cuándo |
|---|---|---|
| `queue:start` | `{total}` | Al arrancar la cola |
| `item:start` | `{id}` | Empieza un archivo |
| `item:done` | `{id, chars, zip_contents}` | Terminó bien, `chars` es el largo del Markdown. `zip_contents` va reconciliado (ver [`zip_contents`](#zip_contents)), `null` si no es un zip |
| `item:error` | `{id, error, zip_contents}` | Falló, con mensaje legible. `zip_contents` igual que arriba: todo lo `pending` pasa a `error` |
| `queue:progress` | `{completed, total}` | Después de cada archivo |
| `queue:done` | `{completed, failed, cancelled}` | Terminó todo |
| `files:added` | `{files}` | Llegaron archivos por arrastre nativo |
| `files:rejected` | `{names, folders}` | Algo quedó afuera: `names` son archivos con formato no soportado, `folders` son carpetas soltadas. Cualquiera de los dos puede venir vacío. |
| `save:error` | `{id, error}` | No se pudo escribir un archivo, o `reveal` no encontró el guardado |

En `queue:progress`, `completed` cuenta **procesados** (convertidos más
fallidos): es lo que hace que la barra general llegue al final. En `queue:done`,
`completed` cuenta solo los que convirtieron bien.

---

## Errores legibles

`converter.py` traduce las excepciones antes de que lleguen a la interfaz. Los
mensajes explican y no se disculpan.

| Origen | Mensaje |
|---|---|
| `FileNotFoundError` | El archivo ya no está en esa ruta |
| `PermissionError` | No hay permiso para leer el archivo |
| `UnsupportedFormatException` | El convertidor no reconoce este formato |
| `MissingDependencyException` | Falta el componente para leer archivos `{ext}` |
| `FileConversionException` | No se pudo leer el archivo, puede estar dañado o protegido con contraseña |
| Cualquier otra | No se pudo convertir el archivo (`{tipo}`) |

---

Anterior: [Arquitectura](overview.md) · Siguiente: [Índice](../index.md)
