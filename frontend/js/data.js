/**
 * ==========================================================
 * DATA.JS - Taxonomía Dinámica (categories.json), Assets y Dataset
 * Subfase 5.11: Optimizado e integrado con CoreState y CoreUtils
 * ==========================================================
 */

(function(window) {
  'use strict';

  // Familias raíz de la taxonomía v2.1.1 (sincronizada con categories.json)
  const ROOT_FAMILIES = {
    ia: { id: 'ia', name: 'Inteligencia Artificial (IA)', colorHex: '#8b5cf6', icon: 'fa-brain' },
    ia_generativa: { id: 'ia_generativa', name: 'IA Generativa', colorHex: '#a855f7', icon: 'fa-wand-magic-sparkles' },
    modelos_ia: { id: 'modelos_ia', name: 'Modelos de IA', colorHex: '#5b21b6', icon: 'fa-microchip' },
    agentes_ia: { id: 'agentes_ia', name: 'Agentes de IA', colorHex: '#0ea5e9', icon: 'fa-robot' },
    modelado_3d: { id: 'modelado_3d', name: 'Modelado 3D & Blender', colorHex: '#0284c7', icon: 'fa-cube' },
    juegos: { id: 'juegos', name: 'Desarrollo de Videojuegos', colorHex: '#d946ef', icon: 'fa-gamepad' },
    dev_tools: { id: 'dev_tools', name: 'Desarrollo & Herramientas', colorHex: '#10b981', icon: 'fa-code' },
    mangas: { id: 'mangas', name: 'Manga, Anime & Ilustración', colorHex: '#f43f5e', icon: 'fa-palette' },
    negocios_saas: { id: 'negocios_saas', name: 'Negocios, SaaS & MRR', colorHex: '#059669', icon: 'fa-sack-dollar' },
    otros: { id: 'otros', name: 'Otros & Misceláneo', colorHex: '#64748b', icon: 'fa-layer-group' }
  };

  // Mapeo dinámico de colores hexadecimales por categoría para renderizado split/bicolor
  const CATEGORY_COLOR_MAP = {
    ia: '#8b5cf6',
    ia_local: '#7c3aed',
    hardware_benchmarks: '#6366f1',
    ia_generativa: '#a855f7',
    gen_imagenes: '#c026d3',
    gen_video: '#db2777',
    gen_audio: '#ec4899',
    gen_3d: '#9333ea',
    gen_texto: '#7e22ce',
    vision: '#6d28d9',
    comfyui: '#a21caf',
    comfyui_workflows: '#86198f',
    comfyui_instalacion: '#701a75',
    modelos_ia: '#5b21b6',
    modelos_huggingface: '#4c1d95',
    lora_civitai: '#3b0764',
    modelos_cuantificados: '#312e81',
    modelos_sin_censura: '#1e1b4b',
    agentes_ia: '#0ea5e9',
    agente_claude: '#0284c7',
    agente_codex: '#0891b2',
    agente_gemini: '#0d9488',
    agente_antigravity: '#14b8a6',
    herramientas_ia: '#06b6d4',
    modelado_3d: '#0284c7',
    blender: '#ea580c',
    blender_addons: '#c2410c',
    blender_tutoriales: '#9a3412',
    blender_dev: '#7c2d12',
    threejs_webgl: '#0369a1',
    motion_design_vfx: '#0284c7',
    otros_3d: '#075985',
    juegos: '#d946ef',
    unity: '#475569',
    unreal: '#0f172a',
    godot: '#1e40af',
    indie_dev: '#a21caf',
    assets_gamedev: '#7e22ce',
    lanzamientos_juegos: '#6b21a8',
    dev_tools: '#10b981',
    frontend_ui_motion: '#059669',
    backend_infra_cli: '#047857',
    mangas: '#f43f5e',
    webcomic_manga_serial: '#e11d48',
    fanart_anime: '#be123c',
    negocios_saas: '#059669',
    otros: '#64748b',
    vfx_compositing: '#14b8a6'
  };

  // Taxonomía principal de categorías (se sincroniza con categories.json vía /api/categories)
  let CATEGORIES = [
    { id: 'comfyui', code: 'CF', name: 'ComfyUI Core', family_id: 'ia', colorHex: '#a21caf', targetCount: 14, avgScoreTarget: 78, avgLikesTarget: 2200 },
    { id: 'comfyui_workflows', code: 'CW', name: 'Workflows ComfyUI', family_id: 'ia', colorHex: '#86198f', targetCount: 18, avgScoreTarget: 82, avgLikesTarget: 3400 },
    { id: 'comfyui_instalacion', code: 'CI', name: 'Instalación ComfyUI', family_id: 'ia', colorHex: '#701a75', targetCount: 10, avgScoreTarget: 74, avgLikesTarget: 1100 },
    { id: 'gen_imagenes', code: 'GI', name: 'Generación Imágenes', family_id: 'ia', colorHex: '#c026d3', targetCount: 22, avgScoreTarget: 85, avgLikesTarget: 4500 },
    { id: 'herramientas_ia', code: 'HI', name: 'Herramientas de IA', family_id: 'ia', colorHex: '#06b6d4', targetCount: 16, avgScoreTarget: 70, avgLikesTarget: 1800 },
    { id: 'blender', code: 'BL', name: 'Blender 3D', family_id: 'modelado_3d', colorHex: '#ea580c', targetCount: 20, avgScoreTarget: 80, avgLikesTarget: 3900 },
    { id: 'blender_addons', code: 'BA', name: 'Addons de Blender', family_id: 'modelado_3d', colorHex: '#c2410c', targetCount: 14, avgScoreTarget: 76, avgLikesTarget: 2600 },
    { id: 'threejs_webgl', code: '3J', name: 'Three.js & WebGL', family_id: 'modelado_3d', colorHex: '#0369a1', targetCount: 15, avgScoreTarget: 81, avgLikesTarget: 2900 },
    { id: 'godot', code: 'GD', name: 'Godot Engine', family_id: 'juegos', colorHex: '#1e40af', targetCount: 12, avgScoreTarget: 72, avgLikesTarget: 1400 },
    { id: 'indie_dev', code: 'ID', name: 'Indie Dev & Devlogs', family_id: 'juegos', colorHex: '#a21caf', targetCount: 18, avgScoreTarget: 75, avgLikesTarget: 2100 },
    { id: 'frontend_ui_motion', code: 'FE', name: 'Frontend & Motion Web', family_id: 'dev_tools', colorHex: '#059669', targetCount: 16, avgScoreTarget: 79, avgLikesTarget: 3100 },
    { id: 'backend_infra_cli', code: 'BE', name: 'Backend, CLI & Infra', family_id: 'dev_tools', colorHex: '#047857', targetCount: 12, avgScoreTarget: 68, avgLikesTarget: 1200 },
    { id: 'webcomic_manga_serial', code: 'MC', name: 'Manga Serializado', family_id: 'mangas', colorHex: '#e11d48', targetCount: 14, avgScoreTarget: 88, avgLikesTarget: 5200 },
    { id: 'negocios_saas', code: 'NS', name: 'Métricas SaaS & MRR', family_id: 'negocios_saas', colorHex: '#059669', targetCount: 15, avgScoreTarget: 77, avgLikesTarget: 2800 },
    { id: 'otros', code: 'OT', name: 'Otros & Vida Cotidiana', family_id: 'otros', colorHex: '#64748b', targetCount: 8, avgScoreTarget: 40, avgLikesTarget: 600 }
  ];

  // Assets multimedia para inspección en Drawer
  const SAMPLE_MEDIA_ASSETS = [
    {
      type: 'video',
      thumb: 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=800&auto=format&fit=crop&q=80',
      duration: '0:42',
      aspectRatio: '16:9'
    },
    {
      type: 'image',
      thumb: 'https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=800&auto=format&fit=crop&q=80',
      duration: 'FOTO',
      aspectRatio: '16:9'
    },
    {
      type: 'video',
      thumb: 'https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=800&auto=format&fit=crop&q=80',
      duration: '1:18',
      aspectRatio: '16:9'
    },
    {
      type: 'image',
      thumb: 'https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=800&auto=format&fit=crop&q=80',
      duration: 'CHART',
      aspectRatio: '16:9'
    }
  ];

  const HOOK_PATTERNS = [
    'Curiosity Gap + Social Proof',
    'Direct Value Proposition',
    'Contrarian Thesis',
    'Step-by-Step Breakdown',
    'Behind the Scenes WIP'
  ];

  // Funciones puente delegadas a CoreUtils
  function formatNumberK(num) {
    return window.CoreUtils ? window.CoreUtils.formatNumberK(num) : (num ? num.toString() : '0');
  }

  function getTileColorClass(score) {
    return window.CoreUtils ? window.CoreUtils.getTileColorClass(score) : 'tile-neutral';
  }

  function isPostAnomaly(post) {
    return window.CoreUtils ? window.CoreUtils.isPostAnomaly(post) : false;
  }

  /**
   * Generador de publicaciones realistas para alimentar las categorías
   */
  function buildRealisticScannedDataset(cats = CATEGORIES) {
    const generated = [];
    const authors = ['0xMovez', 'shadermaster', 'indiedev_99', 'saas_builder', 'rust_coder', 'unity_guru', 'blender_artist', 'comfy_wizard'];

    cats.forEach((cat, catIdx) => {
      const postCount = cat.targetCount || (Math.floor(Math.random() * 8) + 6);
      const avgScore = cat.avgScoreTarget || 65;
      const avgLikes = cat.avgLikesTarget || 1500;

      for (let i = 0; i < postCount; i++) {
        const variance = (Math.random() - 0.48) * 35;
        let score = Math.max(15, Math.min(99, Math.round(avgScore + variance)));
        
        const likesFactor = Math.pow(Math.random(), 1.8) * 2.2 + 0.3;
        let likes = Math.round(avgLikes * likesFactor);

        // Inyectar outliers
        if (i === 1 && catIdx % 3 === 0) {
          score = 28;
          likes = 12500;
        } else if (i === 2 && catIdx % 4 === 0) {
          score = 92;
          likes = 180;
        }

        let retweets = Math.round(likes * (0.08 + Math.random() * 0.12));
        let views = Math.round(likes * (12 + Math.random() * 25));
        let bookmarks = Math.round(likes * (0.05 + Math.random() * 0.1));
        let replies = Math.round(likes * (0.02 + Math.random() * 0.05));

        const asset = SAMPLE_MEDIA_ASSETS[(i + cat.id.length) % SAMPLE_MEDIA_ASSETS.length];
        const hook = HOOK_PATTERNS[i % HOOK_PATTERNS.length];

        // Híbrido 60/40 en aprox 40% de los posts
        const isHybrid = (i % 3 === 0);
        let secondaryCat = null;
        let primaryPct = 100;
        let secondaryPct = 0;

        if (isHybrid && cats.length > 1) {
          const otherCats = cats.filter(c => c.id !== cat.id);
          secondaryCat = otherCats[(i + 3) % otherCats.length];
          primaryPct = 55 + Math.floor(Math.random() * 20); // 55% a 74%
          secondaryPct = 100 - primaryPct;
        }

        const sampleText = isHybrid 
          ? `${cat.name} + ${secondaryCat.name}: Integración técnica y resultados del benchmark con aceleración hardware en producción.`
          : `${cat.name} v2 release: Demostración técnica y arquitectura modular. #buildinpublic #dev`;

        generated.push({
          id: `gen-${cat.id}-${Date.now()}-${i}`,
          author: authors[(i + catIdx) % authors.length],
          text: sampleText,
          likes: likes,
          retweets: retweets,
          views: views,
          bookmarks: bookmarks,
          replies: replies,
          created_at: `14 Oct 2026, 10:${String((i * 7) % 60).padStart(2, '0')}`,
          category_id: cat.id,
          affinity_score: score,
          media: asset,
          hook_type: hook,
          is_hybrid: isHybrid,
          primary_pct: primaryPct,
          secondary_cat_id: secondaryCat ? secondaryCat.id : null,
          secondary_pct: secondaryPct,
          is_outlier: (score < 40 && likes > 4000) || (score > 75 && likes < 500),
          ai_reasoning: isHybrid
            ? `Clasificación dual: ${primaryPct}% "${cat.name}" con ${secondaryPct}% en "${secondaryCat.name}".`
            : `Clasificado puro (${primaryPct}%) en "${cat.name}" con afinidad ${score}%.`
        });
      }
    });

    return generated;
  }

  /**
   * Sincroniza la taxonomía completa y publicaciones con el Backend FastAPI
   */
  async function syncTaxonomyAndPostsWithBackend() {
    try {
      // 1. Obtener categorías desde /api/categories
      const catRes = await fetch('/api/categories');
      if (catRes.ok) {
        const apiCats = await catRes.json();
        if (Array.isArray(apiCats) && apiCats.length > 0) {
          CATEGORIES = apiCats.map(c => {
            CATEGORY_COLOR_MAP[c.id] = c.color_hex || '#8b5cf6';
            return {
              id: c.id,
              code: c.code || c.id.slice(0, 3).toUpperCase(),
              name: c.name || c.label,
              label: c.label || c.name,
              family_id: c.family_id || 'otros',
              colorHex: c.color_hex || '#8b5cf6',
              colorBadge: 'text-white',
              targetCount: 14,
              avgScoreTarget: Math.round((c.threshold || 0.75) * 100),
              avgLikesTarget: 1800,
              description: c.description || '',
              targetKeywords: c.keywords || [],
              threshold: c.threshold || 0.75,
              priority: c.priority || 50
            };
          });
          window.CATEGORIES = CATEGORIES;
        }
      }

      // 2. Obtener publicaciones reales desde /api/posts
      const postsRes = await fetch('/api/posts?limit=1000');
      let realPosts = [];
      if (postsRes.ok) {
        const postsData = await postsRes.json();
        if (postsData && Array.isArray(postsData.posts)) {
          realPosts = postsData.posts.map(p => formatAppPost(p));
        }
      }

      // 3. Almacenar publicaciones en AppState y sincronizar global
      if (window.AppState && typeof window.AppState.setPosts === 'function') {
        window.AppState.setPosts(realPosts);
      } else {
        window.currentScrapedPosts = realPosts;
      }

      console.info(`✓ Sincronización exitosa: ${CATEGORIES.length} categorías, ${realPosts.length} posts reales cargados desde BD SQLite.`);
    } catch (err) {
      console.warn('Backend API offline o inaccesible, iniciando con categorías vacías:', err);
      if (window.AppState && typeof window.AppState.clearPosts === 'function') {
        window.AppState.clearPosts();
      } else {
        window.currentScrapedPosts = [];
      }
    }
  }

  /**
   * Helper universal para estructurar objetos de publicación con metadatos reales,
   * garantizando compatibilidad con Meridian Scraping, Laya Engine y la Matriz Waffle.
   */
  function formatAppPost(p, rawScraping = null, layaOutput = null) {
    const hasSec = p.secondary_categories && p.secondary_categories.length > 0;
    const sec = hasSec ? p.secondary_categories[0] : null;
    const priPct = p.primary_pct !== undefined ? p.primary_pct : (p.affinity_score ? Math.round((p.affinity_score > 1 ? p.affinity_score : p.affinity_score * 100)) : 100);
    const secPct = p.secondary_pct !== undefined ? p.secondary_pct : (sec ? Math.round((sec.score > 1 ? sec.score : sec.score * 100)) : 0);

    const mediaUrls = p.media_urls || (p.media?.thumb ? [p.media.thumb] : []);
    const isVideo = p.media_type === 'video' || (mediaUrls.length > 0 && mediaUrls[0].includes('.mp4'));

    const raw = rawScraping || p.raw_scraping || {
      tweet_id: p.tweet_id || p.id,
      post_url: p.post_url || `https://x.com/${p.author_name || p.author || 'x'}/status/${p.tweet_id || p.id}`,
      author: {
        name: p.author_name || p.author || 'anon_dev',
        nick: p.author_nick || p.author_name || p.author || 'anon_dev',
        verified: !!p.verified,
        profile_image: p.avatar || null
      },
      content: p.content || p.text || '',
      date: p.date || p.created_at || '2026-10-14',
      metrics: {
        likes: p.metrics?.favorite_count ?? (p.likes || 0),
        retweets: p.metrics?.retweet_count ?? (p.retweets || 0),
        replies: p.metrics?.reply_count ?? (p.replies || 0),
        bookmarks: p.metrics?.bookmark_count ?? (p.bookmarks || 0)
      },
      category: isVideo ? 'video' : 'image',
      media_urls: mediaUrls
    };

    const laya = layaOutput || p.laya_output || {
      tweet_id: p.tweet_id || p.id,
      primary_category: p.primary_category || p.category_id || 'otros',
      affinity_score: p.affinity_score ? (p.affinity_score > 1 ? p.affinity_score / 100 : p.affinity_score) : 0.85,
      secondary_categories: p.secondary_categories || (sec ? [sec] : []),
      format: p.format || p.hook_type || 'other',
      format_confidence: p.format_confidence || 0.85,
      technical_depth: p.technical_depth || 2.5,
      assets: p.assets || [],
      status: p.status || 'CLASSIFIED',
      engine_used: p.engine_used || 'laya-cpu',
      inference_latency_ms: p.inference_latency_ms || 28.4
    };

    return {
      id: String(p.tweet_id || p.id),
      author: p.author_name || p.author || 'anon_dev',
      author_nick: p.author_nick || p.author_name || p.author || 'anon_dev',
      avatar: p.avatar || null,
      verified: !!p.verified,
      text: p.content || p.text || '',
      likes: p.metrics ? (p.metrics.favorite_count || 0) : (p.likes || 0),
      retweets: p.metrics ? (p.metrics.retweet_count || 0) : (p.retweets || 0),
      views: p.views || (p.metrics ? (p.metrics.favorite_count * 16) : ((p.likes || 0) * 16)),
      bookmarks: p.metrics ? (p.metrics.bookmark_count || 0) : (p.bookmarks || 0),
      replies: p.metrics ? (p.metrics.reply_count || 0) : (p.replies || 0),
      created_at: p.date || p.created_at || 'Reciente',
      date: p.date || p.created_at || '',
      post_url: p.post_url || `https://x.com/${p.author_name || p.author || 'x'}/status/${p.tweet_id || p.id}`,
      category_id: p.primary_category || p.category_id || 'otros',
      affinity_score: Math.round(p.affinity_score ? (p.affinity_score > 1 ? p.affinity_score : p.affinity_score * 100) : 75),
      media_urls: mediaUrls,
      media_type: isVideo ? 'video' : (mediaUrls.length > 0 ? 'image' : 'none'),
      media: mediaUrls.length > 0 ? {
        type: isVideo ? 'video' : 'image',
        thumb: mediaUrls[0],
        duration: isVideo ? '0:42' : 'FOTO',
        aspectRatio: '16:9'
      } : null,
      hook_type: p.format || p.hook_type || 'other',
      format: p.format || 'other',
      format_confidence: p.format_confidence || 0.85,
      technical_depth: p.technical_depth || 2.5,
      assets: p.assets || [],
      is_hybrid: hasSec,
      primary_pct: priPct,
      secondary_cat_id: sec ? sec.id : null,
      secondary_pct: secPct,
      secondary_categories: p.secondary_categories || [],
      is_outlier: !!p.is_outlier,
      status: p.status || 'CLASSIFIED',
      engine_used: p.engine_used || 'laya',
      taxonomy_version: p.taxonomy_version || '2.1.0',
      reclassification_count: p.reclassification_count || 0,
      raw_json: p.raw_json || raw,
      classification_json: p.classification_json || laya,
      raw_scraping: raw,
      laya_output: laya,
      ai_reasoning: p.ai_reasoning || `Clasificado por Laya System 1: ${priPct}% ${p.primary_category || p.category_id}${hasSec ? ` + ${secPct}% ${sec.id}` : ''}.`
    };
  }

  // Exposición en namespace global
  window.ROOT_FAMILIES = ROOT_FAMILIES;
  window.CATEGORY_COLOR_MAP = CATEGORY_COLOR_MAP;
  window.CATEGORIES = CATEGORIES;
  window.SAMPLE_MEDIA_ASSETS = SAMPLE_MEDIA_ASSETS;
  window.HOOK_PATTERNS = HOOK_PATTERNS;
  window.formatNumberK = formatNumberK;
  window.getTileColorClass = getTileColorClass;
  window.isPostAnomaly = isPostAnomaly;
  window.buildRealisticScannedDataset = buildRealisticScannedDataset;
  window.syncTaxonomyAndPostsWithBackend = syncTaxonomyAndPostsWithBackend;
  window.formatAppPost = formatAppPost;

})(window);
