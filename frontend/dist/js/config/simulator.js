/**
 * SIMULATOR.JS - Multi-Label RLCD Simulation & Decision Sandbox (Laya Engine v2.1.0)
 * Simulación en tiempo real del forward pass determinista, cálculo de boosted_score, desempate y desglose analítico.
 */

(function(window) {
  'use strict';

  function getState() {
    return window.ConfigState || {};
  }

  function getEscapeHtml() {
    return (window.ConfigApp && window.ConfigApp.escapeHtml) ? window.ConfigApp.escapeHtml : (s => String(s || ''));
  }

  const sandboxModal = () => document.getElementById('sandboxModal');

  const ConfigSimulator = {
    /**
     * Abre el simulador cargando opcionalmente el primer ejemplo de una categoría
     */
    openWithCategory(catId = null) {
      const state = getState();
      if (!state.registryData) return;

      if (catId) {
        const cat = (state.registryData.topic_categories || []).find(c => c.id === catId);
        if (cat && cat.examples && cat.examples.length > 0) {
          const input = document.getElementById('sandboxInputText');
          if (input) input.value = cat.examples[0];
        }
      }
      sandboxModal()?.classList.remove('hidden');
      this.runSimulation();
    },

    /**
     * Ejecuta el forward pass determinista de clasificación multi-label
     */
    runSimulation() {
      const state = getState();
      if (!state.registryData) return;

      const escapeHtml = getEscapeHtml();
      const text = (document.getElementById('sandboxInputText')?.value || '').toLowerCase();
      const start = performance.now();

      const scoring = state.registryData.scoring || {};
      const globalSettings = state.registryData.global_settings || {};
      const assetDomainMatchers = scoring.asset_domain_matchers || {
        github_repo: ["github.com/", "gitlab.com/"],
        huggingface_model: ["huggingface.co/", "hf.co/"],
        civitai_lora: ["civitai.com/"],
        comfyui_workflow: ["openart.ai/workflows", "comfyworkflows.com", "flowt.ai"],
        tutorial_link: ["youtube.com/", "youtu.be/", "medium.com/", "substack.com/"]
      };
      const assetTypeBonuses = scoring.asset_type_bonuses || {
        github_repo: 0.10,
        comfyui_workflow: 0.10,
        huggingface_model: 0.10,
        civitai_lora: 0.10,
        installation_guide: 0.06,
        tutorial_link: 0.05,
        prompt_share: 0.04,
        none: 0.00
      };

      // 1. Detección Determinista de Enlaces / Dominios
      let detectedAssetType = 'none';
      let assetBonus = 0.00;

      for (const [assetType, domains] of Object.entries(assetDomainMatchers)) {
        if (domains.some(d => text.includes(d.toLowerCase()))) {
          detectedAssetType = assetType;
          assetBonus = assetTypeBonuses[assetType] || 0.00;
          break;
        }
      }

      // 2. Inferencia y Puntuación sobre Categorías Activas
      const scoredCats = [];
      const defaultThreshold = globalSettings.default_threshold ?? 0.75;
      const activeCats = (state.registryData.topic_categories || []).filter(c => c.active !== false);

      activeCats.forEach(cat => {
        // Umbral efectivo con herencia
        let effectiveThreshold = cat.threshold;
        if (effectiveThreshold === null || effectiveThreshold === undefined) {
          if (cat.parent_id) {
            const parent = (state.registryData.topic_categories || []).find(p => p.id === cat.parent_id);
            effectiveThreshold = parent?.threshold ?? defaultThreshold;
          } else {
            effectiveThreshold = defaultThreshold;
          }
        }

        // Hits de keywords
        let hits = 0;
        (cat.keywords || []).forEach(kw => {
          if (text.includes(kw.toLowerCase())) hits++;
        });

        // Penalización por exclusiones
        let exclusionHit = false;
        (cat.exclusions || []).forEach(exc => {
          if (text.includes(exc.toLowerCase())) exclusionHit = true;
        });

        let baseConfidence = 0.58 + (hits * 0.09);
        if (exclusionHit) baseConfidence -= 0.35;
        baseConfidence = Math.min(0.99, Math.max(0.20, baseConfidence));

        // Boosted score formula
        let boosted = baseConfidence;
        let breakdown = `conf: ${baseConfidence.toFixed(2)}`;

        const supportedAssets = cat.boosters?.reproducible_assets || [];
        if (supportedAssets.includes(detectedAssetType)) {
          boosted += assetBonus;
          breakdown += ` + asset: ${assetBonus.toFixed(2)} (${detectedAssetType})`;
        }

        if (cat.parent_id !== null) {
          const specBonus = scoring.boosters?.specificity_child ?? 0.05;
          boosted += specBonus;
          breakdown += ` + child: ${specBonus.toFixed(2)}`;
        }

        if (hits > 0) {
          const kwBonus = scoring.boosters?.keyword_match ?? 0.03;
          boosted += kwBonus;
          breakdown += ` + kw_match: ${kwBonus.toFixed(2)}`;
        }

        boosted = Math.min(0.99, boosted);

        scoredCats.push({
          category: cat,
          baseConfidence,
          boostedScore: boosted,
          effectiveThreshold,
          breakdown,
          hits,
          qualifies: boosted >= effectiveThreshold
        });
      });

      // 3. Reglas de Desempate: boosted_score desc, priority asc, baseConfidence desc, id asc
      scoredCats.sort((a, b) => {
        if (Math.abs(b.boostedScore - a.boostedScore) > 0.001) {
          return b.boostedScore - a.boostedScore;
        }
        const pA = a.category.priority ?? 50;
        const pB = b.category.priority ?? 50;
        if (pA !== pB) {
          return pA - pB;
        }
        if (Math.abs(b.baseConfidence - a.baseConfidence) > 0.001) {
          return b.baseConfidence - a.baseConfidence;
        }
        return (a.category.id || '').localeCompare(b.category.id || '');
      });

      const qualifying = scoredCats.filter(s => s.qualifies);
      const maxLabels = globalSettings.max_labels_per_post ?? 4;
      const selected = qualifying.slice(0, maxLabels);

      const elapsed = Math.round(performance.now() - start + 28);
      const latencyElem = document.getElementById('sandboxLatency');
      if (latencyElem) latencyElem.textContent = `Inferencia simulada en: ${elapsed} ms · boosted_score`;

      // 4. Renderizar Resultado en Modal
      const verdictBadge = document.getElementById('sandboxVerdictBadge');
      const winner = selected.length > 0 ? selected[0] : null;

      if (winner) {
        if (verdictBadge) {
          verdictBadge.textContent = 'MATCH CONFIRMADO';
          verdictBadge.className = 'px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-700 dark:text-emerald-300';
        }

        const dot = document.getElementById('sandboxWinnerDot');
        if (dot) dot.style.backgroundColor = winner.category.color_hex || '#10b981';

        const label = document.getElementById('sandboxWinnerLabel');
        if (label) label.textContent = winner.category.label;

        const idElem = document.getElementById('sandboxWinnerId');
        if (idElem) idElem.textContent = `[${winner.category.id}] · P${winner.category.priority ?? 50}`;

        const scoreElem = document.getElementById('sandboxWinnerBoosted');
        if (scoreElem) scoreElem.textContent = winner.boostedScore.toFixed(2);

        const breakdownElem = document.getElementById('sandboxWinnerBreakdown');
        if (breakdownElem) breakdownElem.textContent = `${winner.breakdown} (umbral: ${winner.effectiveThreshold.toFixed(2)})`;
      } else {
        // Fallback
        const fallbackId = globalSettings.fallback_category || 'otros';
        if (verdictBadge) {
          verdictBadge.textContent = 'FALLBACK / ABSTENCIÓN';
          verdictBadge.className = 'px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-700 dark:text-amber-300';
        }

        const dot = document.getElementById('sandboxWinnerDot');
        if (dot) dot.style.backgroundColor = '#64748b';

        const label = document.getElementById('sandboxWinnerLabel');
        if (label) label.textContent = 'Otros / Misceláneo (Fallback)';

        const idElem = document.getElementById('sandboxWinnerId');
        if (idElem) idElem.textContent = `[${fallbackId}]`;

        const scoreElem = document.getElementById('sandboxWinnerBoosted');
        if (scoreElem) scoreElem.textContent = '0.50';

        const breakdownElem = document.getElementById('sandboxWinnerBreakdown');
        if (breakdownElem) breakdownElem.textContent = 'Ninguna categoría superó el umbral RLCD efectivo.';
      }

      // Secundarias
      const secondaryList = document.getElementById('sandboxSecondaryList');
      if (secondaryList) {
        secondaryList.innerHTML = '';
        const secondaries = selected.slice(1);

        if (secondaries.length === 0) {
          secondaryList.innerHTML = '<span class="text-[10px] text-[var(--text-muted)] italic">Sin etiquetas secundarias en este forward pass.</span>';
        } else {
          secondaries.forEach(sec => {
            const item = document.createElement('div');
            item.className = 'flex items-center justify-between p-1.5 surface-card rounded font-mono text-[10px]';
            item.innerHTML = `
              <div class="flex items-center gap-2">
                <span class="w-2 h-2 rounded-full" style="background-color: ${sec.category.color_hex || '#7c3aed'}"></span>
                <span class="font-bold">${escapeHtml(sec.category.label)}</span>
                <span class="text-[var(--text-muted)]">[${escapeHtml(sec.category.id)}]</span>
              </div>
              <div class="flex items-center gap-2">
                <span class="text-emerald-600 font-bold">${sec.boostedScore.toFixed(2)}</span>
                <span class="text-[var(--text-muted)]">(P${sec.category.priority ?? 50})</span>
              </div>
            `;
            secondaryList.appendChild(item);
          });
        }
      }

      // Preguntas Suplementarias Simuladas
      const simAsset = document.getElementById('simAsset');
      if (simAsset) simAsset.textContent = detectedAssetType;

      const simFormat = document.getElementById('simFormat');
      if (simFormat) {
        simFormat.textContent = text.includes('lanzamos') || text.includes('v2') || text.includes('release') 
          ? 'launch' 
          : (detectedAssetType === 'github_repo' ? 'opensource' : 'explainer');
      }

      const simDepth = document.getElementById('simDepth');
      if (simDepth) {
        simDepth.textContent = text.includes('gpu') || text.includes('vram') || text.includes('cuantizad') 
          ? 'Nivel 4 (Avanzado)' 
          : 'Nivel 3 (Intermedio)';
      }
    },

    bindEvents() {
      document.getElementById('btnOpenSandbox')?.addEventListener('click', () => {
        ConfigSimulator.openWithCategory(null);
      });

      document.getElementById('btnCloseSandbox')?.addEventListener('click', () => {
        sandboxModal()?.classList.add('hidden');
      });

      document.getElementById('btnRunSimulation')?.addEventListener('click', () => {
        ConfigSimulator.runSimulation();
      });

      document.getElementById('btnLoadSampleOllama')?.addEventListener('click', () => {
        const input = document.getElementById('sandboxInputText');
        if (input) input.value = 'Corriendo Llama 3.1 8B en Ollama con 8GB de VRAM localmente sin depender de APIs en la nube. Repo: https://github.com/ollama/ollama';
        ConfigSimulator.runSimulation();
      });

      document.getElementById('btnLoadSampleWorkflow')?.addEventListener('click', () => {
        const input = document.getElementById('sandboxInputText');
        if (input) input.value = 'Nuevo workflow de ComfyUI para Flux schnell con LoRA arquitectónico de Civitai descargable: https://openart.ai/workflows/flux';
        ConfigSimulator.runSimulation();
      });
    }
  };

  // Exposición en namespace global
  window.ConfigSimulator = ConfigSimulator;

  // Aliases legacy
  window.openSandboxWithCategory = catId => ConfigSimulator.openWithCategory(catId);
  window.runMultiLabelSimulation = () => ConfigSimulator.runSimulation();

})(window);
