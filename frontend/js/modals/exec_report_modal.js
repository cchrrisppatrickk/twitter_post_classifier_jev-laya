/**
 * EXEC_REPORT_MODAL.JS - Strategic Executive Performance Report Modal Controller (Laya Engine v2.1.0)
 * Diagnóstico automatizado de saturación, top formato y recomendaciones de sinergia semántica.
 */

(function(window) {
  'use strict';

  const execReportModal = document.getElementById('execReportModal');
  const openExecReportBtn = document.getElementById('openExecReportBtn');
  const closeExecReportBtn = document.getElementById('closeExecReportBtn');
  const closeExecReportBottomBtn = document.getElementById('closeExecReportBottomBtn');
  const execReportContent = document.getElementById('execReportContent');
  const copyReportTextBtn = document.getElementById('copyReportTextBtn');

  function getCategories() {
    return window.CATEGORIES || [];
  }

  function getCurrentScrapedPosts() {
    return window.currentScrapedPosts || [];
  }

  function getFormatNumberK() {
    return typeof formatNumberK === 'function' ? formatNumberK : (n => n);
  }

  function getShowToast() {
    return typeof showToast === 'function' ? showToast : console.log;
  }

  let lastGeneratedReportText = '';

  const ExecReportModal = {
    renderContent() {
      const categories = getCategories();
      const posts = getCurrentScrapedPosts();
      const formatK = getFormatNumberK();

      if (!execReportContent) return;

      if (!posts || posts.length === 0) {
        lastGeneratedReportText = 'REPORTE ESTRATÉGICO X-VIRALITY · JEV ENGINE v2.1.1\n\nSin publicaciones registradas en base de datos.';
        execReportContent.innerHTML = `
          <div class="bg-stone-50 p-6 rounded-xl border border-stone-200 text-center space-y-2">
            <i class="fa-solid fa-chart-pie text-3xl text-stone-400"></i>
            <h4 class="font-bold text-stone-800 text-xs font-mono">Sin Publicaciones en el Sistema</h4>
            <p class="text-[11px] text-stone-500 max-w-sm mx-auto">
              No hay publicaciones cargadas actualmente. Realiza una ingesta de archivo JSON o streaming SSE para generar el diagnóstico estratégico de rendimiento.
            </p>
          </div>
        `;
        return;
      }

      // 1. Estadísticas por categoría
      const catStats = {};
      posts.forEach(p => {
        const catId = p.category_id || p.primary_category || 'otros';
        if (!catStats[catId]) {
          const catMeta = categories.find(c => c.id === catId);
          catStats[catId] = {
            id: catId,
            name: catMeta?.name || catMeta?.label || catId,
            count: 0,
            totalLikes: 0,
            totalScore: 0
          };
        }
        catStats[catId].count++;
        catStats[catId].totalLikes += (p.likes || 0);
        catStats[catId].totalScore += (p.affinity_score || 0);
      });

      const catList = Object.values(catStats).map(c => ({
        ...c,
        avgLikes: Math.round(c.totalLikes / c.count),
        avgScore: Math.round(c.totalScore / c.count),
        pct: Math.round((c.count / posts.length) * 100)
      }));

      // Categoría de mayor engagement promedio
      const topEngagementCat = [...catList].sort((a, b) => b.avgLikes - a.avgLikes)[0] || catList[0];
      // Categoría de mayor volumen
      const volumeCat = [...catList].sort((a, b) => b.count - a.count)[0] || catList[0];

      // 2. Estadísticas de híbridos y formatos
      const hybridPosts = posts.filter(p => p.is_hybrid || (p.secondary_categories && p.secondary_categories.length > 0));
      const hybridCount = hybridPosts.length;
      const hybridPct = Math.round((hybridCount / posts.length) * 100);

      const hybridAvgLikes = hybridCount > 0
        ? Math.round(hybridPosts.reduce((s, p) => s + (p.likes || 0), 0) / hybridCount)
        : 0;

      const nonHybridPosts = posts.filter(p => !p.is_hybrid && (!p.secondary_categories || p.secondary_categories.length === 0));
      const nonHybridAvgLikes = nonHybridPosts.length > 0
        ? Math.round(nonHybridPosts.reduce((s, p) => s + (p.likes || 0), 0) / nonHybridPosts.length)
        : 0;

      let synergyInsight = '';
      if (nonHybridAvgLikes > 0 && hybridAvgLikes > nonHybridAvgLikes) {
        const upliftPct = Math.round(((hybridAvgLikes - nonHybridAvgLikes) / nonHybridAvgLikes) * 100);
        synergyInsight = `Las publicaciones híbridas multietiqueta superan en un <strong>+${upliftPct}% de engagement</strong> (${formatK(hybridAvgLikes)} vs ${formatK(nonHybridAvgLikes)} likes avg) a las publicaciones monotemáticas.`;
      } else if (hybridCount > 0) {
        synergyInsight = `Se registran <strong>${hybridCount} publicaciones híbridas</strong> (${hybridPct}% del catálogo) con una tracción media de <strong>${formatK(hybridAvgLikes)} likes</strong>.`;
      } else {
        synergyInsight = `No se detectan publicaciones híbridas en la muestra actual (${posts.length} posts). Aplicar co-ocurrencia semántica multi-label puede potenciar el descubrimiento temático cruzado.`;
      }

      // Preparar texto copiable
      lastGeneratedReportText = [
        `REPORTE ESTRATÉGICO X-VIRALITY · JEV ENGINE v2.1.1`,
        `Muestra Analizada: ${posts.length} publicaciones`,
        `1. Top Rendimiento: ${topEngagementCat.name} (${formatK(topEngagementCat.avgLikes)} likes avg)`,
        `2. Concentración de Volumen: ${volumeCat.name} (${volumeCat.count} posts, ${volumeCat.pct}% del catálogo)`,
        `3. Sinergia Híbrida: ${hybridCount} híbridos (${hybridPct}% de la muestra)`,
        `\nGenerado dinámicamente por X Content Classifier.`
      ].join('\n');

      execReportContent.innerHTML = `
        <div class="bg-emerald-50 p-3.5 rounded-xl border border-emerald-200">
          <div class="flex items-center justify-between mb-1">
            <h4 class="font-bold text-emerald-900 text-xs font-mono">1. Máximo Rendimiento por Categoría</h4>
            <span class="text-[10px] font-mono font-bold bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-full">
              ${formatK(topEngagementCat.avgLikes)} likes avg
            </span>
          </div>
          <p class="leading-relaxed text-[11px] text-emerald-800">
            La categoría con mayor tracción media es <strong>${topEngagementCat.name}</strong> (${topEngagementCat.count} post${topEngagementCat.count > 1 ? 's' : ''}). Concentra tus lanzamientos y esfuerzos de ingeniería en esta temática de alto impacto.
          </p>
        </div>
        <div class="bg-amber-50 p-3.5 rounded-xl border border-amber-200">
          <div class="flex items-center justify-between mb-1">
            <h4 class="font-bold text-amber-900 text-xs font-mono">2. Distribución y Volumen de Catálogo</h4>
            <span class="text-[10px] font-mono font-bold bg-amber-100 text-amber-800 px-2 py-0.5 rounded-full">
              ${volumeCat.pct}% del total
            </span>
          </div>
          <p class="leading-relaxed text-[11px] text-amber-800">
            El <strong>${volumeCat.pct}%</strong> de tus publicaciones (${volumeCat.count} de ${posts.length}) pertenecen a <strong>${volumeCat.name}</strong> con una media de ${formatK(volumeCat.avgLikes)} likes. Verifica si el volumen justifica el esfuerzo o si conviene diversificar hacia formatos de mayor conversión.
          </p>
        </div>
        <div class="bg-stone-50 p-3.5 rounded-xl border border-stone-200">
          <h4 class="font-bold text-stone-900 text-xs mb-1 font-mono">3. Recomendación de Sinergia y Co-ocurrencia</h4>
          <p class="leading-relaxed text-[11px] text-stone-600">
            ${synergyInsight}
          </p>
        </div>
      `;
    },

    open() {
      this.renderContent();
      if (execReportModal) execReportModal.classList.remove('hidden');
    },

    close() {
      if (execReportModal) execReportModal.classList.add('hidden');
    },

    copyReport() {
      const toast = getShowToast();
      const summaryText = lastGeneratedReportText || "REPORTE ESTRATÉGICO X-VIRALITY · JEV ENGINE v2.1.1\n\nGenerado por X Content Classifier.";
      
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(summaryText).then(() => {
          toast('Reporte copiado al portapapeles');
        }).catch(() => ExecReportModal.fallbackCopy(summaryText));
      } else {
        ExecReportModal.fallbackCopy(summaryText);
      }
    },

    fallbackCopy(text) {
      const toast = getShowToast();
      const dummyInput = document.createElement('textarea');
      dummyInput.value = text;
      document.body.appendChild(dummyInput);
      dummyInput.select();
      try {
        document.execCommand('copy');
        toast('Reporte copiado al portapapeles');
      } catch (_) {
        toast('Error al copiar al portapapeles');
      }
      document.body.removeChild(dummyInput);
    },

    bindEvents() {
      if (openExecReportBtn) openExecReportBtn.addEventListener('click', () => ExecReportModal.open());
      if (closeExecReportBtn) closeExecReportBtn.addEventListener('click', () => ExecReportModal.close());
      if (closeExecReportBottomBtn) closeExecReportBottomBtn.addEventListener('click', () => ExecReportModal.close());
      if (copyReportTextBtn) copyReportTextBtn.addEventListener('click', () => ExecReportModal.copyReport());
    }
  };

  window.ExecReportModal = ExecReportModal;

  if (document.readyState === 'loading') {
    window.addEventListener('DOMContentLoaded', () => ExecReportModal.bindEvents());
  } else {
    ExecReportModal.bindEvents();
  }

})(window);
