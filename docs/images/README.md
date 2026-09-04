# Imágenes del README

Capturas de la interfaz para la sección de intro del [README](../../README.md).
Faltan por hacer (issue [#14](https://github.com/YERCKEN/tomarkdown/issues/14)).

## Qué falta

| Archivo | Qué muestra |
|---|---|
| `cola-vacia.png` | La ventana recién abierta: la zona de arrastre grande con «Arrastra archivos aquí» y la lista de formatos. |
| `convirtiendo.png` | La cola con varios archivos, uno en `convirtiendo` (con el barrido rojo) y la barra general a mitad de camino. |
| `resultado.png` | La cola con todo en `done`, el botón «Guardar todo» activo. |

## Cómo tomarlas

- App real empaquetada o `uv run python -m app.main`, tema oscuro (es el único).
- Ancho de ventana ~960 px (el default). Recortar al borde de la ventana, sin
  fondo del escritorio.
- PNG. Ideal ~1400-1900 px de ancho para que se vea nítida en la tabla de 3
  columnas del README.
- Contenido de ejemplo neutro (nombres de archivo genéricos, nada personal).

## Cuando estén

1. Dejarlas en esta carpeta con esos nombres exactos.
2. Descomentar el bloque `TODO #14` en el README (arriba del `> [!NOTE]`).
3. Borrar este archivo o dejar solo la nota de que ya están.

Sin GIF: se decidió que alcanza con las tres capturas.
