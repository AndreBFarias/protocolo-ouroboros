// Render — Visão Geral (cluster Home)
montarShell({
  clusterAtivo: 'home', abaAtiva: 'visao-geral',
  breadcrumb: ['Ouroboros', 'Visão Geral'],
  acoes: [
    { label: 'Atualizar', icon: 'refresh', onClick: 'location.reload()' },
    { label: 'Ir para Validação', icon: 'expand', primary: true, href: '10-validacao-arquivos.html' },
  ],
});

const ouroboros = `
<style>
  @keyframes ob-rotate { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
  @keyframes ob-halo   { 0%,100% { opacity: 0.55; transform: scale(1); } 50% { opacity: 0.85; transform: scale(1.04); } }
  .ob-ring   { transform-origin: 160px 160px; animation: ob-rotate 80s linear infinite; }
  .ob-halo   { transform-origin: 160px 160px; animation: ob-halo 6s ease-in-out infinite; }
  .ob-dotted { transform-origin: 160px 160px; animation: ob-rotate 200s linear infinite reverse; opacity:.28; }
</style>
<svg viewBox="0 0 320 320" width="220" height="220" fill="none">
  <defs>
    <linearGradient id="og1" x1="0" x2="1" y1="0" y2="1">
      <stop offset="0%" stop-color="#bd93f9"/>
      <stop offset="100%" stop-color="#ff79c6"/>
    </linearGradient>
    <radialGradient id="ogc" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#bd93f9" stop-opacity="0.18"/>
      <stop offset="60%" stop-color="#bd93f9" stop-opacity="0.04"/>
      <stop offset="100%" stop-color="#bd93f9" stop-opacity="0"/>
    </radialGradient>
  </defs>

  <circle class="ob-halo" cx="160" cy="160" r="110" fill="url(#ogc)"/>
  <circle class="ob-dotted" cx="160" cy="160" r="100" fill="none" stroke="#bd93f9" stroke-width="0.4" stroke-dasharray="1 6"/>

  <g class="ob-ring">
    <path d="M 155 40
             A 120 120 0 0 0 40 160
             A 120 120 0 0 0 160 280
             A 120 120 0 0 0 280 160
             A 120 120 0 0 0 175 40"
          fill="none" stroke="url(#og1)" stroke-width="11" stroke-linecap="round"/>
    <path d="M 155 40
             A 120 120 0 0 0 40 160
             A 120 120 0 0 0 160 280
             A 120 120 0 0 0 280 160
             A 120 120 0 0 0 175 40"
          fill="none" stroke="#0e0f15" stroke-width="11" stroke-linecap="round"
          stroke-dasharray="1.5 13" opacity="0.55"/>

    <circle cx="155" cy="40" r="6" fill="#bd93f9"/>

    <g transform="translate(175,40)">
      <path d="M 0 -2 C -4 -10, -16 -12, -24 -8 C -28 -6, -30 -2, -28 0 L -8 -1 Z"
            fill="#ff79c6" stroke="#bd93f9" stroke-width="0.8" stroke-linejoin="round"/>
      <path d="M 0 2 C -4 8, -14 10, -22 7 C -26 5, -28 2, -26 0 L -8 1 Z"
            fill="#c77ab0" stroke="#bd93f9" stroke-width="0.8" stroke-linejoin="round"/>
      <ellipse cx="-4" cy="-3" rx="9" ry="5" fill="#ff79c6" opacity="0.9"/>
      <circle cx="-6" cy="-4" r="1.8" fill="#0e0f15"/>
      <circle cx="-5.5" cy="-4.6" r="0.6" fill="#f8f8f2"/>
      <path d="M -28 0 L -34 -2 M -28 0 L -34 2"
            stroke="#ff79c6" stroke-width="0.8" stroke-linecap="round" fill="none"/>
    </g>
  </g>

  <text x="160" y="158" text-anchor="middle"
        font-family="ui-monospace, 'JetBrains Mono', monospace"
        font-size="18" font-weight="500" letter-spacing="6" fill="#bd93f9">OUROBOROS</text>
  <text x="160" y="176" text-anchor="middle"
        font-family="ui-monospace, 'JetBrains Mono', monospace"
        font-size="9" letter-spacing="3" fill="#7c7e8c">PROTOCOLO</text>
</svg>`;

const cluster = (file, ic, nome, desc, s1, v1, s2, v2) => `
  <a class="cluster-card" href="${file}">
    <div class="head"><span class="ic">${glyph(ic,18)}</span><h3>${nome}</h3></div>
    <div class="desc">${desc}</div>
    <div class="stats"><span><strong>${v1}</strong>${s1}</span><span><strong>${v2}</strong>${s2}</span></div>
  </a>`;

const tlItem = (when, ic, what) =>
  `<div class="tl-item"><span class="when">${when}</span><span class="ic">${glyph(ic,16)}</span><span class="what">${what}</span></div>`;

document.getElementById('main-root').innerHTML = `
  <div class="hero">
    <div>
      <span class="marca">Sistema agentic-first</span>
      <h1>Os arquivos da sua vida financeira, normalizados.</h1>
      <p>Pipeline auto-referente. Cada arquivo é registrado pelo sha256, extraído em duas vias (ETL determinística + Opus agentic), validado por humano-no-loop, e catalogado para análise. Sprint atual: <code style="color:var(--accent-purple);">VALIDAÇÃO-CSV-01</code> — medindo paridade entre as duas extrações.</p>
    </div>
    <div class="ouroboros">${ouroboros}</div>
  </div>

  <div class="kpi-grid">
    <a class="kpi up" href="07-catalogacao.html" style="text-decoration:none;color:inherit;"><span class="l">Arquivos catalogados</span><span class="v">439</span><span class="d">+12 nas últimas 24h · 7 tipos</span></a>
    <a class="kpi" href="10-validacao-arquivos.html" style="text-decoration:none;color:inherit;"><span class="l">Paridade ETL ↔ Opus</span><span class="v">76%</span><span class="d">Meta sprint: 90% · em calibração</span></a>
    <a class="kpi warn" href="09-revisor.html" style="text-decoration:none;color:inherit;"><span class="l">Aguardando humano</span><span class="v">23</span><span class="d">8 divergências · 15 baixa confiança</span></a>
    <a class="kpi bad" href="14-skills-d7.html" style="text-decoration:none;color:inherit;"><span class="l">Skills regredindo</span><span class="v">2</span><span class="d">recibo_medico · cupom_fiscal</span></a>
  </div>

  <div class="dual">
    <div>
      <h2 style="font-family:var(--ff-mono);font-size:var(--fs-13);letter-spacing:.08em;text-transform:uppercase;color:var(--text-muted);margin:0 0 var(--sp-2);">Os 5 clusters</h2>
      <div class="cluster-grid">
        ${cluster('16-inbox.html','inbox','Inbox','Entrada de dados. Drop por sha8.','aguardando','4','na fila','12')}
        ${cluster('02-extrato.html','financas','Finanças','Extrato, contas, pagamentos, projeções.','contas','6','txns','2.8k')}
        ${cluster('06-busca-global.html','docs','Documentos','Busca, catálogo, completude, revisor, validação.','arquivos','439','com NF','94%')}
        ${cluster('12-analise.html','analise','Análise','Categorias, multi-perspectiva, IRPF.','categorias','24','IRPF','96%')}
        ${cluster('13-metas.html','metas','Metas','Financeiras + operacionais (skills D7).','financeiras','6','operacionais','4')}
        ${cluster('14-skills-d7.html','sigma','Sistema','Skills D7, runs, ADRs, configuração.','skills','18','graduadas','14')}
      </div>
    </div>

    <div>
      <h2 style="font-family:var(--ff-mono);font-size:var(--fs-13);letter-spacing:.08em;text-transform:uppercase;color:var(--text-muted);margin:0 0 var(--sp-2);">Atividade recente</h2>
      <div class="card" style="padding:var(--sp-4);">
        <div class="timeline">
          ${tlItem('14:32','upload','<strong>extrato_nubank_cc_2026-03.pdf</strong> registrado · <code>a3f9c1e2</code>')}
          ${tlItem('14:35','diff','Opus extraiu <code>b7d2a04f</code> com confiança 71% · <strong style="color:var(--accent-yellow);">divergência</strong>')}
          ${tlItem('13:52','check','Sprint <strong>VALIDAÇÃO-CSV-01</strong>: paridade 73% → 76%')}
          ${tlItem('12:10','warn','Skill <strong>recibo_medico</strong> regrediu para D7 41%')}
          ${tlItem('11:08','folder','12 arquivos catalogados · pipeline rodou em <code>43s</code>')}
          ${tlItem('09:00','info','ADR-13 ratificado: sessão de IA é parte do pipeline')}
        </div>
      </div>

      <h2 style="font-family:var(--ff-mono);font-size:var(--fs-13);letter-spacing:.08em;text-transform:uppercase;color:var(--text-muted);margin:var(--sp-5) 0 var(--sp-2);">Sprint atual</h2>
      <div class="card" style="padding:var(--sp-4);">
        <div style="display:flex;align-items:baseline;justify-content:space-between;margin-bottom:var(--sp-3);">
          <div>
            <div style="font-family:var(--ff-mono);font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--text-muted);">Sprint 4 · 2026-04-22 → 2026-05-06</div>
            <div style="font-family:var(--ff-mono);font-size:18px;font-weight:500;margin-top:4px;">VALIDAÇÃO-CSV-01</div>
          </div>
          <span class="pill pill-d7-calibracao">em calibração</span>
        </div>
        <div style="font-size:13px;color:var(--text-secondary);line-height:1.5;">Ativar comparação ETL × Opus em todos os tipos de arquivo. Ler hints. Catalogar padrões. <strong style="color:var(--text-primary);">Próximo dia 6</strong>: review de paridade e graduação de skills D7 ≥ 90%.</div>
      </div>
    </div>
  </div>
`;
hidratarGlyphs(document.getElementById('main-root'));
