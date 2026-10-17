/**
 * ==========================================================
 * APP.JS - Controladores Globales, Filtros, Tema y Arranque
 * ==========================================================
 */

// Notificaciones Toast
const toastNotification = document.getElementById('toastNotification');
const toastMsg = document.getElementById('toastMsg');
let toastTimer = null;

/**
 * Muestra un mensaje flotante tipo toast
 * @param {string} message 
 */
function showToast(message) {
  if (!toastNotification || !toastMsg) return;
  toastMsg.textContent = message;
  toastNotification.classList.remove('translate-y-20', 'opacity-0');
  toastNotification.classList.add('translate-y-0', 'opacity-100');

  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    toastNotification.classList.remove('translate-y-0', 'opacity-100');
    toastNotification.classList.add('translate-y-20', 'opacity-0');
  }, 2800);
}

// ==========================================================
// INTERRUPTORES DE COLOR DE CELDAS: VIRAL / 60-40 DIAG / PIE %
// ==========================================================
const viewModeViralBtn = document.getElementById('viewModeViralBtn');
const viewModeSplitDiagBtn = document.getElementById('viewModeSplitDiagBtn');
const viewModeSplitPieBtn = document.getElementById('viewModeSplitPieBtn');

function setActiveColorModeBtn(activeBtn) {
  [viewModeViralBtn, viewModeSplitDiagBtn, viewModeSplitPieBtn].forEach(btn => {
    if (!btn) return;
    if (btn === activeBtn) {
      btn.className = 'px-2 py-0.5 rounded bg-stone-800 text-white font-mono text-[9px] font-semibold transition flex items-center gap-1';
    } else {
      btn.className = 'px-2 py-0.5 rounded text-stone-600 hover:text-stone-900 font-mono text-[9px] transition flex items-center gap-1';
    }
  });
}

if (viewModeViralBtn) {
  viewModeViralBtn.addEventListener('click', () => {
    currentTileViewMode = 'viral';
    setActiveColorModeBtn(viewModeViralBtn);
    renderMatrix();
    showToast('Color: Score de Viralidad (Verde / Rojo con pips)');
  });
}

if (viewModeSplitDiagBtn) {
  viewModeSplitDiagBtn.addEventListener('click', () => {
    currentTileViewMode = 'split-diagonal';
    setActiveColorModeBtn(viewModeSplitDiagBtn);
    renderMatrix();
    showToast('Color: División Diagonal Proporcional 60/40');
  });
}

if (viewModeSplitPieBtn) {
  viewModeSplitPieBtn.addEventListener('click', () => {
    currentTileViewMode = 'split-pie';
    setActiveColorModeBtn(viewModeSplitPieBtn);
    renderMatrix();
    showToast('Color: Mini Gráfico Circular (Pie % Conic)');
  });
}

// ==========================================================
// SELECTOR DE FAMILIA RAÍZ Y ORDENACIÓN
// ==========================================================
const familyFilterSelect = document.getElementById('familyFilterSelect');
if (familyFilterSelect) {
  familyFilterSelect.addEventListener('change', (e) => {
    currentFamilyFilter = e.target.value;
    renderMatrix();
    const label = e.target.options[e.target.selectedIndex].text;
    showToast(`Familia activa: ${label}`);
  });
}

const sortOrderSelect = document.getElementById('sortOrderSelect');
if (sortOrderSelect) {
  sortOrderSelect.addEventListener('change', (e) => {
    currentSortOrder = e.target.value;
    renderMatrix();
    const sortLabels = {
      default: 'Orden por defecto',
      purity_desc: 'Orden: 100% Puros ➔ Híbridos',
      hybrid_first: 'Orden: Híbridos primero (60-40)',
      likes_desc: 'Orden: Más Likes',
      score_desc: 'Orden: Mayor Score de Afinidad'
    };
    showToast(sortLabels[currentSortOrder] || 'Orden actualizado');
  });
}

// ==========================================================
// FILTROS DE AFINIDAD, HÍBRIDOS Y ANOMALÍAS
// ==========================================================
document.querySelectorAll('.filter-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const filter = btn.getAttribute('data-filter') || 'all';

    document.querySelectorAll('.filter-btn').forEach(b => {
      const bFilter = b.getAttribute('data-filter');
      if (bFilter === 'hybrid') {
        b.className = 'filter-btn px-2.5 py-1 rounded-md bg-white border border-amber-300 text-amber-800 font-semibold text-[10px] hover:bg-amber-50 transition flex items-center gap-1';
      } else if (bFilter === 'anomaly') {
        b.className = 'filter-btn px-2.5 py-1 rounded-md bg-amber-50 border border-amber-400 text-amber-900 font-semibold text-[10px] hover:bg-amber-100 transition flex items-center gap-1';
      } else if (bFilter === 'pending') {
        b.className = 'filter-btn px-2.5 py-1 rounded-md bg-amber-50 border border-amber-300 text-amber-900 font-semibold text-[10px] hover:bg-amber-100 transition flex items-center gap-1';
      } else {
        b.className = 'filter-btn px-2.5 py-1 rounded-md bg-white border border-stone-200 text-stone-700 font-semibold text-[10px] hover:bg-stone-50 transition flex items-center gap-1';
      }
    });

    if (filter === 'hybrid') {
      btn.className = 'filter-btn px-2.5 py-1 rounded-md bg-amber-800 text-white font-semibold text-[10px] transition flex items-center gap-1';
    } else if (filter === 'anomaly') {
      btn.className = 'filter-btn px-2.5 py-1 rounded-md bg-amber-600 text-white font-semibold text-[10px] transition flex items-center gap-1';
    } else if (filter === 'pending') {
      btn.className = 'filter-btn px-2.5 py-1 rounded-md bg-amber-600 text-white font-semibold text-[10px] transition flex items-center gap-1';
    } else {
      btn.className = 'filter-btn px-2.5 py-1 rounded-md bg-stone-900 text-white font-semibold text-[10px] transition flex items-center gap-1';
    }

    currentFilterMode = filter;
    renderMatrix();
  });
});

// ==========================================================
// BÚSQUEDA EN TIEMPO REAL
// ==========================================================
const keywordSearchInput = document.getElementById('keywordSearch') || document.getElementById('searchInput');
if (keywordSearchInput) {
  keywordSearchInput.addEventListener('input', (e) => {
    currentSearchTerm = e.target.value.toLowerCase().trim();
    renderMatrix();
  });
}

// ==========================================================
// MODO OSCURO Y EXPORTACIÓN JSON
// ==========================================================
const themeToggleBtn = document.getElementById('themeToggleBtn');
if (themeToggleBtn) {
  themeToggleBtn.addEventListener('click', () => {
    document.body.classList.toggle('dark-mode');
    const isDark = document.body.classList.contains('dark-mode');
    themeToggleBtn.innerHTML = isDark ? '<i class="fa-solid fa-sun text-amber-400"></i>' : '<i class="fa-solid fa-moon"></i>';
    showToast(isDark ? 'Modo oscuro activado' : 'Modo claro activado');
    if (currentMainView === 'scatter') renderScatterView();
  });
}

const exportJsonBtn = document.getElementById('exportJsonBtn');
if (exportJsonBtn) {
  exportJsonBtn.addEventListener('click', () => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(currentScrapedPosts, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", `x-classified-posts-${Date.now()}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
    showToast('Dataset exportado correctamente en formato JSON');
  });
}

// ==========================================================
// EJECUCIÓN DEL ESCANEO CON EL MOTOR JEV
// ==========================================================
const runAiClassificationBtn = document.getElementById('runAiClassificationBtn');
const aiClassificationProgress = document.getElementById('aiClassificationProgress');
const aiProgressBarFill = document.getElementById('aiProgressBarFill');
const aiProgressPercent = document.getElementById('aiProgressPercent');
const aiProgressText = document.getElementById('aiProgressText');
const targetPostUrlInput = document.getElementById('targetPostUrl');

if (runAiClassificationBtn) {
  runAiClassificationBtn.addEventListener('click', () => {
    const rawVal = targetPostUrlInput ? targetPostUrlInput.value.trim() : '';
    const ingestModal = document.getElementById('ingestModal');
    const jsonPasteArea = document.getElementById('jsonPasteArea');
    const analyzeSingleBtn = document.getElementById('analyzeSingleBtn');

    if (rawVal) {
      if (jsonPasteArea) jsonPasteArea.value = rawVal;
      if (ingestModal) ingestModal.classList.remove('hidden');
      if (analyzeSingleBtn) {
        // Ejecutar análisis directo con Laya Engine
        analyzeSingleBtn.click();
      }
    } else {
      if (ingestModal) ingestModal.classList.remove('hidden');
      showToast('Pega un tweet, URL o JSON para clasificar con Laya AI');
    }
  });
}

// Redibujar el canvas scatter en caso de redimensionamiento de ventana
window.addEventListener('resize', () => {
  if (currentMainView === 'scatter') {
    renderScatterView();
  }
});

// ==========================================================
// INICIALIZACIÓN DE LA APLICACIÓN (SINCRONIZACIÓN CON BACKEND)
// ==========================================================
window.addEventListener('DOMContentLoaded', async () => {
  // Renderizado inicial inmediato con dataset base
  currentScrapedPosts = buildRealisticScannedDataset();
  renderMatrix();

  // Sincronización asíncrona con el backend FastAPI (categories.json y posts en SQLite WAL)
  await syncTaxonomyAndPostsWithBackend();
  renderMatrix();
});
