/**
 * QUESTIONS.JS - Typed Questions Bank & Ingestion Controller (Laya Engine v2.1.0)
 * Visualización, creación, edición y eliminación de preguntas suplementarias (Choice, Score, Noul).
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

  const questionModal = () => document.getElementById('questionEditModal');

  const ConfigQuestions = {
    /**
     * Renderiza el grid de preguntas suplementarias
     */
    renderGrid() {
      const container = document.getElementById('questionsGridContainer');
      const state = getState();
      if (!container) return;

      container.innerHTML = '';
      const escapeHtml = getEscapeHtml();

      const questions = state.supplementaryQuestions || [];

      if (questions.length === 0) {
        container.innerHTML = `
          <div class="col-span-full surface-subtle rounded-xl p-8 text-center text-xs space-y-2">
            <i class="fa-solid fa-clipboard-question text-3xl text-[var(--text-muted)]"></i>
            <p class="font-bold">No hay preguntas suplementarias cargadas.</p>
          </div>
        `;
        return;
      }

      questions.forEach(q => {
        const card = document.createElement('div');
        const isActive = q.active !== false;
        card.className = `surface-subtle p-3.5 rounded-xl border border-[var(--border-main)] space-y-2 flex flex-col justify-between transition ${isActive ? '' : 'opacity-70 bg-stone-50/50'}`;

        const isProtected = (state.PROTECTED_QUESTIONS || []).includes(q.id);
        const typeUpper = (q.type || 'CHOICE').toUpperCase();
        let typeBadgeColor = 'bg-purple-500/10 text-purple-600';
        if (typeUpper === 'SCORE') typeBadgeColor = 'bg-amber-500/10 text-amber-600';
        if (typeUpper === 'NOUL') typeBadgeColor = 'bg-indigo-500/10 text-indigo-600';

        const activeBadge = isActive
          ? '<span class="px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-600 font-bold text-[9px] flex items-center gap-1"><span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>ACTIVA</span>'
          : '<span class="px-1.5 py-0.5 rounded bg-stone-500/10 text-stone-500 font-bold text-[9px] flex items-center gap-1"><span class="w-1.5 h-1.5 rounded-full bg-stone-400"></span>INACTIVA</span>';

        // Choices
        let choicesHtml = '';
        if (q.type === 'choice' && Array.isArray(q.choices)) {
          choicesHtml = `
            <div class="flex flex-wrap gap-1 font-mono text-[9px] pt-1">
              ${q.choices.map(c => `<span class="px-1.5 py-0.5 rounded surface-card border border-[var(--border-main)]">${escapeHtml(c)}</span>`).join('')}
            </div>
          `;
        } else if (q.type === 'score') {
          choicesHtml = `
            <div class="space-y-0.5 font-sans text-[10px] text-[var(--text-secondary)] pt-1">
              <div><span class="font-mono font-bold">1:</span> Básico / Divulgativo</div>
              <div><span class="font-mono font-bold">3:</span> Intermedio / Metodología</div>
              <div><span class="font-mono font-bold">5:</span> Código fuente / Arquitectura técnica</div>
            </div>
          `;
        } else if (q.type === 'noul') {
          choicesHtml = `
            <div class="font-mono text-[10px] text-indigo-600 pt-1">
              Retorna booleano tipado (true / false) ante hits semánticos.
            </div>
          `;
        }

        card.innerHTML = `
          <div class="space-y-2">
            <div class="flex items-center justify-between font-mono">
              <div class="flex items-center gap-1.5">
                <span class="font-bold text-emerald-700 dark:text-emerald-300">${escapeHtml(q.id)}</span>
                ${isProtected ? '<span class="text-[9px] text-[var(--text-muted)] font-mono" title="Pregunta canónica protegida">(sistema)</span>' : ''}
              </div>
              <div class="flex items-center gap-1.5">
                ${activeBadge}
                <span class="px-2 py-0.5 rounded ${typeBadgeColor} font-bold text-[10px]">${typeUpper}</span>
              </div>
            </div>

            <p class="text-[11px] font-semibold text-[var(--text-primary)]">
              "${escapeHtml(q.question || '')}"
            </p>

            ${choicesHtml}
          </div>

          <div class="pt-2 border-t border-[var(--border-main)] flex items-center justify-between text-[11px]">
            <span class="text-[10px] text-[var(--text-muted)] font-mono">
              ${q.type === 'choice' ? `${(q.choices || []).length} opciones` : q.type}
            </span>

            <div class="flex items-center gap-1.5">
              <button class="btn-toggle-question px-2 py-1 rounded text-[10px] font-bold transition flex items-center gap-1 ${isActive ? 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100 border border-emerald-300' : 'bg-stone-100 text-stone-500 hover:bg-stone-200 border border-stone-300'}" data-id="${escapeHtml(q.id)}" title="${isActive ? 'Desactivar de la inferencia Laya' : 'Activar para la inferencia Laya'}">
                <i class="fa-solid ${isActive ? 'fa-toggle-on text-emerald-600' : 'fa-toggle-off text-stone-400'}"></i>
                <span>${isActive ? 'Activa' : 'Inactiva'}</span>
              </button>
              ${!isProtected ? `
                <button class="btn-delete-question text-rose-600 hover:bg-rose-500/10 px-2 py-1 rounded text-[10px] font-bold transition" data-id="${escapeHtml(q.id)}">
                  Eliminar
                </button>
              ` : ''}
              <button class="btn-edit-question bg-stone-900 hover:bg-black dark:bg-stone-700 dark:hover:bg-stone-600 text-white px-2.5 py-1 rounded text-[10px] font-bold transition" data-id="${escapeHtml(q.id)}">
                Editar
              </button>
            </div>
          </div>
        `;

        container.appendChild(card);
      });

      // Bindings
      container.querySelectorAll('.btn-toggle-question').forEach(b => {
        b.addEventListener('click', async e => {
          const qId = e.currentTarget.getAttribute('data-id');
          const toast = getShowToast();
          try {
            const res = await API.categories.toggleSupplementaryQuestion(qId);
            if (res && res.status === 'success') {
              const q = (state.supplementaryQuestions || []).find(item => item.id === qId);
              if (q) q.active = res.active;
              toast(`Pregunta '${qId}' ${res.active ? 'activada' : 'desactivada'} para inferencia Laya`);
              ConfigQuestions.renderQuestions();
            }
          } catch (err) {
            console.error('Error toggling question:', err);
            toast('Error al cambiar estado de la pregunta');
          }
        });
      });

      container.querySelectorAll('.btn-edit-question').forEach(b => {
        b.addEventListener('click', e => {
          const qId = e.currentTarget.getAttribute('data-id');
          ConfigQuestions.openEditModal(qId);
        });
      });

      container.querySelectorAll('.btn-delete-question').forEach(b => {
        b.addEventListener('click', e => {
          const qId = e.currentTarget.getAttribute('data-id');
          ConfigQuestions.confirmDelete(qId);
        });
      });
    },

    /**
     * Abre el modal para crear una nueva pregunta
     */
    openCreateModal() {
      const state = getState();
      document.getElementById('modalQuestionTitle').textContent = 'Nueva Pregunta Tipada';
      document.getElementById('qEditOriginalId').value = '';
      document.getElementById('qInputId').value = '';
      document.getElementById('qInputId').removeAttribute('disabled');
      document.getElementById('qSelectType').value = 'choice';
      document.getElementById('qInputQuestion').value = '';
      state.tempQuestionChoices = ['opcion_a', 'opcion_b'];
      this.renderChoicesTags();
      this.toggleChoicesSection();
      questionModal()?.classList.remove('hidden');
    },

    /**
     * Abre el modal para editar una pregunta existente
     */
    openEditModal(qId) {
      const state = getState();
      const q = (state.supplementaryQuestions || []).find(item => item.id === qId);
      if (!q) return;

      document.getElementById('modalQuestionTitle').textContent = `Editar Pregunta · ${q.id}`;
      document.getElementById('qEditOriginalId').value = q.id;
      document.getElementById('qInputId').value = q.id;
      document.getElementById('qInputId').setAttribute('disabled', 'true');
      document.getElementById('qSelectType').value = q.type || 'choice';
      document.getElementById('qInputQuestion').value = q.question || '';
      state.tempQuestionChoices = Array.isArray(q.choices) ? [...q.choices] : [];
      this.renderChoicesTags();
      this.toggleChoicesSection();
      questionModal()?.classList.remove('hidden');
    },

    toggleChoicesSection() {
      const type = document.getElementById('qSelectType')?.value;
      const section = document.getElementById('qChoicesSection');
      if (section) {
        section.classList.toggle('hidden', type !== 'choice');
      }
    },

    renderChoicesTags() {
      const container = document.getElementById('qChoicesListContainer');
      const state = getState();
      const escapeHtml = getEscapeHtml();
      if (!container) return;

      container.innerHTML = '';
      (state.tempQuestionChoices || []).forEach((ch, idx) => {
        const span = document.createElement('span');
        span.className = 'px-2 py-0.5 rounded-md surface-card border border-[var(--border-main)] text-[11px] font-mono flex items-center gap-1.5 tag-bubble';
        span.innerHTML = `
          <span>${escapeHtml(ch)}</span>
          <button type="button" class="hover:text-rose-500 font-bold" onclick="removeQuestionChoice(${idx})">&times;</button>
        `;
        container.appendChild(span);
      });
    },

    /**
     * Persiste la pregunta tipada en el servidor (PUT o POST)
     */
    async saveFromModal() {
      const state = getState();
      const showToast = getShowToast();

      const originalId = document.getElementById('qEditOriginalId').value.trim();
      const id = document.getElementById('qInputId').value.trim().toLowerCase().replace(/[^a-z0-9_]/g, '_');
      const type = document.getElementById('qSelectType').value;
      const question = document.getElementById('qInputQuestion').value.trim();

      if (!id || !question) {
        showToast('Por favor completa el ID y el texto de la pregunta', true);
        return;
      }

      const saveBtn = document.getElementById('btnSaveQuestionModal');
      if (saveBtn) saveBtn.disabled = true;

      try {
        const payload = {
          id,
          question,
          type,
          choices: type === 'choice' ? state.tempQuestionChoices : null
        };

        if (originalId) {
          await API.categories.updateSupplementaryQuestion(originalId, payload);
          showToast(`Pregunta tipada '${originalId}' actualizada exitosamente.`);
        } else {
          await API.categories.createSupplementaryQuestion(payload);
          showToast(`Nueva pregunta tipada '${id}' agregada al motor.`);
        }

        questionModal()?.classList.add('hidden');
        // Recargar preguntas
        const refreshedQ = await API.categories.getSupplementaryQuestions();
        if (state.parseQuestionsResponse) {
          state.supplementaryQuestions = state.parseQuestionsResponse(refreshedQ);
          window.supplementaryQuestions = state.supplementaryQuestions;
        }
        this.renderGrid();
        if (state.updateTelemetryHUD) state.updateTelemetryHUD();
      } catch (err) {
        console.error('Error al guardar pregunta:', err);
        showToast(err.message || 'Error al persistir pregunta en Laya', true);
      } finally {
        if (saveBtn) saveBtn.disabled = false;
      }
    },

    /**
     * Elimina una pregunta con confirmación modal
     */
    confirmDelete(qId) {
      const state = getState();
      const showToast = getShowToast();
      const askConfirmation = getAskConfirmation();

      if ((state.PROTECTED_QUESTIONS || []).includes(qId)) {
        showToast(`La pregunta '${qId}' es parte del estándar y está protegida.`, true);
        return;
      }

      askConfirmation('Eliminar Pregunta Tipada', `¿Confirmas que deseas eliminar la pregunta '${qId}' de la inferencia de Laya?`, async () => {
        try {
          await API.categories.deleteSupplementaryQuestion(qId);
          showToast(`Pregunta '${qId}' eliminada.`);
          const refreshedQ = await API.categories.getSupplementaryQuestions();
          if (state.parseQuestionsResponse) {
            state.supplementaryQuestions = state.parseQuestionsResponse(refreshedQ);
            window.supplementaryQuestions = state.supplementaryQuestions;
          }
          ConfigQuestions.renderGrid();
          if (state.updateTelemetryHUD) state.updateTelemetryHUD();
        } catch (err) {
          console.error('Error al eliminar pregunta:', err);
          showToast(err.message || 'Error al eliminar pregunta', true);
        }
      });
    },

    bindEvents() {
      document.getElementById('btnCreateQuestion')?.addEventListener('click', () => {
        ConfigQuestions.openCreateModal();
      });
      document.getElementById('btnCloseQuestionModal')?.addEventListener('click', () => {
        questionModal()?.classList.add('hidden');
      });
      document.getElementById('btnCancelQuestionModal')?.addEventListener('click', () => {
        questionModal()?.classList.add('hidden');
      });
      document.getElementById('btnSaveQuestionModal')?.addEventListener('click', () => {
        ConfigQuestions.saveFromModal();
      });
      document.getElementById('qSelectType')?.addEventListener('change', () => {
        ConfigQuestions.toggleChoicesSection();
      });

      document.getElementById('qInputChoiceAdd')?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          const state = getState();
          const val = e.target.value.trim().toLowerCase();
          if (val && !(state.tempQuestionChoices || []).includes(val)) {
            if (!state.tempQuestionChoices) state.tempQuestionChoices = [];
            state.tempQuestionChoices.push(val);
            ConfigQuestions.renderChoicesTags();
            e.target.value = '';
          }
        }
      });
    }
  };

  // Exposición en namespace global
  window.ConfigQuestions = ConfigQuestions;

  // Acceso para inline onclick
  window.removeQuestionChoice = idx => {
    const s = getState();
    if (s.tempQuestionChoices) {
      s.tempQuestionChoices.splice(idx, 1);
      ConfigQuestions.renderChoicesTags();
    }
  };

  // Aliases legacy
  window.renderQuestionsGrid = () => ConfigQuestions.renderGrid();
  window.openCreateQuestionModal = () => ConfigQuestions.openCreateModal();
  window.openEditQuestionModal = qId => ConfigQuestions.openEditModal(qId);
  window.saveQuestionFromModal = () => ConfigQuestions.saveFromModal();
  window.confirmDeleteQuestion = qId => ConfigQuestions.confirmDelete(qId);

})(window);
