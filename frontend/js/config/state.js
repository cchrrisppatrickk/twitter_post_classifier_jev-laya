/**
 * STATE.JS - Config Studio Reactive State Store & Telemetry (Laya Engine v2.1.0)
 * Centraliza el estado reactivo, la carga de datos del backend y la actualización de métricas HUD.
 */

(function(window) {
  'use strict';

  // Familias y preguntas con protección estructural
  const PROTECTED_FAMILIES = ['ia', 'blender', 'modelado_3d', 'juegos', 'dev_tools', 'mangas', 'negocios_saas', 'otros'];
  const PROTECTED_QUESTIONS = ['content_format', 'technical_depth', 'reproducible_asset_type'];

  const ConfigState = {
    registryData: null,
    supplementaryQuestions: [],
    tempKeywords: [],
    tempExamples: [],
    tempExclusions: [],
    tempQuestionChoices: [],
    actionToConfirm: null,
    PROTECTED_FAMILIES,
    PROTECTED_QUESTIONS,

    /**
     * Normaliza la respuesta del endpoint de preguntas suplementarias
     */
    parseQuestionsResponse(qData) {
      const qObj = qData?.supplementary_questions || qData || {};
      if (Array.isArray(qObj)) return qObj;
      return Object.entries(qObj).map(([id, val]) => ({
        id,
        type: val.type || 'choice',
        question: val.instructions || val.question || '',
        active: val.active !== false,
        choices: val.criteria ? (Array.isArray(val.criteria) ? val.criteria : Object.keys(val.criteria)) : (val.choices || [])
      }));
    },

    /**
     * Carga todos los datos del backend (/api/categories y endpoints auxiliares)
     */
    async loadAllStudioData() {
      try {
        const [categoriesArray, globalsData, qData] = await Promise.all([
          API.categories.getAll(),
          API.categories.getGlobalSettings(),
          API.categories.getSupplementaryQuestions()
        ]);

        this.registryData = {
          registry_version: globalsData?.registry_version || '2.1.0',
          global_settings: globalsData?.global_settings || {},
          scoring: globalsData?.scoring || {},
          topic_categories: Array.isArray(categoriesArray) ? categoriesArray : (categoriesArray?.topic_categories || []),
          protected_families: globalsData?.protected_families || PROTECTED_FAMILIES
        };

        this.supplementaryQuestions = this.parseQuestionsResponse(qData);

        // Sincronizar variables globales legacy si se consultan directamente
        window.registryData = this.registryData;
        window.supplementaryQuestions = this.supplementaryQuestions;

        this.updateTelemetryHUD();

        // Invocar renderizado de módulos desacoplados si están disponibles
        if (window.ConfigCategories && typeof window.ConfigCategories.renderGrid === 'function') {
          window.ConfigCategories.renderGrid();
        }
        if (window.ConfigQuestions && typeof window.ConfigQuestions.renderGrid === 'function') {
          window.ConfigQuestions.renderGrid();
        }
        if (window.ConfigGlobals && typeof window.ConfigGlobals.populateForm === 'function') {
          window.ConfigGlobals.populateForm();
        }
      } catch (err) {
        console.error('Error al cargar datos del Registry Studio:', err);
        if (window.ConfigApp && typeof window.ConfigApp.showToast === 'function') {
          window.ConfigApp.showToast('Error al conectar con el servidor API de categorías', true);
        }
        const container = document.getElementById('categoriesGridContainer');
        if (container) {
          container.innerHTML = `
            <div class="col-span-full py-12 surface-card rounded-xl text-center text-xs space-y-2">
              <i class="fa-solid fa-triangle-exclamation text-rose-500 text-2xl"></i>
              <p class="font-bold text-rose-600">No se pudo cargar la taxonomía del servidor.</p>
              <p class="text-[var(--text-muted)]">${err.message || 'Verifica que el backend FastAPI esté ejecutándose.'}</p>
            </div>
          `;
        }
      }
    },

    /**
     * Actualiza los contadores de la barra superior y tarjetas resumen
     */
    updateTelemetryHUD() {
      if (!this.registryData) return;

      const cats = this.registryData.topic_categories || [];
      const globals = this.registryData.global_settings || {};

      const activeCats = cats.filter(c => c.active !== false).length;
      const families = cats.filter(c => c.is_family || c.parent_id === null).length;
      const subcats = cats.filter(c => c.parent_id !== null).length;

      // Header stats
      const statCount = document.getElementById('statCategoriesCount');
      if (statCount) statCount.textContent = activeCats;

      const statStrategy = document.getElementById('statStrategy');
      if (statStrategy) statStrategy.textContent = globals.primary_category_strategy || 'boosted_score';

      const statMax = document.getElementById('statMaxLabels');
      if (statMax) statMax.textContent = globals.max_labels_per_post || 4;

      // Badges resumen
      const badgeFamilies = document.getElementById('badgeTotalFamilies');
      if (badgeFamilies) badgeFamilies.textContent = families;

      const badgeSubcats = document.getElementById('badgeTotalSubcats');
      if (badgeSubcats) badgeSubcats.textContent = subcats;

      const badgeFallback = document.getElementById('badgeFallback');
      if (badgeFallback) badgeFallback.textContent = globals.fallback_category || 'otros';

      const badgeThreshold = document.getElementById('badgeDefaultThreshold');
      if (badgeThreshold) badgeThreshold.textContent = `≥ ${(globals.default_threshold ?? 0.75).toFixed(2)}`;

      // Tab preguntas
      const tabQTitle = document.getElementById('tabQuestionsTitle');
      if (tabQTitle) tabQTitle.textContent = `Banco de Preguntas Tipadas (${this.supplementaryQuestions.length})`;

      const badgeQTotal = document.getElementById('badgeQuestionsTotal');
      if (badgeQTotal) badgeQTotal.textContent = `${this.supplementaryQuestions.length} Consultas Tipadas`;
    }
  };

  // Exposición en namespace global
  window.ConfigState = ConfigState;
  window.PROTECTED_FAMILIES = PROTECTED_FAMILIES;
  window.PROTECTED_QUESTIONS = PROTECTED_QUESTIONS;

  // Aliases legacy para compatibilidad
  window.loadAllStudioData = () => ConfigState.loadAllStudioData();
  window.updateTelemetryHUD = () => ConfigState.updateTelemetryHUD();

})(window);
