// Render — Skills D7 (cluster Sistema)
montarShell({
  clusterAtivo: 'sistema',
  abaAtiva: 'skills-d7',
  breadcrumb: ['Ouroboros', 'Sistema', 'Skills D7'],
  acoes: [
    { label: 'Exportar relatório', icon: 'download', onClick: "toast('Relatório D7 exportado · 18 skills · 52 sem')" },
    { label: 'Rodar calibração', icon: 'refresh', primary: true, onClick: "toast('Calibrando 18 skills...'); setTimeout(()=>toast('14 graduadas · 3 calibração · 1 regredindo'),1500)" },
  ],
});

// ─── helpers ───
const fmtPct = (v) => Math.round(v * 100) + '%';
const d7Cor = (s) => ({
  graduado:   'var(--d7-graduado)',
  calibracao: 'var(--d7-calibracao)',
  regredindo: 'var(--d7-regredindo)',
  pendente:   'var(--d7-pendente)',
}[s]);

function spark(arr, color, w=80, h=22) {
  const min = Math.min(...arr, 0), max = Math.max(...arr, 1);
  const span = Math.max(0.01, max-min);
  const pts = arr.map((v,i) => `${(i/(arr.length-1))*w},${h - ((v-min)/span)*h*0.95 - 1}`).join(' ');
  const last = arr[arr.length-1];
  const lx = w, ly = h - ((last-min)/span)*h*0.95 - 1;
  return `<svg viewBox="0 0 ${w+4} ${h}" preserveAspectRatio="none" style="display:block;width:${w}px;height:${h}px;">
    <polyline points="${pts}" fill="none" stroke="${color}" stroke-width="1.4" stroke-linejoin="round"/>
    <circle cx="${lx-2}" cy="${ly}" r="1.6" fill="${color}"/>
  </svg>`;
}

function donut(parts, size=140) {
  const total = parts.reduce((a,p)=>a+p.value,0);
  const r = size/2 - 12, cx = size/2, cy = size/2;
  let acc = 0;
  const segs = parts.map(p => {
    const start = acc/total * Math.PI*2 - Math.PI/2;
    acc += p.value;
    const end = acc/total * Math.PI*2 - Math.PI/2;
    const large = (end-start) > Math.PI ? 1 : 0;
    const x1 = cx + r*Math.cos(start), y1 = cy + r*Math.sin(start);
    const x2 = cx + r*Math.cos(end),   y2 = cy + r*Math.sin(end);
    return `<path d="M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2} Z" fill="${p.color}" opacity="0.92"/>`;
  }).join('');
  return `<svg viewBox="0 0 ${size} ${size}" width="${size}" height="${size}">
    ${segs}
    <circle cx="${cx}" cy="${cy}" r="${r-26}" fill="var(--bg-surface)"/>
    <text x="${cx}" y="${cy-2}" text-anchor="middle" font-family="JetBrains Mono" font-size="22" font-weight="500" fill="var(--text-primary)">${total}</text>
    <text x="${cx}" y="${cy+12}" text-anchor="middle" font-family="JetBrains Mono" font-size="9" letter-spacing="2" fill="var(--text-muted)">SKILLS</text>
  </svg>`;
}

function areaGrad(data, w=540, h=120) {
  const max = 1.0, min = 0.4;
  const span = max - min;
  const xs = (i) => (i/(data.length-1)) * w;
  const ys = (v) => h - ((v-min)/span) * h * 0.92 - 4;
  const pts = data.map((d,i) => `${xs(i)},${ys(d.media)}`).join(' ');
  const area = `${xs(0)},${h} ${pts} ${xs(data.length-1)},${h}`;
  const labels = data.map((d,i) => `<text x="${xs(i)}" y="${h+12}" text-anchor="middle" font-family="JetBrains Mono" font-size="9" fill="var(--text-muted)">${d.sem}</text>`).join('');
  const grid = [0.5,0.6,0.7,0.8,0.9,1.0].map(g => `<line x1="0" x2="${w}" y1="${ys(g)}" y2="${ys(g)}" stroke="var(--border-subtle)" stroke-dasharray="2 4" opacity="0.5"/><text x="-4" y="${ys(g)+3}" text-anchor="end" font-family="JetBrains Mono" font-size="9" fill="var(--text-muted)">${Math.round(g*100)}</text>`).join('');
  const dots = data.map((d,i)=>`<circle cx="${xs(i)}" cy="${ys(d.media)}" r="2.5" fill="var(--accent-purple)"/>`).join('');
  return `<svg viewBox="-30 -8 ${w+40} ${h+24}" style="width:100%;height:auto;display:block;overflow:visible;">
    <defs><linearGradient id="ag" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stop-color="#bd93f9" stop-opacity="0.45"/><stop offset="100%" stop-color="#bd93f9" stop-opacity="0.02"/></linearGradient></defs>
    ${grid}
    <polygon points="${area}" fill="url(#ag)"/>
    <polyline points="${pts}" fill="none" stroke="var(--accent-purple)" stroke-width="1.6"/>
    ${dots}
    ${labels}
  </svg>`;
}

// Heatmap: skills × dias (últimos 14 dias)
function heatmap() {
  const dias = 14;
  const cells = SKILLS_D7.map(s => {
    // sintetiza 14 dias com base no D7 atual e variação
    const base = s.cobertura;
    const ds = Array.from({length: dias}, (_, i) => {
      const noise = Math.sin(i*1.3 + s.id.length) * 0.06;
      const trend = (s.d7 === 'regredindo') ? -((dias-1-i)/dias) * 0.20 :
                    (s.d7 === 'pendente')   ? -((dias-1-i)/dias) * 0.05 :
                    ((dias-1-i)/dias) * 0.04;
      return Math.max(0.05, Math.min(0.99, base - trend + noise));
    });
    return { skill: s, ds };
  });
  const cellW = 22, cellH = 14;
  const tot = cellW*dias;
  const rows = cells.map((row, ri) => {
    const r = row.ds.map((v, di) => {
      const c = v >= 0.9 ? 'var(--d7-graduado)' :
                v >= 0.7 ? 'var(--d7-calibracao)' :
                v >= 0.5 ? 'var(--d7-regredindo)' :
                'var(--d7-pendente)';
      const op = 0.25 + v*0.75;
      return `<rect x="${di*cellW}" y="${ri*cellH}" width="${cellW-2}" height="${cellH-2}" fill="${c}" opacity="${op}" rx="1"><title>${row.skill.nome} · D-${dias-1-di} · ${Math.round(v*100)}%</title></rect>`;
    }).join('');
    return r;
  }).join('');
  const labels = cells.map((row, ri) => `<text x="-6" y="${ri*cellH + 10}" text-anchor="end" font-family="JetBrains Mono" font-size="10" fill="var(--text-secondary)">${row.skill.nome}</text>`).join('');
  const dayLbl = Array.from({length:dias}, (_,i) => i % 2 === 0 ? `<text x="${i*cellW + (cellW-2)/2}" y="-4" text-anchor="middle" font-family="JetBrains Mono" font-size="9" fill="var(--text-muted)">D-${dias-1-i}</text>` : '').join('');
  return `<svg viewBox="-130 -16 ${tot+140} ${cells.length*cellH+24}" style="width:100%;height:auto;display:block;">
    ${dayLbl}${labels}${rows}
  </svg>`;
}

// ─── KPIs do topo ───
const dist = SKILLS_DISTRIBUICAO;
const total = SKILLS_D7.length;
const cobMedia = SKILLS_D7.reduce((a,s)=>a+s.cobertura,0) / total;
const taxaGrad = dist.graduado / total;
const totalRuns = SKILLS_D7.reduce((a,s)=>a+s.runs7d,0);
const totalDiv = SKILLS_D7.reduce((a,s)=>a+s.divergencias7d,0);

const topoKpis = `
  <div class="d7-kpi-row">
    <div class="d7-kpi"><div class="l">Cobertura média</div><div class="v">${fmtPct(cobMedia)}</div><div class="d">+2pp · 8 semanas</div></div>
    <div class="d7-kpi"><div class="l">Taxa de graduação</div><div class="v" style="color:var(--d7-graduado);">${fmtPct(taxaGrad)}</div><div class="d">${dist.graduado}/${total} skills</div></div>
    <div class="d7-kpi"><div class="l">Em regressão</div><div class="v" style="color:var(--d7-regredindo);">${dist.regredindo}</div><div class="d">recibo_medico · cupom_fiscal</div></div>
    <div class="d7-kpi"><div class="l">Runs · 7d</div><div class="v">${totalRuns}</div><div class="d">${totalDiv} divergências</div></div>
    <div class="d7-kpi"><div class="l">Próxima calibração</div><div class="v" style="font-size:18px;">recibo_medico</div><div class="d">2026-05-02 · em 1 dia</div></div>
  </div>
`;

// ─── tabela skills ───
const linhasSkills = SKILLS_D7.map(s => {
  const cor = d7Cor(s.d7);
  const pillCls = `pill-d7-${s.d7}`;
  const ownerBadge = s.owner === 'etl'
    ? `<span class="badge-owner" style="color:var(--diff-removed-gutter);border-color:rgba(255,85,85,0.3);"><i data-glyph="cog" data-size="10"></i> ETL</span>`
    : `<span class="badge-owner" style="color:var(--accent-purple);border-color:rgba(189,147,249,0.3);"><i data-glyph="sigma" data-size="10"></i> Opus</span>`;
  const trend = s.d7 === 'regredindo'
    ? `<span style="color:var(--accent-red);"> ${Math.round((s.sparkD7[6]-s.sparkD7[0])*100)}pp</span>`
    : `<span style="color:var(--accent-green);"> ${Math.round((s.sparkD7[6]-s.sparkD7[0])*100)}pp</span>`;
  const proxima = s.proximaCalibracao
    ? `<span style="font-family:var(--ff-mono);font-size:11px;color:var(--text-muted);">${s.proximaCalibracao}</span>`
    : `<span style="font-family:var(--ff-mono);font-size:11px;color:var(--d7-graduado);">— estável —</span>`;
  return `
    <tr onclick="abrirSkill('${s.id}')">
      <td><span class="skill-name">${s.nome}</span></td>
      <td>${ownerBadge}</td>
      <td><span class="pill ${pillCls}">${s.d7}</span></td>
      <td class="col-num"><span style="color:${cor};font-weight:500;">${fmtPct(s.cobertura)}</span></td>
      <td>${spark(s.sparkD7, cor)}</td>
      <td class="col-num">${trend}</td>
      <td class="col-num" style="color:var(--text-secondary);">${s.runs7d}</td>
      <td class="col-num" style="color:${s.divergencias7d > 10 ? 'var(--accent-red)' : 'var(--text-secondary)'};">${s.divergencias7d}</td>
      <td>${proxima}</td>
    </tr>
  `;
}).join('');

// ─── eventos ───
const eventoIcone = {
  graduacao:  { ic:'check', cor:'var(--d7-graduado)' },
  regressao:  { ic:'warn',  cor:'var(--d7-regredindo)' },
  calibracao: { ic:'refresh', cor:'var(--accent-purple)' },
  run:        { ic:'cog',  cor:'var(--text-muted)' },
};
const eventos = SKILLS_EVENTOS.map(e => {
  const meta = eventoIcone[e.tipo];
  return `
    <div class="evento" data-tipo="${e.tipo}">
      <span class="evt-ts">${e.ts.split(' ')[1]}</span>
      <span class="evt-ic" style="color:${meta.cor};">${glyph(meta.ic, 12)}</span>
      <span class="evt-skill">${e.skill}</span>
      <span class="evt-tipo" style="color:${meta.cor};">${e.tipo}</span>
      <span class="evt-detalhe">${e.detalhe}</span>
    </div>
  `;
}).join('');

// ─── distribuição donut ───
const donutSvg = donut([
  { value: dist.graduado,   color: 'var(--d7-graduado)' },
  { value: dist.calibracao, color: 'var(--d7-calibracao)' },
  { value: dist.regredindo, color: 'var(--d7-regredindo)' },
  { value: dist.pendente,   color: 'var(--d7-pendente)' },
]);

// ─── mount ───
document.getElementById('main-root').innerHTML = `
  <div class="page-header">
    <div>
      <h1 class="page-title">SKILLS · D7</h1>
      <p class="page-subtitle">Cobertura observável. Cada skill gradua sozinha após 7 dias consecutivos ≥ 90%. <strong style="color:var(--accent-purple);">D7 não é gate</strong> — pipeline roda. Apenas marca o que confia.</p>
    </div>
    <div class="page-meta">
      <span class="sprint-tag">Sprint 4</span>
      <span class="pill pill-d7-calibracao">${dist.calibracao} em calibração</span>
      ${dist.regredindo > 0 ? `<span class="pill pill-d7-regredindo">${dist.regredindo} regredindo</span>` : ''}
    </div>
  </div>

  ${topoKpis}

  <div class="d7-grid-top">
    <div class="card d7-distribuicao">
      <div class="card-head"><h3 class="card-title">Distribuição</h3><span style="font-family:var(--ff-mono);font-size:11px;color:var(--text-muted);">${total} skills</span></div>
      <div class="d7-donut-wrap">${donutSvg}
        <div class="d7-legend">
          <div><span class="dot" style="background:var(--d7-graduado);"></span>Graduado<strong>${dist.graduado}</strong></div>
          <div><span class="dot" style="background:var(--d7-calibracao);"></span>Calibração<strong>${dist.calibracao}</strong></div>
          <div><span class="dot" style="background:var(--d7-regredindo);"></span>Regredindo<strong>${dist.regredindo}</strong></div>
          <div><span class="dot" style="background:var(--d7-pendente);"></span>Pendente<strong>${dist.pendente}</strong></div>
        </div>
      </div>
    </div>

    <div class="card d7-historico">
      <div class="card-head"><h3 class="card-title">Cobertura média · 8 semanas</h3>
        <span style="font-family:var(--ff-mono);font-size:11px;color:var(--accent-green);"> +18pp desde S-7</span>
      </div>
      <div style="padding: var(--sp-3) var(--sp-3) 0;">${areaGrad(SKILLS_HISTORICO_8SEM)}</div>
    </div>

    <div class="card d7-alvos">
      <div class="card-head"><h3 class="card-title">Próximas graduações</h3></div>
      <ul class="alvos">
        ${SKILLS_D7.filter(s=>s.d7==='calibracao').sort((a,b)=>b.cobertura-a.cobertura).slice(0,4).map(s=>{
          const falta = Math.max(0, 0.90 - s.cobertura);
          const dias = Math.max(1, Math.ceil(falta / 0.025));
          return `<li>
            <div class="alvo-l1"><span>${s.nome}</span><strong>${fmtPct(s.cobertura)}</strong></div>
            <div class="alvo-bar"><span style="width:${(s.cobertura/0.9)*100}%;background:var(--d7-calibracao);"></span></div>
            <div class="alvo-l2"><span>${dias}d até graduar</span><span>meta 90%</span></div>
          </li>`;
        }).join('')}
      </ul>
    </div>
  </div>

  <div class="card" style="margin-bottom:var(--sp-4);">
    <div class="card-head">
      <h3 class="card-title">Heatmap · cobertura diária × skill (14d)</h3>
      <div style="display:flex;gap:8px;align-items:center;font-family:var(--ff-mono);font-size:10px;color:var(--text-muted);letter-spacing:0.06em;text-transform:uppercase;">
        <span>0%</span>
        <div style="width:80px;height:8px;background:linear-gradient(90deg, var(--d7-pendente), var(--d7-regredindo), var(--d7-calibracao), var(--d7-graduado));border-radius:2px;"></div>
        <span>100%</span>
      </div>
    </div>
    <div class="d7-heatmap-wrap">${heatmap()}</div>
  </div>

  <div class="d7-grid-bottom">
    <div class="card" style="padding:0;display:flex;flex-direction:column;min-height:0;">
      <div class="card-head" style="padding: var(--sp-3) var(--sp-4); margin:0; border-bottom:1px solid var(--border-subtle);">
        <h3 class="card-title">Skills · ${total} totais</h3>
        <div style="display:flex;gap:6px;">
          <button class="btn btn-sm" data-filtro="todos">todos</button>
          <button class="btn btn-sm" data-filtro="regredindo" style="border-color:rgba(255,184,108,0.3);color:var(--d7-regredindo);">regredindo</button>
          <button class="btn btn-sm" data-filtro="calibracao">calibração</button>
        </div>
      </div>
      <div style="overflow:auto;">
        <table class="table">
          <thead><tr>
            <th>skill</th><th>via</th><th>D7</th>
            <th class="col-num">cobertura</th><th>tendência 7d</th>
            <th class="col-num">Δ7d</th><th class="col-num">runs</th><th class="col-num">div.</th>
            <th>próx. calibração</th>
          </tr></thead>
          <tbody>${linhasSkills}</tbody>
        </table>
      </div>
    </div>

    <div class="card" style="padding:0;display:flex;flex-direction:column;min-height:0;">
      <div class="card-head" style="padding: var(--sp-3) var(--sp-4); margin:0; border-bottom:1px solid var(--border-subtle);">
        <h3 class="card-title">Eventos · 72h</h3>
        <span style="font-family:var(--ff-mono);font-size:11px;color:var(--text-muted);">${SKILLS_EVENTOS.length} eventos</span>
      </div>
      <div class="eventos-feed">${eventos}</div>
    </div>
  </div>

  <div class="card adr-strip" style="margin-top:var(--sp-4);">
    <div style="display:flex;align-items:center;gap:var(--sp-3);">
      <span style="font-family:var(--ff-mono);font-size:11px;letter-spacing:.10em;text-transform:uppercase;color:var(--accent-purple);">ADR-13</span>
      <span style="color:var(--text-secondary);font-size:13px;">D7 é cobertura observável, <strong style="color:var(--text-primary);">não gate</strong>. Pipeline roda mesmo com skill regredindo. Humano calibra abrindo Claude Code CLI no terminal — sem cron, sem API.</span>
      <a href="#" style="margin-left:auto;font-family:var(--ff-mono);font-size:11px;letter-spacing:.06em;text-transform:uppercase;">ler ADR →</a>
    </div>
  </div>
`;
hidratarGlyphs(document.getElementById('main-root'));

function abrirSkill(id) { /* drawer placeholder */ }
