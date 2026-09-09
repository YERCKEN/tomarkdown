# Documentos de ejemplo

Archivos reales para probar ToMarkdown a mano: arrastrarlos a la ventana, ver la
cola convertirse, guardar los `.md`. También sirven para las capturas del
README. No los usa ningún test automático (esos generan sus datos en runtime,
ver [`docs/guias/pruebas.md`](../docs/guias/pruebas.md)); tampoco entran al
binario empaquetado.

## Qué hay

| Archivo | Qué es | Por qué sirve de prueba |
|---|---|---|
| `informe-datos.pdf` | Artículo de Wikipedia *List of countries by GDP (nominal) per capita*, exportado a PDF (8 páginas). | PDF con tablas grandes y un mapa. Ejercita `pdfminer` y muestra los límites de extraer tablas de un PDF a varias columnas. |
| `indicadores.xlsx` | Población por país y año, 1960 en adelante (16 663 filas, una hoja). | Excel con miles de filas: markitdown lo pasa a una tabla Markdown larga (~700 KB de salida). |
| `proyecto-con-carpetas.zip` | Un `.zip` con carpetas (`docs/`, `datos/`) y un archivo no soportado. | Ejercita el árbol de contenido: formatos variados, jerarquía de carpetas, y `foto.jpg` que aparece como «no soportado». |

Contenido del `.zip`:

```
datos/
├── indicadores.xlsx     (el mismo Excel de arriba)
└── indicadores.csv      (las primeras 1500 filas, en CSV)
docs/
├── capitulo.txt         (Alice's Adventures in Wonderland, capítulos I y II)
└── pagina.html          (un HTML mínimo con lista y tabla)
foto.jpg                 (imagen: formato no soportado)
```

## Fuentes y licencias

| Archivo | Fuente | Licencia | Atribución |
|---|---|---|---|
| `informe-datos.pdf` | [Wikipedia: *List of countries by GDP (nominal) per capita*](https://en.wikipedia.org/wiki/List_of_countries_by_GDP_(nominal)_per_capita), exportado con el servicio PDF de Wikimedia | CC BY-SA 4.0 | Wikipedia contributors, CC BY-SA 4.0 |
| `indicadores.xlsx` y `datos/indicadores.csv` del zip | [Our World in Data: Population](https://ourworldindata.org/grapher/population) (recortado a 1960+, convertido a `.xlsx` con `openpyxl`) | CC BY 4.0 | Our World in Data, CC BY 4.0 |
| `docs/capitulo.txt` del zip | *Alice's Adventures in Wonderland*, Lewis Carroll (1865). Texto obtenido vía [Project Gutenberg](https://www.gutenberg.org/ebooks/11), sin el encabezado ni la licencia de Project Gutenberg. | Dominio público | Obra en dominio público |
| `foto.jpg` del zip | [*The Blue Marble*](https://commons.wikimedia.org/wiki/File:The_Blue_Marble_(remastered).jpg), NASA, vía Wikimedia Commons | Dominio público (obra del gobierno de EE.UU.) | NASA |
| `docs/pagina.html` del zip | Hecho para este repo | MIT (como el resto del código) | ToMarkdown |

## Regenerar el `.xlsx`

El Excel se armó una sola vez a partir del CSV de Our World in Data:

```python
import csv
from openpyxl import Workbook

wb = Workbook()
ws = wb.active
ws.title = "Poblacion"
ws.append(["Pais", "Codigo", "Anio", "Poblacion"])
with open("population.csv", encoding="utf-8") as f:
    next(reader := csv.reader(f))
    for entity, code, year, pop in reader:
        if code and int(year) >= 1960:
            ws.append([entity, code, int(year), int(pop) if pop else None])
wb.save("indicadores.xlsx")
```
