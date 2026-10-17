/**
 * RICH_POST_MODAL.JS - Vista Completa de Auditoría y Multimedia (Laya Engine v2.1.0)
 * Reproductor de video MP4, galerías, desglose semántico System 1, visor dual JSON y navegación secuencial.
 */

(function(window) {
  'use strict';

  // Selectores DOM
  const richPostModal = document.getElementById('richPostModal');
  const closeRichModalBtn = document.getElementById('closeRichModalBtn');
  const modalPrevPostBtn = document.getElementById('modalPrevPostBtn');
  const modalNextPostBtn = document.getElementById('modalNextPostBtn');
  const modalNavCounter = document.getElementById('modalNavCounter');
  const modalStatusBadge = document.getElementById('modalStatusBadge');
  const modalCategoryBadge = document.getElementById('modalCategoryBadge');
  const modalPostIdSubtitle = document.getElementById('modalPostIdSubtitle');
  const modalExternalPostLink = document.getElementById('modalExternalPostLink');
  const modalDirectMediaLink = document.getElementById('modalDirectMediaLink');
  const modalUserAvatar = document.getElementById('modalUserAvatar');
  const modalUserName = document.getElementById('modalUserName');
  const modalUserHandle = document.getElementById('modalUserHandle');
  const modalUserVerified = document.getElementById('modalUserVerified');
  const modalTweetBody = document.getElementById('modalTweetBody');
  const modalFormattedDate = document.getElementById('modalFormattedDate');
  const modalMediaContainer = document.getElementById('modalMediaContainer');
  const modalHtmlVideoPlayer = document.getElementById('modalHtmlVideoPlayer');
  const modalImagesGallery = document.getElementById('modalImagesGallery');
  const modalCorsNotice = document.getElementById('modalCorsNotice');
  const modalCorsExternalVideoBtn = document.getElementById('modalCorsExternalVideoBtn');
  const modalMetricReplies = document.getElementById('modalMetricReplies');
  const modalMetricRetweets = document.getElementById('modalMetricRetweets');
  const modalMetricLikes = document.getElementById('modalMetricLikes');
  const modalMetricBookmarks = document.getElementById('modalMetricBookmarks');
  const modalMetricViews = document.getElementById('modalMetricViews');

  // Selectores Pestaña Semántica
  const semanticTopPickName = document.getElementById('semanticTopPickName');
  const semanticPrimaryScoreBadge = document.getElementById('semanticPrimaryScoreBadge');
  const semanticPriCategoryLabel = document.getElementById('semanticPriCategoryLabel');
  const semanticPriCategoryCode = document.getElementById('semanticPriCategoryCode');
  const semanticPriColorDot = document.getElementById('semanticPriColorDot');
  const semanticPriScoreBar = document.getElementById('semanticPriScoreBar');
  const semanticSecondaryList = document.getElementById('semanticSecondaryList');
  const semanticFamilyBadge = document.getElementById('semanticFamilyBadge');
  const semanticFamilyName = document.getElementById('semanticFamilyName');
  const semanticFamilyIconWrap = document.getElementById('semanticFamilyIconWrap');
  const semanticAssetsContainer = document.getElementById('semanticAssetsContainer');
  const semanticHookType = document.getElementById('semanticHookType');
  const semanticFormatConf = document.getElementById('semanticFormatConf');
  const semanticTechDensity = document.getElementById('semanticTechDensity');
  const semanticLatencyVal = document.getElementById('semanticLatencyVal');
  const semanticEngineVal = document.getElementById('semanticEngineVal');
  const modalAuditBanner = document.getElementById('modalAuditBanner');
  const modalAuditNotes = document.getElementById('modalAuditNotes');

  // Selectores Pestaña JSON
  const rawJsonCodeBlock = document.getElementById('rawJsonCodeBlock');
  const subtabJsonScraping = document.getElementById('subtabJsonScraping');
  const subtabJsonLaya = document.getElementById('subtabJsonLaya');
  const copyRawJsonBtn = document.getElementById('copyRawJsonBtn');
  const downloadRawJsonBtn = document.getElementById('downloadRawJsonBtn');

  // Selectores Reclasificación
  const modalReclassifySelect = document.getElementById('modalReclassifySelect');
  const modalReclassifyBtn = document.getElementById('modalReclassifyBtn');

  // Selectores Pestaña Historial y Comparativa A/B (Subfase 5.12.4)
  const modalTabHistoryBtn = document.getElementById('modalTabHistoryBtn');
  const modalHistoryCountBadge = document.getElementById('modalHistoryCountBadge');
  const tabContentHistory = document.getElementById('tabContentHistory');
  const modalTriggerDryRunBtn = document.getElementById('modalTriggerDryRunBtn');
  const modalDiffLoading = document.getElementById('modalDiffLoading');
  const modalDiffWidget = document.getElementById('modalDiffWidget');
  const modalDiffDeltaBadge = document.getElementById('modalDiffDeltaBadge');
  const modalDiffPrevVersionBadge = document.getElementById('modalDiffPrevVersionBadge');
  const modalDiffPrevCatDot = document.getElementById('modalDiffPrevCatDot');
  const modalDiffPrevCatName = document.getElementById('modalDiffPrevCatName');
  const modalDiffPrevScore = document.getElementById('modalDiffPrevScore');
  const modalDiffPrevStatus = document.getElementById('modalDiffPrevStatus');
  const modalDiffNewVersionBadge = document.getElementById('modalDiffNewVersionBadge');
  const modalDiffNewCatDot = document.getElementById('modalDiffNewCatDot');
  const modalDiffNewCatName = document.getElementById('modalDiffNewCatName');
  const modalDiffNewScore = document.getElementById('modalDiffNewScore');
  const modalDiffNewLatency = document.getElementById('modalDiffNewLatency');
  const modalDiffReasoningText = document.getElementById('modalDiffReasoningText');
  const modalDiffDismissBtn = document.getElementById('modalDiffDismissBtn');
  const modalDiffApplyBtn = document.getElementById('modalDiffApplyBtn');
  const modalHistoryListContainer = document.getElementById('modalHistoryListContainer');
  const modalRefreshHistoryBtn = document.getElementById('modalRefreshHistoryBtn');

  // Estado interno del modal
  let currentModalPostIndex = 0;
  let currentActiveJsonSubtab = 'scraping';
  let lastSimulatedDiff = null;

  function getFormatNumberK() {
    return typeof formatNumberK === 'function' ? formatNumberK : (n => n);
  }

  function getShowToast() {
    return typeof showToast === 'function' ? showToast : console.log;
  }

  function getCategories() {
    return window.CATEGORIES || [];
  }

  function getRootFamilies() {
    return window.ROOT_FAMILIES || {};
  }

  function getCurrentScrapedPosts() {
    return window.currentScrapedPosts || [];
  }

  const RichPostModal = {
    /**
     * Conmuta activamente entre las 4 pestañas del modal
     * @param {string} tabName ('preview' | 'semantics' | 'json' | 'history')
     */
    switchTab(tabName) {
      document.querySelectorAll('#richPostModal .tab-btn').forEach(b => {
        const isTarget = b.getAttribute('data-tab') === tabName;
        b.classList.toggle('active-tab', isTarget);
        b.classList.toggle('text-stone-500', !isTarget);
      });
      const pTab = document.getElementById('tabContentPreview');
      const sTab = document.getElementById('tabContentSemantics');
      const jTab = document.getElementById('tabContentJson');
      const hTab = document.getElementById('tabContentHistory');

      if (pTab) pTab.classList.toggle('hidden', tabName !== 'preview');
      if (sTab) sTab.classList.toggle('hidden', tabName !== 'semantics');
      if (jTab) jTab.classList.toggle('hidden', tabName !== 'json');
      if (hTab) hTab.classList.toggle('hidden', tabName !== 'history');

      // Pausar video si salimos de la pestaña multimedia
      if (tabName !== 'preview' && modalHtmlVideoPlayer) {
        modalHtmlVideoPlayer.pause();
      }

      if (tabName === 'history') {
        const posts = getCurrentScrapedPosts();
        const currentPost = posts[currentModalPostIndex] || window.selectedPostForDrawer;
        if (currentPost) {
          RichPostModal.loadPostHistory(currentPost.id);
        }
      }
    },

    /**
     * Abre el modal directamente en una pestaña específica con opción de simular A/B
     */
    openWithTab(post, tabName = 'history', triggerSim = false) {
      this.open(post, tabName, triggerSim);
    },

    /**
     * Abre el modal de vista completa cargando el post proporcionado
     * @param {Object} post 
     * @param {string} [activeTab='preview']
     * @param {boolean} [autoTriggerDryRun=false]
     */
    open(post, activeTab = 'preview', autoTriggerDryRun = false) {
      const posts = getCurrentScrapedPosts();
      const categories = getCategories();
      const rootFamilies = getRootFamilies();
      const formatK = getFormatNumberK();
      const toast = getShowToast();

      if (!post) {
        post = window.selectedPostForDrawer || (posts.length > 0 ? posts[0] : null);
      }
      if (!post) {
        toast('Selecciona primero una publicación para abrir la Vista Completa');
        return;
      }
      window.selectedPostForDrawer = post;

      // Replegar el drawer lateral para dejar espacio libre a la vista completa
      const postDrawer = document.getElementById('postDrawer');
      const drawerOverlay = document.getElementById('drawerOverlay');
      if (postDrawer) postDrawer.classList.add('translate-x-full');
      if (drawerOverlay) drawerOverlay.classList.add('hidden');

      // Localizar índice en currentScrapedPosts para navegación secuencial
      currentModalPostIndex = posts.findIndex(p => String(p.id) === String(post.id));
      if (currentModalPostIndex === -1) currentModalPostIndex = 0;

      const currentCat = categories.find(c => c.id === post.category_id) || categories[0] || { name: 'Sin Categoría', code: 'N/A', colorHex: '#71717a', family_id: 'otros' };
      const fam = rootFamilies[currentCat.family_id] || { name: currentCat.family_id || 'General', colorHex: '#71717a', icon: 'fa-folder' };

      // 1. Cabecera y Contador Secuencial
      if (modalStatusBadge) {
        if (post.status === 'PENDING') {
          modalStatusBadge.className = 'px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-100 text-amber-900 border border-amber-300 animate-pulse';
          modalStatusBadge.textContent = 'PENDING (Abstención)';
        } else if (post.status === 'CLASSIFIED_MANUAL') {
          modalStatusBadge.className = 'px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-blue-100 text-blue-900 border border-blue-300';
          modalStatusBadge.textContent = 'CLASSIFIED_MANUAL (Auditoría Humana)';
        } else {
          modalStatusBadge.className = 'px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-100 text-emerald-800 border border-emerald-300';
          modalStatusBadge.textContent = 'CLASSIFIED (Laya AI)';
        }
      }

      if (modalCategoryBadge) {
        modalCategoryBadge.textContent = `${currentCat.name} (${currentCat.code || 'CAT'})`;
        modalCategoryBadge.style.color = currentCat.colorHex || '#1e293b';
      }
      if (modalPostIdSubtitle) modalPostIdSubtitle.textContent = `Post ID: ${post.id}`;
      if (modalNavCounter) {
        modalNavCounter.textContent = `${currentModalPostIndex + 1} / ${posts.length}`;
      }

      const postUrl = post.post_url || `https://x.com/${post.author || 'anon_dev'}/status/${post.id}`;
      if (modalExternalPostLink) modalExternalPostLink.href = postUrl;

      // 2. Pestaña 1: Visualización Fiel & Multimedia
      const authorNick = post.author_nick || post.author || 'Anon Dev';
      const authorHandle = post.author || 'anon_dev';
      if (modalUserName) modalUserName.textContent = authorNick;
      if (modalUserHandle) modalUserHandle.textContent = `@${authorHandle}`;
      if (modalUserAvatar) modalUserAvatar.textContent = authorNick.slice(0, 2).toUpperCase();
      if (modalUserVerified) modalUserVerified.style.display = post.verified ? 'inline-block' : 'none';
      if (modalTweetBody) modalTweetBody.textContent = post.text;
      if (modalFormattedDate) modalFormattedDate.textContent = post.date || post.created_at || '14 oct. 2026';

      // Multimedia Real
      const mediaUrls = post.media_urls || (post.media?.thumb ? [post.media.thumb] : []);
      const isVideo = post.media_type === 'video' || (mediaUrls.length > 0 && mediaUrls[0].includes('.mp4'));

      // Detener reproductor anterior
      if (modalHtmlVideoPlayer) {
        modalHtmlVideoPlayer.pause();
        modalHtmlVideoPlayer.removeAttribute('src');
        modalHtmlVideoPlayer.load();
      }

      if (modalCorsNotice) modalCorsNotice.classList.add('hidden');

      if (mediaUrls.length > 0) {
        if (isVideo) {
          if (modalHtmlVideoPlayer) {
            modalHtmlVideoPlayer.src = mediaUrls[0];
            modalHtmlVideoPlayer.classList.remove('hidden');
            modalHtmlVideoPlayer.onerror = () => {
              if (modalCorsNotice) modalCorsNotice.classList.remove('hidden');
            };
            modalHtmlVideoPlayer.onloadeddata = () => {
              if (modalCorsNotice) modalCorsNotice.classList.add('hidden');
            };
          }
          if (modalImagesGallery) modalImagesGallery.classList.add('hidden');
          if (modalCorsExternalVideoBtn) modalCorsExternalVideoBtn.href = mediaUrls[0];
          if (modalDirectMediaLink) {
            modalDirectMediaLink.href = mediaUrls[0];
            modalDirectMediaLink.classList.remove('hidden');
          }
        } else {
          if (modalHtmlVideoPlayer) modalHtmlVideoPlayer.classList.add('hidden');
          if (modalImagesGallery) {
            modalImagesGallery.classList.remove('hidden');
            if (mediaUrls.length === 1) {
              modalImagesGallery.className = 'grid grid-cols-1 gap-2 rounded-xl overflow-hidden max-h-[420px]';
            } else {
              modalImagesGallery.className = 'grid grid-cols-2 gap-2 rounded-xl overflow-hidden max-h-[420px]';
            }
            modalImagesGallery.innerHTML = mediaUrls.map(url => `
              <a href="${url}" target="_blank" class="block overflow-hidden rounded-lg group bg-stone-900 aspect-video">
                <img src="${url}" alt="Foto scraping" class="w-full h-full object-cover group-hover:scale-105 transition duration-300" />
              </a>
            `).join('');
          }
          if (modalDirectMediaLink) {
            modalDirectMediaLink.href = mediaUrls[0];
            modalDirectMediaLink.classList.remove('hidden');
          }
        }
        if (modalMediaContainer) modalMediaContainer.classList.remove('hidden');
      } else {
        if (modalHtmlVideoPlayer) modalHtmlVideoPlayer.classList.add('hidden');
        if (modalImagesGallery) modalImagesGallery.classList.add('hidden');
        if (modalMediaContainer) modalMediaContainer.classList.add('hidden');
        if (modalDirectMediaLink) modalDirectMediaLink.classList.add('hidden');
      }

      // Métricas
      if (modalMetricReplies) modalMetricReplies.textContent = formatK(post.replies || 0);
      if (modalMetricRetweets) modalMetricRetweets.textContent = formatK(post.retweets || 0);
      if (modalMetricLikes) modalMetricLikes.textContent = formatK(post.likes || 0);
      if (modalMetricBookmarks) modalMetricBookmarks.textContent = formatK(post.bookmarks || 0);
      if (modalMetricViews) modalMetricViews.textContent = formatK(post.views || (post.likes * 16));

      // 3. Pestaña 2: Desglose Semántico Fiel Laya System 1
      if (semanticTopPickName) semanticTopPickName.textContent = currentCat.name;
      if (semanticPrimaryScoreBadge) semanticPrimaryScoreBadge.textContent = `${post.affinity_score}%`;
      if (semanticPriCategoryLabel) semanticPriCategoryLabel.textContent = currentCat.name;
      if (semanticPriCategoryCode) semanticPriCategoryCode.textContent = currentCat.code || 'CAT';
      if (semanticPriColorDot) semanticPriColorDot.style.backgroundColor = currentCat.colorHex || '#10b981';
      if (semanticPriScoreBar) {
        semanticPriScoreBar.style.width = `${post.affinity_score}%`;
        semanticPriScoreBar.style.backgroundColor = currentCat.colorHex || '#10b981';
      }

      // Banner de Auditoría Humana
      if (modalAuditBanner) {
        if (post.status === 'CLASSIFIED_MANUAL') {
          modalAuditBanner.classList.remove('hidden');
          if (modalAuditNotes) {
            modalAuditNotes.textContent = post.ai_reasoning || 'Reclasificado manualmente por el supervisor analista.';
          }
        } else {
          modalAuditBanner.classList.add('hidden');
        }
      }

      // Categorías Secundarias en Competencia
      if (semanticSecondaryList) {
        semanticSecondaryList.innerHTML = '';
        const secs = post.secondary_categories || [];

        if (secs.length > 0) {
          secs.forEach(sec => {
            const secCat = categories.find(c => c.id === sec.id) || { name: sec.id, code: 'SEC', colorHex: '#f59e0b' };
            const scorePct = Math.round((sec.score > 1 ? sec.score : sec.score * 100));

            const row = document.createElement('div');
            row.className = 'flex items-center gap-3 p-2 bg-stone-50 rounded-lg border border-stone-200';
            row.innerHTML = `
              <span class="w-2.5 h-2.5 rounded-full shrink-0" style="background-color: ${secCat.colorHex || '#f59e0b'}"></span>
              <span class="w-32 font-bold text-stone-800 truncate" title="${secCat.name}">${secCat.name}</span>
              <span class="px-1.5 py-0.5 rounded bg-stone-200 text-stone-600 font-mono text-[10px] font-bold">${secCat.code || 'CAT'}</span>
              <div class="flex-1 bg-stone-200 h-2 rounded-full overflow-hidden">
                <div class="h-full rounded-full transition-all duration-300" style="width: ${scorePct}%; background-color: ${secCat.colorHex || '#f59e0b'}"></div>
              </div>
              <span class="w-10 text-right font-bold text-stone-800">${scorePct}%</span>
            `;
            semanticSecondaryList.appendChild(row);
          });
        } else {
          semanticSecondaryList.innerHTML = `
            <div class="p-3 bg-stone-50 rounded-lg text-stone-500 text-xs italic border border-stone-200">
              ✓ Clasificación unívoca (Puro 100%): Sin categorías secundarias competitivas.
            </div>
          `;
        }
      }

      // Familia Raíz
      if (semanticFamilyBadge) semanticFamilyBadge.textContent = fam.name;
      if (semanticFamilyName) semanticFamilyName.textContent = fam.name;
      if (semanticFamilyIconWrap) {
        semanticFamilyIconWrap.innerHTML = `<i class="fa-solid ${fam.icon || 'fa-folder'}" style="color: ${fam.colorHex}"></i>`;
      }

      // Activos y Dominios Detectados (Assets)
      if (semanticAssetsContainer) {
        semanticAssetsContainer.innerHTML = '';
        const assets = post.assets || [];
        if (assets.length > 0) {
          assets.forEach(asset => {
            const chip = document.createElement('span');
            chip.className = 'px-2.5 py-1 rounded-md text-[11px] font-mono font-semibold bg-stone-100 text-stone-800 border border-stone-200 flex items-center gap-1.5 shadow-xs';
            
            let icon = 'fa-tag';
            if (asset.includes('github')) icon = 'fa-brands fa-github text-stone-900';
            else if (asset.includes('blender')) icon = 'fa-cube text-amber-600';
            else if (asset.includes('mixamo')) icon = 'fa-person-running text-sky-600';
            else if (asset.includes('huggingface')) icon = 'fa-robot text-yellow-600';
            else if (asset.includes('colab')) icon = 'fa-code text-orange-500';

            chip.innerHTML = `<i class="${icon}"></i> <span>${asset}</span>`;
            semanticAssetsContainer.appendChild(chip);
          });
        } else {
          semanticAssetsContainer.innerHTML = `
            <span class="text-stone-400 italic text-[11px]">No se detectaron herramientas externas ni repositorios en el texto.</span>
          `;
        }
      }

      // Formato y Profundidad Técnica
      if (semanticHookType) semanticHookType.textContent = (post.format || 'other').replace(/_/g, ' ').toUpperCase();
      if (semanticFormatConf) {
        const fConf = Math.round((post.format_confidence || 0.85) * 100);
        semanticFormatConf.textContent = `Confianza: ${fConf}%`;
      }
      if (semanticTechDensity) {
        semanticTechDensity.textContent = `${post.technical_depth ? post.technical_depth.toFixed(1) : '2.5'} / 5.0`;
      }
      if (semanticLatencyVal) {
        semanticLatencyVal.textContent = `${post.inference_latency_ms ? post.inference_latency_ms.toFixed(1) : '28.4'} ms`;
      }
      if (semanticEngineVal) semanticEngineVal.textContent = post.engine_used || 'laya-cpu';

      // 4. Pestaña 3: Raw JSON
      this.renderRawJson(post);

      // 5. Barra Inferior de Reclasificación
      if (typeof populateCategorySelectWithOptgroups === 'function' && modalReclassifySelect) {
        populateCategorySelectWithOptgroups(modalReclassifySelect, post.category_id);
      }

      // 6. Reset y carga de Historial y Diff A/B
      if (modalDiffWidget) modalDiffWidget.classList.add('hidden');
      if (modalDiffLoading) modalDiffLoading.classList.add('hidden');
      lastSimulatedDiff = null;

      if (modalHistoryCountBadge) {
        modalHistoryCountBadge.textContent = post.reclassification_count !== undefined ? post.reclassification_count : '0';
      }
      this.loadPostHistory(post.id);

      // 7. Conmutar a la pestaña solicitada
      this.switchTab(activeTab);

      // Si se solicita simulación automática A/B
      if (autoTriggerDryRun) {
        this.triggerDiffSimulation(post);
      }

      // Mostrar modal
      if (richPostModal) richPostModal.classList.remove('hidden');
    },

    /**
     * Renderiza el visor dual de Raw JSON con soporte prioritario para raw_json y classification_json
     */
    renderRawJson(post) {
      if (!rawJsonCodeBlock) return;
      const posts = getCurrentScrapedPosts();
      const currentPost = post || posts[currentModalPostIndex] || window.selectedPostForDrawer;
      if (!currentPost) return;

      if (currentActiveJsonSubtab === 'scraping') {
        let scrapingJson = null;
        if (currentPost.raw_json) {
          try {
            scrapingJson = typeof currentPost.raw_json === 'string' ? JSON.parse(currentPost.raw_json) : currentPost.raw_json;
          } catch (_) {}
        }
        if (!scrapingJson) {
          scrapingJson = currentPost.raw_scraping || {
            tweet_id: currentPost.id,
            post_url: currentPost.post_url,
            author: {
              name: currentPost.author_name || currentPost.author,
              nick: currentPost.author_nick || currentPost.author,
              verified: !!currentPost.verified
            },
            content: currentPost.text,
            date: currentPost.date || currentPost.created_at,
            metrics: {
              likes: currentPost.likes,
              retweets: currentPost.retweets,
              views: currentPost.views,
              bookmarks: currentPost.bookmarks,
              replies: currentPost.replies
            },
            media_type: currentPost.media_type,
            media_urls: currentPost.media_urls
          };
        }
        rawJsonCodeBlock.textContent = JSON.stringify(scrapingJson, null, 2);
      } else {
        let layaJson = null;
        if (currentPost.classification_json) {
          try {
            layaJson = typeof currentPost.classification_json === 'string' ? JSON.parse(currentPost.classification_json) : currentPost.classification_json;
          } catch (_) {}
        }
        if (!layaJson) {
          layaJson = currentPost.laya_output || {
            tweet_id: currentPost.id,
            primary_category: currentPost.category_id,
            affinity_score: (currentPost.affinity_score || 50) / 100,
            secondary_categories: currentPost.secondary_categories || [],
            format: currentPost.format || 'other',
            format_confidence: currentPost.format_confidence || 0.85,
            technical_depth: currentPost.technical_depth || 2.5,
            assets: currentPost.assets || [],
            status: currentPost.status || 'CLASSIFIED',
            engine_used: currentPost.engine_used || 'laya-cpu',
            inference_latency_ms: currentPost.inference_latency_ms || 28.4
          };
        }
        rawJsonCodeBlock.textContent = JSON.stringify(layaJson, null, 2);
      }
    },

    /**
     * Ejecuta simulación de reclasificación A/B (Dry-Run) con Laya System 1
     */
    async triggerDiffSimulation(post) {
      const posts = getCurrentScrapedPosts();
      const currentPost = post || posts[currentModalPostIndex] || window.selectedPostForDrawer;
      if (!currentPost) return;
      const toast = getShowToast();
      const categories = getCategories();

      if (modalDiffLoading) modalDiffLoading.classList.remove('hidden');
      if (modalDiffWidget) modalDiffWidget.classList.add('hidden');

      try {
        let diffData = null;
        if (window.API?.posts?.reclassify) {
          diffData = await window.API.posts.reclassify(currentPost.id, true);
        } else {
          const res = await fetch(`/api/posts/${encodeURIComponent(currentPost.id)}/reclassify`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ dry_run: true })
          });
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          diffData = await res.json();
        }

        lastSimulatedDiff = diffData;

        // Renderizar datos en modalDiffWidget
        const prev = diffData.previous || {};
        const curr = diffData.current || {};
        const prevCatId = prev.primary_category || diffData.previous_category;
        const newCatId = curr.primary_category || diffData.new_category;

        const prevCat = categories.find(c => c.id === prevCatId) || { name: prev.category_label || prevCatId, colorHex: prev.color_hex || '#71717a' };
        const newCat = categories.find(c => c.id === newCatId) || { name: curr.category_label || newCatId, colorHex: curr.color_hex || '#4f46e5' };

        if (modalDiffPrevVersionBadge) modalDiffPrevVersionBadge.textContent = prev.taxonomy_version ? `v${prev.taxonomy_version}` : (diffData.previous_version || 'v2.0.0');
        if (modalDiffPrevCatName) modalDiffPrevCatName.textContent = prevCat.name;
        if (modalDiffPrevCatDot) modalDiffPrevCatDot.style.backgroundColor = prevCat.colorHex || '#71717a';
        const pScore = prev.affinity_score !== undefined ? prev.affinity_score : (diffData.previous_score || 0);
        if (modalDiffPrevScore) modalDiffPrevScore.textContent = `${Math.round(pScore > 1 ? pScore : pScore * 100)}%`;
        if (modalDiffPrevStatus) modalDiffPrevStatus.textContent = prev.status || diffData.previous_status || currentPost.status || 'CLASSIFIED';

        if (modalDiffNewVersionBadge) modalDiffNewVersionBadge.textContent = curr.taxonomy_version ? `v${curr.taxonomy_version}` : (diffData.new_version || 'v2.1.0');
        if (modalDiffNewCatName) modalDiffNewCatName.textContent = newCat.name;
        if (modalDiffNewCatDot) modalDiffNewCatDot.style.backgroundColor = newCat.colorHex || '#4f46e5';
        const nScore = curr.affinity_score !== undefined ? curr.affinity_score : (diffData.new_score || 0);
        if (modalDiffNewScore) modalDiffNewScore.textContent = `${Math.round(nScore > 1 ? nScore : nScore * 100)}%`;
        const lat = curr.inference_latency_ms !== undefined ? curr.inference_latency_ms : (diffData.inference_latency_ms || 28.4);
        if (modalDiffNewLatency) modalDiffNewLatency.textContent = `${lat.toFixed(1)} ms`;

        // Delta
        const rawDelta = diffData.delta_affinity !== undefined ? diffData.delta_affinity : (diffData.score_delta !== undefined ? diffData.score_delta : (nScore - pScore));
        const deltaPct = Math.round(rawDelta > 1 ? rawDelta : rawDelta * 100);
        if (modalDiffDeltaBadge) {
          modalDiffDeltaBadge.textContent = `Delta: ${deltaPct > 0 ? '+' : ''}${deltaPct}%`;
          if (deltaPct > 0) {
            modalDiffDeltaBadge.className = 'px-2 py-0.5 rounded font-mono font-bold text-[10px] bg-emerald-100 text-emerald-800 border border-emerald-300';
          } else if (deltaPct < 0) {
            modalDiffDeltaBadge.className = 'px-2 py-0.5 rounded font-mono font-bold text-[10px] bg-rose-100 text-rose-800 border border-rose-300';
          } else {
            modalDiffDeltaBadge.className = 'px-2 py-0.5 rounded font-mono font-bold text-[10px] bg-stone-100 text-stone-700 border border-stone-300';
          }
        }

        if (modalDiffReasoningText) {
          const reasoning = diffData.reason || (diffData.has_changed ? `Diferencia semántica detectada: sugerido cambio a '${newCat.name}'.` : `Sin cambio de categoría: la afinidad se mantiene consistente.`);
          modalDiffReasoningText.textContent = `${reasoning} Latencia CPU: ${lat.toFixed(1)} ms.`;
        }

        if (modalDiffLoading) modalDiffLoading.classList.add('hidden');
        if (modalDiffWidget) modalDiffWidget.classList.remove('hidden');

      } catch (err) {
        console.error('Error simulando re-clasificación A/B:', err);
        if (modalDiffLoading) modalDiffLoading.classList.add('hidden');
        toast(`❌ Error al simular reclasificación: ${err.message}`);
      }
    },

    /**
     * Aplica y confirma la nueva clasificación calculada (dry_run=False, confirm=True)
     */
    async applyReclassification(post) {
      const posts = getCurrentScrapedPosts();
      const currentPost = post || posts[currentModalPostIndex] || window.selectedPostForDrawer;
      if (!currentPost) return;
      const toast = getShowToast();
      const categories = getCategories();

      try {
        let result = null;
        if (window.API?.posts?.reclassify) {
          result = await window.API.posts.reclassify(currentPost.id, false, true, "Aceptada reclasificación A/B desde vista detallada");
        } else {
          const res = await fetch(`/api/posts/${encodeURIComponent(currentPost.id)}/reclassify`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ dry_run: false, confirm: true, reason: "Aceptada reclasificación A/B desde vista detallada" })
          });
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          result = await res.json();
        }

        const curr = result.current || {};
        const newCatId = curr.primary_category || result.new_category || currentPost.category_id;
        const newScore = curr.affinity_score !== undefined ? curr.affinity_score : (result.new_score || 0.75);

        // Actualizar datos del post en memoria
        currentPost.category_id = newCatId;
        currentPost.primary_category = newCatId;
        currentPost.affinity_score = Math.round(newScore > 1 ? newScore : newScore * 100);
        currentPost.status = curr.status || 'CLASSIFIED';
        currentPost.taxonomy_version = curr.taxonomy_version || result.new_version || '2.1.0';
        currentPost.reclassification_count = curr.reclassification_count !== undefined ? curr.reclassification_count : ((currentPost.reclassification_count || 0) + 1);
        if (result.post) {
          Object.assign(currentPost, result.post);
        }

        const newCat = categories.find(c => c.id === currentPost.category_id);

        if (modalDiffWidget) modalDiffWidget.classList.add('hidden');
        toast(`✓ Reclasificación aceptada: [${newCat?.name || currentPost.category_id}] aplicada en SQLite WAL.`);

        // Refrescar vistas
        if (typeof renderMatrix === 'function') renderMatrix();
        if (typeof openPostDrawer === 'function') openPostDrawer(currentPost, newCat);
        RichPostModal.open(currentPost, 'history');

      } catch (err) {
        console.error('Error aplicando reclasificación:', err);
        toast(`❌ Error al aplicar reclasificación: ${err.message}`);
      }
    },

    /**
     * Desestima la simulación conservando la clasificación previa intacta
     */
    dismissSimulation() {
      const toast = getShowToast();
      if (modalDiffWidget) modalDiffWidget.classList.add('hidden');
      toast('✓ Conservada clasificación previa intacta');
    },

    /**
     * Consulta y renderiza el historial cronológico de versiones y snapshots de SQLite
     */
    async loadPostHistory(tweetId) {
      if (!modalHistoryListContainer) return;
      const categories = getCategories();

      try {
        let historyData = null;
        if (window.API?.posts?.getHistory) {
          historyData = await window.API.posts.getHistory(tweetId);
        } else {
          const res = await fetch(`/api/posts/${encodeURIComponent(tweetId)}/history`);
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          historyData = await res.json();
        }

        const items = historyData.history || [];
        if (modalHistoryCountBadge) {
          modalHistoryCountBadge.textContent = historyData.total_versions || items.length;
        }

        if (items.length === 0) {
          modalHistoryListContainer.innerHTML = `
            <div class="p-4 bg-stone-50 rounded-lg border border-stone-200 text-stone-500 text-center text-xs italic">
              <i class="fa-solid fa-clock mr-1"></i> No hay versiones históricas archivadas previas (Versión actual es la primera registrada).
            </div>
          `;
          return;
        }

        modalHistoryListContainer.innerHTML = items.map((item) => {
          const cat = categories.find(c => c.id === item.primary_category) || { name: item.primary_category, colorHex: '#71717a' };
          const score = Math.round((item.affinity_score > 1 ? item.affinity_score : item.affinity_score * 100));
          const dateStr = item.created_at ? new Date(item.created_at).toLocaleString() : 'Fecha no registrada';
          const triggerBadge = item.trigger_type === 'rollback' ? 'bg-amber-100 text-amber-900 border-amber-300' :
                               (item.trigger_type === 'manual_override' ? 'bg-blue-100 text-blue-900 border-blue-300' :
                               'bg-stone-200 text-stone-800 border-stone-300');

          return `
            <div class="p-3 bg-stone-50 rounded-lg border border-stone-200 flex flex-wrap items-center justify-between gap-2.5 transition hover:bg-stone-100/70">
              <div class="space-y-1">
                <div class="flex items-center gap-2">
                  <span class="w-2.5 h-2.5 rounded-full" style="background-color: ${cat.colorHex}"></span>
                  <span class="font-bold text-stone-900 text-xs">${cat.name}</span>
                  <span class="px-1.5 py-0.2 rounded text-[9px] font-mono font-bold border ${triggerBadge}">
                    ${item.trigger_type || 'snapshot'}
                  </span>
                  <span class="text-[10px] text-stone-500 font-mono">v${item.taxonomy_version || '2.0.0'}</span>
                </div>
                <div class="flex items-center gap-2 text-[10px] text-stone-500 font-mono">
                  <span>Afinidad: <strong class="text-stone-700">${score}%</strong></span>
                  <span>·</span>
                  <span>${dateStr}</span>
                </div>
                ${item.reason ? `<p class="text-[10px] text-stone-600 font-sans italic">${item.reason}</p>` : ''}
              </div>
              <button 
                class="rollback-version-btn px-2.5 py-1.5 bg-white hover:bg-stone-200 text-stone-800 rounded-lg border border-stone-300 text-[11px] font-semibold flex items-center gap-1.5 transition shadow-2xs cursor-pointer"
                data-tweet-id="${item.tweet_id}"
                data-history-id="${item.id}"
                title="Restaurar esta clasificación histórica"
              >
                <i class="fa-solid fa-rotate-left text-[10px] text-amber-600"></i>
                <span>Rollback</span>
              </button>
            </div>
          `;
        }).join('');

        // Vincular eventos a los botones de rollback
        modalHistoryListContainer.querySelectorAll('.rollback-version-btn').forEach(btn => {
          btn.addEventListener('click', () => {
            const tId = btn.getAttribute('data-tweet-id');
            const hId = btn.getAttribute('data-history-id');
            RichPostModal.executeRollback(tId, hId);
          });
        });

      } catch (err) {
        console.error('Error cargando historial de versiones:', err);
        modalHistoryListContainer.innerHTML = `
          <div class="p-3 bg-rose-50 text-rose-800 rounded-lg text-xs border border-rose-200">
            Error al consultar el historial: ${err.message}
          </div>
        `;
      }
    },

    /**
     * Ejecuta rollback seguro hacia un snapshot previo
     */
    async executeRollback(tweetId, historyId) {
      const toast = getShowToast();
      const categories = getCategories();
      const posts = getCurrentScrapedPosts();

      try {
        let result = null;
        if (window.API?.posts?.rollback) {
          result = await window.API.posts.rollback(tweetId, historyId);
        } else {
          const res = await fetch(`/api/posts/${encodeURIComponent(tweetId)}/history/${encodeURIComponent(historyId)}/rollback`, {
            method: 'POST'
          });
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          result = await res.json();
        }

        // Actualizar post en memoria
        const currentPost = posts.find(p => String(p.id) === String(tweetId)) || window.selectedPostForDrawer;
        if (currentPost && result.restored_record) {
          const rec = result.restored_record;
          currentPost.category_id = rec.primary_category;
          currentPost.primary_category = rec.primary_category;
          currentPost.affinity_score = Math.round(rec.affinity_score * 100);
          currentPost.status = 'CLASSIFIED';
          currentPost.taxonomy_version = rec.taxonomy_version;
          currentPost.reclassification_count = (currentPost.reclassification_count || 0) + 1;
        }

        const cat = categories.find(c => c.id === currentPost?.category_id);
        toast(`✓ Rollback ejecutado: post restaurado a [${cat?.name || currentPost?.category_id}].`);

        if (typeof renderMatrix === 'function') renderMatrix();
        if (currentPost && typeof openPostDrawer === 'function') openPostDrawer(currentPost, cat);
        if (currentPost) RichPostModal.open(currentPost, 'history');

      } catch (err) {
        console.error('Error en rollback:', err);
        toast(`❌ Error al ejecutar rollback: ${err.message}`);
      }
    },

    /**
     * Cierra el modal enriquecido y detiene reproducción de video
     */
    close() {
      if (richPostModal) richPostModal.classList.add('hidden');
      if (modalHtmlVideoPlayer) {
        modalHtmlVideoPlayer.pause();
      }
    },

    /**
     * Navega secuencialmente al post anterior (-1) o siguiente (+1)
     */
    navigate(direction) {
      const posts = getCurrentScrapedPosts();
      if (posts.length === 0) return;
      if (modalHtmlVideoPlayer) modalHtmlVideoPlayer.pause();

      currentModalPostIndex = (currentModalPostIndex + direction + posts.length) % posts.length;
      const nextPost = posts[currentModalPostIndex];
      this.open(nextPost);
    },

    bindEvents() {
      if (closeRichModalBtn) closeRichModalBtn.addEventListener('click', () => RichPostModal.close());
      if (modalPrevPostBtn) modalPrevPostBtn.addEventListener('click', () => RichPostModal.navigate(-1));
      if (modalNextPostBtn) modalNextPostBtn.addEventListener('click', () => RichPostModal.navigate(1));

      // Atajos de Teclado Globales (←, →, Esc)
      window.addEventListener('keydown', (e) => {
        if (!richPostModal || richPostModal.classList.contains('hidden')) return;

        if (e.key === 'ArrowLeft') {
          e.preventDefault();
          RichPostModal.navigate(-1);
        } else if (e.key === 'ArrowRight') {
          e.preventDefault();
          RichPostModal.navigate(1);
        } else if (e.key === 'Escape') {
          e.preventDefault();
          RichPostModal.close();
        }
      });

      // Reclasificación desde el Modal Completo
      if (modalReclassifyBtn) {
        modalReclassifyBtn.addEventListener('click', () => {
          const posts = getCurrentScrapedPosts();
          const currentPost = posts[currentModalPostIndex] || window.selectedPostForDrawer;
          if (!currentPost) return;
          const newCatId = modalReclassifySelect.value;
          if (typeof handlePostOverride === 'function') {
            handlePostOverride(currentPost, newCatId);
          }
        });
      }

      // Pestañas Principales del Modal
      document.querySelectorAll('#richPostModal .tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
          const tab = btn.getAttribute('data-tab');
          RichPostModal.switchTab(tab);
        });
      });

      // Simulación Dry-Run desde botón de pestaña Historial
      if (modalTriggerDryRunBtn) {
        modalTriggerDryRunBtn.addEventListener('click', () => {
          RichPostModal.triggerDiffSimulation();
        });
      }

      // Decisión A/B: Conservar previa
      if (modalDiffDismissBtn) {
        modalDiffDismissBtn.addEventListener('click', () => {
          RichPostModal.dismissSimulation();
        });
      }

      // Decisión A/B: Aceptar y confirmar nueva
      if (modalDiffApplyBtn) {
        modalDiffApplyBtn.addEventListener('click', () => {
          RichPostModal.applyReclassification();
        });
      }

      // Refrescar Historial
      if (modalRefreshHistoryBtn) {
        modalRefreshHistoryBtn.addEventListener('click', () => {
          const posts = getCurrentScrapedPosts();
          const currentPost = posts[currentModalPostIndex] || window.selectedPostForDrawer;
          if (currentPost) {
            RichPostModal.loadPostHistory(currentPost.id);
          }
        });
      }

      // Sub-pestañas del Visor Dual de JSON
      if (subtabJsonScraping) {
        subtabJsonScraping.addEventListener('click', () => {
          currentActiveJsonSubtab = 'scraping';
          subtabJsonScraping.className = 'subtab-btn active-subtab px-3 py-1.5 rounded-lg font-semibold transition border border-stone-300 text-xs';
          if (subtabJsonLaya) subtabJsonLaya.className = 'subtab-btn px-3 py-1.5 rounded-lg font-semibold transition border border-stone-200 text-stone-600 hover:text-stone-900 text-xs';
          RichPostModal.renderRawJson();
        });
      }

      if (subtabJsonLaya) {
        subtabJsonLaya.addEventListener('click', () => {
          currentActiveJsonSubtab = 'laya';
          subtabJsonLaya.className = 'subtab-btn active-subtab px-3 py-1.5 rounded-lg font-semibold transition border border-stone-300 text-xs';
          if (subtabJsonScraping) subtabJsonScraping.className = 'subtab-btn px-3 py-1.5 rounded-lg font-semibold transition border border-stone-200 text-stone-600 hover:text-stone-900 text-xs';
          RichPostModal.renderRawJson();
        });
      }

      // Copiar JSON
      if (copyRawJsonBtn) {
        copyRawJsonBtn.addEventListener('click', () => {
          const toast = getShowToast();
          const code = rawJsonCodeBlock ? rawJsonCodeBlock.textContent : '';
          if (!code) return;
          navigator.clipboard.writeText(code).then(() => {
            toast('✓ JSON copiado al portapapeles');
          }).catch(() => {
            const el = document.createElement('textarea');
            el.value = code;
            document.body.appendChild(el);
            el.select();
            document.execCommand('copy');
            document.body.removeChild(el);
            toast('✓ JSON copiado al portapapeles');
          });
        });
      }

      // Descargar .json
      if (downloadRawJsonBtn) {
        downloadRawJsonBtn.addEventListener('click', () => {
          const toast = getShowToast();
          const posts = getCurrentScrapedPosts();
          const code = rawJsonCodeBlock ? rawJsonCodeBlock.textContent : '';
          if (!code) return;
          const currentPost = posts[currentModalPostIndex] || window.selectedPostForDrawer;
          const fileName = `post_${currentPost ? currentPost.id : 'export'}_${currentActiveJsonSubtab}.json`;
          
          const blob = new Blob([code], { type: 'application/json' });
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = fileName;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          URL.revokeObjectURL(url);
          toast(`✓ Archivo ${fileName} descargado`);
        });
      }
    }
  };

  // Exposición en namespace global
  window.RichPostModal = RichPostModal;

  // Aliases legacy
  window.openRichPostModal = (post, tab, sim) => RichPostModal.open(post, tab, sim);
  window.openRichPostModalWithTab = (post, tab, sim) => RichPostModal.openWithTab(post, tab, sim);
  window.closeRichModal = () => RichPostModal.close();
  window.navigateModalPost = dir => RichPostModal.navigate(dir);
  window.renderRawJsonView = post => RichPostModal.renderRawJson(post);

  // Vincular eventos al inicio
  if (document.readyState === 'loading') {
    window.addEventListener('DOMContentLoaded', () => RichPostModal.bindEvents());
  } else {
    RichPostModal.bindEvents();
  }

})(window);
