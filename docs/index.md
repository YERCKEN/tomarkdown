# Documentación de ToMarkdown

Documentación técnica del proyecto. Para instalar y usar la app, el punto de
entrada es el [README](../README.md).

---

## Contenido

| Página | Qué cubre |
|---|---|
| [Arquitectura](arquitectura/overview.md) | Las piezas, el modelo de hilos y por qué la conversión es serial |
| [Contrato de la API](arquitectura/contrato-api.md) | Métodos expuestos al JavaScript, eventos y forma de `FileEntry` |

---

## Guías

| Guía | Qué resuelve |
|---|---|
| [Cambiar el icono de la app](guias/cambiar-el-icono.md) | Reemplazar el icono por defecto de PyInstaller en el `.app` y el `.exe` |
| [Pruebas](guias/pruebas.md) | Cómo se corre `pytest`, qué cubre `tests/` y `--self-check`, y cómo agregar un test |

Cómo arrancar la app en desarrollo (terminal o VSCode) está en el
[README](../README.md#desarrollo).

---

## Mapa rápido

```mermaid
mindmap
  root((ToMarkdown))
    Python
      config
      converter
      queue_runner
      api
      main
    Front
      index.html
      app.js
      Tailwind v4
    Empaquetado
      build.spec
      GitHub Actions
    Guías
      Icono de la app
      Pruebas
```

---

## Convenciones

- Los **encabezados** van en español; el **código, los identificadores y las
  etiquetas de los diagramas** en inglés.
- Los diagramas se escriben en **Mermaid** y se mantienen por debajo de diez
  entidades. Si uno crece, se parte en varios por dominio.
- Cada decisión no obvia se documenta con su **porqué**, no solo con el qué.

---

Siguiente: [Arquitectura](arquitectura/overview.md)
