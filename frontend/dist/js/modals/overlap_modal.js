/**
 * OVERLAP_MODAL.JS - Multiclass Co-occurrence Matrix Modal Controller (Laya Engine v2.1.0)
 * Renderizado de pares híbridos, cálculo de likes promedio y frecuencias de co-ocurrencia.
 */

(function(window) {
  'use strict';

  const overlapModal = document.getElementById('overlapModal');
  const openOverlapModalBtn = document.getElementById('openOverlapModalBtn');
  const closeOverlapModalBtn = document.getElementById('closeOverlapModalBtn');
  const closeOverlapBottomBtn = document.getElementById('closeOverlapBottomBtn');
  const overlapPairsContainer = document.getElementById('overlapPairsContainer');

  function getCurrentScrapedPosts() {
    return window.currentScrapedPosts || [];
  }

  function getCategories() {
    return window.CATEGORIES || [];
  }

  function getFormatNumberK() {
    return typeof formatNumberK === 'function' ? formatNumberK : (n => n);
  }

  const OverlapModal = {
    renderData() {
      if (!overlapPairsContainer) return;
      overlapPairsContainer.innerHTML = '';
      
      const posts = getCurrentScrapedPosts();
      const categories = getCategories();
      const formatK = getFormatNumberK();
      const pairCounts = {};

      posts.filter(p => p.is_hybrid && p.secondary_cat_id).forEach(post => {
        const catA = post.category_id;
        const catB = post.secondary_cat_id;
        const key = [catA, catB].sort().join('___');

        if (!pairCounts[key]) {
          pairCounts[key] = {
            cat1Id: catA,
            cat2Id: catB,
            count: 0,
            likesTotal: 0
          };
        }
        pairCounts[key].count++;
        pairCounts[key].likesTotal += (post.likes || 0);
      });

      const sortedPairs = Object.values(pairCounts).sort((a, b) => b.count - a.count);

      if (sortedPairs.length === 0) {
        overlapPairsContainer.innerHTML = `
          <div class="p-4 text-center text-stone-500 font-mono text-xs">
            No se detectaron publicaciones híbridas en el dataset actual.
          </div>
        `;
        return;
      }

      sortedPairs.forEach(pair => {
        const cat1 = categories.find(c => c.id === pair.cat1Id) || categories[0] || { name: pair.cat1Id, code: 'C1', colorBadge: 'bg-stone-500 text-white' };
        const cat2 = categories.find(c => c.id === pair.cat2Id) || categories[1] || { name: pair.cat2Id, code: 'C2', colorBadge: 'bg-stone-500 text-white' };
        const avgLikes = Math.round(pair.likesTotal / pair.count);

        const row = document.createElement('div');
        row.className = 'p-3 flex items-center justify-between hover:bg-stone-50 transition';
        row.innerHTML = `
          <div class="flex items-center gap-2.5">
            <div class="flex -space-x-1.5">
              <span class="w-5 h-5 rounded-full ${cat1.colorBadge} flex items-center justify-center font-bold text-[8px] border border-white shadow-xs">${cat1.code}</span>
              <span class="w-5 h-5 rounded-full ${cat2.colorBadge} flex items-center justify-center font-bold text-[8px] border border-white shadow-xs">${cat2.code}</span>
            </div>
            <div class="flex items-center gap-1 font-mono">
              <span class="font-bold text-stone-900">${cat1.name}</span>
              <span class="text-stone-400 font-normal">+</span>
              <span class="font-bold text-stone-900">${cat2.name}</span>
            </div>
          </div>
          <div class="text-right font-mono">
            <span class="font-bold text-stone-800 text-xs">${pair.count} posts</span>
            <span class="text-[10px] text-stone-500 block"><i class="fa-regular fa-heart text-rose-500"></i> ${formatK(avgLikes)} avg</span>
          </div>
        `;
        overlapPairsContainer.appendChild(row);
      });
    },

    open() {
      this.renderData();
      if (overlapModal) overlapModal.classList.remove('hidden');
    },

    close() {
      if (overlapModal) overlapModal.classList.add('hidden');
    },

    bindEvents() {
      if (openOverlapModalBtn) openOverlapModalBtn.addEventListener('click', () => OverlapModal.open());
      if (closeOverlapModalBtn) closeOverlapModalBtn.addEventListener('click', () => OverlapModal.close());
      if (closeOverlapBottomBtn) closeOverlapBottomBtn.addEventListener('click', () => OverlapModal.close());
    }
  };

  window.OverlapModal = OverlapModal;
  window.renderOverlapMatrixData = () => OverlapModal.renderData();

  if (document.readyState === 'loading') {
    window.addEventListener('DOMContentLoaded', () => OverlapModal.bindEvents());
  } else {
    OverlapModal.bindEvents();
  }

})(window);
