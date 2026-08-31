/**
 * ToMarkdown — set de iconos.
 *
 * Todo va inline en el repo: la app tiene que funcionar con el wifi apagado, así
 * que no hay CDN ni fuente de iconos. Se carga como script clásico ANTES de
 * `app.js` y expone `Icons` e `icon()` en el ámbito global.
 *
 * ---------------------------------------------------------------------------
 * Iconos de trazo: Lucide — https://lucide.dev
 * ISC License · Copyright (c) 2022 Lucide Contributors
 *
 * Permission to use, copy, modify, and/or distribute this software for any
 * purpose with or without fee is hereby granted, provided that the above
 * copyright notice and this permission notice appear in all copies.
 *
 * THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
 * REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
 * AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
 * INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
 * LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR
 * OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
 * PERFORMANCE OF THIS SOFTWARE.
 *
 * Marca de Markdown: https://github.com/dcurtis/markdown-mark — CC0 1.0
 * (dominio público, sin atribución obligatoria).
 * ---------------------------------------------------------------------------
 */

'use strict';

/**
 * Cuerpo de cada icono. Los de Lucide comparten viewBox 24 y trazo; la marca de
 * Markdown es de relleno y trae su propio viewBox, por eso el valor puede ser
 * un objeto en vez de una cadena.
 */
const Icons = {
  // Lucide — trazo, viewBox 24.
  check: `<path d="m4 12 5 5L20 6"/>`,
  x: `<path d="M6 6 18 18M18 6 6 18"/>`,
  info: `<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>`,
  helpCircle: `<circle cx="12" cy="12" r="9"/><path d="M9.2 9.2a3 3 0 0 1 5.6 1c0 2-3 2.4-3 3.8"/><path d="M12 17h.01"/>`,
  trash2: `<path d="M3 6h18M8 6V4a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2"/><path d="M19 6v14a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V6"/><path d="M10 11v6M14 11v6"/>`,
  download: `<path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M3 17v2a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-2"/>`,
  folderOpen: `<path d="m6 20 3-8h13l-3 8a1 1 0 0 1-1 .7H7a2 2 0 0 1-2-2V5a1 1 0 0 1 1-1h4l2 3h6a1 1 0 0 1 1 1v3"/>`,
  arrowRight: `<path d="M4 12h15"/><path d="m13 6 6 6-6 6"/>`,
  // El anillo abierto es lo que hace legible el giro: un círculo completo se ve
  // quieto por más que rote.
  loader: `<path d="M21 12a9 9 0 1 1-6.2-8.6"/>`,

  // Marca oficial de Markdown (CC0), tal cual la publica dcurtis/markdown-mark:
  // el marco es trazo y la M con la flecha es relleno. No es cuadrada, 208x128.
  markdown: {
    viewBox: '0 0 208 128',
    fill: true,
    body: `<rect x="5" y="5" width="198" height="118" ry="10" fill="none" stroke="currentColor" stroke-width="10"/><path d="M30 98V30h20l20 25 20-25h20v68H90V59L70 84 50 59v39zM155 98l-30-33h20V30h20v35h20z"/>`,
  },
};

/**
 * Devuelve el markup de un icono.
 *
 * @param {string} name Clave de `Icons`.
 * @param {string} [className] Clases del `<svg>`. Por omisión, el tamaño de fila.
 * @returns {string} El SVG listo para inyectar, o cadena vacía si no existe.
 */
function icon(name, className = 'size-4 shrink-0') {
  const entry = Icons[name];
  if (!entry) return '';

  const spec = typeof entry === 'string' ? { body: entry } : entry;
  const viewBox = spec.viewBox ?? '0 0 24 24';

  // Los de relleno pintan con `currentColor`; los de trazo no llevan relleno y
  // heredan el color por el `stroke`.
  const paint = spec.fill
    ? 'fill="currentColor"'
    : 'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"';

  return `<svg class="${className}" viewBox="${viewBox}" ${paint} aria-hidden="true">${spec.body}</svg>`;
}

/** Spinner de los botones en estado de carga. Lo esconde el CSS salvo con `data-loading`. */
function spinnerMarkup(className = 'size-4 shrink-0') {
  return icon('loader', `btn-spinner ${className}`);
}

/**
 * Rellena los `[data-icon]` del HTML estático con su SVG.
 *
 * Se hace acá y no en el markup para que el set de iconos viva en un solo lugar
 * y `index.html` siga siendo legible. Los botones reciben además el nodo del
 * spinner, que el CSS revela cuando llega `data-loading`.
 */
function hydrateIcons(root = document) {
  for (const node of root.querySelectorAll('[data-icon]')) {
    const size = node.dataset.iconSize || 'size-4 shrink-0';
    const markup = icon(node.dataset.icon, size);

    if (node.tagName === 'BUTTON') {
      node.insertAdjacentHTML('afterbegin', markup + spinnerMarkup(size));
    } else {
      node.innerHTML = markup;
    }
  }
}
