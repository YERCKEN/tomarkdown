# assets

Recursos que consume el empaquetado, no el runtime de la app.

| Archivo | Plataforma | Para qué |
|---|---|---|
| `icon.svg` | — | Fuente del icono (editable) |
| `icon.icns` | macOS | Icono del `.app` |
| `icon.ico` | Windows | Icono del `.exe` |

`build.spec` toma `icon.icns` / `icon.ico` **solo si existen**; sin ellos el
build usa el icono por defecto de PyInstaller. Se commitean (no están en
`.gitignore`).

El icono actual es la marca de Markdown ([dcurtis/markdown-mark](https://github.com/dcurtis/markdown-mark),
CC0 1.0) en blanco sobre el rojo de marca — la misma que va en el header de la
app. Para cambiarlo o regenerar los binarios desde `icon.svg`, ver
[Cambiar el icono de la app](../docs/guias/cambiar-el-icono.md).
