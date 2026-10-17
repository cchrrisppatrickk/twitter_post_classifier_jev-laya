/**
 * ANALYSIS_RESULT_MODAL.JS - Laya AI Single Post Inference Modal Controller (v2.1.0)
 * Visualización en demanda del desglose de tokens, afinidad RLCD, formato, profundidad y persistencia.
 */

(function(window) {
  'use strict';

  const analysisResultModal = document.getElementById('analysisResultModal');
  const closeAnalysisResultModalBtn = document.getElementById('closeAnalysisResultModalBtn');
  const closeAnalysisResultModalBtn2 = document.getElementById('closeAnalysisResultModalBtn2');
  const copyAnalysisJsonBtn = document.getElementById('copyAnalysisJsonBtn');
  const copyAnalysisJsonText = document.getElementById('copyAnalysisJsonText');
  const saveAnalysisToMatrixBtn = document.getElementById('saveAnalysisToMatrixBtn');
  const openRichFromAnalysisBtn = document.getElementById('openRichFromAnalysisBtn');
  const viewAnalysisModalBtn = document.getElementById('viewAnalysisModalBtn');

  let currentAnalyzedPost = null;

  function getShowToast() {
    return typeof showToast === 'function' ? showToast : console.log;
  }

  function getCurrentScrapedPosts() {
    return window.currentScrapedPosts || [];
  }

  const AnalysisResultModal = {
    getCurrentPost() {
      return currentAnalyzedPost;
    },

    setCurrentPost(post) {
      currentAnalyzedPost = post;
      window.currentAnalyzedPost = post;
    },

    open() {
      if (analysisResultModal) analysisResultModal.classList.remove('hidden');
    },

    close() {
      if (analysisResultModal) analysisResultModal.classList.add('hidden');
    },

    /**
     * Helper para inyectar datos en el modal de resultados
     * @param {Object} result 
     */
    populate(result) {
      this.setCurrentPost(result);

      const statusBadge = document.getElementById('analysisResultStatusBadge');
      if (statusBadge) {
        statusBadge.textContent = result.status;
        statusBadge.className = result.status === 'CLASSIFIED'
          ? 'px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-100 text-emerald-800 uppercase tracking-wider'
          : 'px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-100 text-amber-800 uppercase tracking-wider';
      }

      const latencyVal = document.getElementById('analysisLatencyVal');
      if (latencyVal) latencyVal.textContent = result.inference_latency_ms ? result.inference_latency_ms.toFixed(2) : '0';

      const engineBadge = document.getElementById('analysisResultEngineBadge');
      if (engineBadge) engineBadge.textContent = result.engine_used || 'laya';

      const authorEl = document.getElementById('analysisAuthorName');
      if (authorEl) authorEl.textContent = `@${result.author_name}`;

      const tweetIdEl = document.getElementById('analysisTweetId');
      if (tweetIdEl) tweetIdEl.textContent = `ID: ${result.tweet_id}`;

      const contentPreview = document.getElementById('analysisContentPreview');
      if (contentPreview) contentPreview.textContent = `"${result.content}"`;

      const catCode = document.getElementById('analysisCategoryCode');
      if (catCode) {
        catCode.textContent = result.code || 'CAT';
        catCode.style.backgroundColor = result.color_hex || '#3b82f6';
      }

      const catLabel = document.getElementById('analysisCategoryLabel');
      if (catLabel) catLabel.textContent = result.category_label || result.primary_category;

      const famLabel = document.getElementById('analysisFamilyLabel');
      if (famLabel) famLabel.textContent = `Familia: ${result.family_id}`;

      const affinityPct = Math.round(result.affinity_score * 100);
      const affText = document.getElementById('analysisAffinityPct');
      if (affText) affText.textContent = `${affinityPct}%`;

      const affBar = document.getElementById('analysisAffinityBar');
      if (affBar) affBar.style.width = `${affinityPct}%`;

      const formatVal = document.getElementById('analysisFormatVal');
      if (formatVal) formatVal.textContent = result.format;

      const formatConf = document.getElementById('analysisFormatConf');
      if (formatConf) formatConf.textContent = `Conf: ${Math.round((result.format_confidence || 0) * 100)}%`;

      const techDepthVal = document.getElementById('analysisTechDepthVal');
      if (techDepthVal) techDepthVal.textContent = `${(result.technical_depth || 1).toFixed(1)} / 5.0`;

      const jsonOutput = document.getElementById('analysisJsonOutput');
      if (jsonOutput) {
        jsonOutput.textContent = JSON.stringify(result, null, 2);
      }
    },

    /**
     * Helper para mostrar errores en la interfaz
     * @param {Error} err 
     */
    handleError(err) {
      const liveScannerBadge = document.getElementById('liveScannerBadge');
      if (liveScannerBadge) {
        liveScannerBadge.textContent = 'ERROR';
        liveScannerBadge.className = 'px-2 py-0.5 rounded bg-rose-600 text-white font-bold text-[10px] font-mono';
      }
      const liveDecisionTarget = document.getElementById('liveDecisionTarget');
      if (liveDecisionTarget) {
        liveDecisionTarget.textContent = 'Fallo de inferencia';
        liveDecisionTarget.className = 'px-2.5 py-0.5 rounded bg-rose-100 text-rose-800 font-bold text-[11px] font-mono';
      }
      const singlePostStageText = document.getElementById('singlePostStageText');
      if (singlePostStageText) singlePostStageText.textContent = `Error: ${err.message}`;
      const singlePostProgressBar = document.getElementById('singlePostProgressBar');
      if (singlePostProgressBar) singlePostProgressBar.className = 'bg-rose-500 h-full w-full rounded-full';
      
      const toast = getShowToast();
      toast('Error en análisis Laya: ' + err.message);
    },

    bindEvents() {
      if (closeAnalysisResultModalBtn) {
        closeAnalysisResultModalBtn.addEventListener('click', () => AnalysisResultModal.close());
      }
      if (closeAnalysisResultModalBtn2) {
        closeAnalysisResultModalBtn2.addEventListener('click', () => AnalysisResultModal.close());
      }

      if (viewAnalysisModalBtn) {
        viewAnalysisModalBtn.addEventListener('click', () => {
          if (currentAnalyzedPost) AnalysisResultModal.open();
        });
      }

      if (openRichFromAnalysisBtn) {
        openRichFromAnalysisBtn.addEventListener('click', () => {
          if (!currentAnalyzedPost) return;
          const formatted = typeof formatAppPost === 'function' 
            ? formatAppPost(currentAnalyzedPost, currentAnalyzedPost.raw_scraping || null, currentAnalyzedPost)
            : currentAnalyzedPost;
          AnalysisResultModal.close();
          if (window.RichPostModal && typeof window.RichPostModal.open === 'function') {
            window.RichPostModal.open(formatted);
          } else if (typeof openRichPostModal === 'function') {
            openRichPostModal(formatted);
          }
        });
      }

      if (copyAnalysisJsonBtn) {
        copyAnalysisJsonBtn.addEventListener('click', async () => {
          const toast = getShowToast();
          if (!currentAnalyzedPost) return;
          try {
            await navigator.clipboard.writeText(JSON.stringify(currentAnalyzedPost, null, 2));
            if (copyAnalysisJsonText) copyAnalysisJsonText.textContent = '¡Copiado!';
            setTimeout(() => {
              if (copyAnalysisJsonText) copyAnalysisJsonText.textContent = 'Copiar JSON';
            }, 2000);
            toast('JSON copiado al portapapeles');
          } catch (e) {
            toast('Error al copiar JSON: ' + e.message);
          }
        });
      }

      if (saveAnalysisToMatrixBtn) {
        saveAnalysisToMatrixBtn.addEventListener('click', async () => {
          const toast = getShowToast();
          if (!currentAnalyzedPost) return;

          // Si no está persistido en la base de datos, persistirlo
          if (!currentAnalyzedPost.persisted) {
            try {
              const persistReq = {
                id: currentAnalyzedPost.tweet_id,
                text: currentAnalyzedPost.content,
                author: currentAnalyzedPost.author_name,
                likes: currentAnalyzedPost.likes || 150,
                retweets: currentAnalyzedPost.retweets || 25,
                persist: true
              };
              await fetch('/api/posts/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(persistReq)
              });
              currentAnalyzedPost.persisted = true;
            } catch (err) {
              console.warn('Error al persistir en DB:', err);
            }
          }

          // Agregar a currentScrapedPosts en memoria y refrescar la matriz
          const posts = getCurrentScrapedPosts();
          const existingIdx = posts.findIndex(p => p.id === currentAnalyzedPost.tweet_id);
          const newPost = typeof formatAppPost === 'function'
            ? formatAppPost(currentAnalyzedPost, currentAnalyzedPost.raw_scraping || null, currentAnalyzedPost)
            : currentAnalyzedPost;

          if (existingIdx >= 0) {
            posts[existingIdx] = newPost;
          } else {
            posts.unshift(newPost);
          }

          if (typeof renderMatrix === 'function') renderMatrix();
          if (typeof renderQuadrantScatter === 'function') renderQuadrantScatter();
          
          toast(`Post añadido a la Matriz Waffle (${currentAnalyzedPost.primary_category})`);
          const persistNotice = document.getElementById('analysisPersistStatus');
          if (persistNotice) {
            persistNotice.innerHTML = '<i class="fa-solid fa-check-double text-emerald-600 mr-1"></i>Guardado en SQLite y Matriz Waffle';
          }
          saveAnalysisToMatrixBtn.disabled = true;
          saveAnalysisToMatrixBtn.classList.add('opacity-50', 'cursor-not-allowed');
        });
      }
    }
  };

  window.AnalysisResultModal = AnalysisResultModal;
  window.populateAnalysisResultModal = res => AnalysisResultModal.populate(res);
  window.handleAnalysisError = err => AnalysisResultModal.handleError(err);

  if (document.readyState === 'loading') {
    window.addEventListener('DOMContentLoaded', () => AnalysisResultModal.bindEvents());
  } else {
    AnalysisResultModal.bindEvents();
  }

})(window);
