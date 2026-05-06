// Render — Extração Tripla (substitui _validacao-render.js).
// Lista esquerda de arquivos por formato → seleção → 3 tabelas centrais.

montarShell({
  clusterAtivo: 'documentos',
  abaAtiva: 'validacao-arquivos',
  breadcrumb: ['Ouroboros', 'Documentos', 'Extração Tripla'],
  acoes: [
    { label: 'Baixar lote', icon: 'download', onClick: "toast('Lote ZIP em fila · 10 arquivos')" },
    { label: 'Salvar validações', icon: 'check', primary: true, onClick: "toast('Flags humanas registradas · 3 arquivos atualizados')" },
  ],
});

// Estado em memória — edits do user persistem na sessão.
const EXTRACAO_USER_EDITS = {}; // { [arqId]: { [campo]: valor } }

function inicializarEditsUser() {
  for (const a of EXTRACAO_ARQUIVOS) {
    const dados = EXTRACAO_DADOS[a.id];
    if (!dados) continue;
    EXTRACAO_USER_EDITS[a.id] = {};
    for (const c of dados.campos) {
      // pré-preenche com consenso
      EXTRACAO_USER_EDITS[a.id][c.campo] = valorConsenso(c);
    }
  }
}
inicializarEditsUser();

let arquivoSelecionado = EXTRACAO_DEFAULT;

// ────────── ZONA A: lista de arquivos agrupada por formato ──────────
function renderListaArquivos() {
  const grupos = arquivosPorFormato();
  const ordem = ['pdf', 'imagem', 'csv', 'xlsx', 'ofx', 'html'];
  const html = ordem.filter(f => grupos[f]).map(f => {
    const meta = EXTRACAO_TIPOS_LABEL[f];
    const itens = grupos[f].map(a => {
      const ativo = a.id === arquivoSelecionado;
      const stats = estatisticasArquivo(a.id);
      const paridadeCor = stats.paridade >= 0.9 ? 'var(--d7-graduado)'
                       : stats.paridade >= 0.7 ? 'var(--d7-calibracao)'
                       : 'var(--d7-regredindo)';
      const flag = a.status_humano === 'aprovado'   ? 'var(--humano-aprovado)'
                 : a.status_humano === 'em_revisao' ? 'var(--humano-revisar)'
                 : 'var(--humano-pendente)';
      return `
        <div class="arq-item ${ativo ? 'sel' : ''}"
             onclick="selecionarArquivo('${a.id}')"
             title="${a.filename}">
          <div class="arq-top">
            <div class="arq-flag" style="background:${flag};" title="status humano: ${a.status_humano}"></div>
            <div class="arq-name">${a.filename}</div>
            <button class="arq-dl"
                    title="Baixar original (${bytesHumano(a.bytes)})"
                    onclick="event.stopPropagation();baixar('${a.id}');">
              ${glyph('download', 12)}
            </button>
          </div>
          <div class="arq-meta">
            <span class="arq-tipo">${a.tipo_arquivo}</span>
            <span class="arq-paridade" style="color:${paridadeCor};">
              ${Math.round(stats.paridade * 100)}% ok
            </span>
            <span class="arq-bytes">${bytesHumano(a.bytes)}</span>
          </div>
        </div>`;
    }).join('');
    return `
      <div class="arq-grupo">
        <div class="arq-grupo-head" style="--cor:${meta.cor};">
          ${glyph(meta.icon, 12)}
          <span>${meta.rotulo}</span>
          <span class="arq-grupo-count">${grupos[f].length}</span>
        </div>
        <div class="arq-grupo-body">${itens}</div>
      </div>`;
  }).join('');

  document.getElementById('lista-arquivos').innerHTML = html;
  hidratarGlyphs(document.getElementById('lista-arquivos'));
}

// ────────── ZONA B: cabeçalho do arquivo selecionado ──────────
function renderCabecalho(a) {
  const meta = EXTRACAO_TIPOS_LABEL[a.formato];
  const stats = estatisticasArquivo(a.id);
  const paridadeCor = stats.paridade >= 0.9 ? 'var(--d7-graduado)'
                   : stats.paridade >= 0.7 ? 'var(--d7-calibracao)'
                   : 'var(--d7-regredindo)';
  const statusPill = a.status_humano === 'aprovado'
    ? '<span class="pill pill-humano-aprovado">aprovado</span>'
    : a.status_humano === 'em_revisao'
    ? '<span class="pill pill-humano-revisar">em revisão</span>'
    : '<span class="pill pill-humano-pendente">aguarda humano</span>';

  return `
    <div class="cab-arq">
      <div class="cab-icone" style="--cor:${meta.cor};">${glyph(meta.icon, 22)}</div>
      <div class="cab-info">
        <div class="cab-titulo">
          <span class="cab-fname">${a.filename}</span>
          <span class="cab-sha">${a.sha8}</span>
          ${statusPill}
        </div>
        <div class="cab-meta">
          <span><strong>tipo:</strong> ${a.tipo_arquivo}</span>
          <span><strong>processado:</strong> ${a.data_processado}</span>
          <span><strong>extrator ETL:</strong> ${a.fonte_etl}</span>
          ${a.paginas != null ? `<span><strong>páginas:</strong> ${a.paginas}</span>` : ''}
          <span><strong>bytes:</strong> ${bytesHumano(a.bytes)}</span>
        </div>
      </div>
      <div class="cab-stats">
        <div class="cab-stat">
          <div class="cab-stat-label">paridade</div>
          <div class="cab-stat-val" style="color:${paridadeCor};">${Math.round(stats.paridade * 100)}%</div>
        </div>
        <div class="cab-stat">
          <div class="cab-stat-label">divergências</div>
          <div class="cab-stat-val" style="color:${stats.divergente ? 'var(--accent-yellow)' : 'var(--text-muted)'};">${stats.divergente}</div>
        </div>
        <div class="cab-stat">
          <div class="cab-stat-label">unilaterais</div>
          <div class="cab-stat-val" style="color:${stats.apenas ? 'var(--accent-orange)' : 'var(--text-muted)'};">${stats.apenas}</div>
        </div>
      </div>
      <div class="cab-acoes">
        <button class="btn btn-sm" onclick="abrirPreview('${a.id}')">${glyph('eye', 14)} Ver original</button>
        <button class="btn btn-sm" onclick="baixar('${a.id}')">${glyph('download', 14)} Baixar</button>
        <button class="btn btn-sm btn-primary" onclick="enviarFlag('${a.id}')">${glyph('check', 14)} Enviar validação</button>
      </div>
    </div>`;
}

// ────────── ZONA B: 3 tabelas lado a lado ──────────
function renderTabelas(a) {
  const dados = EXTRACAO_DADOS[a.id];
  if (!dados) {
    return `<div style="padding:48px;text-align:center;color:var(--text-muted);font-family:var(--ff-mono);">sem dados extraídos para este arquivo</div>`;
  }

  const linhas = dados.campos.map((c, idx) => {
    const status = statusCampo(c);
    const editUser = EXTRACAO_USER_EDITS[a.id][c.campo] ?? '';
    const podeFlag = status !== 'ok';

    // Cor de fundo da linha por status
    const trCls = status === 'divergente' ? 'tr-div'
              : status === 'apenas_etl'  ? 'tr-uni-etl'
              : status === 'apenas_opus' ? 'tr-uni-opus'
              : 'tr-ok';

    // Confiança Opus
    const confCor = c.conf >= 0.85 ? 'var(--d7-graduado)'
                 : c.conf >= 0.65 ? 'var(--d7-calibracao)'
                 : 'var(--d7-regredindo)';

    // Marcador de qual fonte o user "abraçou"
    const userPreenchido = editUser !== '' && editUser != null;
    const userIgualEtl = userPreenchido && String(editUser) === String(c.etl);
    const userIgualOpus = userPreenchido && String(editUser) === String(c.opus);
    const userNovo = userPreenchido && !userIgualEtl && !userIgualOpus;

    return `
      <tr class="${trCls}">
        <td class="cel-campo" title="${c.obs || ''}">
          <div class="campo-nome">${c.campo}</div>
          ${c.obs ? `<div class="campo-obs">${glyph('info', 10)} ${c.obs}</div>` : ''}
        </td>
        <td class="cel-etl ${status === 'apenas_etl' ? 'cel-uni' : ''}">
          ${c.etl !== '' ? `<span class="val">${c.etl}</span>` : '<span class="vazio">—</span>'}
          ${userIgualEtl ? `<span class="adotado" title="user adotou ETL">${glyph('check', 10)}</span>` : ''}
        </td>
        <td class="cel-opus ${status === 'apenas_opus' ? 'cel-uni' : ''}">
          <span class="val">${c.opus !== '' ? c.opus : '<span class="vazio">—</span>'}</span>
          <span class="conf" style="color:${confCor};">${Math.round(c.conf * 100)}%</span>
          ${userIgualOpus ? `<span class="adotado" title="user adotou Opus">${glyph('check', 10)}</span>` : ''}
        </td>
        <td class="cel-user">
          <div class="user-celula">
            <input class="user-input ${podeFlag && !userPreenchido ? 'pendente' : ''} ${userNovo ? 'novo' : ''}"
                   type="text"
                   value="${editUser}"
                   placeholder="${podeFlag ? 'preencher…' : ''}"
                   data-arq="${a.id}" data-campo="${c.campo}"
                   oninput="atualizarUser(this)" />
            ${podeFlag ? `
              <div class="user-quick">
                ${c.etl !== '' ? `<button class="user-quick-btn" title="adotar ETL"
                  onclick="adotarValor('${a.id}','${c.campo}','etl')">←</button>` : ''}
                ${c.opus !== '' ? `<button class="user-quick-btn" title="adotar Opus"
                  onclick="adotarValor('${a.id}','${c.campo}','opus')">→</button>` : ''}
              </div>` : ''}
          </div>
        </td>
        <td class="cel-status">
          ${pillStatus(status)}
        </td>
      </tr>`;
  }).join('');

  return `
    <div class="tabelas-host">
      <table class="tabelas-tripla">
        <colgroup>
          <col class="col-campo">
          <col class="col-etl">
          <col class="col-opus">
          <col class="col-user">
          <col class="col-status">
        </colgroup>
        <thead>
          <tr>
            <th class="th-campo">Campo</th>
            <th class="th-etl">
              <div class="th-fonte">
                ${glyph('cog', 12)}
                <span>ETL determinístico</span>
              </div>
              <div class="th-fonte-sub">${a.fonte_etl}</div>
            </th>
            <th class="th-opus">
              <div class="th-fonte">
                ${glyph('sparkle', 12)}
                <span>Claude Opus agentic</span>
              </div>
              <div class="th-fonte-sub">opus_v1 · ${dados.campos.length} campos</div>
            </th>
            <th class="th-user">
              <div class="th-fonte">
                ${glyph('user', 12)}
                <span>Validação humana</span>
              </div>
              <div class="th-fonte-sub">consenso pré-preenchido · você resolve divergências</div>
            </th>
            <th class="th-status">Status</th>
          </tr>
        </thead>
        <tbody>${linhas}</tbody>
      </table>
    </div>`;
}

function pillStatus(s) {
  if (s === 'ok')           return '<span class="pill pill-humano-aprovado">consenso</span>';
  if (s === 'divergente')   return '<span class="pill pill-humano-rejeitado">divergente</span>';
  if (s === 'apenas_etl')   return '<span class="pill pill-d7-calibracao">só ETL</span>';
  if (s === 'apenas_opus')  return '<span class="pill pill-d7-calibracao">só Opus</span>';
  return '<span class="pill pill-humano-pendente">só humano</span>';
}

// ────────── Render principal ──────────
function renderPainelDireito() {
  const a = EXTRACAO_ARQUIVOS.find(x => x.id === arquivoSelecionado);
  document.getElementById('painel-arquivo').innerHTML =
    renderCabecalho(a) + renderTabelas(a);
  hidratarGlyphs(document.getElementById('painel-arquivo'));
}

// ────────── Interações ──────────
function selecionarArquivo(id) {
  arquivoSelecionado = id;
  renderListaArquivos();
  renderPainelDireito();
}
function atualizarUser(inp) {
  const arq = inp.dataset.arq, campo = inp.dataset.campo;
  EXTRACAO_USER_EDITS[arq][campo] = inp.value;
  // Re-render só a célula seria mais barato, mas para mockup re-renderiza tudo:
  // pequena atualização visual sem rerender pesado:
  inp.classList.toggle('pendente', !inp.value);
  // marcador de "novo" se diferente de etl/opus
  const dados = EXTRACAO_DADOS[arq];
  const c = dados.campos.find(x => x.campo === campo);
  const igualEtl = String(inp.value) === String(c.etl);
  const igualOpus = String(inp.value) === String(c.opus);
  inp.classList.toggle('novo', inp.value && !igualEtl && !igualOpus);
}
function adotarValor(arq, campo, fonte) {
  const dados = EXTRACAO_DADOS[arq];
  const c = dados.campos.find(x => x.campo === campo);
  const valor = fonte === 'etl' ? c.etl : c.opus;
  EXTRACAO_USER_EDITS[arq][campo] = valor;
  renderPainelDireito();
}
function baixar(id) {
  const a = EXTRACAO_ARQUIVOS.find(x => x.id === id);
  toast(`Baixando ${a.filename} (${bytesHumano(a.bytes)})`);
}
function abrirPreview(id) {
  const a = EXTRACAO_ARQUIVOS.find(x => x.id === id);
  toast(`Preview de ${a.filename} (mockup — backend faria render)`);
}
function enviarFlag(id) {
  const a = EXTRACAO_ARQUIVOS.find(x => x.id === id);
  const dados = EXTRACAO_DADOS[id];
  const stats = estatisticasArquivo(id);
  let preenchidos = 0;
  for (const c of dados.campos) {
    const v = EXTRACAO_USER_EDITS[id][c.campo];
    if (v !== '' && v != null) preenchidos++;
  }
  const cobertura = Math.round((preenchidos / dados.campos.length) * 100);
  toast(` Flag humana registrada · ${a.filename} · ${preenchidos}/${dados.campos.length} campos (${cobertura}%) · paridade ${Math.round(stats.paridade * 100)}%`);
  a.status_humano = cobertura === 100 ? 'aprovado' : 'em_revisao';
  renderListaArquivos();
  renderPainelDireito();
}

// ────────── Mount ──────────
document.getElementById('main-root').innerHTML = `
  <div class="page-header">
    <div>
      <h1 class="page-title">EXTRAÇÃO TRIPLA</h1>
      <p class="page-subtitle">Cada arquivo passa por dois extratores — script ETL determinístico e Claude Opus agentic.
      A tabela do <strong style="color:var(--accent-purple);">humano</strong> chega pré-preenchida com o consenso;
      você só edita as divergências e envia. Cada validação registra flag e alimenta o catálogo de hints.</p>
    </div>
    <div class="page-meta">
      <span class="sprint-tag">VALIDAÇÃO-CSV-01</span>
      <span class="pill pill-d7-calibracao">${EXTRACAO_ARQUIVOS.length} arquivos</span>
    </div>
  </div>

  <div class="extracao-layout">
    <aside class="extracao-lista" id="lista-arquivos"></aside>
    <section class="extracao-painel" id="painel-arquivo"></section>
  </div>
`;

renderListaArquivos();
renderPainelDireito();
