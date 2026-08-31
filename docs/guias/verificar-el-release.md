# Publicar y verificar un release

Cómo cortar un release y cómo comprobar, en una máquina sin entorno de
desarrollo, que el artefacto publicado se instala y funciona como dice el
[README](../../README.md).

---

## 1. Cortar el release

```bash
uv run pytest                                   # en verde
uv run python scripts/bump_version.py minor     # major | minor | patch
```

`bump_version.py` sube `__version__` en `app/config.py`, crea el commit
`chore: release vX.Y.Z` y el tag `vX.Y.Z`. **No hace push.**

Antes de empujar:

1. Mover los cambios de `[Unreleased]` a una sección `[X.Y.Z]` con la fecha en
   [`CHANGELOG.md`](../../CHANGELOG.md) y sumar ese cambio al commit
   (`git commit --amend --no-edit`).
2. Empujar la rama y el tag:

   ```bash
   git push origin HEAD --follow-tags
   ```

El tag `vX.Y.Z` dispara [`build.yml`](../../.github/workflows/build.yml):

```mermaid
graph LR;
    TAG["tag vX.Y.Z"] --> CHK["tag == __version__"];
    CHK --> TEST["pytest"];
    TEST --> PACK["pyinstaller"];
    PACK --> SELF["--self-check<br/>(carpeta de muestras)"];
    SELF --> ART["dmg · Setup.exe · zip portable"];
    ART --> REL["release en GitHub"];
```

Si el tag no coincide con `__version__`, el workflow aborta en el primer paso.

---

## 2. Verificar en una máquina limpia

`--self-check` prueba que el bundle está completo, pero no que se instale ni que
Gatekeeper / SmartScreen se comporten como documenta el README. Eso se prueba a
mano, una vez por release, en una máquina (o VM) **sin** Python ni el repo.

Copiá el bloque de la plataforma a un comentario del issue del release y marcá
cada casilla.

### macOS

Ideal: un Mac (o VM) con **macOS 11**, que es el mínimo declarado
(`LSMinimumSystemVersion`).

- [ ] Bajar `ToMarkdown-x.y.z.dmg` desde la página de releases **con el
      navegador** (así queda con la marca de cuarentena real).
- [ ] Montar el `.dmg`: se ve `ToMarkdown.app` y el alias a `Aplicaciones`.
- [ ] Arrastrar `ToMarkdown.app` a `Aplicaciones`.
- [ ] Doble clic: aparece *«no se puede abrir porque proviene de un desarrollador
      no identificado»*.
- [ ] Clic derecho → **Abrir** → **Abrir**: la ventana abre.
- [ ] Arrastrar un `.pdf` y un `.docx` reales a la ventana y convertirlos: quedan
      en `done`.
- [ ] «Guardar todo»: el diálogo de carpeta abre y los `.md` se escriben.
- [ ] «Mostrar en el explorador» de un archivo guardado abre el Finder en su
      carpeta.
- [ ] Cerrar y reabrir con doble clic normal: ya no pide confirmación.
- [ ] En terminal:
      `/Applications/ToMarkdown.app/Contents/MacOS/ToMarkdown --self-check`
      sale con código 0.

### Windows

Ideal: Windows 11 recién instalado.

- [ ] Bajar `ToMarkdown-Setup-x.y.z.exe` con el navegador.
- [ ] Ejecutarlo: SmartScreen avisa → **Más información** → **Ejecutar de todas
      formas**.
- [ ] El instalador corre, pide elevación (UAC) e instala en Archivos de
      programa.
- [ ] Abrir **ToMarkdown** desde el menú inicio: la ventana abre.
- [ ] Convertir un `.pdf` y un `.xlsx` reales arrastrándolos a la ventana.
- [ ] «Guardar todo» y «Mostrar en el explorador» funcionan con los diálogos
      nativos.
- [ ] Desinstalar desde *Aplicaciones instaladas*: se va limpio, sin dejar la
      carpeta ni accesos.
- [ ] Aparte, probar el portable `ToMarkdown-x.y.z-portable.zip`: descomprimir y
      ejecutar `ToMarkdown.exe` sin instalar.

---

## 3. Anotar el resultado

Pegar el checklist completado como comentario en el issue del release (o en
[#4](https://github.com/YERCKEN/tomarkdown/issues/4) para la primera vuelta). Si
algún paso no salió como dice el README, corregir el README en el mismo PR que
arregle el problema.

---

Anterior: [Pruebas](pruebas.md) · Siguiente: [Índice](../index.md)
