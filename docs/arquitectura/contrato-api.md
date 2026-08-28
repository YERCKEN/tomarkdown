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
| `add_paths(paths)` | `list[FileEntry]` | Recibe rutas absolutas, descarta duplicados y formatos no soportados, y devuelve **solo las aceptadas**. |
| `get_supported_extensions()` | `list[str]` | La lista viva de extensiones. El front la usa para el estado vacío y para el mensaje de rechazo. |

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
| `save_one(file_id)` | `str \| None` | Diálogo «guardar como» con el nombre sugerido `<original>.md`. Devuelve la ruta escrita o `None` si se canceló. |
| `save_all(file_ids)` | `dict` | Diálogo de carpeta y escritura de todos los convertidos. |

`save_all` devuelve `{"folder": str, "written": int, "failed": list[str]}`.

Si ya existe un `.md` con ese nombre agrega sufijo numérico, así guardar dos
veces en la misma carpeta no pisa nada:

```
informe.md
informe-2.md
informe-3.md
```

> [!IMPORTANT]
> Solo se pueden guardar archivos en estado `done`. El resto se ignora en
> silencio en vez de fallar.

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
  "saved_to": null
}
```

`status` es uno de: `pending`, `converting`, `done`, `error`, `cancelled`.

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
| `item:done` | `{id, chars}` | Terminó bien, `chars` es el largo del Markdown |
| `item:error` | `{id, error}` | Falló, con mensaje legible |
| `queue:progress` | `{completed, total}` | Después de cada archivo |
| `queue:done` | `{completed, failed, cancelled}` | Terminó todo |
| `files:added` | `{files}` | Llegaron archivos por arrastre nativo |
| `files:rejected` | `{names}` | Se descartaron por formato no soportado |
| `save:error` | `{id, error}` | No se pudo escribir un archivo |

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
