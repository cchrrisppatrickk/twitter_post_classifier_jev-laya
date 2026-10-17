/**
 * DATABASE.JS - Gestor de Almacenamiento, Métricas y Mantenimiento SQLite WAL (Fase 5.13)
 * Telemetría en vivo, limpieza selectiva segura, exportación/importación y optimización.
 */

(function(window) {
  'use strict';

  function showToast(msg, isError = false) {
    if (window.ConfigApp && typeof window.ConfigApp.showToast === 'function') {
      window.ConfigApp.showToast(msg, isError);
    } else {
      console.log(`[ConfigDatabase] ${isError ? 'ERROR: ' : ''}${msg}`);
    }
  }

  const ConfigDatabase = {
    /**
     * Carga y renderiza métricas de almacenamiento desde /api/database/stats
     */
    async loadStats() {
      const refreshBtn = document.getElementById('dbRefreshStatsBtn');
      if (refreshBtn) {
        refreshBtn.classList.add('animate-spin');
      }

      try {
        const response = await fetch('/api/database/stats');
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();

        // Actualizar badges y contadores del HUD
        const elPosts = document.getElementById('dbStatsPostsCount');
        const elHistory = document.getElementById('dbStatsHistoryCount');
        const elCheckpoints = document.getElementById('dbStatsCheckpointsCount');
        const elFeedback = document.getElementById('dbStatsFeedbackCount');
        const elSize = document.getElementById('dbStatsTotalSize');
        const elEngine = document.getElementById('dbStatsEngineMode');
        const elVersion = document.getElementById('dbStatsTaxonomyVersion');

        if (elPosts) elPosts.textContent = data.posts_count.toLocaleString();
        if (elHistory) elHistory.textContent = data.history_count.toLocaleString();
        if (elCheckpoints) elCheckpoints.textContent = data.checkpoints_count.toLocaleString();
        if (elFeedback) elFeedback.textContent = data.feedback_count.toLocaleString();
        if (elSize) elSize.textContent = `${data.db_size_formatted} (WAL: ${data.wal_size_formatted})`;
        if (elEngine) elEngine.textContent = `SQLite v${data.sqlite_version} · Modo ${data.journal_mode}`;
        if (elVersion) elVersion.textContent = `Taxonomía v${data.taxonomy_version}`;

      } catch (err) {
        console.error('[ConfigDatabase] Error al consultar stats de base de datos:', err);
        showToast(`Error al consultar métricas: ${err.message}`, true);
      } finally {
        if (refreshBtn) {
          setTimeout(() => refreshBtn.classList.remove('animate-spin'), 300);
        }
      }
    },

    /**
     * Descarga de copia de seguridad JSON
     */
    async exportBackup() {
      const exportBtn = document.getElementById('dbExportBtn');
      const originalHtml = exportBtn ? exportBtn.innerHTML : '';
      if (exportBtn) {
        exportBtn.disabled = true;
        exportBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i><span>Exportando JSON...</span>';
      }

      try {
        const response = await fetch('/api/database/export?include_history=true');
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const blob = await response.blob();
        const disposition = response.headers.get('content-disposition') || '';
        let filename = 'backup_twitter_classifier.json';
        const filenameMatch = disposition.match(/filename="?([^"]+)"?/);
        if (filenameMatch && filenameMatch[1]) {
          filename = filenameMatch[1];
        }

        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();

        showToast(`Copia de seguridad descargada (${filename})`);
      } catch (err) {
        console.error('[ConfigDatabase] Error en exportación:', err);
        showToast(`Fallo en exportación: ${err.message}`, true);
      } finally {
        if (exportBtn) {
          exportBtn.disabled = false;
          exportBtn.innerHTML = originalHtml;
        }
      }
    },

    /**
     * Mantenimiento proactivo: wal checkpoint y vacuum
     */
    async optimize() {
      const optBtn = document.getElementById('dbOptimizeBtn');
      const originalHtml = optBtn ? optBtn.innerHTML : '';
      if (optBtn) {
        optBtn.disabled = true;
        optBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i><span>Optimizando SQLite...</span>';
      }

      try {
        const response = await fetch('/api/database/optimize', { method: 'POST' });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const result = await response.json();

        showToast(`Optimización completada. Espacio recuperado: ${result.bytes_reclaimed} bytes`);
        await this.loadStats();
      } catch (err) {
        console.error('[ConfigDatabase] Error al optimizar:', err);
        showToast(`Error de optimización: ${err.message}`, true);
      } finally {
        if (optBtn) {
          optBtn.disabled = false;
          optBtn.innerHTML = originalHtml;
        }
      }
    },

    /**
     * Control del Modal de Reinicio con Salvaguarda
     */
    openResetModal() {
      const modal = document.getElementById('databaseResetModal');
      const secInput = document.getElementById('dbResetSecurityInput');
      const confirmBtn = document.getElementById('dbConfirmResetBtn');

      if (secInput) secInput.value = '';
      if (confirmBtn) {
        confirmBtn.disabled = true;
        confirmBtn.className = 'px-4 py-2 bg-stone-300 text-stone-500 font-bold rounded-lg cursor-not-allowed transition';
      }
      if (modal) modal.classList.remove('hidden');
    },

    closeResetModal() {
      const modal = document.getElementById('databaseResetModal');
      if (modal) modal.classList.add('hidden');
    },

    /**
     * Ejecuta el reinicio selectivo tras superar la salvaguarda
     */
    async executeReset() {
      const checkPosts = document.getElementById('dbResetCheckPosts');
      const checkHistory = document.getElementById('dbResetCheckHistory');
      const checkCheckpoints = document.getElementById('dbResetCheckCheckpoints');
      const checkFeedback = document.getElementById('dbResetCheckFeedback');
      const checkVacuum = document.getElementById('dbResetCheckVacuum');
      const confirmBtn = document.getElementById('dbConfirmResetBtn');

      const payload = {
        clear_posts: checkPosts ? checkPosts.checked : true,
        clear_history: checkHistory ? checkHistory.checked : true,
        clear_checkpoints: checkCheckpoints ? checkCheckpoints.checked : true,
        clear_feedback: checkFeedback ? checkFeedback.checked : false,
        vacuum: checkVacuum ? checkVacuum.checked : true
      };

      const originalHtml = confirmBtn ? confirmBtn.innerHTML : '';
      if (confirmBtn) {
        confirmBtn.disabled = true;
        confirmBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i><span>Reiniciando...</span>';
      }

      try {
        const response = await fetch('/api/database/reset', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const result = await response.json();

        this.closeResetModal();
        showToast(result.message || 'Base de datos reiniciada con éxito');
        await this.loadStats();
      } catch (err) {
        console.error('[ConfigDatabase] Error en reset:', err);
        showToast(`Error al reiniciar: ${err.message}`, true);
      } finally {
        if (confirmBtn) {
          confirmBtn.innerHTML = originalHtml;
        }
      }
    },

    /**
     * Importación y restauración de backup JSON
     */
    async handleFileImport(file) {
      if (!file) return;

      const modeSelect = document.getElementById('dbImportModeSelect');
      const mode = modeSelect ? modeSelect.value : 'merge';

      const formData = new FormData();
      formData.append('file', file);
      formData.append('mode', mode);

      try {
        showToast('Restaurando copia de seguridad...');
        const response = await fetch('/api/database/import', {
          method: 'POST',
          body: formData
        });

        if (!response.ok) {
          const err = await response.json().catch(() => ({}));
          throw new Error(err.detail || `HTTP ${response.status}`);
        }

        const res = await response.json();
        showToast(res.message || 'Restauración completada');
        await this.loadStats();
      } catch (err) {
        console.error('[ConfigDatabase] Error en importación:', err);
        showToast(`Fallo al importar: ${err.message}`, true);
      }
    },

    /**
     * Asocia eventos interactivos en la vista de configuración
     */
    bindEvents() {
      // Actualizar stats manual
      const refreshBtn = document.getElementById('dbRefreshStatsBtn');
      if (refreshBtn) refreshBtn.addEventListener('click', () => this.loadStats());

      // Exportar backup
      const exportBtn = document.getElementById('dbExportBtn');
      if (exportBtn) exportBtn.addEventListener('click', () => this.exportBackup());

      // Optimizar
      const optBtn = document.getElementById('dbOptimizeBtn');
      if (optBtn) optBtn.addEventListener('click', () => this.optimize());

      // Modal reset
      const openResetBtn = document.getElementById('dbOpenResetModalBtn');
      if (openResetBtn) openResetBtn.addEventListener('click', () => this.openResetModal());

      const closeResetBtn = document.getElementById('dbCloseResetModalBtn');
      if (closeResetBtn) closeResetBtn.addEventListener('click', () => this.closeResetModal());

      const cancelResetBtn = document.getElementById('dbCancelResetBtn');
      if (cancelResetBtn) cancelResetBtn.addEventListener('click', () => this.closeResetModal());

      // Input de seguridad "REINICIAR"
      const secInput = document.getElementById('dbResetSecurityInput');
      const confirmBtn = document.getElementById('dbConfirmResetBtn');
      if (secInput && confirmBtn) {
        secInput.addEventListener('input', (e) => {
          const val = e.target.value.trim().toUpperCase();
          if (val === 'REINICIAR') {
            confirmBtn.disabled = false;
            confirmBtn.className = 'px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white font-bold rounded-lg transition shadow-sm cursor-pointer';
          } else {
            confirmBtn.disabled = true;
            confirmBtn.className = 'px-4 py-2 bg-stone-300 text-stone-500 font-bold rounded-lg cursor-not-allowed transition';
          }
        });
      }

      if (confirmBtn) {
        confirmBtn.addEventListener('click', () => this.executeReset());
      }

      // Input de importación de archivo
      const importBtn = document.getElementById('dbImportBtn');
      const fileInput = document.getElementById('dbImportFileInput');
      if (importBtn && fileInput) {
        importBtn.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', (e) => {
          const file = e.target.files[0];
          if (file) {
            this.handleFileImport(file);
            fileInput.value = '';
          }
        });
      }
    }
  };

  window.ConfigDatabase = ConfigDatabase;

})(window);
