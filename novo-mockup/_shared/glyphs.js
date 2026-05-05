/* Ouroboros — glyphs custom desenhados (não-Lucide).
   Estética mono-linha 1.5px, traço quadrado, viewBox 24x24.
   Uso: glyph('inbox', 16) → string SVG. */

const OUROBOROS_GLYPHS = {
  // Brand
  ouroboros: '<circle cx="12" cy="12" r="7" fill="none"/><path d="M5.5 9.5 L4 8 L6 7"/><path d="M18.5 14.5 L20 16 L18 17"/>',
  // Cluster
  inbox:    '<path d="M3 13v5a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-5"/><path d="M3 13l3-8h12l3 8"/><path d="M3 13h5l1 3h6l1-3h5"/>',
  home:     '<path d="M4 11l8-7 8 7v9a1 1 0 0 1-1 1h-4v-7h-6v7H5a1 1 0 0 1-1-1z"/>',
  docs:     '<path d="M6 3h9l4 4v14H6z"/><path d="M14 3v5h5"/><path d="M9 13h7M9 17h7"/>',
  analise:  '<path d="M3 20h18"/><path d="M5 20V8M10 20V4M15 20V11M20 20V6"/>',
  metas:    '<circle cx="12" cy="12" r="8" fill="none"/><circle cx="12" cy="12" r="4" fill="none"/><circle cx="12" cy="12" r="1" fill="currentColor"/>',
  financas: '<path d="M3 20V8l4-3 5 3 5-3 4 3v12z"/><path d="M3 13h18M9 8v12M15 8v12"/>',
  // Ações
  search:   '<circle cx="11" cy="11" r="6" fill="none"/><path d="m20 20-4.35-4.35"/>',
  upload:   '<path d="M12 16V4M7 9l5-5 5 5"/><path d="M4 18v2h16v-2"/>',
  download: '<path d="M12 4v12M7 11l5 5 5-5"/><path d="M4 18v2h16v-2"/>',
  diff:     '<path d="M9 4v16M15 4v16"/><path d="M5 8h4M5 16h4M15 8h4M15 16h4"/>',
  validar:  '<path d="m4 12 5 5 11-11"/>',
  rejeitar: '<path d="M5 5l14 14M19 5 5 19"/>',
  revisar:  '<circle cx="12" cy="12" r="8" fill="none"/><path d="M12 8v4M12 16h.01"/>',
  drag:     '<circle cx="9" cy="6" r="1" fill="currentColor"/><circle cx="15" cy="6" r="1" fill="currentColor"/><circle cx="9" cy="12" r="1" fill="currentColor"/><circle cx="15" cy="12" r="1" fill="currentColor"/><circle cx="9" cy="18" r="1" fill="currentColor"/><circle cx="15" cy="18" r="1" fill="currentColor"/>',
  more:     '<circle cx="6" cy="12" r="1" fill="currentColor"/><circle cx="12" cy="12" r="1" fill="currentColor"/><circle cx="18" cy="12" r="1" fill="currentColor"/>',
  filter:   '<path d="M4 5h16l-6 8v6l-4 2v-8z"/>',
  expand:   '<path d="M9 6l6 6-6 6"/>',
  collapse: '<path d="M6 9l6 6 6-6"/>',
  close:    '<path d="M6 6l12 12M18 6 6 18"/>',
  terminal: '<rect x="3" y="5" width="18" height="14" rx="1" fill="none"/><path d="M7 10l3 2-3 2M13 14h4"/>',
  folder:   '<path d="M3 6a1 1 0 0 1 1-1h5l2 2h8a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z"/>',
  refresh: '<path d="M4 4v5h5M20 20v-5h-5"/><path d="M5 9a8 8 0 0 1 14-2M19 15a8 8 0 0 1-14 2"/>',
  link:     '<path d="M10 14a4 4 0 0 0 5.66 0l3-3a4 4 0 0 0-5.66-5.66l-1 1"/><path d="M14 10a4 4 0 0 0-5.66 0l-3 3a4 4 0 0 0 5.66 5.66l1-1"/>',
  warn:     '<path d="m12 3 10 18H2z" fill="none"/><path d="M12 10v5M12 18h.01"/>',
  info:     '<circle cx="12" cy="12" r="8" fill="none"/><path d="M12 8h.01M11 12h1v5h1"/>',
  check:    '<path d="m4 12 5 5 11-11"/>',
  clock:    '<circle cx="12" cy="12" r="8" fill="none"/><path d="M12 7v5l3 2"/>',
  hash:     '<path d="M5 9h14M5 15h14M9 4 7 20M17 4l-2 16"/>',
  sigma:    '<path d="M6 4h12l-7 8 7 8H6"/>',
  // Tipos de documento (thumbnails)
  pdf:      '<rect x="4" y="3" width="16" height="18" rx="1" fill="none"/><text x="12" y="15" font-size="6" font-family="JetBrains Mono" font-weight="700" fill="currentColor" text-anchor="middle">PDF</text>',
  csv:      '<rect x="4" y="3" width="16" height="18" rx="1" fill="none"/><text x="12" y="15" font-size="6" font-family="JetBrains Mono" font-weight="700" fill="currentColor" text-anchor="middle">CSV</text>',
  xlsx:     '<rect x="4" y="3" width="16" height="18" rx="1" fill="none"/><text x="12" y="15" font-size="5" font-family="JetBrains Mono" font-weight="700" fill="currentColor" text-anchor="middle">XLS</text>',
  ofx:      '<rect x="4" y="3" width="16" height="18" rx="1" fill="none"/><text x="12" y="15" font-size="6" font-family="JetBrains Mono" font-weight="700" fill="currentColor" text-anchor="middle">OFX</text>',
  img:      '<rect x="3" y="5" width="18" height="14" rx="1" fill="none"/><circle cx="9" cy="10" r="1.5" fill="currentColor"/><path d="m3 17 5-5 4 4 3-3 6 6"/>',
  json:     '<rect x="4" y="3" width="16" height="18" rx="1" fill="none"/><path d="M9 7c-1 0-2 1-2 2v2c0 .5-.5 1-1 1 .5 0 1 .5 1 1v2c0 1 1 2 2 2"/><path d="M15 7c1 0 2 1 2 2v2c0 .5.5 1 1 1-.5 0-1 .5-1 1v2c0 1-1 2-2 2"/>',
  // Adicionados — extração tripla
  table:      '<rect x="3" y="4" width="18" height="16" rx="1" fill="none"/><path d="M3 9h18M3 14h18M9 4v16M15 4v16"/>',
  user:       '<circle cx="12" cy="8" r="3.5" fill="none"/><path d="M5 20c1-3.5 4-5 7-5s6 1.5 7 5"/>',
  sparkle:    '<path d="M12 4v6M12 14v6M4 12h6M14 12h6"/><path d="m7 7 3 3M14 14l3 3M7 17l3-3M14 10l3-3"/>',
  cog:        '<circle cx="12" cy="12" r="3" fill="none"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M19 5l-2 2M5 19l2-2"/>',
  eye:        '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z" fill="none"/><circle cx="12" cy="12" r="3" fill="none"/>',
  'arrow-left':  '<path d="M19 12H5M11 6l-6 6 6 6"/>',
  'arrow-right': '<path d="M5 12h14M13 6l6 6-6 6"/>',
  warning:    '<path d="m12 3 10 18H2z" fill="none"/><path d="M12 10v5M12 18h.01"/>',
  // Adicionados — cluster Bem-estar
  heart:      '<path d="M12 20s-7-4.5-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.5-7 10-7 10z" fill="none"/>',
  calendar:   '<rect x="3" y="5" width="18" height="16" rx="1" fill="none"/><path d="M3 10h18M8 3v4M16 3v4"/>',
  alarm:      '<circle cx="12" cy="13" r="7" fill="none"/><path d="M12 9v4l2 2M5 4l3 3M19 4l-3 3"/>',
  list:       '<path d="M4 6h16M4 12h16M4 18h16"/><circle cx="2" cy="6" r="0.5" fill="currentColor"/><circle cx="2" cy="12" r="0.5" fill="currentColor"/><circle cx="2" cy="18" r="0.5" fill="currentColor"/>',
  repeat:     '<path d="M17 3l3 3-3 3"/><path d="M3 12V9a3 3 0 0 1 3-3h14"/><path d="M7 21l-3-3 3-3"/><path d="M21 12v3a3 3 0 0 1-3 3H4"/>',
  plus:       '<path d="M12 5v14M5 12h14"/>',
  mood:       '<circle cx="12" cy="12" r="8" fill="none"/><circle cx="9" cy="10" r="0.5" fill="currentColor"/><circle cx="15" cy="10" r="0.5" fill="currentColor"/><path d="M8 14c1 1.5 2.5 2.5 4 2.5s3-1 4-2.5"/>',
  trend:      '<path d="M3 17l6-6 4 4 8-8"/><path d="M14 7h7v7"/>',
  trash:      '<path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"/>',
  cycle:      '<circle cx="12" cy="12" r="8" fill="none"/><path d="M12 4v8l5 3"/><path d="M4 8l3 1M20 8l-3 1M4 16l3-1M20 16l-3-1"/>',
};

/**
 * Renderiza glyph como string SVG.
 * @param {string} nome - chave em OUROBOROS_GLYPHS
 * @param {number} tamanho - lado em px (default 16)
 * @param {string} classes - classes CSS extras
 */
function glyph(nome, tamanho = 16, classes = '') {
  const conteudo = OUROBOROS_GLYPHS[nome] || '';
  return `<svg class="glyph ${classes}" width="${tamanho}" height="${tamanho}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="square" stroke-linejoin="miter">${conteudo}</svg>`;
}

// Auto-substitui <i data-glyph="nome" data-size="16"></i> por SVG inline.
function hidratarGlyphs(raiz = document) {
  raiz.querySelectorAll('i[data-glyph]').forEach((el) => {
    const nome = el.getAttribute('data-glyph');
    const tamanho = parseInt(el.getAttribute('data-size') || '16', 10);
    el.outerHTML = glyph(nome, tamanho, el.className || '');
  });
}

if (typeof document !== 'undefined') {
  document.addEventListener('DOMContentLoaded', () => hidratarGlyphs());
}
