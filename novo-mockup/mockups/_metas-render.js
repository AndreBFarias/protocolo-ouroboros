// Render — Metas (cluster Metas)
montarShell({
  clusterAtivo:'metas', abaAtiva:'metas',
  breadcrumb:['Ouroboros','Metas'],
  acoes:[{ label:'Snapshot', icon:'download', onClick:"toast('Snapshot mensal exportado · 10 metas')" },{ label:'Nova meta', icon:'plus', primary:true, onClick:"toast('Wizard de nova meta · em dev','warn')" }],
});

const fmtBR = (v) => 'R$ ' + v.toLocaleString('pt-BR', { minimumFractionDigits:0, maximumFractionDigits:0 });
const fmtPct = (v) => Math.round(v*100) + '%';

function ringSvg(pct, color, size=120) {
  const r = (size-16)/2, c = 2*Math.PI*r, off = c*(1-pct);
  const cx = size/2;
  return `<svg viewBox="0 0 ${size} ${size}" width="${size}" height="${size}">
    <circle cx="${cx}" cy="${cx}" r="${r}" stroke="var(--border-subtle)" stroke-width="6" fill="none"/>
    <circle cx="${cx}" cy="${cx}" r="${r}" stroke="${color}" stroke-width="6" fill="none"
      stroke-dasharray="${c}" stroke-dashoffset="${off}" stroke-linecap="round"
      transform="rotate(-90 ${cx} ${cx})"/>
    <text x="${cx}" y="${cx-2}" text-anchor="middle" font-family="JetBrains Mono" font-size="22" font-weight="500" fill="var(--text-primary)">${Math.round(pct*100)}</text>
    <text x="${cx}" y="${cx+14}" text-anchor="middle" font-family="JetBrains Mono" font-size="9" letter-spacing="2" fill="var(--text-muted)">PERCENT</text>
  </svg>`;
}

function spark(arr, color, w=120, h=28, fmt='pct') {
  const min = Math.min(...arr), max = Math.max(...arr);
  const span = Math.max(0.01, max-min);
  const pts = arr.map((v,i)=>`${(i/(arr.length-1))*w},${h-((v-min)/span)*h*0.85-2}`).join(' ');
  return `<svg viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" style="width:100%;height:${h}px;display:block;">
    <polyline points="${pts}" fill="none" stroke="${color}" stroke-width="1.4"/>
  </svg>`;
}

function aporteBars(data, w=540, h=110) {
  const max = Math.max(...data.map(d=>d.total));
  const bw = w/data.length - 4;
  const bars = data.map((d,i)=>{
    const bh = (d.total/max) * h * 0.82;
    return `<g>
      <rect x="${i*(w/data.length)+2}" y="${h-bh}" width="${bw}" height="${bh}" fill="var(--accent-purple)" opacity="${0.4 + 0.6*(d.total/max)}" rx="1"/>
      <text x="${i*(w/data.length)+bw/2+2}" y="${h+12}" text-anchor="middle" font-family="JetBrains Mono" font-size="9" fill="var(--text-muted)">${d.mes}</text>
    </g>`;
  }).join('');
  const avg = data.reduce((a,d)=>a+d.total,0)/data.length;
  const avgY = h - (avg/max)*h*0.82;
  return `<svg viewBox="0 -8 ${w} ${h+24}" style="width:100%;height:auto;display:block;">
    <line x1="0" x2="${w}" y1="${avgY}" y2="${avgY}" stroke="var(--accent-pink)" stroke-dasharray="2 3" stroke-width="1"/>
    <text x="${w-2}" y="${avgY-4}" text-anchor="end" font-family="JetBrains Mono" font-size="9" fill="var(--accent-pink)">média ${fmtBR(Math.round(avg))}</text>
    ${bars}
  </svg>`;
}

// KPIs topo
const totalAlvo = METAS_FINANCEIRAS.reduce((a,m)=>a+m.alvo,0);
const totalAtual = METAS_FINANCEIRAS.reduce((a,m)=>a+m.atual,0);
const totalMensal = METAS_FINANCEIRAS.filter(m=>!m.concluida).reduce((a,m)=>a+m.mensalidade,0);
const concluidas = METAS_FINANCEIRAS.filter(m=>m.concluida).length;

const topoKpis = `
  <div class="metas-kpi-row">
    <div class="d7-kpi"><div class="l">Acumulado · 5 metas</div><div class="v">${fmtBR(totalAtual)}</div><div class="d">${fmtPct(totalAtual/totalAlvo)} de ${fmtBR(totalAlvo)}</div></div>
    <div class="d7-kpi"><div class="l">Aporte mensal</div><div class="v" style="color:var(--accent-purple);">${fmtBR(totalMensal)}</div><div class="d">automático · 4 metas</div></div>
    <div class="d7-kpi"><div class="l">Concluídas (12m)</div><div class="v" style="color:var(--d7-graduado);">${concluidas}</div><div class="d">mestrado UFSC · 02/2026</div></div>
    <div class="d7-kpi"><div class="l">Próximo deadline</div><div class="v" style="font-size:18px;">Japão · 10/2026</div><div class="d">faltam R$ 5.550 · 5 meses</div></div>
  </div>
`;

// Metas financeiras — cards detalhados
const cardsFin = METAS_FINANCEIRAS.map(m => {
  const pct = Math.min(1, m.atual/m.alvo);
  const falta = Math.max(0, m.alvo-m.atual);
  const meses = m.mensalidade > 0 ? Math.ceil(falta/m.mensalidade) : null;
  const conclu = m.concluida ? 'concluida' : '';
  return `
    <div class="meta-card ${conclu}" style="--meta-cor: ${m.cor};">
      <div class="meta-card-l">
        ${ringSvg(pct, m.cor)}
      </div>
      <div class="meta-card-r">
        <div class="meta-head">
          <div>
            <div class="meta-tipo">${m.tipo}</div>
            <h4>${m.nome}${m.concluida?' <span class="pill pill-d7-graduado" style="margin-left:8px;">concluída</span>':''}</h4>
          </div>
          <button class="btn btn-icon btn-sm btn-ghost" title="Editar">${glyph('more',12)}</button>
        </div>
        <div class="meta-vals">
          <div><span class="lbl">acumulado</span><strong>${fmtBR(m.atual)}</strong></div>
          <div><span class="lbl">alvo</span><strong>${fmtBR(m.alvo)}</strong></div>
          <div><span class="lbl">aporte</span><strong>${m.mensalidade?fmtBR(m.mensalidade)+'/mês':'—'}</strong></div>
        </div>
        <div class="meta-bar"><span style="width:${pct*100}%;background:${m.cor};"></span></div>
        <div class="meta-foot">
          <span>${m.nota}</span>
          ${meses?`<span style="margin-left:auto;color:var(--text-muted);">${meses} meses · ${m.deadline}</span>`:`<span style="margin-left:auto;color:var(--text-muted);">${m.deadline}</span>`}
        </div>
      </div>
    </div>
  `;
}).join('');

// Metas operacionais — linhas
const linhasOp = METAS_OPERACIONAIS.map(m => {
  let pct;
  if (m.formato === 'pct')      pct = Math.min(1, m.atual/m.alvo);
  else if (m.formato === 'inv') pct = m.atual === 0 ? 1 : Math.max(0, 1 - m.atual/30);
  else                          pct = m.atual;
  const valorTxt = m.formato === 'pct' ? fmtPct(m.atual) :
                   m.formato === 'inv' ? `${m.atual}` :
                   m.atual === 1 ? 'verde' : 'vermelho';
  const alvoTxt  = m.formato === 'pct' ? fmtPct(m.alvo) :
                   m.formato === 'inv' ? `${m.alvo}` : '—';
  const status = pct >= 1 ? 'pill-d7-graduado' : pct >= 0.8 ? 'pill-d7-calibracao' : 'pill-d7-regredindo';
  return `
    <tr>
      <td><span style="font-family:var(--ff-mono);">${m.nome}</span></td>
      <td class="col-num"><strong style="color:${m.cor};">${valorTxt}</strong></td>
      <td class="col-num" style="color:var(--text-muted);">${alvoTxt}</td>
      <td><div class="meta-bar" style="width:140px;"><span style="width:${pct*100}%;background:${m.cor};"></span></div></td>
      <td>${spark(m.sparkline, m.cor, 80, 22)}</td>
      <td><span class="pill ${status}">${pct>=1?'atingida':pct>=0.8?'no caminho':'distante'}</span></td>
      <td style="color:var(--text-muted);font-size:12px;">${m.nota}</td>
    </tr>
  `;
}).join('');

// Log
const logIc = { aporte:'upload', milestone:'check', concluida:'check' };
const logCor = { aporte:'var(--accent-purple)', milestone:'var(--accent-cyan)', concluida:'var(--d7-graduado)' };
const log = METAS_LOG.map(l => `
  <div class="evento">
    <span class="evt-ts">${l.ts.slice(5)}</span>
    <span class="evt-ic" style="color:${logCor[l.tipo]};">${glyph(logIc[l.tipo], 12)}</span>
    <span class="evt-skill">${l.meta}</span>
    <span class="evt-tipo" style="color:${logCor[l.tipo]};">${l.tipo}</span>
    <span class="evt-detalhe"><strong style="color:var(--text-primary);">${l.valor}</strong> · ${l.detalhe}</span>
  </div>
`).join('');

document.getElementById('main-root').innerHTML = `
  <div class="page-header">
    <div>
      <h1 class="page-title">METAS</h1>
      <p class="page-subtitle">Duas naturezas em um cluster: <strong style="color:var(--accent-pink);">objetivos financeiros</strong> com aportes datados, e <strong style="color:var(--accent-purple);">contratos operacionais</strong> do pipeline. Ambos medem progresso. Nenhum é gate.</p>
    </div>
    <div class="page-meta">
      <span class="sprint-tag">Sprint 4</span>
      <span class="pill pill-d7-graduado">${concluidas} concluída</span>
    </div>
  </div>

  ${topoKpis}

  <div class="section-bar">
    <h2><span class="dot" style="background:var(--accent-pink);"></span>Financeiras · ${METAS_FINANCEIRAS.length}</h2>
    <span class="section-meta">${fmtBR(totalAtual)} de ${fmtBR(totalAlvo)} · aporte ${fmtBR(totalMensal)}/mês</span>
  </div>
  <div class="metas-grid">${cardsFin}</div>

  <div class="metas-grid-2">
    <div class="card" style="padding:0;">
      <div class="card-head" style="padding:var(--sp-3) var(--sp-4); margin:0; border-bottom:1px solid var(--border-subtle);">
        <h3 class="card-title">Aporte total · 12 meses</h3>
        <span style="font-family:var(--ff-mono);font-size:11px;color:var(--accent-green);"> +19% YoY</span>
      </div>
      <div style="padding:var(--sp-4);">${aporteBars(METAS_APORTE_12M)}</div>
    </div>
    <div class="card" style="padding:0;display:flex;flex-direction:column;">
      <div class="card-head" style="padding:var(--sp-3) var(--sp-4); margin:0; border-bottom:1px solid var(--border-subtle);">
        <h3 class="card-title">Log · últimos eventos</h3>
        <span style="font-family:var(--ff-mono);font-size:11px;color:var(--text-muted);">${METAS_LOG.length} eventos</span>
      </div>
      <div class="eventos-feed">${log}</div>
    </div>
  </div>

  <div class="section-bar">
    <h2><span class="dot" style="background:var(--accent-purple);"></span>Operacionais · pipeline</h2>
    <span class="section-meta">contratos do sistema · medidos a cada run</span>
  </div>
  <div class="card" style="padding:0;">
    <table class="table">
      <thead><tr>
        <th>contrato</th><th class="col-num">atual</th><th class="col-num">alvo</th>
        <th>progresso</th><th>tendência 8d</th><th>status</th><th>contexto</th>
      </tr></thead>
      <tbody>${linhasOp}</tbody>
    </table>
  </div>

  <div class="card adr-strip" style="margin-top:var(--sp-4);">
    <div style="display:flex;align-items:center;gap:var(--sp-3);">
      <span style="font-family:var(--ff-mono);font-size:11px;letter-spacing:.10em;text-transform:uppercase;color:var(--accent-purple);">Princípio</span>
      <span style="color:var(--text-secondary);font-size:13px;">Metas operacionais herdam <strong style="color:var(--text-primary);">ADR-13</strong>: D7 não bloqueia. Calibração é manual via Claude Code CLI. Aportes financeiros, idem — automáticos no banco, manuais aqui.</span>
    </div>
  </div>
`;
hidratarGlyphs(document.getElementById('main-root'));
