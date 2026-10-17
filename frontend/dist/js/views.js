/**
 * ==========================================================
 * VIEWS.JS - Vistas de Cuadrante Scatter Canvas 2D, Tabla Ejecutiva y Densidad
 * ==========================================================
 */

// Referencias DOM de Vistas Principales
const matrixViewContainer = document.getElementById('matrixViewContainer');
const scatterViewContainer = document.getElementById('scatterViewContainer');
const tableViewContainer = document.getElementById('tableViewContainer');

const viewSwitchWaffleBtn = document.getElementById('viewSwitchWaffleBtn');
const viewSwitchScatterBtn = document.getElementById('viewSwitchScatterBtn');
const viewSwitchTableBtn = document.getElementById('viewSwitchTableBtn');

// Referencias DOM de Densidad
const densityCompactBtn = document.getElementById('densityCompactBtn');
const densityNormalBtn = document.getElementById('densityNormalBtn');
const densityLargeBtn = document.getElementById('densityLargeBtn');

/**
 * Alterna entre las tres vistas principales: Waffle, Scatter y Tabla
 * @param {string} viewName - 'waffle' | 'scatter' | 'table'
 */
function switchMainView(viewName) {
  currentMainView = viewName;

  if (matrixViewContainer) matrixViewContainer.classList.add('hidden');
  if (scatterViewContainer) scatterViewContainer.classList.add('hidden');
  if (tableViewContainer) tableViewContainer.classList.add('hidden');

  [viewSwitchWaffleBtn, viewSwitchScatterBtn, viewSwitchTableBtn].forEach(btn => {
    if (btn) {
      btn.className = 'px-2 py-0.5 rounded text-stone-600 hover:text-stone-900 font-mono text-[9px] transition flex items-center gap-1';
    }
  });

  if (viewName === 'waffle') {
    if (matrixViewContainer) matrixViewContainer.classList.remove('hidden');
    if (viewSwitchWaffleBtn) {
      viewSwitchWaffleBtn.className = 'px-2 py-0.5 rounded bg-stone-900 text-white font-mono text-[9px] font-semibold transition flex items-center gap-1';
    }
    renderMatrix();
  } else if (viewName === 'scatter') {
    if (scatterViewContainer) scatterViewContainer.classList.remove('hidden');
    if (viewSwitchScatterBtn) {
      viewSwitchScatterBtn.className = 'px-2 py-0.5 rounded bg-stone-900 text-white font-mono text-[9px] font-semibold transition flex items-center gap-1';
    }
    // Timeout para asegurar que el contenedor sea visible y tenga dimensiones calculadas
    setTimeout(() => {
      renderScatterView();
    }, 50);
  } else if (viewName === 'table') {
    if (tableViewContainer) tableViewContainer.classList.remove('hidden');
    if (viewSwitchTableBtn) {
      viewSwitchTableBtn.className = 'px-2 py-0.5 rounded bg-stone-900 text-white font-mono text-[9px] font-semibold transition flex items-center gap-1';
    }
    renderTableView();
  }
}

/**
 * Modifica la densidad de celdas del Waffle Grid (S / M / L)
 * @param {string} density - 'compact' | 'normal' | 'large'
 */
function setGridDensity(density) {
  currentDensity = density;
  document.body.classList.remove('density-compact', 'density-large');

  if (densityCompactBtn) densityCompactBtn.className = 'px-1.5 py-0.5 rounded text-stone-600 hover:bg-stone-100';
  if (densityNormalBtn) densityNormalBtn.className = 'px-1.5 py-0.5 rounded text-stone-600 hover:bg-stone-100';
  if (densityLargeBtn) densityLargeBtn.className = 'px-1.5 py-0.5 rounded text-stone-600 hover:bg-stone-100';

  if (density === 'compact') {
    document.body.classList.add('density-compact');
    if (densityCompactBtn) densityCompactBtn.className = 'px-1.5 py-0.5 rounded bg-stone-800 text-white font-bold';
    showToast('Densidad: Compacta (8px)');
  } else if (density === 'large') {
    document.body.classList.add('density-large');
    if (densityLargeBtn) densityLargeBtn.className = 'px-1.5 py-0.5 rounded bg-stone-800 text-white font-bold';
    showToast('Densidad: Amplia (16px)');
  } else {
    if (densityNormalBtn) densityNormalBtn.className = 'px-1.5 py-0.5 rounded bg-stone-800 text-white font-bold';
    showToast('Densidad: Estándar (11px)');
  }
  renderMatrix();
}

// ==========================================================
// RENDERIZADOR DEL CUADRANTE SCATTER EN CANVAS 2D
// ==========================================================
let scatterPointsCache = [];

function renderScatterView() {
  const canvas = document.getElementById('scatterCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const parent = canvas.parentElement;
  const rect = parent ? parent.getBoundingClientRect() : canvas.getBoundingClientRect();

  if (rect.width === 0 || rect.height === 0) return;

  const dpr = window.devicePixelRatio || 1;
  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;
  ctx.scale(dpr, dpr);

  const width = rect.width;
  const height = rect.height;
  const pad = 55;

  const isDark = document.body.classList.contains('dark-mode');

  // Limpiar lienzo
  ctx.clearRect(0, 0, width, height);

  // Ejes centrales (Score 50% e interacción media)
  const midX = pad + ((width - pad * 2) * 0.5);
  const midY = pad + ((height - pad * 2) * 0.5);

  // Cuadrantes sombreados
  // Q1: Superior Derecho (Alto Score, Alta Viralidad)
  ctx.fillStyle = isDark ? 'rgba(16, 185, 129, 0.08)' : 'rgba(16, 185, 129, 0.05)';
  ctx.fillRect(midX, pad, width - pad - midX, midY - pad);

  // Q2: Superior Izquierdo (Bajo Score, Alta Viralidad - Outliers)
  ctx.fillStyle = isDark ? 'rgba(245, 158, 11, 0.08)' : 'rgba(245, 158, 11, 0.04)';
  ctx.fillRect(pad, pad, midX - pad, midY - pad);

  // Q3: Inferior Izquierdo (Bajo Score, Baja Viralidad - Flop / Desalineado)
  ctx.fillStyle = isDark ? 'rgba(239, 68, 68, 0.06)' : 'rgba(239, 68, 68, 0.03)';
  ctx.fillRect(pad, midY, midX - pad, height - pad - midY);

  // Q4: Inferior Derecho (Alto Score, Baja Viralidad - Gemas Ocultas / Nicho)
  ctx.fillStyle = isDark ? 'rgba(2, 132, 199, 0.06)' : 'rgba(2, 132, 199, 0.03)';
  ctx.fillRect(midX, midY, width - pad - midX, height - pad - midY);

  // Líneas divisorias punteadas
  ctx.strokeStyle = isDark ? '#333742' : '#e5e4de';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.setLineDash([4, 4]);
  ctx.moveTo(midX, pad);
  ctx.lineTo(midX, height - pad);
  ctx.moveTo(pad, midY);
  ctx.lineTo(width - pad, midY);
  ctx.stroke();

  // Bordes del área de trazado
  ctx.beginPath();
  ctx.setLineDash([]);
  ctx.strokeStyle = isDark ? '#40434f' : '#d6d3d1';
  ctx.strokeRect(pad, pad, width - pad * 2, height - pad * 2);

  // Etiquetas de los 4 Cuadrantes
  ctx.font = '10px JetBrains Mono, monospace';

  // Q1
  ctx.fillStyle = '#10b981';
  ctx.fillText('Q1: ALTO SCORE + ALTA VIRALIDAD (HITS)', midX + 12, pad + 20);

  // Q2
  ctx.fillStyle = '#d97706';
  ctx.fillText('Q2: OUTLIERS (BAJO SCORE + VIRAL)', pad + 12, pad + 20);

  // Q3
  ctx.fillStyle = isDark ? '#9ca3af' : '#78716c';
  ctx.fillText('Q3: DESALINEADOS / FLOP', pad + 12, height - pad - 12);

  // Q4
  ctx.fillStyle = '#0284c7';
  ctx.fillText('Q4: GEMAS DE NICHO (ALTO SCORE / MENOR ALCANCE)', midX + 12, height - pad - 12);

  // Ejes y Títulos
  ctx.fillStyle = isDark ? '#a1a1aa' : '#57534e';
  ctx.fillText('SCORE DE AFINIDAD (0% ➔ 100%)', width - 230, height - pad + 32);

  ctx.save();
  ctx.translate(pad - 32, midY + 45);
  ctx.rotate(-Math.PI / 2);
  ctx.fillText('ENGAGEMENT REAL (0 ➔ 20K+ LIKES)', 0, 0);
  ctx.restore();

  // Ticks y valores de referencia
  ctx.fillStyle = isDark ? '#71717a' : '#a8a29e';
  ctx.font = '9px JetBrains Mono, monospace';
  ctx.fillText('0%', pad, height - pad + 16);
  ctx.fillText('50%', midX - 8, height - pad + 16);
  ctx.fillText('100%', width - pad - 20, height - pad + 16);

  ctx.fillText('0', pad - 18, height - pad);
  ctx.fillText('10K', pad - 26, midY + 3);
  ctx.fillText('20K+', pad - 30, pad + 10);

  // Trazar puntos de datos
  scatterPointsCache = [];
  const maxLikes = 20000;

  // Filtrar según familia activa si aplica
  let postsToPlot = currentScrapedPosts;
  if (currentFamilyFilter && currentFamilyFilter !== 'all') {
    const validCatIds = new Set(CATEGORIES.filter(c => c.family_id === currentFamilyFilter).map(c => c.id));
    postsToPlot = currentScrapedPosts.filter(p => validCatIds.has(p.category_id));
  }

  postsToPlot.forEach(post => {
    const scoreVal = Math.max(0, Math.min(100, post.affinity_score || 50));
    const x = pad + ((scoreVal / 100) * (width - pad * 2));

    const likesVal = Math.max(0, post.likes || 0);
    const normalizedLikes = Math.min(likesVal, maxLikes) / maxLikes;
    const y = (height - pad) - (normalizedLikes * (height - pad * 2));

    const color = CATEGORY_COLOR_MAP[post.category_id] || '#8b5cf6';
    const isAnomaly = isPostAnomaly(post);

    // Filtrado visual interactivo
    let isMatch = true;
    if (currentFilterMode === 'high' && post.affinity_score < 70) isMatch = false;
    if (currentFilterMode === 'mid' && (post.affinity_score < 45 || post.affinity_score >= 70)) isMatch = false;
    if (currentFilterMode === 'low' && post.affinity_score >= 45) isMatch = false;
    if (currentFilterMode === 'hybrid' && !post.is_hybrid) isMatch = false;
    if (currentFilterMode === 'anomaly' && !isAnomaly) isMatch = false;

    if (currentSearchTerm && !post.text.toLowerCase().includes(currentSearchTerm)) {
      isMatch = false;
    }

    const radius = isAnomaly ? 6.5 : (post.is_hybrid ? 5 : 4);

    ctx.save();
    if (!isMatch) {
      ctx.globalAlpha = 0.12;
    }

    // Dibujar punto
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.fillStyle = isAnomaly ? '#f59e0b' : color;
    ctx.fill();

    // Borde: para posts híbridos, dibujar anillo secundario
    if (post.is_hybrid && post.secondary_cat_id) {
      const secColor = CATEGORY_COLOR_MAP[post.secondary_cat_id] || '#06b6d4';
      ctx.strokeStyle = secColor;
      ctx.lineWidth = 2;
    } else {
      ctx.strokeStyle = isAnomaly ? '#b45309' : (isDark ? '#ffffff' : '#ffffff');
      ctx.lineWidth = isAnomaly ? 2 : 1;
    }
    ctx.stroke();
    ctx.restore();

    scatterPointsCache.push({ x, y, post, radius });
  });
}

// Tooltip interactivo sobre el Canvas Scatter
const scatterCanvas = document.getElementById('scatterCanvas');
const scatterTooltip = document.getElementById('scatterTooltip');

if (scatterCanvas && scatterTooltip) {
  scatterCanvas.addEventListener('mousemove', (e) => {
    const rect = scatterCanvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    let found = null;
    for (const pt of scatterPointsCache) {
      const dist = Math.hypot(pt.x - mouseX, pt.y - mouseY);
      if (dist <= (pt.radius + 5)) {
        found = pt;
        break;
      }
    }

    if (found) {
      const post = found.post;
      const cat = CATEGORIES.find(c => c.id === post.category_id);
      const catName = cat ? cat.name : post.category_id;
      const isAnomaly = isPostAnomaly(post);
      const color = CATEGORY_COLOR_MAP[post.category_id] || '#8b5cf6';

      let secTag = '';
      if (post.is_hybrid && post.secondary_cat_id) {
        const secCat = CATEGORIES.find(c => c.id === post.secondary_cat_id);
        secTag = `<span class="text-amber-400 font-bold ml-1">+ ${post.secondary_pct}% ${(secCat ? secCat.code : post.secondary_cat_id)}</span>`;
      }

      scatterTooltip.innerHTML = `
        <div class="font-bold border-b border-stone-700 pb-1.5 mb-1.5 flex items-center justify-between gap-3">
          <div class="flex items-center gap-1.5 truncate">
            <span class="w-2.5 h-2.5 rounded-full inline-block" style="background-color: ${color}"></span>
            <span class="text-stone-200">@${post.author || 'anon'}</span>
          </div>
          <span class="text-emerald-400 font-mono text-[10px] font-bold">${post.affinity_score}% Afin.</span>
        </div>
        <div class="line-clamp-2 text-stone-300 text-[10px] mb-2 leading-relaxed font-sans">
          ${isAnomaly ? `<span class="text-amber-400 font-bold font-mono mr-1">[OUTLIER]</span>` : ''}
          ${post.text}
        </div>
        <div class="flex items-center justify-between text-[9px] font-mono text-stone-400 border-t border-stone-800 pt-1">
          <span class="truncate max-w-[130px]">${catName}${secTag}</span>
          <span class="text-rose-400 font-bold flex items-center gap-1">
            <i class="fa-regular fa-heart"></i> ${formatNumberK(post.likes)}
          </span>
        </div>
        <div class="text-[8px] text-stone-500 font-mono text-right mt-1">Clic para inspeccionar</div>
      `;

      scatterTooltip.style.left = `${Math.min(rect.width - 240, Math.max(10, mouseX + 15))}px`;
      scatterTooltip.style.top = `${Math.max(10, Math.min(rect.height - 130, mouseY - 70))}px`;
      scatterTooltip.classList.remove('hidden');
    } else {
      scatterTooltip.classList.add('hidden');
    }
  });

  scatterCanvas.addEventListener('mouseleave', () => {
    scatterTooltip.classList.add('hidden');
  });

  scatterCanvas.addEventListener('click', (e) => {
    const rect = scatterCanvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    for (const pt of scatterPointsCache) {
      const dist = Math.hypot(pt.x - mouseX, pt.y - mouseY);
      if (dist <= (pt.radius + 6)) {
        const cat = CATEGORIES.find(c => c.id === pt.post.category_id);
        if (typeof openPostDrawer === 'function') {
          openPostDrawer(pt.post, cat);
        }
        break;
      }
    }
  });
}

// ==========================================================
// RENDERIZADOR DE LA TABLA EJECUTIVA ANALÍTICA
// ==========================================================
function renderTableView() {
  const tbody = document.getElementById('tableCategoryBody');
  if (!tbody) return;
  tbody.innerHTML = '';

  let catsToRender = [...CATEGORIES];
  if (currentFamilyFilter && currentFamilyFilter !== 'all') {
    catsToRender = catsToRender.filter(c => c.family_id === currentFamilyFilter);
  }

  // Ordenar por volumen de posts descendente
  catsToRender.sort((a, b) => {
    const countA = currentScrapedPosts.filter(p => p.category_id === a.id).length;
    const countB = currentScrapedPosts.filter(p => p.category_id === b.id).length;
    return countB - countA;
  });

  catsToRender.forEach(cat => {
    const catPosts = currentScrapedPosts.filter(p => p.category_id === cat.id);
    const count = catPosts.length;
    if (count === 0) return;

    const avgLikes = Math.round(catPosts.reduce((acc, p) => acc + (p.likes || 0), 0) / count);
    const avgScore = (catPosts.reduce((acc, p) => acc + (p.affinity_score || 0), 0) / count).toFixed(1);
    const hybridCount = catPosts.filter(p => p.is_hybrid).length;
    const hybridPct = Math.round((hybridCount / count) * 100);
    const viralCount = catPosts.filter(p => p.affinity_score >= 70).length;
    const viralPct = Math.round((viralCount / count) * 100);

    const priColor = cat.colorHex || CATEGORY_COLOR_MAP[cat.id] || '#8b5cf6';
    const famInfo = ROOT_FAMILIES[cat.family_id] || { name: cat.family_id, icon: 'fa-folder' };

    const tr = document.createElement('tr');
    tr.className = 'hover:bg-stone-50 transition border-b border-stone-100 cursor-pointer text-xs';
    tr.innerHTML = `
      <td class="py-2.5 px-3">
        <span class="w-6 h-6 rounded-md flex items-center justify-center font-bold text-[9px] text-white shadow-xs" style="background-color: ${priColor}">
          ${cat.code || 'CAT'}
        </span>
      </td>
      <td class="py-2.5 px-3">
        <div class="font-bold text-stone-900">${cat.name}</div>
        <div class="text-[9px] text-stone-400 font-mono uppercase">${famInfo.name}</div>
      </td>
      <td class="py-2.5 px-3 text-right font-bold text-stone-800">${count}</td>
      <td class="py-2.5 px-3 text-right text-stone-700 font-semibold">${avgScore}%</td>
      <td class="py-2.5 px-3 text-right text-stone-700 font-semibold">
        <i class="fa-regular fa-heart text-rose-500 mr-1"></i>${formatNumberK(avgLikes)}
      </td>
      <td class="py-2.5 px-3 text-right text-amber-700 font-bold">${hybridPct}%</td>
      <td class="py-2.5 px-3 text-right font-bold ${viralPct >= 40 ? 'text-emerald-600' : 'text-stone-500'}">${viralPct}%</td>
      <td class="py-2.5 px-3 text-stone-500 text-[10px] truncate max-w-xs font-sans">${cat.description || (cat.targetKeywords || []).slice(0, 4).join(', ')}</td>
    `;

    tr.addEventListener('click', () => {
      currentFilterMode = 'all';
      currentSearchTerm = cat.name.toLowerCase();
      switchMainView('waffle');
      showToast(`Filtrando Waffle Grid por "${cat.name}"`);
    });

    tbody.appendChild(tr);
  });
}

// Asignación de eventos de cambio de vista y densidad
if (viewSwitchWaffleBtn) viewSwitchWaffleBtn.addEventListener('click', () => switchMainView('waffle'));
if (viewSwitchScatterBtn) viewSwitchScatterBtn.addEventListener('click', () => switchMainView('scatter'));
if (viewSwitchTableBtn) viewSwitchTableBtn.addEventListener('click', () => switchMainView('table'));

if (densityCompactBtn) densityCompactBtn.addEventListener('click', () => setGridDensity('compact'));
if (densityNormalBtn) densityNormalBtn.addEventListener('click', () => setGridDensity('normal'));
if (densityLargeBtn) densityLargeBtn.addEventListener('click', () => setGridDensity('large'));
