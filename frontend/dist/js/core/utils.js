/**
 * UTILS.JS - Core Pure Utility Functions (Laya Engine v2.1.0)
 * Funciones puras de escape seguro, formateo numérico, detección de anomalías y mapeo térmico.
 */

(function(window) {
  'use strict';

  const CoreUtils = {
    /**
     * Formatea cantidades numéricas con sufijo K (ej. 1500 -> 1.5K)
     * @param {number|string} num 
     * @returns {string}
     */
    formatNumberK(num) {
      if (!num && num !== 0) return '0';
      const n = Number(num);
      if (isNaN(n)) return '0';
      if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
      return n.toString();
    },

    /**
     * Sanitiza cadenas de texto para evitar vulnerabilidades XSS
     * @param {*} text 
     * @returns {string}
     */
    escapeHtml(text) {
      if (!text && text !== 0) return '';
      return String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
    },

    /**
     * Devuelve la clase CSS del mapa de calor según el score de afinidad
     * @param {number} score 
     * @returns {string}
     */
    getTileColorClass(score) {
      if (score >= 80) return 'tile-high';
      if (score >= 65) return 'tile-mid-high';
      if (score >= 50) return 'tile-mid';
      if (score >= 42) return 'tile-neutral';
      if (score >= 32) return 'tile-mid-low';
      if (score >= 20) return 'tile-low';
      return 'tile-flop';
    },

    /**
     * Detecta si una publicación es una anomalía algorítmica (outlier)
     * @param {Object} post 
     * @returns {boolean}
     */
    isPostAnomaly(post) {
      if (!post) return false;
      if (post.is_outlier) return true;
      const score = post.affinity_score || 0;
      const likes = post.likes || 0;
      return (score < 40 && likes > 4000) || (score > 75 && likes < 500);
    },

    /**
     * Trunca un texto de forma segura agregando elipsis
     * @param {string} text 
     * @param {number} maxLen 
     * @returns {string}
     */
    truncateText(text, maxLen = 70) {
      if (!text) return '';
      const s = String(text).trim();
      return s.length > maxLen ? s.substring(0, maxLen) + '...' : s;
    },

    /**
     * Parseo tolerante de JSON limpiando comas sobrantes y backticks de markdown
     * @param {string} raw 
     * @returns {any}
     */
    safeJsonParse(raw) {
      if (!raw) return null;
      let cleaned = String(raw).trim()
        .replace(/^```json\s*/i, '')
        .replace(/^```\s*/, '')
        .replace(/```\s*$/, '')
        .replace(/,\s*([\]}])/g, '$1')
        .trim();
      return JSON.parse(cleaned);
    }
  };

  // Exposición en namespace global
  window.CoreUtils = CoreUtils;

  // Funciones de conveniencia globales
  window.formatNumberK = num => CoreUtils.formatNumberK(num);
  window.escapeHtml = text => CoreUtils.escapeHtml(text);
  window.getTileColorClass = score => CoreUtils.getTileColorClass(score);
  window.isPostAnomaly = post => CoreUtils.isPostAnomaly(post);
  window.truncateText = (text, len) => CoreUtils.truncateText(text, len);

})(window);
