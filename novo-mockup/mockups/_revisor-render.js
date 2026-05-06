// Render do Revisor — 4-way + lista de transações.
montarShell({
  clusterAtivo: 'documentos',
  abaAtiva: 'revisor',
  breadcrumb: ['Ouroboros', 'Documentos', 'Revisor'],
  acoes: [
    { label: 'Próxima divergência', icon: 'expand', onClick: "toast('Pulando para próxima divergência (3 restantes)')" },
    { label: 'Aprovar Opus & avançar', icon: 'check', primary: true, onClick: "toast('Opus aprovado · transação #2847 catalogada'); setTimeout(()=>toast('Próxima: 142 transações pendentes','ok'),900)" },
  ],
});

// helpers
function estadoPill(e) {
  const map = {
    apurado:    { cls: 'pill-d7-graduado',    txt: 'apurado' },
    rascunho:   { cls: 'pill-d7-pendente',    txt: 'rascunho' },
    divergente: { cls: 'pill-humano-rejeitado', txt: 'divergente' },
  };
  const m = map[e] || map.rascunho;
  return `<span class="pill ${m.cls}">${m.txt}</span>`;
}

function moeda(v) {
  const sinal = v < 0 ? '-' : '+';
  const abs = Math.abs(v).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return `${sinal}R$ ${abs}`;
}

// Lista
const tlist = REVISOR_TRANSACOES.map(t => `
  <div class="t-row ${t.id === REVISOR_4WAY.id ? 'sel' : ''}">
    <span class="data">${t.data.slice(5)}</span>
    <span>${estadoPill(t.estado)}</span>
    <span class="desc" title="${t.desc}">${t.desc}</span>
    <span class="val ${t.valor < 0 ? 'neg' : 'pos'}">${moeda(t.valor)}</span>
    <span style="color:var(--text-muted);">${(t.conf*100).toFixed(0)}%</span>
    <span>${t.divergencia ? `<span class="estado-pill" style="color:var(--accent-yellow);border-color:var(--accent-yellow);">!${' '}auditoria</span>` : ''}</span>
    <span style="color:var(--text-muted);">${glyph('chevron-right',12)}</span>
  </div>
`).join('');

// Card 4-way: helper para campos
function fieldRow(k, v, opts = {}) {
  const cls = opts.cls || '';
  const html = opts.html || `<span class="v ${cls}">${v || '<span class="miss">— vazio —</span>'}</span>`;
  return `<div class="field"><span class="k">${k}</span>${html}</div>`;
}

// Coluna OFX (read-only)
function colOfx() {
  const f = REVISOR_4WAY.ofx.fields;
  return `
    <div class="fw-card col-ofx">
      <div class="fw-head">
        <div>
          <div class="ttl">${REVISOR_4WAY.ofx.label}</div>
          <div class="src">${REVISOR_4WAY.ofx.src}</div>
        </div>
        <span class="col-icon">${glyph('bank', 18)}</span>
      </div>
      <div class="fw-body">
        ${fieldRow('data', f.data)}
        ${fieldRow('descrição', f.descricao)}
        ${fieldRow('valor', f.valor, { cls: 'diff' })}
        ${fieldRow('tipo', f.tipo)}
        ${fieldRow('memo', f.memo)}
        ${fieldRow('FITID', f.identificador, { cls: 'muted' })}
      </div>
      <div class="action-row" style="opacity:.6;">
        <span style="font-family:var(--ff-mono);font-size:11px;color:var(--text-muted);">${glyph('lock',12)} read-only · banco</span>
      </div>
    </div>`;
}

// Coluna rascunho ETL
function colRascunho() {
  const f = REVISOR_4WAY.rascunho.fields;
  return `
    <div class="fw-card col-rascunho">
      <div class="fw-head">
        <div>
          <div class="ttl">${REVISOR_4WAY.rascunho.label}</div>
          <div class="src">${REVISOR_4WAY.rascunho.src}</div>
        </div>
        <span class="col-icon">${glyph('cog', 18)}</span>
      </div>
      <div class="fw-body">
        ${fieldRow('data', f.data)}
        ${fieldRow('descrição', f.descricao)}
        ${fieldRow('valor', f.valor)}
        ${fieldRow('categoria', f.categoria, { cls: 'miss' })}
        ${fieldRow('fornecedor', f.fornecedor, { cls: 'miss' })}
        ${fieldRow('é pessoal', f.eh_pessoal, { cls: 'miss' })}
        ${fieldRow('observação', f.observacao, { cls: 'miss' })}
      </div>
      <div class="action-row">
        <button class="btn btn-sm btn-ghost" disabled>${glyph('arrow-right',12)} usar como ponto de partida</button>
      </div>
    </div>`;
}

// Coluna Opus
function colOpus() {
  const f = REVISOR_4WAY.opus.fields;
  return `
    <div class="fw-card col-opus">
      <div class="fw-head">
        <div>
          <div class="ttl">${REVISOR_4WAY.opus.label}</div>
          <div class="src">${REVISOR_4WAY.opus.src}</div>
        </div>
        <span class="col-icon">${glyph('sparkle', 18)}</span>
      </div>
      <div class="fw-body">
        ${fieldRow('data', f.data)}
        ${fieldRow('descrição', f.descricao)}
        ${fieldRow('valor', f.valor)}
        ${fieldRow('categoria', f.categoria)}
        ${fieldRow('fornecedor', f.fornecedor)}
        ${fieldRow('é pessoal', f.eh_pessoal)}
        ${fieldRow('observação', f.observacao, { cls: 'diff' })}
        ${fieldRow('confiança', `${(parseFloat(f.conf)*100).toFixed(0)}%`, { cls: 'muted' })}
      </div>
      <div class="action-row">
        <button class="btn btn-sm btn-primary">${glyph('check',12)} Aceitar como humano</button>
        <button class="btn btn-sm">${glyph('refresh',12)} Re-gerar c/ hint</button>
      </div>
    </div>`;
}

// Coluna humano (editável)
function colHumano() {
  const f = REVISOR_4WAY.humano.fields;
  const o = REVISOR_4WAY.opus.fields;
  return `
    <div class="fw-card col-humano">
      <div class="fw-head">
        <div>
          <div class="ttl">${REVISOR_4WAY.humano.label}</div>
          <div class="src">${REVISOR_4WAY.humano.src}</div>
        </div>
        <span class="col-icon">${glyph('user', 18)}</span>
      </div>
      <div class="fw-body">
        ${fieldRow('data', '', { html: `<span class="v"><input type="text" value="${f.data}"></span>` })}
        ${fieldRow('descrição', '', { html: `<span class="v"><input type="text" placeholder="${o.descricao}"></span>` })}
        ${fieldRow('valor', '', { html: `<span class="v"><input type="text" value="${f.valor}"></span>` })}
        ${fieldRow('categoria', '', { html: `<span class="v"><select><option value="">— selecione —</option><option>${o.categoria}</option><option>Despesa pessoal</option><option>Despesa trabalho</option></select></span>` })}
        ${fieldRow('fornecedor', '', { html: `<span class="v"><input type="text" placeholder="${o.fornecedor}"></span>` })}
        ${fieldRow('é pessoal', '', { html: `<span class="v"><select><option>— selecione —</option><option>pessoal</option><option>trabalho</option><option>misto</option></select></span>` })}
        ${fieldRow('observação', '', { html: `<span class="v"><textarea placeholder="adicionar nota humana…"></textarea></span>` })}
      </div>
      <div class="action-row" style="background: rgba(255,121,198,0.04);">
        <button class="btn btn-sm btn-primary">${glyph('check',12)} Apurar transação</button>
        <button class="btn btn-sm">${glyph('warning',12)} Marcar para revisar depois</button>
      </div>
    </div>`;
}

document.getElementById('main-root').innerHTML = `
  <div class="page-header">
    <div>
      <h1 class="page-title">REVISOR DE TRANSAÇÕES</h1>
      <p class="page-subtitle">
        Cada transação tem 4 fontes que NÃO se sobrescrevem.
        OFX é imutável (banco). Rascunho é a extração legacy. Opus é a proposta agentic. Humano é a verdade final.
      </p>
    </div>
    <div class="page-meta">
      <span class="sprint-tag">Apuração 2026</span>
      <span class="pill pill-d7-pendente">15 transações · 2 divergentes</span>
    </div>
  </div>

  <div style="display:grid; grid-template-columns: minmax(0, 380px) 1fr; gap: var(--sp-4); height: calc(100vh - 280px); min-height: 640px;">
    <!-- LISTA -->
    <div class="transacao-list" style="display:flex; flex-direction:column;">
      <div class="transacao-tabs">
        <span class="tab active">Mês atual</span>
        <span class="tab">Só divergentes</span>
        <span class="tab">Só rascunhos</span>
        <span class="tab">Apurado</span>
      </div>
      <div style="padding: 8px 12px; border-bottom: 1px solid var(--border-subtle); display:flex; gap: 8px; align-items:center; background: var(--bg-inset);">
        <span style="font-family:var(--ff-mono); font-size:11px; color:var(--text-muted); letter-spacing:0.06em; text-transform:uppercase;">Nubank · CC ••42</span>
        <span style="margin-left:auto; font-family:var(--ff-mono); font-size:11px; color:var(--text-muted);">2026-03</span>
      </div>
      <div style="overflow:auto; flex:1;">
        ${tlist}
      </div>
      <div style="padding: 10px 12px; border-top: 1px solid var(--border-subtle); display:flex; justify-content:space-between; font-family:var(--ff-mono); font-size:11px; color:var(--text-muted);">
        <span>15 transações</span>
        <span>saldo: <strong style="color:var(--text-primary);">+R$ 4.102,15</strong></span>
      </div>
    </div>

    <!-- 4-WAY -->
    <div style="display:flex; flex-direction:column; gap: var(--sp-3); min-height: 0;">
      <div style="display:flex; align-items:center; gap: var(--sp-3); flex-wrap:wrap;">
        <div>
          <div style="font-family: var(--ff-mono); font-size: var(--fs-11); color: var(--text-muted); letter-spacing:.06em; text-transform:uppercase;">transação selecionada</div>
          <div style="font-family: var(--ff-mono); font-size: var(--fs-18); font-weight:500;">#${REVISOR_4WAY.id} · 2026-03-15 · C6 BANK FATURA · -R$ 2.847,90</div>
        </div>
        <span class="pill pill-humano-rejeitado">divergente</span>
        <span class="pill" style="background:var(--bg-inset);color:var(--text-secondary);border-color:var(--border-subtle);">sha8 ${REVISOR_4WAY.contexto.sha8}</span>
        <div style="margin-left:auto; display:flex; gap: var(--sp-2);">
          <button class="btn btn-sm">${glyph('arrow-left',14)} anterior</button>
          <button class="btn btn-sm">${glyph('arrow-right',14)} próxima</button>
        </div>
      </div>

      <div class="fourway" style="flex:1; min-height:0;">
        ${colOfx()}
        ${colRascunho()}
        ${colOpus()}
        ${colHumano()}
      </div>

      <!-- Auditoria do Opus -->
      <div class="card" style="padding: 0;">
        <div class="transacao-tabs" style="border-bottom: 1px solid var(--border-subtle);">
          ${REVISOR_TABS.map((t,i) => `<span class="tab ${i===1?'active':''}">${t}</span>`).join('')}
        </div>
        <div style="padding: var(--sp-3) var(--sp-4); display:grid; grid-template-columns: 1fr 1fr; gap: var(--sp-4);">
          <div>
            <div style="font-family:var(--ff-mono); font-size:var(--fs-11); letter-spacing:0.06em; text-transform:uppercase; color:var(--text-muted); margin-bottom: 8px;">trace de raciocínio</div>
            <div style="font-family:var(--ff-mono); font-size:var(--fs-12); line-height:1.6; color: var(--text-secondary);">
              <div>1. Identifiquei "C6 BANK FATURA" como pagamento de cartão.</div>
              <div>2. Cruzei com fatura sha8 <code style="color:var(--accent-purple);">b7d2a04f</code> (mesmo mês).</div>
              <div>3. Total da fatura: <span style="color:var(--accent-yellow);">R$ 2.874,90</span> · valor desta transação: <span style="color:var(--accent-yellow);">R$ 2.847,90</span>.</div>
              <div>4. Hipótese: OCR confundiu "47" com "74" no extrato bancário.</div>
              <div>5. Como OFX é fonte autoritativa, mantive valor R$ 2.847,90 e flaguei divergência.</div>
            </div>
          </div>
          <div>
            <div style="font-family:var(--ff-mono); font-size:var(--fs-11); letter-spacing:0.06em; text-transform:uppercase; color:var(--text-muted); margin-bottom: 8px;">arquivos consultados</div>
            <div style="display:flex; flex-direction:column; gap: 6px;">
              <div class="card" style="padding: 8px 10px; display:flex; align-items:center; gap:8px;">
                <span style="color:var(--accent-purple);">${glyph('pdf',14)}</span>
                <span style="font-family:var(--ff-mono); font-size:var(--fs-12);">extrato_nubank_cc_2026-03.pdf</span>
                <span style="margin-left:auto; font-family:var(--ff-mono); font-size:11px; color:var(--text-muted);">a3f9c1e2</span>
              </div>
              <div class="card" style="padding: 8px 10px; display:flex; align-items:center; gap:8px;">
                <span style="color:var(--accent-yellow);">${glyph('pdf',14)}</span>
                <span style="font-family:var(--ff-mono); font-size:var(--fs-12);">fatura_c6_cartao_2026-03.pdf</span>
                <span style="margin-left:auto; font-family:var(--ff-mono); font-size:11px; color:var(--text-muted);">b7d2a04f</span>
              </div>
            </div>
            <div style="margin-top: var(--sp-3); font-family:var(--ff-mono); font-size:var(--fs-11); letter-spacing:0.06em; text-transform:uppercase; color:var(--text-muted); margin-bottom: 8px;">próximas ações sugeridas</div>
            <ul style="margin:0; padding-left: 16px; font-family:var(--ff-mono); font-size:var(--fs-12); color: var(--text-secondary); line-height:1.7;">
              <li>Confirmar valor com o app do Nubank</li>
              <li>Reprocessar fatura C6 c/ hint "papel térmico"</li>
              <li>Marcar transação como "OFX-vencedor"</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  </div>
`;
hidratarGlyphs(document.getElementById('main-root'));
