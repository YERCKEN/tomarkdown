"""Punto de entrada: crea la ventana nativa y arranca pywebview."""

from __future__ import annotations

import logging
import os
import sys

import webview
from webview.dom import DOMEventHandler

from app.api import Api
from app.config import (
    APP_NAME,
    BACKGROUND,
    MIN_SIZE,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
    __version__,
    resource_path,
)

logger = logging.getLogger(__name__)


def _setup_logging(debug: bool) -> None:
    """Configura el logging de la app.

    Empaquetada en modo ventana no hay consola: en el `.exe` de Windows
    `sys.stderr` es `None`, y un `StreamHandler` sobre `None` falla en cada
    línea que se registre. Por eso el handler se elige en runtime.
    """
    handler: logging.Handler = (
        logging.StreamHandler(sys.stderr) if sys.stderr is not None else logging.NullHandler()
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-8s %(name)s: %(message)s"))
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        handlers=[handler],
        force=True,
    )


def _swallow(event: dict) -> None:
    """Handler vacío para dragenter/dragover.

    No hace nada por sí mismo: existe para que pywebview registre el evento con
    `prevent_default`, sin lo cual el WebView abre el archivo soltado y se sale
    de la aplicación.
    """


def _make_drag_binder(api: Api):
    """Devuelve el handler de `loaded` que suscribe los eventos de arrastre.

    Tiene que colgarse de `loaded` y no del callable de `webview.start()`: ese
    corre en un hilo apenas arranca el proceso, antes de que exista el WebView,
    y `window.dom` necesita evaluar JS. Hacerlo ahí levanta
    `WebViewException: Main window failed to start`.

    pywebview pasa la ventana a los handlers cuyo parámetro se llame `window`.
    """
    bound = False

    def on_loaded(window: webview.Window) -> None:
        nonlocal bound
        if bound:
            return

        document = window.dom.document
        document.events.dragenter += DOMEventHandler(_swallow, True, True)
        document.events.dragover += DOMEventHandler(_swallow, True, True, debounce=200)
        document.events.drop += DOMEventHandler(api.on_native_drop, True, True)
        bound = True
        logger.info("🚀 Arrastre nativo enlazado")

    return on_loaded


def _self_check(paths: list[str]) -> int:
    """Convierte sin abrir la ventana, para comprobar que el empaquetado está completo.

    Sin argumentos usa una muestra propia, que ya ejercita la parte frágil del
    bundle: la detección de tipo de markitdown carga el modelo ONNX de magika
    desde los datos empaquetados. Con argumentos convierte esos archivos.

    :param paths: Rutas a convertir. Vacío para usar la muestra interna.
    :returns: Código de salida, 0 si todo convirtió.
    """
    import tempfile

    from app.converter import ConversionError, convert

    with tempfile.TemporaryDirectory() as tmp:
        if not paths:
            sample = os.path.join(tmp, "prueba.txt")
            with open(sample, "w", encoding="utf-8") as handle:
                handle.write("# Prueba\n\nTexto con acentos: ñ á é\n")
            paths = [sample]

        failures = 0
        for path in paths:
            try:
                markdown = convert(path)
            except ConversionError as exc:
                failures += 1
                print(f"  ✗ {os.path.basename(path)}: {exc}")
            else:
                print(f"  ✓ {os.path.basename(path)}: {len(markdown)} caracteres")

    if failures:
        print(f"\n🔴 {failures} archivos fallaron")
        return 1

    print(f"\n✅ {APP_NAME} {__version__} convierte correctamente")
    return 0


def main() -> None:
    """Crea la ventana y entra en el bucle de la interfaz. Bloquea hasta cerrarla."""
    debug = os.getenv("TOMARKDOWN_DEBUG") == "1"
    _setup_logging(debug)

    if "--self-check" in sys.argv:
        rest = [arg for arg in sys.argv[1:] if arg != "--self-check"]
        raise SystemExit(_self_check(rest))

    api = Api()
    window = webview.create_window(
        APP_NAME,
        url=resource_path("web/index.html"),
        js_api=api,
        width=WINDOW_WIDTH,
        height=WINDOW_HEIGHT,
        min_size=MIN_SIZE,
        background_color=BACKGROUND,
    )
    api.attach(window)
    window.events.loaded += _make_drag_binder(api)

    logger.info("🚀 %s iniciando", APP_NAME)
    webview.start(debug=debug)


if __name__ == "__main__":
    main()
