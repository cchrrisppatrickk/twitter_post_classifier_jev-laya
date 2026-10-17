/**
 * INGEST_MODAL.JS - Data Ingestion & SSE Batch Streaming Controller (Laya Engine v2.1.0)
 * Parseo tolerante de JSON / Meridian, subida de archivos, análisis individual y batch streaming interactivo.
 */

(function(window) {
  'use strict';

  // Selectores DOM
  const ingestModal = document.getElementById('ingestModal');
  const openIngestModalBtn = document.getElementById('openIngestModalBtn');
  const closeIngestModalBtn = document.getElementById('closeIngestModalBtn');
  const cancelIngestBtn = document.getElementById('cancelIngestBtn');
  const submitIngestBtn = document.getElementById('submitIngestBtn');
  const loadSampleInModalBtn = document.getElementById('loadSampleInModalBtn');
  const jsonFileInput = document.getElementById('jsonFileInput');
  const jsonPasteArea = document.getElementById('jsonPasteArea');

  // Selectores de Archivo
  const fileInfoCard = document.getElementById('fileInfoCard');
  const fileInfoName = document.getElementById('fileInfoName');
  const fileInfoSize = document.getElementById('fileInfoSize');
  const fileInfoPostsCount = document.getElementById('fileInfoPostsCount');
  const fileInfoEngine = document.getElementById('fileInfoEngine');
  const clearSelectedFileBtn = document.getElementById('clearSelectedFileBtn');
  const pasteSectionSeparator = document.getElementById('pasteSectionSeparator');
  const pasteSectionContainer = document.getElementById('pasteSectionContainer');
  const analyzeBtnLabel = document.getElementById('analyzeBtnLabel');
  const analyzeSingleBtn = document.getElementById('analyzeSingleBtn');
  const clearMatrixBtn = document.getElementById('clearMatrixBtn');

  // Selectores de Batch Streaming y Pausa
  const pauseResumeBatchBtn = document.getElementById('pauseResumeBatchBtn');
  const pauseResumeIcon = document.getElementById('pauseResumeIcon');
  const pauseResumeText = document.getElementById('pauseResumeText');
  const cancelBatchBtn = document.getElementById('cancelBatchBtn');

  // Estado interno
  let loadedFilePosts = null;
  let isBatchPaused = false;
  let pauseBatchResolver = null;
  let activeBatchLimit = 5; // Default 5 posts para protección de CPU
  let cachedRegisteredIds = null;
  let lastFetchedIdsTime = 0;

  function getShowToast() {
    return typeof showToast === 'function' ? showToast : console.log;
  }

  function getCurrentScrapedPosts() {
    return window.currentScrapedPosts || [];
  }

  function getSelectedDuplicateStrategy() {
    const checked = document.querySelector('input[name="duplicateStrategy"]:checked');
    return checked ? checked.value : 'skip';
  }

  function getSelectedQuestionsList() {
    const checkedProfile = document.querySelector('input[name="questionsProfile"]:checked');
    const profileVal = checkedProfile ? checkedProfile.value : 'full';

    if (profileVal === 'fast') {
      return ['category'];
    }
    if (profileVal === 'custom') {
      const checkedBoxes = Array.from(document.querySelectorAll('.custom-q-chk:checked')).map(el => el.value);
      return checkedBoxes.length > 0 ? checkedBoxes : ['category'];
    }
    // 'full': null para indicar que el backend use todas las preguntas activas
    return null;
  }

  function updateQuestionsProfileUI() {
    const checkedProfile = document.querySelector('input[name="questionsProfile"]:checked');
    const profileVal = checkedProfile ? checkedProfile.value : 'full';
    const container = document.getElementById('customQuestionsContainer');
    const badge = document.getElementById('activeQuestionsSummaryBadge');

    if (container) {
      if (profileVal === 'custom') {
        container.classList.remove('hidden');
      } else {
        container.classList.add('hidden');
      }
    }

    if (badge) {
      if (profileVal === 'full') {
        badge.textContent = 'Completo (Todas)';
        badge.className = 'text-[10px] text-purple-700 bg-purple-100 px-2 py-0.5 rounded font-bold';
      } else if (profileVal === 'fast') {
        badge.textContent = 'Rápido (Solo Waffle)';
        badge.className = 'text-[10px] text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded font-bold';
      } else {
        const checkedCount = document.querySelectorAll('.custom-q-chk:checked').length;
        badge.textContent = `${checkedCount} seleccionadas`;
        badge.className = 'text-[10px] text-indigo-700 bg-indigo-100 px-2 py-0.5 rounded font-bold';
      }
    }
  }

  async function populateCustomQuestionsList() {
    const listContainer = document.getElementById('customQuestionsCheckboxList');
    if (!listContainer) return;
    try {
      const res = await fetch('/api/categories/questions/supplementary');
      if (!res.ok) return;
      const data = await res.json();
      const supp = data.supplementary_questions || {};

      listContainer.innerHTML = '';

      // Checkbox permanente para la pregunta central category
      const catDiv = document.createElement('label');
      catDiv.className = 'flex items-center gap-1.5 p-1.5 rounded border border-purple-200 bg-purple-50/50 cursor-pointer hover:bg-purple-50';
      catDiv.innerHTML = `
        <input type="checkbox" value="category" checked class="custom-q-chk text-purple-600 rounded focus:ring-purple-500">
        <span class="font-bold text-stone-800">category</span>
        <span class="text-[9px] text-stone-500 truncate">(Matriz Waffle 48 cats)</span>
      `;
      listContainer.appendChild(catDiv);

      // Checkboxes para cada pregunta suplementaria
      Object.entries(supp).forEach(([qId, qCfg]) => {
        const isChecked = qCfg.active !== false;
        const div = document.createElement('label');
        div.className = 'flex items-center gap-1.5 p-1.5 rounded border border-stone-200 bg-white cursor-pointer hover:bg-stone-50';
        div.innerHTML = `
          <input type="checkbox" value="${qId}" ${isChecked ? 'checked' : ''} class="custom-q-chk text-indigo-600 rounded focus:ring-indigo-500">
          <span class="font-bold text-stone-800">${qId}</span>
          <span class="text-[9px] text-stone-400 font-mono">(${qCfg.type || 'choice'})</span>
        `;
        listContainer.appendChild(div);
      });

      // Añadir listeners para actualizar badge
      listContainer.querySelectorAll('.custom-q-chk').forEach(chk => {
        chk.addEventListener('change', updateQuestionsProfileUI);
      });
      updateQuestionsProfileUI();
    } catch (e) {
      console.warn('[IngestModal] Error cargando preguntas suplementarias:', e);
    }
  }

  async function fetchRegisteredTweetIds(force = false) {
    const now = Date.now();
    if (!force && cachedRegisteredIds && (now - lastFetchedIdsTime < 15000)) {
      return cachedRegisteredIds;
    }
    try {
      const res = await fetch('/api/posts/ids');
      if (res.ok) {
        const data = await res.json();
        if (data && Array.isArray(data.tweet_ids)) {
          cachedRegisteredIds = new Set(data.tweet_ids.map(id => String(id).trim()));
          lastFetchedIdsTime = now;
          return cachedRegisteredIds;
        }
      }
    } catch (e) {
      console.warn('[IngestModal] Fallo obteniendo /api/posts/ids:', e);
    }
    const memPosts = getCurrentScrapedPosts();
    cachedRegisteredIds = new Set(memPosts.map(p => String(p.id || p.tweet_id).trim()).filter(Boolean));
    lastFetchedIdsTime = now;
    return cachedRegisteredIds;
  }

  function partitionPostsByRegistration(posts, registeredIds) {
    const registered = [];
    const pending = [];
    if (!Array.isArray(posts)) return { registered, pending };
    for (const p of posts) {
      const pid = String(p.id || p.tweet_id || '').trim();
      if (pid && registeredIds && registeredIds.has(pid)) {
        registered.push(p);
      } else {
        pending.push(p);
      }
    }
    return { registered, pending };
  }

  function getActiveBatchLimit(totalAvailable) {
    if (activeBatchLimit === 'all' || !activeBatchLimit) {
      return totalAvailable;
    }
    const num = parseInt(activeBatchLimit, 10);
    return isNaN(num) || num <= 0 ? totalAvailable : Math.min(num, totalAvailable);
  }

  async function updateBatchLimitUI(totalAvailable) {
    const input = document.getElementById('batchLimitInput');
    const badgeCount = document.getElementById('batchLimitCurrentCount');
    const presetBtns = document.querySelectorAll('.limit-preset-btn');
    const explanationEl = document.getElementById('batchLimitExplanation');
    const qTotal = document.getElementById('queueTotalCount');
    const qReg = document.getElementById('queueRegisteredCount');
    const qPend = document.getElementById('queuePendingCount');

    const dupStrategy = getSelectedDuplicateStrategy();
    const registeredIds = await fetchRegisteredTweetIds();

    let targetArray = loadedFilePosts || [];
    if (!loadedFilePosts && jsonPasteArea && jsonPasteArea.value.trim()) {
      try {
        targetArray = IngestModal.parseAndNormalizeRawInput(jsonPasteArea.value.trim());
      } catch (_) {}
    }

    const { registered, pending } = partitionPostsByRegistration(targetArray, registeredIds);
    const totalCount = targetArray.length || totalAvailable || 0;
    const registeredCount = registered.length;
    const pendingCount = pending.length;

    if (qTotal) qTotal.textContent = String(totalCount);
    if (qReg) qReg.textContent = String(registeredCount);
    if (qPend) qPend.textContent = String(pendingCount);

    const baseForLimit = dupStrategy === 'skip' ? pendingCount : totalCount;
    const effective = getActiveBatchLimit(baseForLimit);

    if (badgeCount) {
      if (activeBatchLimit === 'all') {
        badgeCount.textContent = `Todos (${baseForLimit})`;
      } else {
        badgeCount.textContent = `${effective}`;
      }
    }

    if (input && document.activeElement !== input) {
      input.value = activeBatchLimit === 'all' ? (baseForLimit || '') : effective;
    }

    presetBtns.forEach(btn => {
      const btnLimit = btn.getAttribute('data-limit');
      const isSelected = (activeBatchLimit === 'all' && btnLimit === 'all') ||
                         (String(activeBatchLimit) === String(btnLimit));
      if (isSelected) {
        btn.className = 'limit-preset-btn px-2.5 py-1 rounded-lg border border-emerald-600 bg-emerald-50 text-emerald-800 font-bold transition hover:bg-emerald-100';
      } else {
        btn.className = 'limit-preset-btn px-2.5 py-1 rounded-lg border border-stone-300 bg-white text-stone-700 transition hover:bg-stone-100';
      }
    });

    if (analyzeBtnLabel) {
      if (totalCount > 0) {
        if (dupStrategy === 'skip') {
          if (pendingCount > 0) {
            analyzeBtnLabel.textContent = `Analizar Próximos ${effective} de ${pendingCount} Pendientes`;
            if (analyzeSingleBtn) analyzeSingleBtn.disabled = false;
          } else {
            analyzeBtnLabel.textContent = `✓ Todas las publicaciones ya están en BD (0 pendientes)`;
            if (analyzeSingleBtn) analyzeSingleBtn.disabled = true;
          }
        } else {
          analyzeBtnLabel.textContent = `Re-evaluar Lote (${effective} de ${totalCount} posts con Laya)`;
          if (analyzeSingleBtn) analyzeSingleBtn.disabled = false;
        }
      } else {
        analyzeBtnLabel.textContent = 'Analizar con Laya AI';
        if (analyzeSingleBtn) analyzeSingleBtn.disabled = false;
      }
    }

    if (explanationEl) {
      if (dupStrategy === 'skip') {
        explanationEl.textContent = `Modo inteligente: detecta ${registeredCount} en BD y avanza automáticamente sobre los ${pendingCount} posts pendientes.`;
      } else {
        explanationEl.textContent = `Modo re-evaluación: reclasifica con taxonomía actual archivando historial para auditoría.`;
      }
    }
  }

  const IngestModal = {
    async open() {
      if (ingestModal) ingestModal.classList.remove('hidden');
      await fetchRegisteredTweetIds(true);
      await populateCustomQuestionsList();
      const total = loadedFilePosts ? loadedFilePosts.length : 0;
      updateBatchLimitUI(total);
    },

    close() {
      if (ingestModal) ingestModal.classList.add('hidden');
    },

    clearLoadedFile() {
      loadedFilePosts = null;
      if (jsonFileInput) jsonFileInput.value = '';
      if (fileInfoCard) fileInfoCard.classList.add('hidden');
      if (pasteSectionSeparator) pasteSectionSeparator.classList.remove('hidden');
      if (pasteSectionContainer) pasteSectionContainer.classList.remove('hidden');
      if (analyzeBtnLabel) analyzeBtnLabel.textContent = 'Analizar con Laya AI';
      if (analyzeSingleBtn) analyzeSingleBtn.disabled = false;
      updateBatchLimitUI(0);
    },

    /**
     * Parsea y normaliza publicaciones desde Meridian scraper, array plano o tweet individual
     */
    parseAndNormalizeRawInput(rawVal) {
      if (!rawVal) return [];
      let cleaned = rawVal.trim();

      // Limpieza de bloques de código markdown ```json ... ```
      cleaned = cleaned.replace(/^```json\s*/i, '').replace(/^```\s*/, '').replace(/```\s*$/, '').trim();

      let parsedItems = [];
      const looksLikeJson = cleaned.startsWith('{') || cleaned.startsWith('[');

      if (looksLikeJson) {
        try {
          const fixedJson = cleaned.replace(/,\s*([\]}])/g, '$1');
          const parsed = JSON.parse(fixedJson);

          if (Array.isArray(parsed)) {
            parsedItems = parsed;
          } else if (parsed && typeof parsed === 'object') {
            if (Array.isArray(parsed.posts)) {
              parsedItems = parsed.posts;
            } else if (Array.isArray(parsed.tweets)) {
              parsedItems = parsed.tweets;
            } else {
              parsedItems = [parsed];
            }
          }
        } catch (parseErr) {
          throw new Error(`Sintaxis JSON inválida (${parseErr.message}). Verifica comas o caracteres incompletos.`);
        }
      } else {
        parsedItems = [{ text: cleaned, author: 'dev_user' }];
      }

      // Normalizar cada post
      return parsedItems.map((item, idx) => {
        if (typeof item === 'string') {
          const trimmed = item.trim();
          return {
            text: trimmed || '[Publicación sin texto]',
            author: 'dev_user',
            id: `post_${Date.now()}_${idx + 1}`,
            persist: true
          };
        }

        let textContent = (item.text || item.content || item.full_text || '').trim();

        // Extracción de autor
        let authorName = 'dev_user';
        if (typeof item.author === 'string') {
          authorName = item.author;
        } else if (item.author && typeof item.author === 'object') {
          authorName = item.author.nick || item.author.name || 'dev_user';
        } else if (item.author_name) {
          authorName = item.author_name;
        }

        // Extracción de métricas
        let likesCount = 0;
        let retweetsCount = 0;
        if (item.metrics && typeof item.metrics === 'object') {
          likesCount = Number(item.metrics.likes) || 0;
          retweetsCount = Number(item.metrics.retweets) || 0;
        } else {
          likesCount = Number(item.likes ?? item.favorite_count) || 0;
          retweetsCount = Number(item.retweets ?? item.retweet_count) || 0;
        }

        // Extracción de media y categoría
        let mediaType = item.media_type || 'none';
        const mediaUrls = Array.isArray(item.media_urls) ? item.media_urls : [];
        if (item.category === 'video') {
          mediaType = 'video';
        } else if (item.category === 'image' || item.category === 'photo') {
          mediaType = 'photo';
        } else if (mediaUrls.length > 0 && mediaType === 'none') {
          mediaType = 'photo';
        }

        if (!textContent) {
          if (mediaType && mediaType !== 'none') {
            textContent = `[Multimedia: ${mediaType}]`;
          } else {
            textContent = '[Publicación sin contenido textual]';
          }
        }

        return {
          text: textContent,
          id: String(item.tweet_id || item.id || `post_${Date.now()}_${idx + 1}`),
          author: authorName,
          date: item.date || item.created_at || null,
          post_url: item.post_url || item.url || null,
          likes: likesCount,
          retweets: retweetsCount,
          media_urls: mediaUrls,
          media_type: mediaType,
          persist: true
        };
      }).filter(p => p.text && p.text.trim().length >= 1);
    },

    /**
     * Inicia el análisis Laya AI (individual o batch stream)
     */
    async executeAnalysis() {
      const toast = getShowToast();
      let normalizedPosts = [];

      if (loadedFilePosts && loadedFilePosts.length > 0) {
        normalizedPosts = loadedFilePosts;
      } else {
        const rawVal = jsonPasteArea ? jsonPasteArea.value.trim() : '';
        if (!rawVal) {
          toast('Por favor escribe o pega un texto, o selecciona un archivo JSON');
          return;
        }
        try {
          normalizedPosts = this.parseAndNormalizeRawInput(rawVal);
        } catch (parseError) {
          toast(parseError.message);
          return;
        }
      }

      if (!normalizedPosts || normalizedPosts.length === 0) {
        toast('No se detectaron publicaciones con texto válido para analizar');
        return;
      }

      // Aplicar límite configurable de lote inteligente (Smart Pending Queue)
      const dupStrategy = getSelectedDuplicateStrategy();
      const registeredIds = await fetchRegisteredTweetIds(true);
      const { registered, pending } = partitionPostsByRegistration(normalizedPosts, registeredIds);

      let postsToProcess = [];
      if (dupStrategy === 'skip') {
        if (pending.length === 0) {
          toast(`Todas las publicaciones (${normalizedPosts.length}) ya están registradas en la base de datos.`);
          return;
        }
        const limitVal = getActiveBatchLimit(pending.length);
        postsToProcess = (limitVal && limitVal < pending.length)
          ? pending.slice(0, limitVal)
          : pending;
      } else {
        const limitVal = getActiveBatchLimit(normalizedPosts.length);
        postsToProcess = (limitVal && limitVal < normalizedPosts.length)
          ? normalizedPosts.slice(0, limitVal)
          : normalizedPosts;
      }

      const isBatch = postsToProcess.length > 1;

      // 2. Cerrar inmediatamente modal de ingest
      this.close();

      // 3. Enfocar barra de análisis en vivo
      const liveCard = document.getElementById('liveAnalysisCard');
      if (liveCard) {
        liveCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }

      const liveScannerBadge = document.getElementById('liveScannerBadge');
      const livePostAuthor = document.getElementById('livePostAuthor');
      const livePostSnippet = document.getElementById('livePostSnippet');
      const liveDecisionTarget = document.getElementById('liveDecisionTarget');
      const viewBtn = document.getElementById('viewAnalysisModalBtn');
      const singlePostStageText = document.getElementById('singlePostStageText');
      const singlePostPercent = document.getElementById('singlePostPercent');
      const singlePostProgressBar = document.getElementById('singlePostProgressBar');
      const batchProgressLabel = document.getElementById('batchProgressLabel');
      const batchProgressPercent = document.getElementById('batchProgressPercent');
      const batchProgressBar = document.getElementById('batchProgressBar');

      if (viewBtn) viewBtn.classList.add('hidden');

      // =========================================================================
      // CASO A: ANÁLISIS INDIVIDUAL (1 POST)
      // =========================================================================
      if (!isBatch) {
        const postToAnalyze = postsToProcess[0];

        if (liveScannerBadge) {
          liveScannerBadge.textContent = 'ANALIZANDO POST';
          liveScannerBadge.className = 'px-2 py-0.5 rounded bg-amber-500 text-white font-bold text-[10px] font-mono uppercase tracking-wider shrink-0 animate-pulse shadow-xs';
        }
        if (livePostAuthor) livePostAuthor.textContent = `@${postToAnalyze.author}`;
        if (livePostSnippet) livePostSnippet.textContent = `"${postToAnalyze.text}"`;
        if (liveDecisionTarget) {
          liveDecisionTarget.textContent = 'Calculando con Laya...';
          liveDecisionTarget.className = 'px-2.5 py-0.5 rounded bg-amber-100 text-amber-900 font-bold text-[11px] font-mono transition-all animate-pulse shadow-xs';
          liveDecisionTarget.style.backgroundColor = '';
          liveDecisionTarget.style.color = '';
        }

        if (singlePostStageText) singlePostStageText.textContent = '1/3 Extrayendo estructura semántica y tokens del post...';
        if (singlePostPercent) singlePostPercent.textContent = '15%';
        if (singlePostProgressBar) {
          singlePostProgressBar.style.width = '15%';
          singlePostProgressBar.className = 'bg-amber-500 h-full transition-all duration-150 rounded-full';
        }

        if (batchProgressLabel) batchProgressLabel.textContent = 'Progreso total del lote clasificado';
        if (batchProgressPercent) batchProgressPercent.textContent = '0% (0/1)';
        if (batchProgressBar) {
          batchProgressBar.style.width = '15%';
          batchProgressBar.className = 'bg-gradient-to-r from-amber-500 via-emerald-500 to-teal-400 h-full transition-all duration-300 rounded-full';
        }

        let currentSimPct = 15;
        const simInterval = setInterval(() => {
          if (currentSimPct < 65) {
            currentSimPct += 18;
            if (singlePostPercent) singlePostPercent.textContent = `${currentSimPct}%`;
            if (singlePostProgressBar) singlePostProgressBar.style.width = `${currentSimPct}%`;
            if (singlePostStageText) singlePostStageText.textContent = '2/3 Evaluando afinidad contra 48 categorías en CPU...';
          } else if (currentSimPct < 88) {
            currentSimPct += 6;
            if (singlePostPercent) singlePostPercent.textContent = `${currentSimPct}%`;
            if (singlePostProgressBar) singlePostProgressBar.style.width = `${currentSimPct}%`;
            if (singlePostStageText) singlePostStageText.textContent = '3/3 Aplicando Family Gating y detección de activos...';
          }
        }, 380);

        const originalBtnHtml = analyzeSingleBtn.innerHTML;
        analyzeSingleBtn.disabled = true;
        analyzeSingleBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i><span>Analizando con Laya...</span>';

        try {
          const activeQList = getSelectedQuestionsList();
          const response = await fetch('/api/posts/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              ...postToAnalyze,
              active_questions: activeQList
            })
          });

          if (!response.ok) {
            const errJson = await response.json().catch(() => ({}));
            throw new Error(errJson.detail || `HTTP ${response.status}`);
          }

          const result = await response.json();
          clearInterval(simInterval);

          if (singlePostPercent) singlePostPercent.textContent = '100%';
          if (singlePostProgressBar) {
            singlePostProgressBar.style.width = '100%';
            singlePostProgressBar.className = result.is_outlier
              ? 'bg-orange-500 h-full w-full transition-all duration-150 rounded-full'
              : 'bg-emerald-500 h-full w-full transition-all duration-150 rounded-full';
          }
          if (singlePostStageText) {
            singlePostStageText.textContent = `Clasificado en ${result.category_label || result.primary_category} (${result.code})`;
          }

          if (liveScannerBadge) {
            if (result.is_outlier) {
              liveScannerBadge.textContent = 'ANOMALÍA DETECTADA';
              liveScannerBadge.className = 'px-2 py-0.5 rounded bg-orange-500 text-white font-bold text-[10px] font-mono uppercase tracking-wider shrink-0 shadow-xs';
            } else if (result.status === 'PENDING') {
              liveScannerBadge.textContent = 'PENDIENTE';
              liveScannerBadge.className = 'px-2 py-0.5 rounded bg-amber-600 text-white font-bold text-[10px] font-mono uppercase tracking-wider shrink-0 shadow-xs';
            } else {
              liveScannerBadge.textContent = 'CLASIFICADO';
              liveScannerBadge.className = 'px-2 py-0.5 rounded bg-emerald-600 text-white font-bold text-[10px] font-mono uppercase tracking-wider shrink-0 shadow-xs';
            }
          }

          if (liveDecisionTarget) {
            liveDecisionTarget.textContent = `${result.category_label || result.primary_category} (${result.code}) · ${Math.round(result.affinity_score * 100)}%`;
            liveDecisionTarget.style.backgroundColor = result.color_hex || '#059669';
            liveDecisionTarget.style.color = '#ffffff';
            liveDecisionTarget.className = 'px-2.5 py-0.5 rounded font-bold text-[11px] font-mono transition-all flex items-center gap-1.5 shadow-xs text-white';
          }

          if (batchProgressPercent) batchProgressPercent.textContent = '100% (1/1)';
          if (batchProgressBar) {
            batchProgressBar.style.width = '100%';
            batchProgressBar.className = 'bg-gradient-to-r from-emerald-600 via-emerald-500 to-teal-400 h-full w-full transition-all duration-150 rounded-full';
          }
          if (viewBtn) viewBtn.classList.remove('hidden');

          // Inyectar en Matriz Waffle
          const posts = getCurrentScrapedPosts();
          const existingIdx = posts.findIndex(p => p.id === result.tweet_id);
          const newPost = typeof formatAppPost === 'function' ? formatAppPost(result, postToAnalyze, result) : result;

          if (existingIdx >= 0) {
            posts[existingIdx] = newPost;
            if (typeof renderMatrix === 'function') renderMatrix();
          } else {
            posts.unshift(newPost);
            if (typeof appendPostToMatrixRow === 'function') {
              appendPostToMatrixRow(newPost);
            } else if (typeof renderMatrix === 'function') {
              renderMatrix();
            }
          }

          if (window.AnalysisResultModal && typeof window.AnalysisResultModal.populate === 'function') {
            window.AnalysisResultModal.populate(result);
          } else if (typeof populateAnalysisResultModal === 'function') {
            populateAnalysisResultModal(result);
          }

          toast(`Inyectado en [${result.category_label || result.primary_category}]`);

          // Apertura automática del modal tras celebración
          setTimeout(() => {
            const modal = document.getElementById('analysisResultModal');
            if (modal && modal.classList.contains('hidden')) {
              modal.classList.remove('hidden');
            }
          }, 1800);

        } catch (err) {
          clearInterval(simInterval);
          if (window.AnalysisResultModal && typeof window.AnalysisResultModal.handleError === 'function') {
            window.AnalysisResultModal.handleError(err);
          } else if (typeof handleAnalysisError === 'function') {
            handleAnalysisError(err);
          }
        } finally {
          analyzeSingleBtn.disabled = false;
          analyzeSingleBtn.innerHTML = originalBtnHtml;
        }

        return;
      }

      // =========================================================================
      // CASO B: ANÁLISIS EN LOTE (BATCH STREAMING SSE)
      // =========================================================================
      const totalBatchPosts = postsToProcess.length;
      let abortBatchCtrl = new AbortController();
      isBatchPaused = false;

      // Mostrar botón de pausa/reanudación
      if (pauseResumeBatchBtn) {
        pauseResumeBatchBtn.classList.remove('hidden');
        if (pauseResumeIcon) pauseResumeIcon.className = 'fa-solid fa-pause text-[9px]';
        if (pauseResumeText) pauseResumeText.textContent = 'Pausar';
        pauseResumeBatchBtn.className = 'px-2.5 py-0.5 rounded bg-amber-100 hover:bg-amber-200 text-amber-800 text-[10px] font-semibold transition flex items-center gap-1 shadow-xs';
      }

      // Mostrar botón de cancelación
      if (cancelBatchBtn) {
        cancelBatchBtn.classList.remove('hidden');
        cancelBatchBtn.onclick = () => {
          if (abortBatchCtrl) abortBatchCtrl.abort();
          if (pauseBatchResolver) {
            pauseBatchResolver();
            pauseBatchResolver = null;
          }
          isBatchPaused = false;
          if (pauseResumeBatchBtn) pauseResumeBatchBtn.classList.add('hidden');
          cancelBatchBtn.classList.add('hidden');
          if (liveScannerBadge) {
            liveScannerBadge.textContent = 'LOTE DETENIDO';
            liveScannerBadge.className = 'px-2 py-0.5 rounded bg-rose-600 text-white font-bold text-[10px] font-mono';
          }
          toast('Procesamiento de lote detenido por el usuario');
        };
      }

      if (liveScannerBadge) {
        liveScannerBadge.textContent = `LOTE EN CURSO (0/${totalBatchPosts})`;
        liveScannerBadge.className = 'px-2 py-0.5 rounded bg-indigo-600 text-white font-bold text-[10px] font-mono uppercase tracking-wider shrink-0 animate-pulse shadow-xs';
      }

      if (batchProgressLabel) batchProgressLabel.textContent = `Progreso total del lote clasificado (${totalBatchPosts} posts)`;
      if (batchProgressPercent) batchProgressPercent.textContent = `0% (0/${totalBatchPosts})`;
      if (batchProgressBar) {
        batchProgressBar.style.width = '0%';
        batchProgressBar.className = 'bg-gradient-to-r from-indigo-500 via-emerald-500 to-teal-400 h-full transition-all duration-150 rounded-full';
      }

      // Vista previa inmediata del primer post
      if (postsToProcess.length > 0) {
        const first = postsToProcess[0];
        if (livePostAuthor) livePostAuthor.textContent = `@${first.author}`;
        const snippetSnippet = first.text.length > 70 ? first.text.substring(0, 70) + '...' : first.text;
        if (livePostSnippet) livePostSnippet.textContent = `"${snippetSnippet}"`;
        if (singlePostStageText) singlePostStageText.textContent = `Analizando post 1/${totalBatchPosts} con Laya AI...`;
        if (singlePostPercent) singlePostPercent.textContent = '20%';
        if (singlePostProgressBar) {
          singlePostProgressBar.style.width = '20%';
          singlePostProgressBar.className = 'bg-amber-500 h-full rounded-full transition-all duration-150';
        }
      }

      const originalBtnHtml = analyzeSingleBtn.innerHTML;
      analyzeSingleBtn.disabled = true;
      analyzeSingleBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i><span>Lote (0/${totalBatchPosts})...</span>`;

      try {
        const dupStrategy = getSelectedDuplicateStrategy();
        const activeQList = getSelectedQuestionsList();
        const response = await fetch('/api/posts/analyze-batch-stream', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            posts: postsToProcess,
            persist: true,
            duplicate_strategy: dupStrategy,
            max_new_posts: dupStrategy === 'skip' ? postsToProcess.length : null,
            active_questions: activeQList
          }),
          signal: abortBatchCtrl.signal
        });

        if (!response.ok) {
          let errDetail = `HTTP ${response.status}: Error al iniciar stream de lote`;
          try {
            const errJson = await response.json();
            if (errJson && errJson.detail) {
              if (Array.isArray(errJson.detail)) {
                errDetail = errJson.detail.map(d => `${d.loc ? d.loc.join('.') : ''}: ${d.msg}`).join(' | ');
              } else {
                errDetail = String(errJson.detail);
              }
            }
          } catch (_) {}
          console.error('[IngestModal] Error en backend al iniciar stream:', errDetail);
          throw new Error(errDetail);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';

        while (true) {
          if (isBatchPaused) {
            await new Promise(r => { pauseBatchResolver = r; });
          }
          if (abortBatchCtrl.signal.aborted) break;

          const { value, done } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop();

          for (const line of lines) {
            if (!line.trim()) continue;
            let eventItem = null;
            try {
              eventItem = JSON.parse(line.trim());
            } catch (_) {
              continue;
            }

            if (eventItem.event === 'item_completed' && eventItem.post) {
              const p = eventItem.post;
              if (p && p.tweet_id && cachedRegisteredIds) {
                cachedRegisteredIds.add(String(p.tweet_id).trim());
              }
              const isSkipped = !!(eventItem.telemetry && eventItem.telemetry.skipped);
              const isReclassified = !!(eventItem.telemetry && eventItem.telemetry.reclassified);

              // 1. Actualizar Micro-barra del Post Individual finalizado
              if (livePostAuthor) livePostAuthor.textContent = `@${p.author_name}`;
              const compSnippet = p.content.length > 70 ? p.content.substring(0, 70) + '...' : p.content;
              if (livePostSnippet) livePostSnippet.textContent = `"${compSnippet}"`;

              if (singlePostPercent) singlePostPercent.textContent = '100%';
              if (singlePostProgressBar) {
                singlePostProgressBar.style.width = '100%';
                if (isSkipped) {
                  singlePostProgressBar.className = 'bg-slate-400 h-full rounded-full';
                } else if (p.is_outlier) {
                  singlePostProgressBar.className = 'bg-orange-500 h-full rounded-full';
                } else {
                  singlePostProgressBar.className = 'bg-emerald-500 h-full rounded-full';
                }
              }
              if (singlePostStageText) {
                if (isSkipped) {
                  singlePostStageText.textContent = `[OMITIDO/0ms] ${p.category_label || p.primary_category} (Métricas actualizadas)`;
                } else if (isReclassified) {
                  singlePostStageText.textContent = `[RECLASIFICADO] ${p.category_label || p.primary_category} (v${p.taxonomy_version || '2.1.0'} · Intento #${p.reclassification_count || 1})`;
                } else {
                  singlePostStageText.textContent = `[${p.code}] ${p.category_label || p.primary_category} (${Math.round(p.affinity_score * 100)}% afinidad)`;
                }
              }

              if (liveDecisionTarget) {
                const badgeLabel = isSkipped ? `${p.code} · OMITIDO` : (isReclassified ? `${p.code} · RECLASIF.` : `${p.code} · ${Math.round(p.affinity_score * 100)}%`);
                liveDecisionTarget.textContent = `${p.category_label || p.primary_category} (${badgeLabel})`;
                liveDecisionTarget.style.backgroundColor = isSkipped ? '#64748b' : (p.color_hex || '#059669');
                liveDecisionTarget.style.color = '#ffffff';
                liveDecisionTarget.className = 'px-2.5 py-0.5 rounded font-bold text-[11px] font-mono transition-all flex items-center gap-1.5 shadow-xs text-white';
              }

              // 2. Actualizar Barra Global de Lote
              const batchPct = Math.round((eventItem.index / totalBatchPosts) * 100);
              if (batchProgressPercent) batchProgressPercent.textContent = `${batchPct}% (${eventItem.index}/${totalBatchPosts})`;
              if (batchProgressBar) batchProgressBar.style.width = `${batchPct}%`;

              if (liveScannerBadge && !isBatchPaused) {
                liveScannerBadge.textContent = isSkipped ? `OMITIDO (${eventItem.index}/${totalBatchPosts})` : `LOTE EN CURSO (${eventItem.index}/${totalBatchPosts})`;
              }

              // 3. Inyectar progresivamente en la Matriz Waffle deduplicando en memoria
              const posts = getCurrentScrapedPosts();
              const rawSrc = (normalizedPosts && normalizedPosts[eventItem.index - 1]) ? normalizedPosts[eventItem.index - 1] : null;
              const newPost = typeof formatAppPost === 'function' ? formatAppPost(p, rawSrc, p) : p;

              const existingIdx = posts.findIndex(item => (item.id === newPost.id || item.tweet_id === newPost.id || item.id === p.tweet_id));
              if (existingIdx !== -1) {
                posts[existingIdx] = newPost;
                if (typeof renderMatrix === 'function') {
                  renderMatrix();
                }
              } else {
                posts.unshift(newPost);
                if (typeof appendPostToMatrixRow === 'function') {
                  appendPostToMatrixRow(newPost);
                } else if (typeof renderMatrix === 'function') {
                  renderMatrix();
                }
              }

              // Actualizar vista previa del SIGUIENTE post en la micro-barra
              if (eventItem.index < totalBatchPosts) {
                const nextP = normalizedPosts[eventItem.index];
                if (nextP) {
                  setTimeout(() => {
                    if (livePostAuthor) livePostAuthor.textContent = `@${nextP.author}`;
                    const nSnippet = nextP.text.length > 70 ? nextP.text.substring(0, 70) + '...' : nextP.text;
                    if (livePostSnippet) livePostSnippet.textContent = `"${nSnippet}"`;
                    if (singlePostStageText) singlePostStageText.textContent = `Analizando post ${eventItem.index + 1}/${totalBatchPosts} con Laya AI...`;
                    if (singlePostPercent) singlePostPercent.textContent = '20%';
                    if (singlePostProgressBar) {
                      singlePostProgressBar.style.width = '20%';
                      singlePostProgressBar.className = 'bg-amber-500 h-full rounded-full transition-all duration-150';
                    }
                  }, 100);
                }
              }

              if (window.AnalysisResultModal && typeof window.AnalysisResultModal.populate === 'function') {
                window.AnalysisResultModal.populate(p);
              }
              if (viewBtn) viewBtn.classList.remove('hidden');

            } else if (eventItem.event === 'batch_completed') {
              if (batchProgressPercent) batchProgressPercent.textContent = `100% (${totalBatchPosts}/${totalBatchPosts})`;
              if (batchProgressBar) batchProgressBar.style.width = '100%';
              if (liveScannerBadge) {
                liveScannerBadge.textContent = `LOTE COMPLETADO (${totalBatchPosts} POSTS)`;
                liveScannerBadge.className = 'px-2 py-0.5 rounded bg-emerald-600 text-white font-bold text-[10px] font-mono uppercase tracking-wider shrink-0 shadow-xs';
              }
              if (singlePostStageText) {
                singlePostStageText.textContent = `Lote finalizado con éxito: ${totalBatchPosts} posts analizados e inyectados.`;
              }
              if (pauseResumeBatchBtn) pauseResumeBatchBtn.classList.add('hidden');
              if (cancelBatchBtn) cancelBatchBtn.classList.add('hidden');
              if (typeof renderQuadrantScatter === 'function') {
                renderQuadrantScatter();
              }
              if (cachedRegisteredIds) {
                postsToProcess.forEach(item => {
                  if (item.id) cachedRegisteredIds.add(String(item.id).trim());
                  if (item.tweet_id) cachedRegisteredIds.add(String(item.tweet_id).trim());
                });
              }
              const total = loadedFilePosts ? loadedFilePosts.length : 0;
              updateBatchLimitUI(total);
              toast(`Lote de ${totalBatchPosts} posts clasificado exitosamente en la Matriz`);
            }
          }
        }

      } catch (err) {
        if (err.name !== 'AbortError') {
          if (window.AnalysisResultModal && typeof window.AnalysisResultModal.handleError === 'function') {
            window.AnalysisResultModal.handleError(err);
          } else if (typeof handleAnalysisError === 'function') {
            handleAnalysisError(err);
          }
        }
      } finally {
        if (pauseResumeBatchBtn) pauseResumeBatchBtn.classList.add('hidden');
        if (cancelBatchBtn) cancelBatchBtn.classList.add('hidden');
        analyzeSingleBtn.disabled = false;
        analyzeSingleBtn.innerHTML = originalBtnHtml;
      }
    },

    bindEvents() {
      if (openIngestModalBtn) openIngestModalBtn.addEventListener('click', () => IngestModal.open());
      if (closeIngestModalBtn) closeIngestModalBtn.addEventListener('click', () => IngestModal.close());
      if (cancelIngestBtn) cancelIngestBtn.addEventListener('click', () => IngestModal.close());

      if (loadSampleInModalBtn) {
        loadSampleInModalBtn.addEventListener('click', () => {
          if (jsonPasteArea) {
            jsonPasteArea.value = JSON.stringify([
              { id: "101", text: "Announcing our new open source 3D physics library in Rust with benchmarks!", likes: 1420, retweets: 310 },
              { id: "102", text: "Breakdown of how we scaled WebSockets to 50k concurrent users step by step.", likes: 890, retweets: 140 },
              { id: "103", text: "Hit $15k MRR this month after shipping our v2 onboarding flow.", likes: 2150, retweets: 430 },
              { id: "104", text: "Why you should stop using microservices for early stage MVP startups.", likes: 4300, retweets: 890 }
            ], null, 2);
          }
        });
      }

      if (clearSelectedFileBtn) {
        clearSelectedFileBtn.addEventListener('click', () => {
          IngestModal.clearLoadedFile();
          const toast = getShowToast();
          toast('Archivo descartado. Puedes escribir o pegar texto manual.');
        });
      }

      if (jsonFileInput) {
        jsonFileInput.addEventListener('change', (e) => {
          const file = e.target.files[0];
          const toast = getShowToast();
          if (!file) {
            IngestModal.clearLoadedFile();
            return;
          }
          const reader = new FileReader();
          reader.onload = (evt) => {
            try {
              const rawContent = evt.target.result;
              const normalized = IngestModal.parseAndNormalizeRawInput(rawContent);
              if (!normalized || normalized.length === 0) {
                throw new Error('No se detectaron publicaciones con texto válido dentro del archivo');
              }
              loadedFilePosts = normalized;

              if (fileInfoCard) fileInfoCard.classList.remove('hidden');
              if (fileInfoName) fileInfoName.textContent = file.name;
              if (fileInfoSize) {
                const kb = (file.size / 1024).toFixed(1);
                fileInfoSize.textContent = `${kb} KB`;
              }
              if (fileInfoPostsCount) fileInfoPostsCount.textContent = `${normalized.length}`;
              
              let engineName = 'JSON estándar';
              try {
                const quickObj = JSON.parse(rawContent.replace(/,\s*([\]}])/g, '$1'));
                if (quickObj.metadata && quickObj.metadata.engine) {
                  engineName = quickObj.metadata.engine;
                }
              } catch (_) {}
              if (fileInfoEngine) fileInfoEngine.textContent = `Motor: ${engineName}`;

              if (pasteSectionSeparator) pasteSectionSeparator.classList.add('hidden');
              if (pasteSectionContainer) pasteSectionContainer.classList.add('hidden');
              if (normalized.length > 5 && activeBatchLimit === 'all') {
                activeBatchLimit = 5;
              }
              updateBatchLimitUI(normalized.length);
              toast(`Archivo cargado: ${normalized.length} publicaciones listas para clasificar`);
            } catch (err) {
              toast(`Error al procesar archivo JSON: ${err.message}`);
              IngestModal.clearLoadedFile();
            }
          };
          reader.readAsText(file);
        });
      }

      // Listeners de presets de límite de lote (Subfase 5.13.1 - Control de CPU)
      const presetBtns = document.querySelectorAll('.limit-preset-btn');
      presetBtns.forEach(btn => {
        btn.addEventListener('click', () => {
          const lim = btn.getAttribute('data-limit');
          activeBatchLimit = lim === 'all' ? 'all' : parseInt(lim, 10);
          const total = loadedFilePosts ? loadedFilePosts.length : 100;
          updateBatchLimitUI(total);
        });
      });

      const limitInput = document.getElementById('batchLimitInput');
      if (limitInput) {
        limitInput.addEventListener('input', (e) => {
          const val = parseInt(e.target.value, 10);
          if (!isNaN(val) && val > 0) {
            activeBatchLimit = val;
          } else if (e.target.value === '') {
            activeBatchLimit = 'all';
          }
          const total = loadedFilePosts ? loadedFilePosts.length : 100;
          updateBatchLimitUI(total);
        });
      }

      if (pauseResumeBatchBtn) {
        pauseResumeBatchBtn.addEventListener('click', () => {
          const toast = getShowToast();
          isBatchPaused = !isBatchPaused;
          const badge = document.getElementById('liveScannerBadge');

          if (isBatchPaused) {
            if (pauseResumeIcon) pauseResumeIcon.className = 'fa-solid fa-play text-[9px]';
            if (pauseResumeText) pauseResumeText.textContent = 'Reanudar';
            pauseResumeBatchBtn.className = 'px-2.5 py-0.5 rounded bg-emerald-100 hover:bg-emerald-200 text-emerald-800 text-[10px] font-semibold transition flex items-center gap-1 shadow-xs';
            if (badge) {
              badge.textContent = 'LOTE EN PAUSA';
              badge.className = 'px-2 py-0.5 rounded bg-amber-500 text-white font-bold text-[10px] font-mono uppercase tracking-wider shrink-0 shadow-xs';
            }
            toast('Lote pausado. Pulsa Reanudar para continuar');
          } else {
            if (pauseResumeIcon) pauseResumeIcon.className = 'fa-solid fa-pause text-[9px]';
            if (pauseResumeText) pauseResumeText.textContent = 'Pausar';
            pauseResumeBatchBtn.className = 'px-2.5 py-0.5 rounded bg-amber-100 hover:bg-amber-200 text-amber-800 text-[10px] font-semibold transition flex items-center gap-1 shadow-xs';
            if (badge) {
              badge.textContent = 'LOTE EN CURSO';
              badge.className = 'px-2 py-0.5 rounded bg-indigo-600 text-white font-bold text-[10px] font-mono uppercase tracking-wider shrink-0 animate-pulse shadow-xs';
            }
            if (pauseBatchResolver) {
              pauseBatchResolver();
              pauseBatchResolver = null;
            }
            toast('Reanudando análisis del lote...');
          }
        });
      }

      if (analyzeSingleBtn) {
        analyzeSingleBtn.addEventListener('click', () => IngestModal.executeAnalysis());
      }

      if (jsonPasteArea) {
        jsonPasteArea.addEventListener('input', () => {
          updateBatchLimitUI();
        });
      }

      const dupRadios = document.querySelectorAll('input[name="duplicateStrategy"]');
      dupRadios.forEach(radio => {
        radio.addEventListener('change', () => {
          const total = loadedFilePosts ? loadedFilePosts.length : 0;
          updateBatchLimitUI(total);
        });
      });

      const profileRadios = document.querySelectorAll('input[name="questionsProfile"]');
      profileRadios.forEach(radio => {
        radio.addEventListener('change', () => {
          updateQuestionsProfileUI();
        });
      });

      if (clearMatrixBtn) {
        clearMatrixBtn.addEventListener('click', () => {
          const toast = getShowToast();
          window.currentScrapedPosts = [];
          if (typeof renderMatrix === 'function') renderMatrix();

          const badge = document.getElementById('liveScannerBadge');
          if (badge) {
            badge.textContent = 'EN ESPERA';
            badge.className = 'px-2 py-0.5 rounded bg-stone-200 text-stone-700 font-bold text-[10px] font-mono uppercase tracking-wider shrink-0 transition-colors';
          }
          const author = document.getElementById('livePostAuthor');
          if (author) author.textContent = '@dev_user';
          const snippet = document.getElementById('livePostSnippet');
          if (snippet) snippet.textContent = 'Pega un post en "JSON" y pulsa "Analizar con Laya AI" para observar cómo se clasifica e inyecta en la Matriz...';
          const target = document.getElementById('liveDecisionTarget');
          if (target) {
            target.textContent = '—';
            target.className = 'px-2.5 py-0.5 rounded bg-stone-200/80 text-stone-600 font-bold text-[11px] transition-all flex items-center gap-1.5 shadow-xs';
            target.style.backgroundColor = '';
            target.style.color = '';
          }
          const viewBtn = document.getElementById('viewAnalysisModalBtn');
          if (viewBtn) viewBtn.classList.add('hidden');
          const singleText = document.getElementById('singlePostStageText');
          if (singleText) singleText.textContent = 'Etapa del post: Listo para analizar tokens y estructura semántica';
          const singlePct = document.getElementById('singlePostPercent');
          if (singlePct) singlePct.textContent = '0%';
          const singleBar = document.getElementById('singlePostProgressBar');
          if (singleBar) {
            singleBar.style.width = '0%';
            singleBar.className = 'bg-amber-500 h-full w-0 transition-all duration-100 rounded-full';
          }
          const batchLabel = document.getElementById('batchProgressLabel');
          if (batchLabel) batchLabel.textContent = 'Progreso total del lote clasificado';
          const batchPct = document.getElementById('batchProgressPercent');
          if (batchPct) batchPct.textContent = '0% (0/0)';
          const batchBar = document.getElementById('batchProgressBar');
          if (batchBar) {
            batchBar.style.width = '0%';
            batchBar.className = 'bg-gradient-to-r from-emerald-600 via-emerald-500 to-teal-400 h-full w-0 transition-all duration-150 rounded-full';
          }
          toast('Matriz reiniciada: todas las categorías están vacías');
        });
      }

      const quickResetDbBtn = document.getElementById('quickResetDbBtn');
      if (quickResetDbBtn) {
        quickResetDbBtn.addEventListener('click', async () => {
          const toast = getShowToast();
          const confirmed = window.confirm(
            '¿Deseas vaciar los posts de prueba de la base de datos SQLite?\n\n' +
            'Esta acción eliminará los registros analizados para permitir un lote limpio.\n' +
            '(La taxonomía categories.json permanecerá 100% protegida e intacta).'
          );
          if (!confirmed) return;

          try {
            toast('Reiniciando base de datos SQLite...');
            const response = await fetch('/api/database/reset', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                clear_posts: true,
                clear_history: true,
                clear_checkpoints: true,
                clear_feedback: false,
                vacuum: true
              })
            });

            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const res = await response.json();

            // Limpiar memoria y UI
            window.currentScrapedPosts = [];
            if (window.AppState && typeof window.AppState.clearPosts === 'function') {
              window.AppState.clearPosts();
            }
            if (typeof renderMatrix === 'function') renderMatrix();

            // Reset de scanner visual
            if (clearMatrixBtn) clearMatrixBtn.click();

            toast(res.message || 'Base de datos y matriz reiniciadas a cero');
          } catch (err) {
            console.error('[IngestModal] Error en reinicio rápido:', err);
            toast(`Error al reiniciar: ${err.message}`, true);
          }
        });
      }
    }
  };

  window.IngestModal = IngestModal;
  window.parseAndNormalizeRawInput = raw => IngestModal.parseAndNormalizeRawInput(raw);

  if (document.readyState === 'loading') {
    window.addEventListener('DOMContentLoaded', () => IngestModal.bindEvents());
  } else {
    IngestModal.bindEvents();
  }

})(window);
