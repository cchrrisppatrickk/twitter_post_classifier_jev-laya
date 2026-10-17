/**
 * ==========================================================
 * DRAWER.JS - Inspección Lateral y Reclasificación Manual en Caliente
 * Subfase 5.11: Desacoplado de #richPostModal, enfocado exclusivamente en el Drawer
 * ==========================================================
 */

(function(window) {
  'use strict';

  let selectedPostForDrawer = null;

  // Referencias DOM del Drawer Lateral
  const postDrawer = document.getElementById('postDrawer');
  const drawerOverlay = document.getElementById('drawerOverlay');
  const closeDrawerBtn = document.getElementById('closeDrawerBtn');
  const drawerStatusBadge = document.getElementById('drawerStatusBadge');
  const drawerAuthorName = document.getElementById('drawerAuthorName');
  const drawerAuthorHandle = document.getElementById('drawerAuthorHandle');
  const drawerVerifiedBadge = document.getElementById('drawerVerifiedBadge');
  const drawerAvatar = document.getElementById('drawerAvatar');
  const drawerTweetText = document.getElementById('drawerTweetText');
  const drawerTweetTimestamp = document.getElementById('drawerTweetTimestamp');
  const drawerTweetCategoryBadge = document.getElementById('drawerTweetCategoryBadge');
  const drawerExternalLink = document.getElementById('drawerExternalLink');
  const drawerMediaPreviewContainer = document.getElementById('drawerMediaPreviewContainer');
  const drawerMediaThumb = document.getElementById('drawerMediaThumb');
  const drawerMediaPlayIcon = document.getElementById('drawerMediaPlayIcon');
  const drawerMediaBadge = document.getElementById('drawerMediaBadge');
  const drawerMediaDuration = document.getElementById('drawerMediaDuration');
  const drawerLikes = document.getElementById('drawerLikes');
  const drawerRetweets = document.getElementById('drawerRetweets');
  const drawerViews = document.getElementById('drawerViews');
  const drawerBookmarks = document.getElementById('drawerBookmarks');
  const drawerAffinityScore = document.getElementById('drawerAffinityScore');
  const drawerAffinityBar = document.getElementById('drawerAffinityBar');
  const drawerSplitPercentBar = document.getElementById('drawerSplitPercentBar');
  const drawerSplitLegend = document.getElementById('drawerSplitLegend');
  const drawerHybridTypeBadge = document.getElementById('drawerHybridTypeBadge');
  const drawerAiReasoning = document.getElementById('drawerAiReasoning');
  const drawerInferenceCost = document.getElementById('drawerInferenceCost');
  const drawerReclassifySelect = document.getElementById('drawerReclassifySelect');
  const drawerReclassifyBtn = document.getElementById('drawerReclassifyBtn');
  const drawerReclassifyBtnText = document.getElementById('drawerReclassifyBtnText');
  const drawerExpandModalBtn = document.getElementById('drawerExpandModalBtn');
  const drawerTaxonomyVersionBadge = document.getElementById('drawerTaxonomyVersionBadge');
  const drawerReclassCountBadge = document.getElementById('drawerReclassCountBadge');
  const drawerReclassifyLayaBtn = document.getElementById('drawerReclassifyLayaBtn');

  function getCategories() {
    return window.CATEGORIES || [];
  }

  function getRootFamilies() {
    return window.ROOT_FAMILIES || {};
  }

  function getCategoryColorMap() {
    return window.CATEGORY_COLOR_MAP || {};
  }

  function getFormatNumberK() {
    return typeof formatNumberK === 'function' ? formatNumberK : (n => n);
  }

  function getShowToast() {
    return typeof showToast === 'function' ? showToast : console.log;
  }

  /**
   * Agrupa las 48 categorías dinámicas por Familias Maestras (<optgroup>)
   * para mantener un orden visual limpio en el dropdown de reclasificación.
   * @param {HTMLSelectElement} selectEl 
   * @param {string} selectedCategoryId 
   */
  function populateCategorySelectWithOptgroups(selectEl, selectedCategoryId) {
    if (!selectEl) return;
    selectEl.innerHTML = '';

    const categories = getCategories();
    const rootFamilies = getRootFamilies();
    const groups = {};

    categories.forEach(cat => {
      const famId = cat.family_id || 'otros';
      if (!groups[famId]) groups[famId] = [];
      groups[famId].push(cat);
    });

    const famOrder = ['dev_tools', 'ia', 'modelado_3d', 'juegos', 'mangas', 'negocios_saas', 'otros'];
    const allFamKeys = Array.from(new Set([...famOrder, ...Object.keys(rootFamilies)]));

    allFamKeys.forEach(famId => {
      const cats = groups[famId];
      if (!cats || cats.length === 0) return;

      const fam = rootFamilies[famId] || { name: famId, colorHex: '#64748b' };
      const optgroup = document.createElement('optgroup');
      optgroup.label = `── ${fam.name} ──`;

      cats.forEach(c => {
        const opt = document.createElement('option');
        opt.value = c.id;
        opt.textContent = `[${c.code || 'CAT'}] ${c.name}`;
        if (c.id === selectedCategoryId) opt.selected = true;
        optgroup.appendChild(opt);
      });

      selectEl.appendChild(optgroup);
    });
  }

  /**
   * Abre el Drawer lateral e inspecciona a fondo una publicación
   * @param {Object} post 
   * @param {Object} category 
   */
  function openPostDrawer(post, category) {
    if (!post) return;
    selectedPostForDrawer = post;
    window.selectedPostForDrawer = post;

    const categories = getCategories();
    const colorMap = getCategoryColorMap();
    const formatK = getFormatNumberK();
    const currentCat = category || categories.find(c => c.id === post.category_id) || categories[0] || { name: 'Sin Categoría', colorHex: '#71717a' };

    // 1. Estado y badges
    if (drawerStatusBadge) {
      if (post.status === 'PENDING') {
        drawerStatusBadge.className = 'px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-100 text-amber-900 border border-amber-300 animate-pulse';
        drawerStatusBadge.textContent = 'PENDING (Abstención)';
      } else if (post.status === 'CLASSIFIED_MANUAL') {
        drawerStatusBadge.className = 'px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-blue-100 text-blue-900 border border-blue-300';
        drawerStatusBadge.textContent = 'CLASSIFIED_MANUAL';
      } else {
        drawerStatusBadge.className = 'px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-100 text-emerald-800 border border-emerald-300';
        drawerStatusBadge.textContent = 'CLASSIFIED (Auto)';
      }
    }

    // 2. Metadatos de Autor
    const authorNick = post.author_nick || post.author || 'Anon Dev';
    const authorHandle = post.author || 'anon_dev';
    if (drawerAuthorName) drawerAuthorName.textContent = authorNick;
    if (drawerAuthorHandle) drawerAuthorHandle.textContent = `@${authorHandle}`;
    if (drawerAvatar) drawerAvatar.textContent = authorNick.slice(0, 2).toUpperCase();
    if (drawerVerifiedBadge) {
      drawerVerifiedBadge.style.display = post.verified ? 'inline-block' : 'none';
    }

    // 3. Contenido y Enlaces
    if (drawerTweetText) drawerTweetText.textContent = post.text;
    if (drawerTweetTimestamp) drawerTweetTimestamp.textContent = post.date || post.created_at || '14 Oct 2026';
    if (drawerTweetCategoryBadge) {
      drawerTweetCategoryBadge.textContent = currentCat.name;
      drawerTweetCategoryBadge.style.color = currentCat.colorHex || '#1e293b';
    }

    const postUrl = post.post_url || `https://x.com/${authorHandle}/status/${post.id}`;
    if (drawerExternalLink) drawerExternalLink.href = postUrl;

    // 4. Multimedia Real
    const mediaUrls = post.media_urls || (post.media?.thumb ? [post.media.thumb] : []);
    const isVideo = post.media_type === 'video' || (mediaUrls.length > 0 && mediaUrls[0].includes('.mp4'));

    if (mediaUrls.length > 0) {
      if (drawerMediaThumb) drawerMediaThumb.src = mediaUrls[0];
      if (drawerMediaPlayIcon) drawerMediaPlayIcon.style.display = isVideo ? 'flex' : 'none';
      if (drawerMediaBadge && drawerMediaDuration) {
        drawerMediaDuration.textContent = isVideo ? 'MP4 · Video' : `${mediaUrls.length} Foto(s)`;
      }
      if (drawerMediaPreviewContainer) drawerMediaPreviewContainer.classList.remove('hidden');
    } else {
      if (drawerMediaPreviewContainer) drawerMediaPreviewContainer.classList.add('hidden');
    }

    // 5. Métricas de Engagement Verídicas
    if (drawerLikes) drawerLikes.textContent = formatK(post.likes || 0);
    if (drawerRetweets) drawerRetweets.textContent = formatK(post.retweets || 0);
    if (drawerViews) drawerViews.textContent = formatK(post.views || (post.likes * 16));
    if (drawerBookmarks) drawerBookmarks.textContent = formatK(post.bookmarks || 0);

    // 6. Barra de Afinidad
    const score = post.affinity_score || 50;
    if (drawerAffinityScore) {
      drawerAffinityScore.textContent = `${score}%`;
      drawerAffinityScore.className = score >= 70 ? 'text-sm font-bold text-emerald-600' : (score >= 45 ? 'text-sm font-bold text-amber-600' : 'text-sm font-bold text-rose-600');
    }
    if (drawerAffinityBar) {
      drawerAffinityBar.style.width = `${score}%`;
      drawerAffinityBar.className = score >= 70 ? 'bg-emerald-600 h-full transition-all duration-300' : (score >= 45 ? 'bg-amber-500 h-full transition-all duration-300' : 'bg-rose-500 h-full transition-all duration-300');
    }

    // 7. Barra de Composición Multicategoría
    if (drawerSplitPercentBar && drawerSplitLegend && drawerHybridTypeBadge) {
      drawerSplitPercentBar.innerHTML = '';
      drawerSplitLegend.innerHTML = '';

      if (post.is_hybrid && post.secondary_cat_id) {
        const secCat = categories.find(c => c.id === post.secondary_cat_id) || { name: post.secondary_cat_id, colorHex: '#f59e0b' };
        drawerHybridTypeBadge.textContent = `Híbrido ${post.primary_pct}/${post.secondary_pct}`;
        drawerHybridTypeBadge.className = 'px-1.5 py-0.5 rounded text-[9px] bg-amber-100 text-amber-900 border border-amber-300 font-mono font-bold';

        const priSegment = document.createElement('div');
        priSegment.style.width = `${post.primary_pct}%`;
        priSegment.style.backgroundColor = currentCat.colorHex || colorMap[post.category_id] || '#0369a1';
        priSegment.className = 'h-full transition-all duration-300';
        drawerSplitPercentBar.appendChild(priSegment);

        const secSegment = document.createElement('div');
        secSegment.style.width = `${post.secondary_pct}%`;
        secSegment.style.backgroundColor = secCat.colorHex || colorMap[post.secondary_cat_id] || '#f59e0b';
        secSegment.className = 'h-full transition-all duration-300';
        drawerSplitPercentBar.appendChild(secSegment);

        drawerSplitLegend.innerHTML = `
          <div class="flex items-center gap-1">
            <span class="w-2.5 h-2.5 rounded-sm shrink-0" style="background-color: ${currentCat.colorHex}"></span>
            <span class="font-bold text-stone-800">${post.primary_pct}% ${currentCat.name}</span>
          </div>
          <span class="text-stone-300">·</span>
          <div class="flex items-center gap-1">
            <span class="w-2.5 h-2.5 rounded-sm shrink-0" style="background-color: ${secCat.colorHex}"></span>
            <span class="font-bold text-stone-800">${post.secondary_pct}% ${secCat.name}</span>
          </div>
        `;
      } else {
        drawerHybridTypeBadge.textContent = 'Puro 100%';
        drawerHybridTypeBadge.className = 'px-1.5 py-0.5 rounded text-[9px] bg-stone-100 text-stone-700 border border-stone-300 font-mono font-bold';

        const singleSegment = document.createElement('div');
        singleSegment.style.width = '100%';
        singleSegment.style.backgroundColor = currentCat.colorHex || colorMap[post.category_id] || '#0369a1';
        singleSegment.className = 'h-full transition-all duration-300';
        drawerSplitPercentBar.appendChild(singleSegment);

        drawerSplitLegend.innerHTML = `
          <div class="flex items-center gap-1">
            <span class="w-2.5 h-2.5 rounded-sm shrink-0" style="background-color: ${currentCat.colorHex}"></span>
            <span class="font-bold text-stone-800">100% ${currentCat.name}</span>
          </div>
        `;
      }
    }

    // 8. Razonamiento y Costo
    if (drawerAiReasoning) {
      drawerAiReasoning.textContent = post.ai_reasoning || `Clasificado semánticamente en "${currentCat.name}" por análisis de vocabulario y señales estructurales.`;
    }
    if (drawerInferenceCost) {
      drawerInferenceCost.textContent = `$0.00000 (Laya PyTorch CPU)`;
    }

    // 9. Selector con optgroups
    populateCategorySelectWithOptgroups(drawerReclassifySelect, post.category_id);
    if (drawerReclassifyBtnText) {
      drawerReclassifyBtnText.textContent = post.status === 'PENDING' ? 'Confirmar y Resolver PENDING' : 'Mover Categoría';
    }

    // 10. Versionado taxonómico y contador de reclasificaciones (Fase 5.12)
    if (drawerTaxonomyVersionBadge) {
      drawerTaxonomyVersionBadge.textContent = post.taxonomy_version ? `v${post.taxonomy_version}` : 'v2.1.0';
    }
    if (drawerReclassCountBadge) {
      drawerReclassCountBadge.textContent = `#${post.reclassification_count || 0}`;
    }

    // Mostrar Drawer
    if (postDrawer) postDrawer.classList.remove('translate-x-full');
    if (drawerOverlay) drawerOverlay.classList.remove('hidden');
  }

  /**
   * Cierra el Drawer lateral
   */
  function closePostDrawer() {
    if (postDrawer) postDrawer.classList.add('translate-x-full');
    if (drawerOverlay) drawerOverlay.classList.add('hidden');
    selectedPostForDrawer = null;
    window.selectedPostForDrawer = null;
  }

  /**
   * Reclasifica un post en caliente invocando POST /api/posts/{id}/override
   * @param {Object} post 
   * @param {string} newCategoryId 
   */
  async function handlePostOverride(post, newCategoryId) {
    if (!post || !newCategoryId) return;
    const categories = getCategories();
    const toast = getShowToast();
    const targetCat = categories.find(c => c.id === newCategoryId);
    if (!targetCat) return;

    try {
      const response = await fetch(`/api/posts/${encodeURIComponent(post.id)}/override`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          primary_category: newCategoryId,
          secondary_categories: (post.secondary_categories || []).map(s => typeof s === 'string' ? s : s.id),
          status: 'CLASSIFIED_MANUAL'
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: No se pudo completar la reclasificación.`);
      }

      const data = await response.json();

      // Actualizar estado en memoria
      post.category_id = newCategoryId;
      post.primary_category = newCategoryId;
      post.status = 'CLASSIFIED_MANUAL';
      post.affinity_score = 100;
      post.ai_reasoning = `Reclasificado manualmente por el analista hacia "${targetCat.name}".`;

      if (data.post) {
        post.updated_at = data.post.updated_at;
      }

      // Actualizar vista completa y drawer si están abiertos
      if (typeof renderMatrix === 'function') renderMatrix();
      openPostDrawer(post, targetCat);

      const richModal = document.getElementById('richPostModal');
      if (richModal && !richModal.classList.contains('hidden')) {
        if (window.RichPostModal && typeof window.RichPostModal.open === 'function') {
          window.RichPostModal.open(post);
        } else if (typeof openRichPostModal === 'function') {
          openRichPostModal(post);
        }
      }

      toast(`✓ Reclasificado a [${targetCat.name}] (SQLite WAL actualizado)`);
    } catch (err) {
      console.error('Error al ejecutar reclasificación:', err);
      toast(`❌ Error al reclasificar: ${err.message}`);
    }
  }

  // Bindings del Drawer
  if (closeDrawerBtn) closeDrawerBtn.addEventListener('click', closePostDrawer);

  if (drawerOverlay) {
    drawerOverlay.addEventListener('click', () => {
      closePostDrawer();
      if (window.RichPostModal && typeof window.RichPostModal.close === 'function') {
        window.RichPostModal.close();
      } else if (typeof closeRichModal === 'function') {
        closeRichModal();
      }
    });
  }

  if (drawerReclassifyBtn) {
    drawerReclassifyBtn.addEventListener('click', () => {
      if (!selectedPostForDrawer) return;
      const newCatId = drawerReclassifySelect.value;
      handlePostOverride(selectedPostForDrawer, newCatId);
    });
  }

  if (drawerExpandModalBtn) {
    drawerExpandModalBtn.addEventListener('click', () => {
      const posts = window.currentScrapedPosts || [];
      const post = selectedPostForDrawer || (posts.length > 0 ? posts[0] : null);
      if (post) {
        if (window.RichPostModal && typeof window.RichPostModal.open === 'function') {
          window.RichPostModal.open(post);
        } else if (typeof openRichPostModal === 'function') {
          openRichPostModal(post);
        }
      } else {
        const toast = getShowToast();
        toast('Selecciona primero una publicación en la Matriz para abrir la Vista Completa');
      }
    });
  }

  // Re-evaluar con Laya actual (A/B Diff) abriendo directamente la pestaña Historial & Simulación
  if (drawerReclassifyLayaBtn) {
    drawerReclassifyLayaBtn.addEventListener('click', () => {
      const posts = window.currentScrapedPosts || [];
      const post = selectedPostForDrawer || (posts.length > 0 ? posts[0] : null);
      if (!post) {
        const toast = getShowToast();
        toast('Selecciona primero una publicación en la Matriz para re-evaluar.');
        return;
      }
      if (window.RichPostModal && typeof window.RichPostModal.openWithTab === 'function') {
        window.RichPostModal.openWithTab(post, 'history', true);
      } else if (window.RichPostModal && typeof window.RichPostModal.open === 'function') {
        window.RichPostModal.open(post, 'history', true);
      } else if (typeof openRichPostModalWithTab === 'function') {
        openRichPostModalWithTab(post, 'history', true);
      } else if (typeof openRichPostModal === 'function') {
        openRichPostModal(post, 'history', true);
      }
    });
  }

  if (drawerMediaPreviewContainer) {
    drawerMediaPreviewContainer.addEventListener('click', () => {
      const posts = window.currentScrapedPosts || [];
      const post = selectedPostForDrawer || (posts.length > 0 ? posts[0] : null);
      if (post) {
        if (window.RichPostModal && typeof window.RichPostModal.open === 'function') {
          window.RichPostModal.open(post);
        } else if (typeof openRichPostModal === 'function') {
          openRichPostModal(post);
        }
      }
    });
  }

  // Exposición en namespace global
  window.openPostDrawer = openPostDrawer;
  window.closePostDrawer = closePostDrawer;
  window.handlePostOverride = handlePostOverride;
  window.populateCategorySelectWithOptgroups = populateCategorySelectWithOptgroups;

})(window);
