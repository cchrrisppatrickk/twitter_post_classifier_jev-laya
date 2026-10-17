/**
 * PIPELINE_MODAL.JS - Scraping & Proxy Telemetry Console Modal Controller (Laya Engine v2.1.0)
 * Visualización de logs de proxies, rotación de User-Agents y estado del pipeline de recolección.
 */

(function(window) {
  'use strict';

  const pipelineModal = document.getElementById('pipelineModal');
  const openPipelineBtn = document.getElementById('openPipelineBtn');
  const closePipelineModalBtn = document.getElementById('closePipelineModalBtn');
  const closePipelineBottomBtn = document.getElementById('closePipelineBottomBtn');

  const PipelineModal = {
    open() {
      if (pipelineModal) pipelineModal.classList.remove('hidden');
    },

    close() {
      if (pipelineModal) pipelineModal.classList.add('hidden');
    },

    bindEvents() {
      if (openPipelineBtn) openPipelineBtn.addEventListener('click', () => PipelineModal.open());
      if (closePipelineModalBtn) closePipelineModalBtn.addEventListener('click', () => PipelineModal.close());
      if (closePipelineBottomBtn) closePipelineBottomBtn.addEventListener('click', () => PipelineModal.close());
    }
  };

  window.PipelineModal = PipelineModal;

  if (document.readyState === 'loading') {
    window.addEventListener('DOMContentLoaded', () => PipelineModal.bindEvents());
  } else {
    PipelineModal.bindEvents();
  }

})(window);
