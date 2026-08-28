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
    resource_path,
)

logger = logging.getLogger(__name__)


def _setup_logging(debug: bool) -> None:
    """Configura el logging de la app. En modo empaquetado no hay consola visible."""
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        stream=sys.stderr,
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


def main() -> None:
    """Crea la ventana y entra en el bucle de la interfaz. Bloquea hasta cerrarla."""
    debug = os.getenv("TOMARKDOWN_DEBUG") == "1"
    _setup_logging(debug)

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
