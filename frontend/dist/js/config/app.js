/**
 * APP.JS - Config Studio Master Application Orchestrator (Laya Engine v2.1.0)
 * Orquestador principal, navegación de pestañas, tema visual, exportación JSON, confirmaciones y toasts.
 */

(function(window) {
  'use strict';

  function getState() {
    return window.ConfigState || {};
  }

  let actionToConfirm = null;

  const ConfigApp = {
    /**
     * Inicialización general del Registry Studio
     */
    async init() {
      this.initTheme();
      this.setupTabs();
      this.setupEventListeners();

      if (window.ConfigGlobals && typeof window.ConfigGlobals.bindSliderEvents === 'function') {
        window.ConfigGlobals.bindSliderEvents();
      }
      if (window.ConfigQuestions && typeof window.ConfigQuestions.bindEvents === 'function') {
        window.ConfigQuestions.bindEvents();
      }
      if (window.ConfigSimulator && typeof window.ConfigSimulator.bindEvents === 'function') {
        window.ConfigSimulator.bindEvents();
      }
      if (window.ConfigDatabase && typeof window.ConfigDatabase.bindEvents === 'function') {
        window.ConfigDatabase.bindEvents();
      }

      if (window.ConfigState && typeof window.ConfigState.loadAllStudioData === 'function') {
        await window.ConfigState.loadAllStudioData();
      }
    },

    /**
     * Sincroniza el tema visual claro/oscuro con localStorage y preferencias del sistema
     */
    initTheme() {
      const savedTheme = localStorage.getItem('tpcm_theme');
      const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
      const isDark = savedTheme === 'dark' || (!savedTheme && prefersDark);

      if (isDark) {
        document.body.classList.add('dark-mode');
      } else {
        document.body.classList.remove('dark-mode');
      }
      this.updateThemeToggleUI(isDark);
    },

    updateThemeToggleUI(isDark) {
      const icon = document.getElementById('themeIcon');
      const text = document.getElementById('themeText');
      if (icon) icon.className = isDark ? 'fa-solid fa-sun text-amber-400' : 'fa-solid fa-moon text-stone-600';
      if (text) text.textContent = isDark ? 'Tema Claro' : 'Modo Oscuro';
    },

    /**
     * Configura el enrutamiento de pestañas
     */
    setupTabs() {
      const tabButtons = document.querySelectorAll('.tab-btn');
      tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
          tabButtons.forEach(b => {
            b.classList.remove('active-tab');
            b.classList.add('surface-subtle');
          });
          btn.classList.add('active-tab');
          btn.classList.remove('surface-subtle');

          const target = btn.getAttribute('data-tab');
          const secCats = document.getElementById('sectionCategories');
          const secGlobals = document.getElementById('sectionGlobals');
          const secQuestions = document.getElementById('sectionQuestions');
          const secRules = document.getElementById('sectionRules');
          const secDatabase = document.getElementById('sectionDatabase');

          if (secCats) secCats.classList.toggle('hidden', target !== 'tab-categories');
          if (secGlobals) secGlobals.classList.toggle('hidden', target !== 'tab-globals');
          if (secQuestions) secQuestions.classList.toggle('hidden', target !== 'tab-questions');
          if (secRules) secRules.classList.toggle('hidden', target !== 'tab-rules');
          if (secDatabase) secDatabase.classList.toggle('hidden', target !== 'tab-database');

          if (target === 'tab-database' && window.ConfigDatabase && typeof window.ConfigDatabase.loadStats === 'function') {
            window.ConfigDatabase.loadStats();
          }
        });
      });
    },

    /**
     * Muestra notificación Toast flotante
     */
    showToast(message, isError = false) {
      const toast = document.getElementById('toastNotification');
      const toastMsg = document.getElementById('toastMessage');
      const toastIcon = document.getElementById('toastIcon');
      if (!toast || !toastMsg) return;

      toastMsg.textContent = message;
      if (isError) {
        toast.classList.remove('border-emerald-500/50');
        toast.classList.add('border-rose-500/60');
        if (toastIcon) toastIcon.className = 'fa-solid fa-circle-exclamation text-rose-500 text-sm';
      } else {
        toast.classList.remove('border-rose-500/60');
        toast.classList.add('border-emerald-500/50');
        if (toastIcon) toastIcon.className = 'fa-solid fa-circle-check text-emerald-500 text-sm';
      }

      toast.classList.remove('translate-y-16', 'opacity-0');
      toast.classList.add('translate-y-0', 'opacity-100');

      setTimeout(() => {
        toast.classList.remove('translate-y-0', 'opacity-100');
        toast.classList.add('translate-y-16', 'opacity-0');
      }, 2600);
    },

    /**
     * Modal seguro de confirmación para acciones destructivas
     */
    askConfirmation(title, message, onConfirm) {
      const titleElem = document.getElementById('confirmActionTitle');
      const msgElem = document.getElementById('confirmActionMessage');
      const modal = document.getElementById('confirmActionModal');

      if (titleElem) titleElem.textContent = title;
      if (msgElem) msgElem.textContent = message;
      actionToConfirm = onConfirm;
      if (modal) modal.classList.remove('hidden');
    },

    /**
     * Abre el modal de exportación de esquema JSON
     */
    openJsonModal() {
      const state = getState();
      if (!state.registryData) return;
      const codeElem = document.getElementById('jsonPreviewCode');
      if (codeElem) codeElem.textContent = JSON.stringify(state.registryData, null, 2);
      document.getElementById('jsonModal')?.classList.remove('hidden');
    },

    escapeHtml(text) {
      if (!text) return '';
      return String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
    },

    fallbackCopy(text) {
      const dummy = document.createElement('textarea');
      dummy.value = text;
      document.body.appendChild(dummy);
      dummy.select();
      try {
        document.execCommand('copy');
        this.showToast('JSON v2.1.0 copiado al portapapeles');
      } catch (err) {
        this.showToast('Error al copiar el texto', true);
      }
      document.body.removeChild(dummy);
    },

    setupEventListeners() {
      // Toggle Tema Claro / Oscuro
      document.getElementById('btnToggleTheme')?.addEventListener('click', () => {
        document.body.classList.toggle('dark-mode');
        const isDark = document.body.classList.contains('dark-mode');
        localStorage.setItem('tpcm_theme', isDark ? 'dark' : 'light');
        ConfigApp.updateThemeToggleUI(isDark);
      });

      // Búsqueda y Filtros de Categorías
      document.getElementById('searchCategoriesInput')?.addEventListener('input', () => {
        if (window.ConfigCategories) window.ConfigCategories.renderGrid();
      });
      document.getElementById('filterFamilySelect')?.addEventListener('change', () => {
        if (window.ConfigCategories) window.ConfigCategories.renderGrid();
      });
      document.getElementById('sortCategoriesSelect')?.addEventListener('change', () => {
        if (window.ConfigCategories) window.ConfigCategories.renderGrid();
      });

      // Botones de Creación de Categoría
      document.getElementById('btnCreateCategoryHeader')?.addEventListener('click', () => {
        if (window.ConfigCategories) window.ConfigCategories.openCreateModal();
      });
      document.getElementById('btnCreateCategoryBody')?.addEventListener('click', () => {
        if (window.ConfigCategories) window.ConfigCategories.openCreateModal();
      });

      // Cerrar y Guardar Modal Categoría
      document.getElementById('btnCloseCatModal')?.addEventListener('click', () => {
        if (window.ConfigCategories) window.ConfigCategories.hideModal();
      });
      document.getElementById('btnCancelCatModal')?.addEventListener('click', () => {
        if (window.ConfigCategories) window.ConfigCategories.hideModal();
      });
      document.getElementById('btnSaveCatModal')?.addEventListener('click', () => {
        if (window.ConfigCategories) window.ConfigCategories.saveFromForm();
      });
      document.getElementById('btnDeleteCategoryModal')?.addEventListener('click', () => {
        if (window.ConfigCategories) window.ConfigCategories.handleDeleteClick();
      });

      // Modal Confirmación
      document.getElementById('btnCancelConfirmAction')?.addEventListener('click', () => {
        document.getElementById('confirmActionModal')?.classList.add('hidden');
        actionToConfirm = null;
      });
      document.getElementById('btnExecuteConfirmAction')?.addEventListener('click', () => {
        if (actionToConfirm) actionToConfirm();
        document.getElementById('confirmActionModal')?.classList.add('hidden');
        actionToConfirm = null;
      });

      // Color picker sync
      document.getElementById('catInputColor')?.addEventListener('input', (e) => {
        const val = e.target.value;
        const txt = document.getElementById('catColorText');
        const circle = document.getElementById('modalCategoryColorCircle');
        if (txt) txt.textContent = val.toUpperCase();
        if (circle) circle.style.backgroundColor = val;
      });

      // Slider threshold sync
      document.getElementById('catInputThreshold')?.addEventListener('input', (e) => {
        const label = document.getElementById('catModalThresholdLabel');
        const chk = document.getElementById('catCheckboxInheritThreshold');
        if (label) label.textContent = parseFloat(e.target.value).toFixed(2);
        if (chk) chk.checked = false;
      });

      document.getElementById('catCheckboxInheritThreshold')?.addEventListener('change', (e) => {
        const label = document.getElementById('catModalThresholdLabel');
        const input = document.getElementById('catInputThreshold');
        if (label) {
          label.textContent = e.target.checked 
            ? 'Heredado' 
            : parseFloat(input ? input.value : 0.75).toFixed(2);
        }
      });

      // Tags inputs en modal categoría
      document.getElementById('catInputKeywordAdd')?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          const state = getState();
          const val = e.target.value.trim().toLowerCase();
          if (val && !(state.tempKeywords || []).includes(val)) {
            if (!state.tempKeywords) state.tempKeywords = [];
            state.tempKeywords.push(val);
            if (window.ConfigCategories) window.ConfigCategories.renderModalTags();
            e.target.value = '';
          }
        }
      });

      document.getElementById('catInputExampleAdd')?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          const state = getState();
          const val = e.target.value.trim();
          if (val) {
            if (!state.tempExamples) state.tempExamples = [];
            state.tempExamples.push(val);
            if (window.ConfigCategories) window.ConfigCategories.renderModalTags();
            e.target.value = '';
          }
        }
      });

      document.getElementById('catInputExclusionAdd')?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          const state = getState();
          const val = e.target.value.trim();
          if (val) {
            if (!state.tempExclusions) state.tempExclusions = [];
            state.tempExclusions.push(val);
            if (window.ConfigCategories) window.ConfigCategories.renderModalTags();
            e.target.value = '';
          }
        }
      });

      // Export JSON Modal
      document.getElementById('btnExportJSON')?.addEventListener('click', () => {
        ConfigApp.openJsonModal();
      });
      document.getElementById('btnCloseJsonModal')?.addEventListener('click', () => {
        document.getElementById('jsonModal')?.classList.add('hidden');
      });
      document.getElementById('btnCopyJsonSchema')?.addEventListener('click', () => {
        const text = document.getElementById('jsonPreviewCode')?.textContent || '';
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(text).then(() => {
            ConfigApp.showToast('JSON v2.1.0 copiado al portapapeles');
          }).catch(() => ConfigApp.fallbackCopy(text));
        } else {
          ConfigApp.fallbackCopy(text);
        }
      });
    }
  };

  // Exposición en namespace global
  window.ConfigApp = ConfigApp;

  // Aliases legacy globales
  window.showToast = (msg, err) => ConfigApp.showToast(msg, err);
  window.askConfirmation = (t, m, fn) => ConfigApp.askConfirmation(t, m, fn);
  window.openJsonModal = () => ConfigApp.openJsonModal();
  window.escapeHtml = text => ConfigApp.escapeHtml(text);

  // Iniciar al cargar el DOM o si ya está cargado
  if (document.readyState === 'loading') {
    window.addEventListener('DOMContentLoaded', () => ConfigApp.init());
  } else {
    ConfigApp.init();
  }

})(window);
