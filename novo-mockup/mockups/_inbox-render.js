// Render do Inbox — sidebar + main + drawer.
const STATUS_LABEL = {
  aguardando: { label: 'aguardando', cls: 'pill-d7-pendente' },
  extraido:   { label: 'extraído',   cls: 'pill-d7-graduado' },
  falhou:     { label: 'falhou',     cls: 'pill-humano-rejeitado' },
  duplicado:  { label: 'pulado-duplicado', cls: 'pill-d7-calibracao' },
};

montarShell({
  clusterAtivo: 'inbox',
  abaAtiva: 'inbox',
  breadcrumb: ['Ouroboros', 'Inbox'],
  acoes: [
    { label: 'Abrir pasta', icon: 'folder', onClick: "toast('Abrindo ~/Ouroboros/inbox no Finder')" },
    { label: 'Atualizar fila', icon: 'refresh', primary: true, onClick: "toast('Verificando inbox...'); setTimeout(()=>toast('3 novos arquivos detectados'),1200)" },
  ],
});

function _filaLinha(item, novo) {
  const st = STATUS_LABEL[item.status];
  return `
    <tr class="${novo ? 'row-novo' : ''}" data-sha="${item.sha8}">
      <td class="thumb-cell"><div class="fila-thumb">${glyph(item.tipo, 18)}</div></td>
      <td>${item.filename}<br><span style="font-size:11px;color:var(--text-muted);">${item.tipoArquivo}</span></td>
      <td class="col-num">${item.tamanho}</td>
      <td class="col-mono" style="color:var(--text-secondary);">${item.sha8}</td>
      <td><span class="pill ${st.cls}">${st.label}</span></td>
      <td class="col-mono" style="color:var(--text-muted);">${item.data}</td>
      <td>
        <button class="btn btn-sm btn-ghost" onclick="abrirDrawer('${item.sha8}')">${glyph('expand',12)} sidecar</button>
      </td>
    </tr>`;
}

const total       = INBOX_FILA.length;
const aguardando  = INBOX_FILA.filter(i => i.status==='aguardando').length;
const extraido    = INBOX_FILA.filter(i => i.status==='extraido').length;
const falhou      = INBOX_FILA.filter(i => i.status==='falhou').length;
const duplicado   = INBOX_FILA.filter(i => i.status==='duplicado').length;

document.getElementById('main-root').innerHTML = `
  <div class="page-header">
    <div>
      <h1 class="page-title">INBOX</h1>
      <p class="page-subtitle">Entrada de dados. Arquivos chegam aqui antes de serem extraídos pelo pipeline agentic. <strong style="color:var(--accent-purple);">${aguardando}</strong> arquivo${aguardando===1?'':'s'} aguardando extração.</p>
    </div>
    <div class="page-meta">
      <span class="sprint-tag">Cluster novo</span>
      <span class="pill pill-d7-calibracao">Em calibração</span>
    </div>
  </div>

  <div class="barra-status">
    <div class="status-tile aguardando"><div class="v">${aguardando}</div><div class="l">Aguardando</div></div>
    <div class="status-tile extraido"><div class="v">${extraido}</div><div class="l">Extraído</div></div>
    <div class="status-tile duplicado"><div class="v">${duplicado}</div><div class="l">Pulado (duplicado)</div></div>
    <div class="status-tile falhou"><div class="v">${falhou}</div><div class="l">Falhou</div></div>
    <div class="status-tile" style="flex:0 0 200px;"><div class="v" style="color:var(--text-primary);">${total}</div><div class="l">Total na fila</div></div>
  </div>

  <div class="dropzone" id="dropzone">
    <div class="dropzone-glyph">${glyph('upload', 48)}</div>
    <h3>Arraste arquivos aqui ou clique para escolher</h3>
    <p>Aceita extratos bancários, faturas, recibos, cupons, notas, comprovantes. Cada arquivo é registrado pelo sha8 — duplicados são detectados antes da extração.</p>
    <div class="tipos">
      ${INBOX_TIPOS_SUPORTADOS.map(t => `<span class="tipo-chip">${t}</span>`).join('')}
    </div>
  </div>

  <div class="card" style="margin-top:var(--sp-4);padding:0;">
    <div class="fila-head" style="padding:var(--sp-4) var(--sp-4) var(--sp-3);">
      <h2>Fila</h2>
      <div style="display:flex;gap:var(--sp-2);">
        <button class="btn btn-sm">${glyph('filter',14)} Filtros</button>
        <button class="btn btn-sm btn-ghost">${glyph('hash',14)} agrupar por sha8</button>
      </div>
    </div>
    <div style="overflow:auto;max-height:380px;">
      <table class="table">
        <thead><tr>
          <th></th><th>Arquivo</th><th class="col-num">Tamanho</th><th>sha8</th>
          <th>Status</th><th>Registrado</th><th>Ações</th>
        </tr></thead>
        <tbody>
          ${INBOX_FILA.map((it, i) => _filaLinha(it, i < 2)).join('')}
        </tbody>
      </table>
    </div>
  </div>

  <div class="skill-instr" style="margin-top:var(--sp-4);">
    <h4>Para extrair os arquivos pendentes</h4>
    <ol>
      <li>Abra o Claude Code CLI no terminal, na raiz do projeto.</li>
      <li>Digite: <code>/validar-arquivo</code></li>
      <li>Volte aqui — a fila atualiza sozinha.</li>
    </ol>
    <div class="why">
      Por que terminal? <strong>ADR-13</strong> — paradigma agentic-first. A sessão de IA é parte do pipeline, não cliente externo dele. Sem custo de API, sem cron, humano-no-loop deliberado.
    </div>
  </div>

  <div id="drawer-mount"></div>
`;
hidratarGlyphs(document.getElementById('main-root'));

// Drawer
function abrirDrawer(sha) {
  const mount = document.getElementById('drawer-mount');
  mount.innerHTML = `
    <div class="drawer-overlay" onclick="fecharDrawer()"></div>
    <aside class="drawer" role="dialog" aria-label="Sidecar do arquivo">
      <div class="drawer-head">
        <div>
          <div style="font-family:var(--ff-mono);font-size:var(--fs-11);letter-spacing:.06em;text-transform:uppercase;color:var(--text-muted);">Sidecar</div>
          <div style="font-family:var(--ff-mono);font-size:var(--fs-16);">${sha}</div>
        </div>
        <button class="btn btn-icon btn-ghost" onclick="fecharDrawer()">${glyph('close',14)}</button>
      </div>
      <div class="drawer-tabs" role="tablist">
        <button class="drawer-tab active" data-t="json">JSON sidecar</button>
        <button class="drawer-tab" data-t="legacy">vs. legacy</button>
        <button class="drawer-tab" data-t="hist">Histórico</button>
      </div>
      <div class="drawer-body">
        <pre style="margin:0;font-family:var(--ff-mono);font-size:12px;line-height:1.55;color:var(--text-secondary);white-space:pre-wrap;">${syntax(JSON.stringify(INBOX_SIDECAR, null, 2))}</pre>
      </div>
    </aside>`;
}
function fecharDrawer() { document.getElementById('drawer-mount').innerHTML = ''; }
function syntax(s) {
  return s
    .replace(/("[^"]+")(\s*:)/g, '<span style="color:var(--syn-key);">$1</span>$2')
    .replace(/:\s*("[^"]*")/g, ': <span style="color:var(--syn-string);">$1</span>')
    .replace(/:\s*(-?\d+\.?\d*)/g, ': <span style="color:var(--syn-number);">$1</span>')
    .replace(/:\s*(true|false)/g, ': <span style="color:var(--syn-bool);">$1</span>');
}

// Drag-drop simulado (sem upload real)
const dz = document.getElementById('dropzone');
['dragenter','dragover'].forEach(ev => dz.addEventListener(ev, e => { e.preventDefault(); dz.classList.add('over'); }));
['dragleave','drop'].forEach(ev => dz.addEventListener(ev, e => { e.preventDefault(); dz.classList.remove('over'); }));
