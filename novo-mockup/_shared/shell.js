/* Ouroboros — shell (sidebar + topbar) renderizado por JS.
   Cada mockup chama montarShell({clusterAtivo, abaAtiva, breadcrumb}). */

const CLUSTERS_OUROBOROS = [
  {
    id: 'inbox',
    nome: 'Inbox',
    glyph: 'inbox',
    badge: '3',
    abas: [
      { id: 'inbox', nome: 'Inbox', file: '16-inbox.html' },
    ],
  },
  {
    id: 'home',
    nome: 'Home',
    glyph: 'home',
    abas: [
      { id: 'visao-geral', nome: 'Visão Geral', file: '01-visao-geral.html' },
      { id: 'home-financas', nome: 'Finanças', file: '02-extrato.html' },
      { id: 'home-documentos', nome: 'Documentos', file: '06-busca-global.html' },
      { id: 'home-analise', nome: 'Análise', file: '12-analise.html' },
      { id: 'home-metas', nome: 'Metas', file: '13-metas.html' },
    ],
  },
  {
    id: 'financas',
    nome: 'Finanças',
    glyph: 'financas',
    abas: [
      { id: 'extrato', nome: 'Extrato', file: '02-extrato.html' },
      { id: 'contas', nome: 'Contas', file: '03-contas.html' },
      { id: 'pagamentos', nome: 'Pagamentos', file: '04-pagamentos.html' },
      { id: 'projecoes', nome: 'Projeções', file: '05-projecoes.html' },
    ],
  },
  {
    id: 'documentos',
    nome: 'Documentos',
    glyph: 'docs',
    abas: [
      { id: 'busca-global', nome: 'Busca Global', file: '06-busca-global.html' },
      { id: 'catalogacao', nome: 'Catalogação', file: '07-catalogacao.html' },
      { id: 'completude', nome: 'Completude', file: '08-completude.html' },
      { id: 'revisor', nome: 'Revisor', file: '09-revisor.html' },
      { id: 'validacao-arquivos', nome: 'Validação por Arquivo', file: '10-validacao-arquivos.html' },
      { id: 'grafo-obsidian', nome: 'Grafo + Obsidian', file: '06-busca-global.html' },
    ],
  },
  {
    id: 'analise',
    nome: 'Análise',
    glyph: 'analise',
    abas: [
      { id: 'categorias', nome: 'Categorias', file: '11-categorias.html' },
      { id: 'analise', nome: 'Análise', file: '12-analise.html' },
      { id: 'irpf', nome: 'IRPF', file: '15-irpf.html' },
    ],
  },
  {
    id: 'metas',
    nome: 'Metas',
    glyph: 'metas',
    abas: [
      { id: 'metas', nome: 'Metas', file: '13-metas.html' },
    ],
  },
  {
    id: 'bem-estar',
    nome: 'Bem-estar',
    glyph: 'heart',
    abas: [
      { id: 'be-hoje',     nome: 'Hoje',             file: '17-bem-estar-hoje.html' },
      { id: 'be-humor',    nome: 'Humor',            file: '18-humor-heatmap.html' },
      { id: 'be-diario',   nome: 'Diário emocional', file: '19-diario-emocional.html' },
      { id: 'be-rotina',   nome: 'Rotina',           file: '20-rotina.html' },
      { id: 'be-recap',    nome: 'Recap',            file: '21-recap.html' },
      { id: 'be-eventos',  nome: 'Eventos',          file: '22-eventos.html' },
      { id: 'be-memorias', nome: 'Memórias',         file: '23-memorias.html' },
      { id: 'be-medidas',  nome: 'Medidas',          file: '24-medidas.html' },
      { id: 'be-ciclo',    nome: 'Ciclo',            file: '25-ciclo.html' },
      { id: 'be-cruzamentos', nome: 'Cruzamentos',   file: '26-cruzamentos.html' },
      { id: 'be-privacidade', nome: 'Privacidade A↔B', file: '27-privacidade.html' },
      { id: 'be-rotina-toml', nome: 'Editor rotina.toml', file: '28-rotina-toml.html' },
    ],
  },
  {
    id: 'sistema',
    nome: 'Sistema',
    glyph: 'terminal',
    abas: [
      { id: 'skills-d7', nome: 'Skills D7', file: '14-skills-d7.html' },
      { id: 'styleguide', nome: 'Styleguide', file: '../styleguide.html' },
      { id: 'indice', nome: 'Índice', file: '../index.html' },
    ],
  },
];

function _resolveHref(file) {
  // Detecta se estamos em /mockups/ ou na raiz, e ajusta o prefixo.
  const naRaiz = !window.location.pathname.includes('/mockups/');
  if (file.startsWith('../')) {
    // file aponta para raiz a partir de mockups/
    return naRaiz ? './' + file.slice(3) : file;
  }
  // file é um mockup (ex: '14-skills-d7.html')
  return naRaiz ? './mockups/' + file : './' + file;
}

function _sidebarHTML(clusterAtivo, abaAtiva) {
  const clusters = CLUSTERS_OUROBOROS.map((c) => {
    const itens = c.abas.map((a) => {
      const ativa = (c.id === clusterAtivo && a.id === abaAtiva);
      const href = a.file ? _resolveHref(a.file) : '#';
      const cls = ativa ? 'sidebar-item active' : 'sidebar-item';
      const semMockup = !a.file ? '<span class="count" title="ainda não modelada">·</span>' : '';
      return `<a class="${cls}" href="${href}" data-aba="${a.id}">${a.nome}${semMockup}</a>`;
    }).join('');
    const badge = c.badge ? `<span class="badge">${c.badge}</span>` : '';
    return `
      <div class="sidebar-cluster">
        <div class="sidebar-cluster-header">
          <span style="display:inline-flex;align-items:center;gap:8px;">
            ${glyph(c.glyph, 14)} ${c.nome}
          </span>
          ${badge}
        </div>
        ${itens}
      </div>`;
  }).join('');

  return `
    <aside class="sidebar" aria-label="Navegação">
      <a class="sidebar-brand" href="${_resolveHref('../index.html')}" style="text-decoration:none;color:inherit;">
        ${glyph('ouroboros', 18)}
        <span>Ouroboros</span>
      </a>
      <div class="sidebar-search">
        ${glyph('search', 14, 'sidebar-search-icon')}
        <input type="text" placeholder="Buscar fornecedor, sha8, valor..." aria-label="Buscar">
        <kbd>/</kbd>
      </div>
      ${clusters}
      <div style="margin-top:auto;padding:12px 16px;border-top:1px solid var(--border-subtle);font-size:11px;color:var(--text-muted);font-family:var(--ff-mono);">
        <div>D7 · cobertura observável</div>
      </div>
    </aside>`;
}

function _topbarHTML(breadcrumb, acoes) {
  const segs = breadcrumb.map((s, i) => {
    const last = i === breadcrumb.length - 1;
    const cls = last ? 'seg current' : 'seg';
    const sep = last ? '' : '<span class="sep">/</span>';
    // primeiro segmento ("Ouroboros") leva ao índice
    if (i === 0 && !last) {
      return `<a class="${cls}" href="${_resolveHref('../index.html')}" style="text-decoration:none;color:inherit;">${s}</a>${sep}`;
    }
    return `<span class="${cls}">${s}</span>${sep}`;
  }).join('');
  const acoesHTML = (acoes || []).map((a) => {
    const cls = a.primary ? 'btn btn-primary btn-sm' : 'btn btn-sm';
    const inner = `${a.icon ? glyph(a.icon, 14) : ''} ${a.label}`;
    if (a.href) {
      const href = a.href.endsWith('.html') ? _resolveHref(a.href) : a.href;
      return `<a class="${cls}" href="${href}" style="text-decoration:none;display:inline-flex;align-items:center;gap:6px;">${inner}</a>`;
    }
    if (a.onClick) {
      return `<button class="${cls}" onclick="${a.onClick}">${inner}</button>`;
    }
    return `<button class="${cls}">${inner}</button>`;
  }).join('');
  return `
    <header class="topbar">
      <nav class="breadcrumb" aria-label="Localização">${segs}</nav>
      <div class="topbar-actions">${acoesHTML}</div>
    </header>`;
}

/**
 * Monta sidebar + topbar dentro de um <div id="shell-root"> e devolve <main>.
 * @param {Object} opts
 * @param {string} opts.clusterAtivo - id do cluster
 * @param {string} opts.abaAtiva - id da aba
 * @param {string[]} opts.breadcrumb - segmentos
 * @param {Array} opts.acoes - [{label, icon, primary}]
 */
function montarShell(opts) {
  const root = document.getElementById('shell-root');
  if (!root) return;
  root.classList.add('shell');
  root.innerHTML =
    _sidebarHTML(opts.clusterAtivo, opts.abaAtiva) +
    _topbarHTML(opts.breadcrumb, opts.acoes) +
    '<main class="main" id="main-root"></main>';
  // Atalhos de teclado: g h, g i, g v, g r, g f, /, ?
  _instalarAtalhos();
}

function _instalarAtalhos() {
  let buffer = '';
  let timer = null;
  const mapa = {
    'gh': _resolveHref('01-visao-geral.html'),
    'gi': _resolveHref('16-inbox.html'),
    'gv': _resolveHref('10-validacao-arquivos.html'),
    'gr': _resolveHref('09-revisor.html'),
    'gf': _resolveHref('15-irpf.html'),
    'gc': _resolveHref('07-catalogacao.html'),
  };
  document.addEventListener('keydown', (e) => {
    if (e.target.matches('input, textarea')) return;
    if (e.key === '/') {
      e.preventDefault();
      const inp = document.querySelector('.sidebar-search input');
      if (inp) inp.focus();
      return;
    }
    if (e.key === '?') {
      _toggleAjuda();
      return;
    }
    if (e.key === 'Escape') {
      const overlay = document.getElementById('ajuda-overlay');
      if (overlay) overlay.remove();
      return;
    }
    buffer += e.key.toLowerCase();
    clearTimeout(timer);
    timer = setTimeout(() => { buffer = ''; }, 800);
    if (mapa[buffer]) {
      const dest = mapa[buffer];
      buffer = '';
      window.location.href = dest;
    }
  });
}

/* Toast — feedback simples para ações sem backend.
   Uso: toast('Mensagem'); ou toast('Erro', 'error'); */
function toast(msg, tipo = 'ok') {
  let host = document.getElementById('toast-host');
  if (!host) {
    host = document.createElement('div');
    host.id = 'toast-host';
    host.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:80;display:flex;flex-direction:column;gap:8px;pointer-events:none;';
    document.body.appendChild(host);
  }
  const cor = tipo === 'error' ? 'var(--accent-red)' : tipo === 'warn' ? 'var(--accent-yellow)' : 'var(--accent-purple)';
  const t = document.createElement('div');
  t.style.cssText = `pointer-events:auto;background:var(--bg-elevated);border:1px solid var(--border-subtle);border-left:3px solid ${cor};border-radius:var(--r-sm);padding:10px 14px;font-family:var(--ff-mono);font-size:12px;color:var(--text-primary);box-shadow:0 8px 24px rgba(0,0,0,0.4);min-width:240px;opacity:0;transform:translateX(20px);transition:opacity .2s,transform .2s;`;
  t.textContent = msg;
  host.appendChild(t);
  requestAnimationFrame(() => { t.style.opacity = '1'; t.style.transform = 'translateX(0)'; });
  setTimeout(() => { t.style.opacity = '0'; t.style.transform = 'translateX(20px)'; setTimeout(() => t.remove(), 250); }, 2400);
}

function _toggleAjuda() {
  const existente = document.getElementById('ajuda-overlay');
  if (existente) { existente.remove(); return; }
  const ov = document.createElement('div');
  ov.id = 'ajuda-overlay';
  ov.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.7);z-index:60;display:grid;place-items:center;';
  ov.innerHTML = `
    <div class="card" style="min-width:480px;max-width:560px;">
      <div class="card-head">
        <h3 class="card-title">Atalhos de teclado</h3>
        <button class="btn btn-icon btn-ghost" onclick="document.getElementById('ajuda-overlay').remove()">${glyph('close',14)}</button>
      </div>
      <table style="width:100%;font-size:13px;">
        <tr><td style="padding:6px 0;"><kbd class="kbd">g h</kbd></td><td>Visão Geral</td></tr>
        <tr><td style="padding:6px 0;"><kbd class="kbd">g i</kbd></td><td>Inbox</td></tr>
        <tr><td style="padding:6px 0;"><kbd class="kbd">g v</kbd></td><td>Validação por Arquivo</td></tr>
        <tr><td style="padding:6px 0;"><kbd class="kbd">g r</kbd></td><td>Revisor</td></tr>
        <tr><td style="padding:6px 0;"><kbd class="kbd">g f</kbd></td><td>IRPF</td></tr>
        <tr><td style="padding:6px 0;"><kbd class="kbd">g c</kbd></td><td>Catalogação</td></tr>
        <tr><td style="padding:6px 0;"><kbd class="kbd">/</kbd></td><td>Focar busca</td></tr>
        <tr><td style="padding:6px 0;"><kbd class="kbd">?</kbd></td><td>Esta ajuda</td></tr>
        <tr><td style="padding:6px 0;"><kbd class="kbd">Esc</kbd></td><td>Fechar overlay</td></tr>
      </table>
    </div>`;
  document.body.appendChild(ov);
  ov.addEventListener('click', (e) => { if (e.target === ov) ov.remove(); });
}
