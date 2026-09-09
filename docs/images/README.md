# Imágenes de la documentación

Capturas usadas en el [README](../../README.md) y en la
[guía de instalación](../guias/instalacion.md).

| Archivo | Dónde se usa |
|---|---|
| `app-empty-state.png` | README (hero) y guía de instalación: la ventana recién abierta. |
| `queue-done-zip-tree.png` | README (hero): la cola convertida con el árbol de un `.zip` desplegado. |
| `instalacion/macos-*.png` | Guía de instalación: montar el `.dmg`, el aviso de Gatekeeper, quitar la cuarentena. |
| `instalacion/windows-*.jpg` | Guía de instalación: SmartScreen y el asistente de Inno Setup paso a paso. |

Las capturas de la app se toman a ~960 px de ancho (el default de la ventana),
tema oscuro, recortadas al borde de la ventana, y se bajan a ~1000 px con
`sips --resampleWidth 1000` antes de commitear.
