/**
 * GLOBALS.JS - Global Settings & Deterministic Boosters Controller (Laya Engine v2.1.0)
 * Sincronización del formulario de umbrales por defecto, sliders reactivos y persistencia con PUT /api/categories/settings/globals.
 */

(function(window) {
  'use strict';

  function getState() {
    return window.ConfigState || {};
  }

  function getShowToast() {
    return (window.ConfigApp && window.ConfigApp.showToast) ? window.ConfigApp.showToast : console.log;
  }

  const ConfigGlobals = {
    /**
     * Rellena el formulario de ajustes globales con los datos actuales
     */
    populateForm() {
      const state = getState();
      if (!state.registryData?.global_settings) return;
      const g = state.registryData.global_settings;

      const fallbackCat = document.getElementById('settingFallbackCategory');
      if (fallbackCat) fallbackCat.value = g.fallback_category || 'otros';

      const fallbackFmt = document.getElementById('settingFallbackFormat');
      if (fallbackFmt) fallbackFmt.value = g.fallback_format || 'other';

      const maxLabels = document.getElementById('settingMaxLabels');
      if (maxLabels) maxLabels.value = g.max_labels_per_post || 4;

      const defThresh = document.getElementById('settingDefaultThreshold');
      const labelDefThresh = document.getElementById('labelGlobalThreshold');
      if (defThresh) {
        defThresh.value = g.default_threshold ?? 0.75;
        if (labelDefThresh) labelDefThresh.textContent = parseFloat(defThresh.value).toFixed(2);
      }

      const minConf = document.getElementById('settingMinConfidence');
      const labelMinConf = document.getElementById('labelMinConfidence');
      if (minConf) {
        minConf.value = g.min_confidence_abstain ?? 0.55;
        if (labelMinConf) labelMinConf.textContent = parseFloat(minConf.value).toFixed(2);
      }

      const minPrim = document.getElementById('settingMinPrimary');
      const labelMinPrim = document.getElementById('labelMinPrimary');
      if (minPrim) {
        minPrim.value = g.min_threshold_for_primary ?? 0.70;
        if (labelMinPrim) labelMinPrim.textContent = parseFloat(minPrim.value).toFixed(2);
      }
    },

    /**
     * Persiste los ajustes globales en el backend FastAPI (categories.json)
     */
    async saveSettings() {
      const state = getState();
      const showToast = getShowToast();

      const saveBtn = document.getElementById('btnSaveGlobals');
      if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-1"></i> Guardando...';
      }

      const payload = {
        fallback_category: document.getElementById('settingFallbackCategory')?.value.trim() || 'otros',
        fallback_format: document.getElementById('settingFallbackFormat')?.value.trim() || 'other',
        default_threshold: parseFloat(document.getElementById('settingDefaultThreshold')?.value) || 0.75,
        min_confidence_abstain: parseFloat(document.getElementById('settingMinConfidence')?.value) || 0.55,
        max_labels_per_post: parseInt(document.getElementById('settingMaxLabels')?.value, 10) || 4,
        min_threshold_for_primary: parseFloat(document.getElementById('settingMinPrimary')?.value) || 0.70
      };

      try {
        const res = await API.categories.updateGlobalSettings(payload);
        showToast('Ajustes globales actualizados exitosamente en categories.json');
        if (state.registryData) {
          state.registryData.global_settings = { ...state.registryData.global_settings, ...res.settings };
        }
        if (state.updateTelemetryHUD) state.updateTelemetryHUD();
        if (window.ConfigCategories && typeof window.ConfigCategories.renderGrid === 'function') {
          window.ConfigCategories.renderGrid();
        }
      } catch (err) {
        console.error('Error al guardar ajustes globales:', err);
        showToast(err.message || 'Error al persistir ajustes globales', true);
      } finally {
        if (saveBtn) {
          saveBtn.disabled = false;
          saveBtn.innerHTML = '<i class="fa-solid fa-floppy-disk text-xs"></i> <span>Guardar Ajustes Globales</span>';
        }
      }
    },

    /**
     * Registra los observadores de cambio en sliders y controles de ajustes
     */
    bindSliderEvents() {
      document.getElementById('settingDefaultThreshold')?.addEventListener('input', e => {
        const val = parseFloat(e.target.value).toFixed(2);
        const label = document.getElementById('labelGlobalThreshold');
        const badge = document.getElementById('badgeDefaultThreshold');
        if (label) label.textContent = val;
        if (badge) badge.textContent = `≥ ${val}`;
      });

      document.getElementById('settingMinConfidence')?.addEventListener('input', e => {
        const label = document.getElementById('labelMinConfidence');
        if (label) label.textContent = parseFloat(e.target.value).toFixed(2);
      });

      document.getElementById('settingMinPrimary')?.addEventListener('input', e => {
        const label = document.getElementById('labelMinPrimary');
        if (label) label.textContent = parseFloat(e.target.value).toFixed(2);
      });

      document.getElementById('btnSaveGlobals')?.addEventListener('click', () => {
        ConfigGlobals.saveSettings();
      });
    }
  };

  // Exposición en namespace global
  window.ConfigGlobals = ConfigGlobals;

  // Aliases legacy
  window.populateGlobalsForm = () => ConfigGlobals.populateForm();
  window.saveGlobalSettings = () => ConfigGlobals.saveSettings();

})(window);
