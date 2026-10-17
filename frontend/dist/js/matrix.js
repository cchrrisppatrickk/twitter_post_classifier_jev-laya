/**
 * ==========================================================
 * MATRIX.JS - Waffle Grid Dinámico, Celdas Split Bicolores y Ghost Linking
 * Adaptado para 48 categorías dinámicas agrupadas en 8 familias maestras.
 * ==========================================================
 */

const categoriesContainer = document.getElementById('categoriesContainer');
const tileTooltip = document.getElementById('tileTooltip');
const tipCategory = document.getElementById('tipCategory');
const tipScoreBadge = document.getElementById('tipScoreBadge');
const tipContent = document.getElementById('tipContent');
const tipAuthor = document.getElementById('tipAuthor');
const tipLikes = document.getElementById('tipLikes');

/**
 * Renderizado de la matriz de cuadrícula (Waffle Grid) dinámica con soporte
 * para 48 categorías de categories.json, celdas bicolores (Split % Cat),
 * Score Viral, Mini Pie, Anomalías y Ghost Linking.
 */
function renderMatrix() {
  if (!categoriesContainer) return;
  categoriesContainer.innerHTML = '';

  let totalClassified = currentScrapedPosts.length;
  let totalScoreSum = 0;
  let totalLikesSum = 0;

  // Filtrado por familia raíz
  let catsToRender = [...CATEGORIES];
  if (currentFamilyFilter && currentFamilyFilter !== 'all') {
    catsToRender = catsToRender.filter(c => c.family_id === currentFamilyFilter);
  }

  // Ordenar por orden lógico de familias y prioridad
  const famOrder = ['dev_tools', 'ia', 'modelado_3d', 'juegos', 'mangas', 'negocios_saas', 'otros'];
  catsToRender.sort((a, b) => {
    const famA = famOrder.indexOf(a.family_id);
    const famB = famOrder.indexOf(b.family_id);
    if (famA !== -1 && famB !== -1 && famA !== famB) return famA - famB;
    return (a.priority || 50) - (b.priority || 50);
  });

  if (catsToRender.length === 0) {
    categoriesContainer.innerHTML = `
      <div class="py-12 text-center text-stone-400 font-mono text-xs">
        No hay categorías registradas en la familia seleccionada.
      </div>
    `;
    return;
  }

  let currentFamilySection = null;

  catsToRender.forEach(cat => {
    // Encabezado separador por familia en vista general
    if (currentFamilyFilter === 'all' && cat.family_id !== currentFamilySection) {
      currentFamilySection = cat.family_id;
      const fam = ROOT_FAMILIES[cat.family_id] || { name: cat.family_id, colorHex: '#71717a', icon: 'fa-folder' };
      const famHeader = document.createElement('div');
      famHeader.className = 'family-section-divider pt-4 pb-1.5 px-1.5 flex items-center justify-between text-[11px] font-mono font-bold uppercase tracking-wider text-stone-700 border-b border-stone-200/90 bg-stone-50/50 rounded-t-lg mt-2';
      famHeader.innerHTML = `
        <div class="flex items-center gap-2">
          <span class="w-2.5 h-2.5 rounded-full shadow-xs" style="background-color: ${fam.colorHex}"></span>
          <i class="fa-solid ${fam.icon} text-stone-500 text-[10px]"></i>
          <span>${fam.name}</span>
        </div>
        <span class="text-[10px] text-stone-400 font-normal lowercase">${catsToRender.filter(c => c.family_id === cat.family_id).length} categorías</span>
      `;
      categoriesContainer.appendChild(famHeader);
    }

    let catPosts = currentScrapedPosts.filter(p => p.category_id === cat.id);

    // Ordenación interna de publicaciones según el criterio activo
    if (currentSortOrder === 'purity_desc') {
      catPosts.sort((a, b) => (a.is_hybrid === b.is_hybrid) ? 0 : a.is_hybrid ? 1 : -1);
    } else if (currentSortOrder === 'hybrid_first') {
      catPosts.sort((a, b) => (a.is_hybrid === b.is_hybrid) ? 0 : a.is_hybrid ? -1 : 1);
    } else if (currentSortOrder === 'likes_desc') {
      catPosts.sort((a, b) => (b.likes || 0) - (a.likes || 0));
    } else if (currentSortOrder === 'score_desc') {
      catPosts.sort((a, b) => (b.affinity_score || 0) - (a.affinity_score || 0));
    }

    const scoreSum = catPosts.reduce((acc, p) => acc + (p.affinity_score || 50), 0);
    const avgScore = catPosts.length > 0 ? (scoreSum / catPosts.length).toFixed(1) : '0.0';

    const likesSum = catPosts.reduce((acc, p) => acc + (p.likes || 0), 0);
    totalLikesSum += likesSum;
    totalScoreSum += catPosts.length > 0 ? parseFloat(avgScore) : 0;

    const avgLikesText = catPosts.length > 0 ? formatNumberK(Math.round(likesSum / catPosts.length)) : '-';

    // Envoltura de la fila por categoría
    const rowWrapper = document.createElement('div');
    rowWrapper.className = 'category-row py-2.5 flex flex-col lg:flex-row items-start lg:items-center justify-between gap-3 hover:bg-stone-100/40 transition-colors px-1 rounded-lg';
    rowWrapper.setAttribute('data-category-row', cat.id);

    const priColor = cat.colorHex || CATEGORY_COLOR_MAP[cat.id] || '#8b5cf6';

    // 1. Meta Izquierda: Código, Nombre, Familia y Conteo
    const leftMeta = document.createElement('div');
    leftMeta.className = 'flex items-center gap-2.5 w-full lg:w-48 shrink-0';
    leftMeta.innerHTML = `
      <div class="cat-badge w-6 h-6 rounded-md text-white flex items-center justify-center font-bold text-[9px] tracking-tight shrink-0 shadow-xs" style="background-color: ${priColor}" data-category-badge="${cat.id}">
        ${cat.code || 'CAT'}
      </div>
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-1.5 flex-wrap">
          <span class="font-bold text-xs text-stone-900 truncate" title="${cat.name}">${cat.name}</span>
          <span class="text-[9px] text-stone-400 font-mono font-medium">(${catPosts.length})</span>
        </div>
        <div class="flex items-baseline gap-1 mt-0.5 font-mono">
          <span class="text-xs font-bold text-stone-800 tracking-tight">${avgScore}%</span>
          <span class="text-[9px] text-stone-400 font-normal">afinidad</span>
        </div>
      </div>
    `;

    // 2. Columna Central: Matriz Waffle (Grid con soporte para densidad S/M/L)
    const centerMatrix = document.createElement('div');
    centerMatrix.className = 'flex-1 w-full overflow-x-auto pb-1 lg:pb-0 scrollbar-thin';

    const matrixGrid = document.createElement('div');
    matrixGrid.className = 'matrix-row-grid grid grid-rows-4 grid-flow-col gap-1 w-max p-1 bg-transparent';

    catPosts.forEach(post => {
      const tile = document.createElement('div');
      tile.setAttribute('data-id', post.id);
      tile.setAttribute('data-category', cat.id);

      const priColorHex = priColor;
      const secColorHex = post.secondary_cat_id ? (CATEGORY_COLOR_MAP[post.secondary_cat_id] || '#f59e0b') : priColorHex;

      tile.style.setProperty('--pri-cat-color', priColorHex);
      tile.style.setProperty('--sec-cat-color', secColorHex);
      tile.style.setProperty('--split-pct', `${post.primary_pct || 65}%`);

      // Modo 1: Renderizado por Score Viral (Verde a Rojo)
      if (currentTileViewMode === 'viral') {
        tile.className = `post-tile ${getTileColorClass(post.affinity_score)}`;
        if (post.is_hybrid) {
          tile.classList.add('tile-hybrid-badge');
        }
      }
      // Modo 2: Corte Diagonal 60/40
      else if (currentTileViewMode === 'split-diagonal') {
        if (post.is_hybrid) {
          tile.className = 'post-tile tile-split-diagonal';
        } else {
          tile.className = 'post-tile';
          tile.style.backgroundColor = priColorHex;
        }
      }
      // Modo 3: Mini Gráfico Circular (Conic Gradient)
      else if (currentTileViewMode === 'split-pie') {
        if (post.is_hybrid) {
          tile.className = 'post-tile tile-split-pie';
        } else {
          tile.className = 'post-tile';
          tile.style.backgroundColor = priColorHex;
        }
      }

      // Detección y pulso visual de anomalía (Outlier)
      const isAnomaly = isPostAnomaly(post);
      if (isAnomaly) {
        tile.classList.add('tile-anomaly');
        tile.setAttribute('title', 'Outlier: Comportamiento anómalo respecto a la media');
      }

      // Detección y borde pulsante de publicación PENDING (Requiere resolución humana)
      if (post.status === 'PENDING') {
        tile.classList.add('tile-pending');
        tile.setAttribute('title', 'Estado PENDING: Requiere desempate o supervisión humana');
      }

      // Filtrado visual interactivo
      let isMatch = true;
      if (currentFilterMode === 'high' && post.affinity_score < 70) isMatch = false;
      if (currentFilterMode === 'mid' && (post.affinity_score < 45 || post.affinity_score >= 70)) isMatch = false;
      if (currentFilterMode === 'low' && post.affinity_score >= 45) isMatch = false;
      if (currentFilterMode === 'hybrid' && !post.is_hybrid) isMatch = false;
      if (currentFilterMode === 'anomaly' && !isAnomaly) isMatch = false;
      if (currentFilterMode === 'pending' && post.status !== 'PENDING') isMatch = false;

      if (currentSearchTerm && !post.text.toLowerCase().includes(currentSearchTerm)) {
        isMatch = false;
      }

      if (!isMatch) {
        tile.classList.add('tile-dimmed');
      } else if (currentSearchTerm) {
        tile.classList.add('tile-highlighted');
      }

      // Eventos interactivos
      tile.addEventListener('mouseenter', (e) => {
        showTooltip(e, post, cat.name);
        if (post.is_hybrid && post.secondary_cat_id) {
          triggerGhostLinking(post.id, post.secondary_cat_id);
        }
      });

      tile.addEventListener('mouseleave', () => {
        hideTooltip();
        clearGhostLinking();
      });

      tile.addEventListener('mousemove', moveTooltip);
      tile.addEventListener('click', () => {
        if (typeof openPostDrawer === 'function') openPostDrawer(post, cat);
      });

      matrixGrid.appendChild(tile);
    });

    // Microcuadros fantasma proyectados al final
    const ghostCount = Math.max(3, 16 - (catPosts.length % 16));
    for (let g = 0; g < ghostCount; g++) {
      const ghost = document.createElement('div');
      ghost.className = 'post-tile tile-empty pointer-events-none';
      matrixGrid.appendChild(ghost);
    }

    centerMatrix.appendChild(matrixGrid);

    // 3. Meta Derecha: Promedio de likes
    const rightMeta = document.createElement('div');
    rightMeta.className = 'hidden lg:flex items-center justify-end gap-1.5 w-24 shrink-0 text-stone-700 text-xs font-mono font-medium';
    rightMeta.innerHTML = `
      <i class="fa-regular fa-heart text-stone-400 text-[11px]"></i>
      <span>${avgLikesText}</span>
    `;

    rowWrapper.appendChild(leftMeta);
    rowWrapper.appendChild(centerMatrix);
    rowWrapper.appendChild(rightMeta);
    categoriesContainer.appendChild(rowWrapper);
  });

  // Actualizar contadores y telemetría superior
  const hybridCount = currentScrapedPosts.filter(p => p.is_hybrid).length;
  const anomalyCount = currentScrapedPosts.filter(p => isPostAnomaly(p)).length;
  const pendingCount = currentScrapedPosts.filter(p => p.status === 'PENDING').length;

  const headerCountEl = document.getElementById('headerPostCount');
  if (headerCountEl) headerCountEl.innerText = `x · ${totalClassified} posts`;

  const filterAllCountEl = document.getElementById('filterAllCount');
  if (filterAllCountEl) filterAllCountEl.innerText = totalClassified;

  const filterHybridCountEl = document.getElementById('filterHybridCount');
  if (filterHybridCountEl) filterHybridCountEl.innerText = hybridCount;

  const filterAnomalyCountEl = document.getElementById('filterAnomalyCount');
  if (filterAnomalyCountEl) filterAnomalyCountEl.innerText = anomalyCount;

  const filterPendingCountEl = document.getElementById('filterPendingCount');
  if (filterPendingCountEl) filterPendingCountEl.innerText = pendingCount;

  const statChecksEl = document.getElementById('statChecks');
  if (statChecksEl) statChecksEl.innerText = currentChecksCount.toLocaleString();

  const statCostEl = document.getElementById('statCost');
  if (statCostEl) statCostEl.innerText = `$${currentTotalCost.toFixed(2)}`;

  const statLatencyEl = document.getElementById('statLatency');
  if (statLatencyEl) statLatencyEl.innerText = `${currentLatency.toFixed(1)}s`;

  const globalAvg = catsToRender.length > 0 ? (totalScoreSum / catsToRender.length).toFixed(1) : '0.0';
  const statAvgScoreEl = document.getElementById('statAvgScore');
  if (statAvgScoreEl) statAvgScoreEl.innerText = `${globalAvg}%`;

  const globalAvgLikes = totalClassified > 0 ? formatNumberK(Math.round(totalLikesSum / totalClassified)) : '0';
  const statAvgLikesEl = document.getElementById('statAvgLikes');
  if (statAvgLikesEl) statAvgLikesEl.innerText = globalAvgLikes;

  // Actualizar vistas secundarias si están activas
  if (typeof renderTableView === 'function' && currentMainView === 'table') {
    renderTableView();
  } else if (typeof renderScatterView === 'function' && currentMainView === 'scatter') {
    renderScatterView();
  }
}

/**
 * Sincronización Espejo (Ghost Linking):
 * Al posar el ratón sobre cualquier celda híbrida, se resalta y
 * parpadea un destello en la categoría secundaria asociada.
 */
function triggerGhostLinking(postId, secondaryCatId) {
  const targetRow = document.querySelector(`[data-category-row="${secondaryCatId}"]`);
  if (targetRow) {
    targetRow.classList.add('category-row-linked');
  }

  const targetBadge = document.querySelector(`[data-category-badge="${secondaryCatId}"]`);
  if (targetBadge) {
    targetBadge.classList.add('tile-sync-linked');
  }

  const targetTiles = document.querySelectorAll(`.post-tile[data-category="${secondaryCatId}"]`);
  targetTiles.forEach(tile => {
    tile.classList.add('tile-sync-linked');
  });
}

/**
 * Limpia el estado visual de Ghost Linking
 */
function clearGhostLinking() {
  document.querySelectorAll('.category-row-linked').forEach(el => el.classList.remove('category-row-linked'));
  document.querySelectorAll('.tile-sync-linked').forEach(el => el.classList.remove('tile-sync-linked'));
}

/**
 * Muestra el tooltip flotante con información del post
 */
function showTooltip(e, post, categoryName) {
  if (!tileTooltip) return;
  tipCategory.textContent = categoryName;

  if (post.is_hybrid && post.secondary_cat_id) {
    const secCat = CATEGORIES.find(c => c.id === post.secondary_cat_id);
    const secName = secCat ? secCat.code : 'MIX';
    tipScoreBadge.textContent = `${post.primary_pct}% ${categoryName.slice(0, 4)} · ${post.secondary_pct}% ${secName}`;
    tipScoreBadge.className = 'px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-900 text-amber-200 border border-amber-700';
  } else {
    tipScoreBadge.textContent = `${post.affinity_score}% Afin.`;
    if (post.affinity_score >= 70) {
      tipScoreBadge.className = 'px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-800 text-emerald-200';
    } else if (post.affinity_score >= 45) {
      tipScoreBadge.className = 'px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-800 text-amber-200';
    } else {
      tipScoreBadge.className = 'px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-rose-900 text-rose-200';
    }
  }

  const isAnomaly = isPostAnomaly(post);
  tipContent.innerHTML = (isAnomaly ? `<span class="text-amber-400 font-bold mr-1">[OUTLIER]</span>` : '') + (post.text || 'Sin texto');
  tipAuthor.innerHTML = `<i class="fa-regular fa-user"></i> @${post.author || '0xMovez'}`;
  tipLikes.innerHTML = `<i class="fa-regular fa-heart text-rose-400"></i> ${formatNumberK(post.likes)}`;

  tileTooltip.classList.remove('hidden');
  moveTooltip(e);
}

/**
 * Oculta el tooltip flotante
 */
function hideTooltip() {
  if (tileTooltip) tileTooltip.classList.add('hidden');
}

/**
 * Desplaza el tooltip acompañando la posición del cursor
 */
function moveTooltip(e) {
  if (!tileTooltip) return;
  const padding = 12;
  let left = e.clientX + padding;
  let top = e.clientY + padding;

  const rect = tileTooltip.getBoundingClientRect();
  if (left + rect.width > window.innerWidth - 10) {
    left = e.clientX - rect.width - padding;
  }
  if (top + rect.height > window.innerHeight - 10) {
    top = e.clientY - rect.height - padding;
  }

  tileTooltip.style.left = `${Math.max(10, left)}px`;
  tileTooltip.style.top = `${Math.max(10, top)}px`;
}

/**
 * Inserción incremental y reactiva de una celda en la Waffle Grid sin rehacer el DOM completo.
 * Ideal para procesamiento en lote con miles de publicaciones.
 */
function appendPostToMatrixRow(post) {
  if (!post || !post.category_id) return;
  const targetRow = document.querySelector(`[data-category-row="${post.category_id}"]`);
  if (!targetRow) {
    renderMatrix();
    return;
  }

  const grid = targetRow.querySelector('.matrix-row-grid');
  if (!grid) {
    renderMatrix();
    return;
  }

  const cat = CATEGORIES.find(c => c.id === post.category_id) || { id: post.category_id, name: post.category_id, code: 'CAT', colorHex: '#8b5cf6' };
  const priColorHex = cat.colorHex || CATEGORY_COLOR_MAP[cat.id] || '#8b5cf6';
  const secColorHex = post.secondary_cat_id ? (CATEGORY_COLOR_MAP[post.secondary_cat_id] || '#f59e0b') : priColorHex;

  const tile = document.createElement('div');
  tile.setAttribute('data-id', post.id);
  tile.setAttribute('data-category', cat.id);
  tile.style.setProperty('--pri-cat-color', priColorHex);
  tile.style.setProperty('--sec-cat-color', secColorHex);
  tile.style.setProperty('--split-pct', `${post.primary_pct || 65}%`);

  if (currentTileViewMode === 'viral') {
    tile.className = `post-tile ${getTileColorClass(post.affinity_score)}`;
    if (post.is_hybrid) tile.classList.add('tile-hybrid-badge');
  } else if (currentTileViewMode === 'split-diagonal') {
    tile.className = post.is_hybrid ? 'post-tile tile-split-diagonal' : 'post-tile';
    if (!post.is_hybrid) tile.style.backgroundColor = priColorHex;
  } else {
    tile.className = post.is_hybrid ? 'post-tile tile-split-pie' : 'post-tile';
    if (!post.is_hybrid) tile.style.backgroundColor = priColorHex;
  }

  const isAnomaly = isPostAnomaly(post);
  if (isAnomaly) {
    tile.classList.add('tile-anomaly');
    tile.setAttribute('title', 'Outlier: Comportamiento anómalo');
  }

  tile.addEventListener('mouseenter', (e) => {
    showTooltip(e, post, cat.name);
    if (post.is_hybrid && post.secondary_cat_id) {
      triggerGhostLinking(post.id, post.secondary_cat_id);
    }
  });
  tile.addEventListener('mouseleave', () => {
    hideTooltip();
    clearGhostLinking();
  });
  tile.addEventListener('mousemove', moveTooltip);
  tile.addEventListener('click', () => {
    if (typeof openPostDrawer === 'function') openPostDrawer(post, cat);
  });

  // Reemplazar un microcuadro fantasma o insertar antes del primero
  const ghost = grid.querySelector('.tile-empty');
  if (ghost) {
    grid.insertBefore(tile, ghost);
    ghost.remove();
  } else {
    grid.appendChild(tile);
  }

  // Actualizar contador numérico de la fila
  const catPosts = currentScrapedPosts.filter(p => p.category_id === post.category_id);
  const countSpan = targetRow.querySelector('.font-mono.font-medium');
  if (countSpan) countSpan.textContent = `(${catPosts.length})`;

  // Actualizar promedio de afinidad de la fila
  const scoreSum = catPosts.reduce((acc, p) => acc + (p.affinity_score || 50), 0);
  const avgScore = (scoreSum / catPosts.length).toFixed(1);
  const scoreSpan = targetRow.querySelector('.font-mono .font-bold.text-stone-800');
  if (scoreSpan) scoreSpan.textContent = `${avgScore}%`;

  // Actualizar contador del header
  const headerCountEl = document.getElementById('headerPostCount');
  if (headerCountEl) headerCountEl.textContent = currentScrapedPosts.length;
  const filterAllCount = document.getElementById('filterAllCount');
  if (filterAllCount) filterAllCount.textContent = currentScrapedPosts.length;

  // Scroll suave y destello verde en la fila
  targetRow.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  targetRow.classList.add('bg-emerald-50/80', 'ring-2', 'ring-emerald-400/50');
  setTimeout(() => {
    targetRow.classList.remove('bg-emerald-50/80', 'ring-2', 'ring-emerald-400/50');
  }, 2000);
}
