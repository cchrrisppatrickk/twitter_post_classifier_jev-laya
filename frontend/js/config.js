/**
 * CONFIG.JS - Registry Studio Backward Compatibility Facade (Laya Engine v2.1.0)
 *
 * NOTA ARQUITECTÓNICA:
 * A partir de la Subfase 5.11.1, la lógica monolítica de este archivo ha sido
 * refactorizada y desacoplada en la suite modular 'frontend/js/config/':
 * - state.js: Estado reactivo, telemetría HUD y consumo de API.
 * - categories.js: Grid de 48 tarjetas, filtros, ordenación y modal CRUD de taxonomía.
 * - globals.js: Formulario de ajustes globales y boosters deterministas.
 * - questions.js: Banco de preguntas tipadas (Choice, Score, Noul) y modal CRUD.
 * - simulator.js: Simulador de inferencia Multi-Label RLCD y desempate.
 * - app.js: Orquestador principal, navegación de tabs, tema visual y modales.
 *
 * Este archivo se mantiene como fachada de interoperabilidad.
 */

(function(window) {
  'use strict';

  // Si los módulos aún no han sido cargados (por ejemplo, en un entorno legado que incluya solo config.js),
  // se definen proxies delegadores hacia ConfigApp / ConfigState
  window.initStudio = function() {
    if (window.ConfigApp && typeof window.ConfigApp.init === 'function') {
      window.ConfigApp.init();
    } else {
      console.warn('[Registry Studio] Los submódulos en /js/config/ deben cargarse para inicializar el Studio.');
    }
  };

  console.log('[Registry Studio v2.1.0] Módulos de configuración activos en /js/config/');
})(window);
