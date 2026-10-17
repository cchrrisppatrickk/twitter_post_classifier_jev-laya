/**
 * api.js - Centralized API Client for Twitter Post Classifier Master v2.1.2
 * Proporciona acceso tipado y modular a todos los endpoints de FastAPI con
 * manejo estándar de errores y compatibilidad backward-compatible.
 */

(function () {
  'use strict';

  const BASE_URL = '';

  /**
   * Helper unificado para realizar peticiones fetch con JSON.
   */
  async function request(endpoint, options = {}) {
    const url = `${BASE_URL}${endpoint}`;
    const defaultHeaders = {
      'Accept': 'application/json',
    };

    if (options.body && !(options.body instanceof FormData)) {
      defaultHeaders['Content-Type'] = 'application/json';
    }

    const config = {
      ...options,
      headers: {
        ...defaultHeaders,
        ...options.headers,
      },
    };

    try {
      const response = await fetch(url, config);
      if (!response.ok) {
        let errorDetail = `HTTP ${response.status} ${response.statusText}`;
        try {
          const errJson = await response.json();
          if (errJson && errJson.detail) {
            errorDetail = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
          }
        } catch (_) {}
        const error = new Error(errorDetail);
        error.status = response.status;
        error.response = response;
        throw error;
      }
      return await response.json();
    } catch (err) {
      console.error(`[API Error] ${config.method || 'GET'} ${url}:`, err);
      throw err;
    }
  }

  const API = {
    /**
     * Endpoints de Categorías y Taxonomía
     */
    categories: {
      async getAll(family = null) {
        const query = family ? `?family=${encodeURIComponent(family)}` : '';
        return await request(`/api/categories${query}`);
      },
      async getById(categoryId) {
        return await request(`/api/categories/${encodeURIComponent(categoryId)}`);
      },
      async create(categoryData) {
        return await request('/api/categories', {
          method: 'POST',
          body: JSON.stringify(categoryData),
        });
      },
      async update(categoryId, categoryData) {
        return await request(`/api/categories/${encodeURIComponent(categoryId)}`, {
          method: 'PUT',
          body: JSON.stringify(categoryData),
        });
      },
      async delete(categoryId) {
        return await request(`/api/categories/${encodeURIComponent(categoryId)}`, {
          method: 'DELETE',
        });
      },
      async getGlobalSettings() {
        return await request('/api/categories/settings/globals');
      },
      async updateGlobalSettings(settingsData) {
        return await request('/api/categories/settings/globals', {
          method: 'PUT',
          body: JSON.stringify(settingsData),
        });
      },
      async getSupplementaryQuestions() {
        return await request('/api/categories/questions/supplementary');
      },
      async createSupplementaryQuestion(questionData) {
        return await request('/api/categories/questions/supplementary', {
          method: 'POST',
          body: JSON.stringify(questionData),
        });
      },
      async updateSupplementaryQuestion(questionId, questionData) {
        return await request(`/api/categories/questions/supplementary/${encodeURIComponent(questionId)}`, {
          method: 'PUT',
          body: JSON.stringify(questionData),
        });
      },
      async deleteSupplementaryQuestion(questionId) {
        return await request(`/api/categories/questions/supplementary/${encodeURIComponent(questionId)}`, {
          method: 'DELETE',
        });
      },
      async toggleSupplementaryQuestion(questionId) {
        return await request(`/api/categories/questions/supplementary/${encodeURIComponent(questionId)}/toggle`, {
          method: 'PATCH',
        });
      },
    },

    /**
     * Endpoints de Publicaciones (Posts) y Análisis Laya AI
     */
    posts: {
      async getAll(params = {}) {
        const query = new URLSearchParams(params).toString();
        const endpoint = query ? `/api/posts?${query}` : '/api/posts';
        return await request(endpoint);
      },
      async getById(tweetId) {
        return await request(`/api/posts/${encodeURIComponent(tweetId)}`);
      },
      async overrideCategory(tweetId, newCategory, reason = 'Supervisión manual desde Drawer/Modal') {
        return await request(`/api/posts/${encodeURIComponent(tweetId)}/override`, {
          method: 'POST',
          body: JSON.stringify({
            new_category: newCategory,
            reason: reason,
          }),
        });
      },
      async analyze(payload) {
        return await request('/api/posts/analyze', {
          method: 'POST',
          body: JSON.stringify(payload),
        });
      },
      async analyzeBatchStream(payload) {
        return await fetch('/api/posts/analyze-batch-stream', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'text/event-stream',
          },
          body: JSON.stringify(payload),
        });
      },
      async reclassify(tweetId, dryRun = true, confirm = false, reason = null) {
        return await request(`/api/posts/${encodeURIComponent(tweetId)}/reclassify`, {
          method: 'POST',
          body: JSON.stringify({
            dry_run: dryRun,
            confirm: confirm,
            reason: reason,
          }),
        });
      },
      async getHistory(tweetId) {
        return await request(`/api/posts/${encodeURIComponent(tweetId)}/history`);
      },
      async rollback(tweetId, historyId) {
        return await request(`/api/posts/${encodeURIComponent(tweetId)}/history/${encodeURIComponent(historyId)}/rollback`, {
          method: 'POST',
        });
      },
    },

    /**
     * Endpoints de Telemetría y Salud del Sistema
     */
    system: {
      async getHealth() {
        return await request('/api/system/health');
      },
      async getCheckpoints() {
        return await request('/api/system/checkpoints');
      },
    },
  };

  // Exponer API globalmente en window
  window.API = API;
})();
