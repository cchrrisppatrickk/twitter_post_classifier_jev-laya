/**
 * STATE.JS - Core Dashboard Reactive State Store (Laya Engine v2.1.0)
 * Centraliza las variables de estado reactivo del dashboard, filtros, vistas y sincronización global.
 */

(function(window) {
  'use strict';

  const AppState = {
    currentScrapedPosts: [],
    currentFilterMode: 'all',        // 'all', 'high', 'mid', 'low', 'hybrid', 'anomaly', 'pending'
    currentFamilyFilter: 'all',      // 'all' o un id de familia ('ia', 'modelado_3d', etc.)
    currentTileViewMode: 'viral',    // 'viral' | 'split-diagonal' | 'split-pie'
    currentSortOrder: 'default',     // 'default' | 'purity_desc' | 'hybrid_first' | 'likes_desc' | 'score_desc'
    currentMainView: 'waffle',       // 'waffle' | 'scatter' | 'table'
    currentDensity: 'normal',        // 'compact' | 'normal' | 'large'
    currentSearchTerm: '',
    selectedPostForDrawer: null,
    currentChecksCount: 7440,
    currentTotalCost: 0.75,
    currentLatency: 8.0,

    /**
     * Sincroniza el array de posts en memoria
     * @param {Array} posts 
     */
    setPosts(posts) {
      this.currentScrapedPosts = Array.isArray(posts) ? posts : [];
      window.currentScrapedPosts = this.currentScrapedPosts;
    },

    /**
     * Agrega un post al inicio del dataset
     * @param {Object} post 
     */
    unshiftPost(post) {
      this.currentScrapedPosts.unshift(post);
      window.currentScrapedPosts = this.currentScrapedPosts;
    },

    /**
     * Actualiza un post existente o lo agrega si no existe
     * @param {Object} post 
     */
    upsertPost(post) {
      const idx = this.currentScrapedPosts.findIndex(p => String(p.id) === String(post.id));
      if (idx >= 0) {
        this.currentScrapedPosts[idx] = post;
      } else {
        this.currentScrapedPosts.unshift(post);
      }
      window.currentScrapedPosts = this.currentScrapedPosts;
    },

    /**
     * Limpia todas las publicaciones en memoria
     */
    clearPosts() {
      this.currentScrapedPosts = [];
      window.currentScrapedPosts = [];
    }
  };

  // Exposición en namespace global
  window.AppState = AppState;

  // Variables globales interoperables
  window.currentScrapedPosts = AppState.currentScrapedPosts;
  window.currentFilterMode = AppState.currentFilterMode;
  window.currentFamilyFilter = AppState.currentFamilyFilter;
  window.currentTileViewMode = AppState.currentTileViewMode;
  window.currentSortOrder = AppState.currentSortOrder;
  window.currentMainView = AppState.currentMainView;
  window.currentDensity = AppState.currentDensity;
  window.currentSearchTerm = AppState.currentSearchTerm;
  window.selectedPostForDrawer = AppState.selectedPostForDrawer;
  window.currentChecksCount = AppState.currentChecksCount;
  window.currentTotalCost = AppState.currentTotalCost;
  window.currentLatency = AppState.currentLatency;

})(window);
