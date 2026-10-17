/**
 * CATEGORIES.JS - Taxonomy Catalog & CRUD Controller (Laya Engine v2.1.0)
 * Renderizado de grid reactivo (48 tarjetas), filtros, ordenación y modal #categoryEditModal.
 */

(function(window) {
  'use strict';

  function getState() {
    return window.ConfigState || {};
  }

  function getEscapeHtml() {
    return (window.ConfigApp && window.ConfigApp.escapeHtml) ? window.ConfigApp.escapeHtml : (s => String(s || ''));
  }

  function getShowToast() {
    return (window.ConfigApp && window.ConfigApp.showToast) ? window.ConfigApp.showToast : console.log;
  }

  function getAskConfirmation() {
    return (window.ConfigApp && window.ConfigApp.askConfirmation) ? window.ConfigApp.askConfirmation : (t, m, fn) => { if (confirm(`${t}\n${m}`)) fn(); };
  }

  const catModal = () => document.getElementById('categoryEditModal');
  const catModalDialog = () => document.getElementById('catModalDialog');

  const ConfigCategories = {
    /**
     * Renderiza el catálogo de categorías en el grid reactivo
     */
    renderGrid() {
      const container = document.getElementById('categoriesGridContainer');
      const state = getState();
      if (!container || !state.registryData) return;

      container.innerHTML = '';
      const escapeHtml = getEscapeHtml();

      const searchQuery = (document.getElementById('searchCategoriesInput')?.value || '').toLowerCase().trim();
      const filterMode = document.getElementById('filterFamilySelect')?.value || 'all';
      const sortMode = document.getElementById('sortCategoriesSelect')?.value || 'priority_asc';
      const defaultThreshold = state.registryData.global_settings?.default_threshold ?? 0.75;

      let cats = [...(state.registryData.topic_categories || [])];

      // 1. Filtrado
      let filtered = cats.filter(cat => {
        if (filterMode === 'families' && !cat.is_family && cat.parent_id !== null) return false;
        if (filterMode === 'subcategories' && (cat.parent_id === null || cat.is_family)) return false;
        if (filterMode === 'active' && cat.active === false) return false;

        if (searchQuery) {
          const matchLabel = (cat.label || '').toLowerCase().includes(searchQuery);
          const matchId = (cat.id || '').toLowerCase().includes(searchQuery);
          const matchDesc = (cat.description || '').toLowerCase().includes(searchQuery);
          const matchKws = (cat.keywords || []).some(k => k.toLowerCase().includes(searchQuery));
          const matchEx = (cat.examples || []).some(e => e.toLowerCase().includes(searchQuery));
          const matchExc = (cat.exclusions || []).some(ex => ex.toLowerCase().includes(searchQuery));
          if (!matchLabel && !matchId && !matchDesc && !matchKws && !matchEx && !matchExc) return false;
        }
        return true;
      });

      // 2. Ordenamiento
      filtered.sort((a, b) => {
        if (sortMode === 'priority_asc') {
          const pA = a.priority ?? 50;
          const pB = b.priority ?? 50;
          return pA - pB;
        }
        if (sortMode === 'name_asc') {
          return (a.label || '').localeCompare(b.label || '');
        }
        if (sortMode === 'threshold_desc') {
          const tA = a.threshold ?? defaultThreshold;
          const tB = b.threshold ?? defaultThreshold;
          return tB - tA;
        }
        return 0;
      });

      if (filtered.length === 0) {
        container.innerHTML = `
          <div class="col-span-full surface-card rounded-xl p-8 text-center text-xs space-y-2">
            <i class="fa-solid fa-folder-open text-3xl text-[var(--text-muted)]"></i>
            <p class="font-bold">No se encontraron categorías para este filtro.</p>
            <p class="text-[var(--text-muted)]">Intenta buscar otro término o reiniciar los filtros de búsqueda.</p>
          </div>
        `;
        return;
      }

      // 3. Generación de Tarjetas
      filtered.forEach(cat => {
        const card = document.createElement('div');
        const isInactive = cat.active === false;
        card.className = `surface-card rounded-xl p-4 flex flex-col justify-between space-y-3.5 hover:border-stone-400 dark:hover:border-stone-600 transition shadow-xs group ${isInactive ? 'opacity-60 bg-stone-100/50 dark:bg-stone-900/40' : ''}`;

        // Determinar Umbral Efectivo (Herencia)
        let effectiveThreshold = cat.threshold;
        let isInherited = false;
        if (effectiveThreshold === null || effectiveThreshold === undefined) {
          isInherited = true;
          if (cat.parent_id) {
            const parent = cats.find(c => c.id === cat.parent_id);
            effectiveThreshold = parent?.threshold ?? defaultThreshold;
          } else {
            effectiveThreshold = defaultThreshold;
          }
        }

        // Tags de palabras clave
        const kws = cat.keywords || [];
        const kwBadges = kws.slice(0, 4).map(kw => 
          `<span class="px-1.5 py-0.5 rounded text-[10px] bg-stone-200/70 dark:bg-stone-800 text-[var(--text-primary)] font-mono">${escapeHtml(kw)}</span>`
        ).join('');
        const extraKw = kws.length > 4 ? `<span class="text-[9px] text-[var(--text-muted)] font-mono">+${kws.length - 4}</span>` : '';

        // Badge de Parent o Familia
        let parentBadgeHtml = '';
        if (cat.is_family) {
          parentBadgeHtml = `<span class="px-1.5 py-0.5 rounded text-[9px] font-bold bg-purple-500/15 text-purple-700 dark:text-purple-300 font-mono">FAMILIA</span>`;
        } else if (cat.parent_id) {
          parentBadgeHtml = `<span class="px-1.5 py-0.5 rounded text-[9px] font-mono text-[var(--text-muted)] surface-subtle">padre: ${escapeHtml(cat.parent_id)}</span>`;
        }

        const boosterAssets = cat.boosters?.reproducible_assets || [];
        const boosterAssetsBadge = boosterAssets.length > 0 
          ? `<span class="text-emerald-600 font-bold"><i class="fa-solid fa-bolt mr-0.5"></i>+${boosterAssets.length} assets</span>` 
          : '';

        const examplesCount = (cat.examples || []).length;
        const exclusionsCount = (cat.exclusions || []).length;
        const colorHex = cat.color_hex || '#7c3aed';

        card.innerHTML = `
          <div>
            <!-- Header de Tarjeta -->
            <div class="flex items-start justify-between gap-2 pb-2.5 border-b border-[var(--border-main)]">
              <div class="flex items-center gap-2.5">
                <span class="w-3.5 h-3.5 rounded-full shrink-0 ring-2 ring-stone-400/20" style="background-color: ${colorHex}"></span>
                <div>
                  <div class="flex items-center gap-1.5">
                    <h4 class="font-extrabold text-xs tracking-tight">${escapeHtml(cat.label || cat.id)}</h4>
                    ${parentBadgeHtml}
                  </div>
                  <span class="text-[10px] text-[var(--text-muted)] font-mono">[${escapeHtml(cat.id)}]</span>
                </div>
              </div>

              <!-- Prioridad y Umbral -->
              <div class="text-right">
                <div class="flex items-center justify-end gap-1">
                  <span class="text-[9px] text-[var(--text-muted)] font-mono">P${cat.priority ?? 50}</span>
                  <span class="text-[10px] font-mono font-extrabold text-emerald-600">
                    ≥ ${(effectiveThreshold * 100).toFixed(0)}%
                  </span>
                </div>
                <span class="text-[8px] text-[var(--text-muted)] block font-mono">
                  ${isInherited ? '(heredado)' : 'umbral RLCD'}
                </span>
              </div>
            </div>

            <!-- Directiva de Inferencia -->
            <div class="mt-2.5 space-y-1">
              <p class="text-[11px] font-sans text-[var(--text-secondary)] line-clamp-2 leading-relaxed" title="${escapeHtml(cat.description || '')}">
                "${escapeHtml(cat.description || 'Sin directiva especificada')}"
              </p>
            </div>

            <!-- Palabras Clave y Boosters -->
            <div class="mt-3 space-y-1.5">
              <div class="flex items-center justify-between text-[9px] text-[var(--text-muted)] font-mono">
                <span class="font-bold uppercase">Keywords (${kws.length}):</span>
                ${boosterAssetsBadge}
              </div>
              <div class="flex flex-wrap items-center gap-1">
                ${kwBadges}
                ${extraKw}
              </div>
            </div>
          </div>

          <!-- Footer con Acciones -->
          <div class="pt-2.5 border-t border-[var(--border-main)] flex items-center justify-between text-[11px]">
            <div class="flex items-center gap-2 text-[10px] text-[var(--text-muted)] font-mono">
              <span title="Ejemplos representativos"><i class="fa-solid fa-list-check mr-1"></i>${examplesCount} ex.</span>
              <span title="Exclusiones estrictas"><i class="fa-solid fa-ban mr-1 text-rose-500"></i>${exclusionsCount}</span>
            </div>

            <div class="flex items-center gap-1.5">
              <button 
                class="btn-card-test px-2 py-1 surface-subtle hover:bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 rounded font-semibold text-[10px] transition" 
                data-id="${escapeHtml(cat.id)}"
                title="Probar en simulador"
              >
                <i class="fa-solid fa-play text-[8px] mr-1"></i>Test
              </button>
              <button 
                class="btn-card-edit px-2.5 py-1 bg-stone-900 hover:bg-black dark:bg-stone-700 dark:hover:bg-stone-600 text-white rounded font-bold text-[10px] transition" 
                data-id="${escapeHtml(cat.id)}"
              >
                Editar
              </button>
            </div>
          </div>
        `;

        container.appendChild(card);
      });

      // Event bindings para tarjetas
      container.querySelectorAll('.btn-card-edit').forEach(btn => {
        btn.addEventListener('click', (e) => {
          const id = e.currentTarget.getAttribute('data-id');
          ConfigCategories.openEditModal(id);
        });
      });

      container.querySelectorAll('.btn-card-test').forEach(btn => {
        btn.addEventListener('click', (e) => {
          const id = e.currentTarget.getAttribute('data-id');
          if (window.ConfigSimulator && typeof window.ConfigSimulator.openWithCategory === 'function') {
            window.ConfigSimulator.openWithCategory(id);
          }
        });
      });
    },

    /**
     * Rellena el selector de familias padre en el modal
     */
    populateParentSelect(selectedId = null, excludeId = null) {
      const select = document.getElementById('catSelectParent');
      const state = getState();
      if (!select || !state.registryData) return;

      select.innerHTML = '<option value="">Ninguno (Categoría Raíz / Familia)</option>';

      const cats = state.registryData.topic_categories || [];
      cats
        .filter(c => (c.is_family || c.parent_id === null) && c.id !== excludeId)
        .forEach(family => {
          const opt = document.createElement('option');
          opt.value = family.id;
          opt.textContent = `${family.label} [${family.id}]`;
          if (selectedId === family.id) opt.selected = true;
          select.appendChild(opt);
        });
    },

    /**
     * Abre el modal para crear una nueva categoría
     */
    openCreateModal() {
      const state = getState();
      document.getElementById('modalCategoryTitle').textContent = 'Nueva Categoría de Decisión';
      document.getElementById('modalCategorySub').textContent = 'Crear nuevo choice semántico en categories.json';
      document.getElementById('catEditOriginalId').value = '';
      document.getElementById('catInputLabel').value = '';
      document.getElementById('catInputId').value = '';
      document.getElementById('catInputId').removeAttribute('disabled');
      document.getElementById('catInputColor').value = '#8b5cf6';
      document.getElementById('catColorText').textContent = '#8B5CF6';
      document.getElementById('modalCategoryColorCircle').style.backgroundColor = '#8b5cf6';
      document.getElementById('catInputPriority').value = '20';
      document.getElementById('catCheckboxIsFamily').checked = false;
      document.getElementById('catInputDescription').value = '';
      document.getElementById('catInputThreshold').value = '0.75';
      document.getElementById('catModalThresholdLabel').textContent = '0.75';
      document.getElementById('catCheckboxInheritThreshold').checked = false;
      document.getElementById('catInputActiveToggle').checked = true;

      // Botón eliminar oculto para nuevas
      const deleteBtn = document.getElementById('btnDeleteCategoryModal');
      deleteBtn.classList.add('hidden');

      this.populateParentSelect(null, null);

      state.tempKeywords = [];
      state.tempExamples = [];
      state.tempExclusions = [];
      this.renderModalTags();
      this.resetAssetCheckboxes([]);

      this.showModal();
    },

    /**
     * Abre el modal para editar una categoría existente
     */
    openEditModal(id) {
      const state = getState();
      if (!state.registryData) return;
      const cat = state.registryData.topic_categories.find(c => c.id === id);
      if (!cat) return;

      document.getElementById('modalCategoryTitle').textContent = `Editar Categoría · ${cat.label}`;
      document.getElementById('modalCategorySub').textContent = `ID: ${cat.id} · Laya Schema v2.1.0`;
      document.getElementById('catEditOriginalId').value = cat.id;
      document.getElementById('catInputLabel').value = cat.label || '';
      document.getElementById('catInputId').value = cat.id || '';
      
      const color = cat.color_hex || '#7c3aed';
      document.getElementById('catInputColor').value = color;
      document.getElementById('catColorText').textContent = color.toUpperCase();
      document.getElementById('modalCategoryColorCircle').style.backgroundColor = color;
      
      document.getElementById('catInputPriority').value = cat.priority ?? 50;
      document.getElementById('catCheckboxIsFamily').checked = !!cat.is_family;
      document.getElementById('catInputDescription').value = cat.description || '';
      
      const isInherited = cat.threshold === null || cat.threshold === undefined;
      document.getElementById('catCheckboxInheritThreshold').checked = isInherited;
      document.getElementById('catInputThreshold').value = isInherited ? '0.75' : cat.threshold;
      document.getElementById('catModalThresholdLabel').textContent = isInherited ? 'Heredado' : cat.threshold.toFixed(2);
      document.getElementById('catInputActiveToggle').checked = cat.active !== false;

      // Manejo de protección de eliminación
      const deleteBtn = document.getElementById('btnDeleteCategoryModal');
      if (state.PROTECTED_FAMILIES.includes(cat.id) || cat.is_family) {
        deleteBtn.classList.add('hidden');
      } else {
        deleteBtn.classList.remove('hidden');
      }

      this.populateParentSelect(cat.parent_id, cat.id);

      state.tempKeywords = [...(cat.keywords || [])];
      state.tempExamples = [...(cat.examples || [])];
      state.tempExclusions = [...(cat.exclusions || [])];
      this.renderModalTags();
      this.resetAssetCheckboxes(cat.boosters?.reproducible_assets || []);

      this.showModal();
    },

    showModal() {
      const modal = catModal();
      const dialog = catModalDialog();
      if (!modal || !dialog) return;

      modal.classList.remove('hidden');
      setTimeout(() => {
        dialog.classList.remove('scale-95', 'opacity-0');
        dialog.classList.add('scale-100', 'opacity-100');
      }, 10);
    },

    hideModal() {
      const modal = catModal();
      const dialog = catModalDialog();
      if (!modal || !dialog) return;

      dialog.classList.remove('scale-100', 'opacity-100');
      dialog.classList.add('scale-95', 'opacity-0');
      setTimeout(() => {
        modal.classList.add('hidden');
      }, 140);
    },

    resetAssetCheckboxes(selectedAssets) {
      document.querySelectorAll('.cat-asset-chk').forEach(chk => {
        chk.checked = selectedAssets.includes(chk.value);
      });
    },

    renderModalTags() {
      const state = getState();
      const escapeHtml = getEscapeHtml();

      // 1. Keywords
      const kwContainer = document.getElementById('catKeywordsListContainer');
      if (kwContainer) {
        kwContainer.innerHTML = '';
        (state.tempKeywords || []).forEach((kw, idx) => {
          const span = document.createElement('span');
          span.className = 'px-2 py-0.5 rounded-md surface-card border border-[var(--border-main)] text-[11px] font-mono flex items-center gap-1.5 tag-bubble';
          span.innerHTML = `
            <span>${escapeHtml(kw)}</span>
            <button type="button" class="hover:text-rose-500 font-bold" onclick="removeKwTag(${idx})">&times;</button>
          `;
          kwContainer.appendChild(span);
        });
      }

      // 2. Examples
      const exContainer = document.getElementById('catExamplesContainer');
      if (exContainer) {
        exContainer.innerHTML = '';
        (state.tempExamples || []).forEach((ex, idx) => {
          const div = document.createElement('div');
          div.className = 'flex items-center justify-between text-[11px] surface-card p-1.5 rounded tag-bubble';
          div.innerHTML = `
            <span class="truncate pr-2">"${escapeHtml(ex)}"</span>
            <button type="button" class="text-stone-400 hover:text-rose-500 font-bold px-1" onclick="removeExTag(${idx})">&times;</button>
          `;
          exContainer.appendChild(div);
        });
      }

      // 3. Exclusions
      const excContainer = document.getElementById('catExclusionsContainer');
      if (excContainer) {
        excContainer.innerHTML = '';
        (state.tempExclusions || []).forEach((exc, idx) => {
          const div = document.createElement('div');
          div.className = 'flex items-center justify-between text-[11px] surface-card p-1.5 rounded tag-bubble text-rose-700 dark:text-rose-300';
          div.innerHTML = `
            <span class="truncate pr-2">"${escapeHtml(exc)}"</span>
            <button type="button" class="text-stone-400 hover:text-rose-500 font-bold px-1" onclick="removeExcTag(${idx})">&times;</button>
          `;
          excContainer.appendChild(div);
        });
      }
    },

    /**
     * Guarda la categoría (POST si nueva, PUT si existente)
     */
    async saveFromForm() {
      const state = getState();
      const showToast = getShowToast();

      const originalId = document.getElementById('catEditOriginalId').value.trim();
      const label = document.getElementById('catInputLabel').value.trim();
      const id = document.getElementById('catInputId').value.trim().toLowerCase().replace(/[^a-z0-9_]/g, '_');
      const color = document.getElementById('catInputColor').value;
      const parentId = document.getElementById('catSelectParent').value || null;
      const priority = parseInt(document.getElementById('catInputPriority').value, 10) || 50;
      const isFamily = document.getElementById('catCheckboxIsFamily').checked;
      const description = document.getElementById('catInputDescription').value.trim();
      const inheritThreshold = document.getElementById('catCheckboxInheritThreshold').checked;
      const threshold = inheritThreshold ? null : parseFloat(document.getElementById('catInputThreshold').value);
      const active = document.getElementById('catInputActiveToggle').checked;

      const selectedAssets = [];
      document.querySelectorAll('.cat-asset-chk:checked').forEach(c => selectedAssets.push(c.value));

      if (!label || !id || !description) {
        showToast('Por favor completa todos los campos requeridos (*)', true);
        return;
      }

      const saveBtn = document.getElementById('btnSaveCatModal');
      if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-1"></i> Guardando...';
      }

      try {
        if (originalId) {
          // Modificar existente (PUT)
          const updatePayload = {
            label,
            description,
            color_hex: color,
            parent_id: parentId,
            priority,
            threshold,
            is_family: isFamily,
            keywords: [...(state.tempKeywords || [])],
            examples: [...(state.tempExamples || [])],
            exclusions: [...(state.tempExclusions || [])],
            boosters: {
              reproducible_assets: selectedAssets,
              keywords: []
            },
            active
          };

          await API.categories.update(originalId, updatePayload);
          showToast(`Categoría "${label}" actualizada y sincronizada en disco.`);
        } else {
          // Crear nueva (POST)
          const createPayload = {
            id,
            name: label,
            label,
            code: id.slice(0, 4).toUpperCase(),
            description,
            color_hex: color,
            parent_id: parentId,
            priority,
            threshold: threshold ?? 0.75,
            is_family: isFamily,
            keywords: state.tempKeywords?.length > 0 ? [...state.tempKeywords] : [id],
            examples: [...(state.tempExamples || [])],
            exclusions: [...(state.tempExclusions || [])],
            boosters: {
              reproducible_assets: selectedAssets,
              keywords: []
            },
            active
          };

          await API.categories.create(createPayload);
          showToast(`Nueva categoría "${label}" creada exitosamente en Laya.`);
        }

        this.hideModal();
        // Recargar datos y refrescar UI
        const refreshed = await API.categories.getAll();
        if (state.registryData) {
          state.registryData.topic_categories = Array.isArray(refreshed) ? refreshed : (refreshed?.topic_categories || []);
        }
        this.renderGrid();
        if (state.updateTelemetryHUD) state.updateTelemetryHUD();
      } catch (err) {
        console.error('Error al guardar categoría:', err);
        showToast(err.message || 'Error al persistir categoría en el servidor', true);
      } finally {
        if (saveBtn) {
          saveBtn.disabled = false;
          saveBtn.innerHTML = '<i class="fa-solid fa-check text-[11px]"></i> <span>Guardar en Registro</span>';
        }
      }
    },

    /**
     * Ejecuta eliminación de categoría con validación de seguridad
     */
    handleDeleteClick() {
      const state = getState();
      const showToast = getShowToast();
      const askConfirmation = getAskConfirmation();

      const id = document.getElementById('catEditOriginalId')?.value;
      if (!id || !state.registryData) return;

      const cat = state.registryData.topic_categories.find(c => c.id === id);
      if (!cat) return;

      if (state.PROTECTED_FAMILIES.includes(id) || cat.is_family) {
        showToast('Esta familia raíz está protegida contra eliminación para garantizar el gating.', true);
        return;
      }

      askConfirmation(
        'Eliminar Categoría de Decisión', 
        `¿Confirmas que deseas eliminar permanentemente la categoría "${cat.label}" [${cat.id}]? Se reasignarán automáticamente todas las publicaciones huérfanas a 'otros' en SQLite WAL.`, 
        async () => {
          try {
            const res = await API.categories.delete(id);
            showToast(`Categoría "${cat.label}" eliminada. Posts reasignados: ${res.reassigned_posts}`);
            ConfigCategories.hideModal();
            const refreshed = await API.categories.getAll();
            if (state.registryData) {
              state.registryData.topic_categories = Array.isArray(refreshed) ? refreshed : (refreshed?.topic_categories || []);
            }
            ConfigCategories.renderGrid();
            if (state.updateTelemetryHUD) state.updateTelemetryHUD();
          } catch (err) {
            console.error('Error al eliminar categoría:', err);
            showToast(err.message || 'Error al eliminar categoría en el servidor', true);
          }
        }
      );
    }
  };

  // Exposición en namespace global
  window.ConfigCategories = ConfigCategories;

  // Funciones de eliminación de tags accesibles desde DOM onclick
  window.removeKwTag = idx => {
    const s = getState();
    if (s.tempKeywords) {
      s.tempKeywords.splice(idx, 1);
      ConfigCategories.renderModalTags();
    }
  };

  window.removeExTag = idx => {
    const s = getState();
    if (s.tempExamples) {
      s.tempExamples.splice(idx, 1);
      ConfigCategories.renderModalTags();
    }
  };

  window.removeExcTag = idx => {
    const s = getState();
    if (s.tempExclusions) {
      s.tempExclusions.splice(idx, 1);
      ConfigCategories.renderModalTags();
    }
  };

  // Aliases legacy
  window.renderCategoriesGrid = () => ConfigCategories.renderGrid();
  window.openCreateCategoryModal = () => ConfigCategories.openCreateModal();
  window.openEditCategoryModal = id => ConfigCategories.openEditModal(id);
  window.hideCategoryModal = () => ConfigCategories.hideModal();
  window.saveCategoryFromForm = () => ConfigCategories.saveFromForm();

})(window);
