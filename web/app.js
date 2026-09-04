/**
 * ToMarkdown: interfaz.
 *
 * Todo el estado de la cola vive en el objeto `state`. El DOM se deriva de él;
 * nunca al revés. Lo único que se guarda en un elemento es el `data-id` que
 * necesita la delegación de eventos.
 *
 * La comunicación con Python va por el puente `js_api` de pywebview:
 *   - de JS a Python:  await pywebview.api.metodo(args)
 *   - de Python a JS:  window.toMarkdown.onEvent(payload)
 */

'use strict';

// --------------------------------------------------------------------- estado

const state = {
  /** @type {Array<Object>} entradas de archivo, en orden de llegada */
  files: [],
  /** true mientras el hilo de conversión está corriendo */
  running: false,
  /** archivos procesados de la cola actual */
  completed: 0,
  /** tamaño de la cola actual */
  total: 0,
  /** extensiones soportadas, las trae Python al arrancar */
  supported: [],
  /** true mientras «Guardar todo» tiene el diálogo abierto o está escribiendo */
  savingAll: false,
  /** true mientras la pantalla «Qué hace ToMarkdown» está abierta */
  aboutOpen: false,
};

const el = {
  headerCount: document.getElementById('header-count'),
  clear: document.getElementById('btn-clear'),
  dropFull: document.getElementById('drop-full'),
  dropSlim: document.getElementById('drop-slim'),
  browseFull: document.getElementById('btn-browse-full'),
  browseSlim: document.getElementById('btn-browse-slim'),
  formats: document.getElementById('formats-full'),
  notice: document.getElementById('notice'),
  noticeText: document.getElementById('notice-text'),
  queue: document.getElementById('queue'),
  progressRow: document.getElementById('progress-row'),
  progressFill: document.getElementById('progress-fill'),
  progressLabel: document.getElementById('progress-label'),
  saveAll: document.getElementById('btn-save-all'),
  convert: document.getElementById('btn-convert'),
  about: document.getElementById('about'),
  aboutCard: document.querySelector('#about .about-card'),
  aboutBtn: document.getElementById('btn-about'),
  aboutClose: document.getElementById('btn-about-close'),
  aboutFormats: document.getElementById('about-formats'),
  aboutVersion: document.getElementById('about-version'),
  aboutPasteShortcut: document.getElementById('about-paste-shortcut'),
  linkAbout: document.getElementById('link-about'),
};

// -------------------------------------------------------------------- helpers

/** Escapa texto que viene del sistema de archivos antes de inyectarlo. */
function esc(value) {
  return String(value ?? '').replace(
    /[&<>"']/g,
    (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c],
  );
}

const numberFormat = new Intl.NumberFormat('es', { maximumFractionDigits: 1 });

/** Formatea bytes de forma corta y legible: 940 B, 180 KB, 2,4 MB. */
function formatSize(bytes) {
  if (!bytes) return '0 B';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${numberFormat.format(bytes / 1024 / 1024)} MB`;
  return `${numberFormat.format(bytes / 1024 / 1024 / 1024)} GB`;
}

/**
 * Parte un nombre en cabeza y cola para truncarlo AL MEDIO.
 * La cola nunca se recorta, así la extensión siempre queda visible.
 */
const TAIL_CHARS = 10;
function splitName(name) {
  if (name.length <= TAIL_CHARS + 6) return [name, ''];
  return [name.slice(0, -TAIL_CHARS), name.slice(-TAIL_CHARS)];
}

function find(id) {
  return state.files.find((file) => file.id === id);
}

/** Archivos que todavía tiene sentido convertir. */
function pendingFiles() {
  return state.files.filter((file) => file.status !== 'done');
}

function doneFiles() {
  return state.files.filter((file) => file.status === 'done');
}

// ---------------------------------------------------------------------- iconos
// El set vive en `icons.js`, que se carga antes que este archivo.

const ICON_OK = icon('check', 'size-3.5 shrink-0 text-ok');
const ICON_ERR = icon('x', 'size-3.5 shrink-0 text-danger');

/** Tamaño de icono de los botones chicos de la cola. */
const ROW_ICON = 'size-3.5 shrink-0';

/* El nombre del explorador cambia según el sistema, y el botón de revelar lo
   nombra en su tooltip. Se resuelve en JS y no en Python: es texto de interfaz,
   y el user agent del WebView ya distingue las dos plataformas. */
const REVEAL_LABEL = /Mac/i.test(navigator.userAgent)
  ? 'Mostrar en Finder'
  : 'Mostrar en el explorador';

/* Mismo criterio que `REVEAL_LABEL`: el atajo de pegar cambia de tecla según
   el sistema, y es texto de interfaz que no necesita ida y vuelta a Python. */
const IS_MAC = /Mac/i.test(navigator.userAgent);
const PASTE_SHORTCUT = IS_MAC ? '⌘V' : 'Ctrl+V';

// --------------------------------------------------------------------- render

/** Cache de nodos ya renderizados, para no recrear filas que no cambiaron. */
const rowCache = new Map();

function rowSignature(file) {
  // El separador es NUL y no un espacio: `saved_to` es una ruta y puede traer
  // espacios, así que un espacio produciría firmas ambiguas. Va como escape
  // `\0` y no como byte crudo, que era invisible al editar el archivo.
  // `saving` es transitorio pero visible: sin él acá la fila reusa el nodo
  // viejo y el spinner no se dibuja nunca.
  const flags = [file.status, file.error ?? '', file.saved_to ?? '', file.saving ? '1' : ''];
  return flags.join('\0');
}

/** Botón redondo de la fila, con estado de carga y nombre accesible. */
function rowButton({ action, id, iconName, label, loading }) {
  return `<button type="button" class="btn btn-ghost btn-sm btn-icon"
    data-action="${action}" data-id="${esc(id)}"
    aria-label="${esc(label)}" title="${esc(label)}"${loading ? ' data-loading aria-busy="true"' : ''}
    >${icon(iconName, ROW_ICON)}${spinnerMarkup(ROW_ICON)}</button>`;
}

/** Devuelve el HTML de la columna de estado según en qué va el archivo. */
function statusMarkup(file) {
  switch (file.status) {
    case 'converting':
      return `<span class="sweep-dot"></span>
        <span class="text-[12.5px] text-ink-muted">convirtiendo</span>`;

    // Guardado no es una etiqueta que informe un hecho consumado: es la puerta
    // al archivo en el disco.
    case 'done':
      if (file.saved_to) {
        return `${ICON_OK}${rowButton({
          action: 'reveal',
          id: file.id,
          iconName: 'folderOpen',
          label: REVEAL_LABEL,
          loading: false,
        })}`;
      }
      return `${ICON_OK}${rowButton({
        action: 'save',
        id: file.id,
        iconName: 'download',
        label: 'Guardar como…',
        loading: Boolean(file.saving),
      })}`;

    case 'error':
      return `${ICON_ERR}<span class="truncate text-[12.5px] text-danger"
        title="${esc(file.error)}">${esc(file.error)}</span>`;

    case 'cancelled':
      return `<span class="text-[12.5px] text-ink-dim">cancelado</span>`;

    default:
      return `<span class="text-[12.5px] text-ink-dim">en espera</span>`;
  }
}

function buildRow(file) {
  const [head, tail] = splitName(file.name);
  const row = document.createElement('li');
  row.className =
    'flex items-center gap-3 border-b border-line-soft px-5 py-2.5 transition-colors duration-150';
  if (file.status === 'converting') row.classList.add('row-active');

  row.innerHTML = `
    <span class="ext-badge">${esc(file.ext)}</span>
    <span class="filename min-w-0 flex-1 text-[13px] text-ink" title="${esc(file.name)}"
      ><span class="filename-head">${esc(head)}</span
      ><span class="filename-tail">${esc(tail)}</span></span>
    <span class="w-16 shrink-0 text-right font-mono text-[11.5px] text-ink-dim tabular-nums"
      >${esc(formatSize(file.size_bytes))}</span>
    <span class="flex w-44 shrink-0 items-center justify-end gap-2 overflow-hidden"
      >${statusMarkup(file)}</span>`;

  return row;
}

function renderQueue() {
  const hasFiles = state.files.length > 0;
  el.queue.hidden = !hasFiles;
  el.dropFull.hidden = hasFiles;
  el.dropSlim.hidden = !hasFiles;

  if (!hasFiles) {
    rowCache.clear();
    el.queue.replaceChildren();
    return;
  }

  const seen = new Set();
  const nodes = state.files.map((file) => {
    seen.add(file.id);
    const signature = rowSignature(file);
    const cached = rowCache.get(file.id);

    // Reusar el nodo evita que el barrido de la fila activa se reinicie en
    // cada evento de progreso de la cola.
    if (cached && cached.signature === signature) return cached.node;

    const node = buildRow(file);
    rowCache.set(file.id, { signature, node });
    return node;
  });

  for (const id of rowCache.keys()) {
    if (!seen.has(id)) rowCache.delete(id);
  }

  el.queue.replaceChildren(...nodes);
}

function renderControls() {
  const count = state.files.length;
  const ready = doneFiles().length;

  el.headerCount.textContent = count === 0 ? '' : count === 1 ? '1 archivo' : `${count} archivos`;
  el.clear.disabled = count === 0 || state.running;
  el.saveAll.disabled = ready === 0 || state.running;

  // `className` se reasigna entero, así que el contenido también se rehace acá:
  // si el icono quedara solo en el HTML, el primer render lo borraría.
  if (state.running) {
    el.convert.className = 'btn btn-ghost';
    el.convert.innerHTML = `${icon('x')}Cancelar`;
    el.convert.disabled = false;
  } else {
    el.convert.className = 'btn btn-primary';
    el.convert.innerHTML = `${icon('arrowRight')}Convertir`;
    el.convert.disabled = pendingFiles().length === 0;
  }

  // `aria-busy` es enumerado: quiere "true"/"false", no un atributo vacío.
  el.saveAll.toggleAttribute('data-loading', state.savingAll);
  el.saveAll.setAttribute('aria-busy', String(state.savingAll));

  el.progressRow.hidden = state.total === 0;
  if (state.total > 0) {
    const ratio = Math.min(1, state.completed / state.total);
    el.progressFill.style.width = `${ratio * 100}%`;
    el.progressLabel.textContent = `${state.completed} de ${state.total}`;
  }
}

function render() {
  renderQueue();
  renderControls();
}

// --------------------------------------------------------------------- avisos

let noticeTimer = null;

function showNotice(text) {
  el.noticeText.textContent = text;
  el.notice.hidden = false;
  clearTimeout(noticeTimer);
  noticeTimer = setTimeout(() => {
    el.notice.hidden = true;
  }, 8000);
}

/** Enumera hasta 3 nombres y resume el resto: «a, b, c y 2 más». */
function nameList(names) {
  const head = names.slice(0, 3).join(', ');
  const rest = names.length > 3 ? ` y ${names.length - 3} más` : '';
  return `${head}${rest}`;
}

/**
 * Aviso de lo que quedó afuera al soltar o elegir archivos. `names` son
 * archivos con formato no soportado; `folders` son carpetas (que no se
 * convierten). Cualquiera de los dos puede venir vacío o ausente.
 */
function reportRejected(names, folders) {
  const parts = [];

  if (folders && folders.length > 0) {
    const plural = folders.length === 1 ? 'Esta carpeta no' : 'Estas carpetas no';
    parts.push(`${plural} se puede convertir: ${nameList(folders)}. Soltá los archivos que tiene adentro.`);
  }

  if (names && names.length > 0) {
    const plural = names.length === 1 ? 'Este formato no' : 'Estos formatos no';
    parts.push(
      `${plural} se puede convertir: ${nameList(names)}. Formatos admitidos: ${state.supported.join(', ')}.`,
    );
  }

  if (parts.length > 0) showNotice(parts.join(' '));
}

// ------------------------------------------------------- eventos desde Python

/**
 * Punto de entrada de los eventos que empuja `queue_runner.py` con `run_js`.
 * Se define antes de cualquier llamada para que nunca llegue un evento a un
 * objeto inexistente.
 */
window.toMarkdown = {
  onEvent(payload) {
    switch (payload.event) {
      case 'files:added':
        addFiles(payload.files);
        return;

      case 'files:rejected':
        reportRejected(payload.names, payload.folders);
        return;

      case 'queue:start':
        state.running = true;
        state.total = payload.total;
        state.completed = 0;
        break;

      case 'item:start': {
        const file = find(payload.id);
        if (file) {
          file.status = 'converting';
          file.error = null;
        }
        break;
      }

      case 'item:done': {
        const file = find(payload.id);
        if (file) {
          file.status = 'done';
          file.error = null;
        }
        break;
      }

      case 'item:error': {
        const file = find(payload.id);
        if (file) {
          file.status = 'error';
          file.error = payload.error;
        }
        break;
      }

      case 'queue:progress':
        state.completed = payload.completed;
        state.total = payload.total;
        break;

      case 'queue:done':
        state.running = false;
        // El runner ya marcó los pendientes como cancelados en su store;
        // el front alinea el suyo. El archivo en curso alcanza a terminar, así
        // que a esta altura ya no queda ninguno en `converting`.
        if (payload.cancelled > 0) {
          for (const file of state.files) {
            if (file.status === 'pending' || file.status === 'converting') {
              file.status = 'cancelled';
            }
          }
        }
        break;

      case 'save:error':
        showNotice(payload.error);
        return;

      default:
        return;
    }

    render();
  },
};

// ------------------------------------------------------------------- acciones

function addFiles(entries) {
  if (!entries || entries.length === 0) return;
  state.files.push(...entries);
  render();
}

async function browse() {
  try {
    addFiles(await window.pywebview.api.pick_files());
  } catch (error) {
    showNotice('No se pudo abrir el selector de archivos');
    console.error(error);
  }
}

/** Pega los archivos copiados en el portapapeles del sistema, si hay alguno. */
async function pasteFiles() {
  try {
    addFiles(await window.pywebview.api.paste_files());
  } catch (error) {
    showNotice('No se pudo leer el portapapeles');
    console.error(error);
  }
}

async function convertOrCancel() {
  if (state.running) {
    await window.pywebview.api.cancel_conversion();
    return;
  }

  const ids = pendingFiles().map((file) => file.id);
  if (ids.length === 0) return;

  // Optimismo mínimo: el botón cambia ya, el resto lo dictan los eventos.
  state.running = true;
  state.total = ids.length;
  state.completed = 0;
  for (const file of pendingFiles()) {
    file.status = 'pending';
    file.error = null;
  }
  render();

  await window.pywebview.api.start_conversion(ids);
}

async function saveOne(id) {
  const file = find(id);
  if (!file || file.saving) return;

  // El diálogo nativo bloquea del lado de Python, no acá: sin esta marca la
  // fila se queda muda todo el tiempo que el usuario pasa eligiendo carpeta.
  file.saving = true;
  render();

  try {
    const path = await window.pywebview.api.save_one(id);
    if (path) file.saved_to = path;
  } finally {
    file.saving = false;
    render();
  }
}

/** Abre el explorador del sistema con el `.md` ya guardado seleccionado. */
async function reveal(id) {
  await window.pywebview.api.reveal(id);
}

async function saveAll() {
  if (state.savingAll) return;

  const ids = doneFiles().map((file) => file.id);
  if (ids.length === 0) return;

  state.savingAll = true;
  render();

  let result;
  try {
    result = await window.pywebview.api.save_all(ids);
  } finally {
    state.savingAll = false;
    render();
  }

  if (!result || !result.folder) return;

  // `saved` trae la ruta real de cada archivo. Guardar la carpeta en su lugar
  // dejaba al front con un dato que no sirve para revelar ni para el tooltip.
  const saved = result.saved || {};
  for (const file of doneFiles()) {
    if (saved[file.id]) file.saved_to = saved[file.id];
  }
  render();

  const written = result.written === 1 ? '1 archivo' : `${result.written} archivos`;
  if (result.failed && result.failed.length > 0) {
    showNotice(`Se guardaron ${written}. No se pudo escribir: ${result.failed.join(', ')}.`);
  } else {
    showNotice(`Se guardaron ${written} en ${result.folder}`);
  }
}

async function clearQueue() {
  await window.pywebview.api.clear();
  state.files = [];
  state.running = false;
  state.completed = 0;
  state.total = 0;
  el.notice.hidden = true;
  render();
}

// ------------------------------------------------------ pantalla «qué hace»

function openAbout() {
  if (state.aboutOpen) return;
  state.aboutOpen = true;
  el.about.hidden = false;
  // Foco a la tarjeta: es scrolleable, así el teclado puede recorrer el texto.
  el.aboutCard.focus();
}

function closeAbout() {
  if (!state.aboutOpen) return;
  state.aboutOpen = false;
  el.about.hidden = true;
  // El foco vuelve a lo que abrió la pantalla, no se pierde en el body.
  el.aboutBtn.focus();
}

/**
 * Cicla el foco dentro del overlay con Tab / Shift+Tab: sin esto el foco se
 * escapa a la ventana de atrás, que está tapada.
 */
function trapAboutFocus(event) {
  if (event.key !== 'Tab') return;
  const nodes = el.about.querySelectorAll('[tabindex="0"], button, a[href]');
  if (nodes.length === 0) return;

  const first = nodes[0];
  const last = nodes[nodes.length - 1];
  const active = document.activeElement;

  // Si el foco se escapó de la tarjeta (p. ej. un click en el texto), se vuelve.
  if (!el.about.contains(active)) {
    event.preventDefault();
    first.focus();
  } else if (event.shiftKey && active === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && active === last) {
    event.preventDefault();
    first.focus();
  }
}

// --------------------------------------------------------------------- enlace

el.browseFull.addEventListener('click', browse);
el.browseSlim.addEventListener('click', browse);
el.convert.addEventListener('click', convertOrCancel);
el.saveAll.addEventListener('click', saveAll);
el.clear.addEventListener('click', clearQueue);

el.aboutBtn.addEventListener('click', openAbout);
el.linkAbout.addEventListener('click', openAbout);
el.aboutClose.addEventListener('click', closeAbout);
el.about.addEventListener('click', (event) => {
  // Click en el fondo (no dentro de la tarjeta) cierra.
  if (event.target === el.about) closeAbout();
});

document.addEventListener('keydown', (event) => {
  if (state.aboutOpen) {
    if (event.key === 'Escape') closeAbout();
    else trapAboutFocus(event);
    return;
  }

  const isPaste = (IS_MAC ? event.metaKey : event.ctrlKey) && event.key.toLowerCase() === 'v';
  if (isPaste) pasteFiles();
});

// Punto de entrada por si un menú nativo quiere abrir la pantalla.
window.toMarkdown.openAbout = openAbout;

el.queue.addEventListener('click', (event) => {
  const button = event.target.closest('[data-action]');
  if (!button) return;

  if (button.dataset.action === 'save') saveOne(button.dataset.id);
  else if (button.dataset.action === 'reveal') reveal(button.dataset.id);
});

/*
 * Arrastre. Las rutas reales las entrega pywebview del lado Python
 * (`pywebviewFullPath`); acá solo se maneja el resaltado visual.
 *
 * El preventDefault de dragover es obligatorio: sin él el WebView abre el
 * archivo soltado y el usuario se sale de la aplicación. pywebview ya lo hace
 * en su handler, esto es el cinturón además de los tirantes.
 */
let dragDepth = 0;

function highlightDrop(active) {
  for (const zone of [el.dropFull, el.dropSlim]) {
    // El punteado ya no es un `border`, lo dibuja una máscara SVG: el color va
    // por la variable que lee `.dashed-zone::before`.
    zone.classList.toggle('is-dragging', active);
    zone.classList.toggle('bg-primary-dim', active);
  }
}

document.addEventListener('dragover', (event) => event.preventDefault());

document.addEventListener('dragenter', (event) => {
  event.preventDefault();
  dragDepth += 1;
  highlightDrop(true);
});

document.addEventListener('dragleave', () => {
  dragDepth = Math.max(0, dragDepth - 1);
  if (dragDepth === 0) highlightDrop(false);
});

document.addEventListener('drop', (event) => {
  event.preventDefault();
  dragDepth = 0;
  highlightDrop(false);
});

// -------------------------------------------------------------------- arranque

async function init() {
  // Antes del primer render: los botones estáticos del HTML declaran su icono
  // con `data-icon` y es acá donde reciben el SVG.
  hydrateIcons();

  const [info, supported] = await Promise.all([
    window.pywebview.api.get_app_info(),
    window.pywebview.api.get_supported_extensions(),
  ]);

  state.supported = supported;
  const formatsText = supported.join(' · ');
  el.formats.textContent = formatsText;
  el.aboutFormats.textContent = formatsText;
  el.aboutVersion.textContent = `v${info.version}`;
  el.aboutPasteShortcut.textContent = PASTE_SHORTCUT;

  render();
}

// pywebview inyecta `window.pywebview.api` y luego dispara `pywebviewready`.
// Si el puente ya estaba listo cuando corre este script, el evento no vuelve.
if (window.pywebview && window.pywebview.api) {
  init();
} else {
  window.addEventListener('pywebviewready', init, { once: true });
}
