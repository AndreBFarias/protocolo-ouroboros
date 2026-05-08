# Auditoria visual 2026-05-08 — Bem-estar restante (Recap, Eventos, Memórias, Medidas, Ciclo, Cruzamentos)

## 21 — Recap (sprint UX-V-2.17 — concluída)

**OK**: KPIs (Humor médio, Eventos, Treinos, Peso variação), comparativo de humor (gráfico de barras), decisão ADR-13 honrada (sem LLM API).

**Faltantes vs spec V-2.17**:
- Bloco "Comparativo vs 30D anteriores" estruturado como tabela com deltas (humor +0.42, ansiedade -1.10, etc) — dashboard mostra só barras simples.
- "Destaques do mês" 5 cards canônicos — ausente no dashboard.
- Bloco "narrativa do mês (gerada manualmente via /gerar-recap)" prometido pela auditoria 2026-05-07 — ausente.

**Classificação**: MÉDIA. V-2.17 entregou KPIs e gráfico, faltou comparativo estruturado e destaques. Sprint UX-V-2.17-FIX adequada.

---

## 22 — Eventos (sprint UX-V-2.9 — concluída)

**OK estrutural**:
- Layout 2-col com timeline + calendário visual lateral.
- Distribuição por tipo bar chart.
- Bloco Cruzamento com humor (placeholder "Em produção").

**Faltantes vs mockup**:
- Mockup mostra 8+ eventos com TIMELINE direto + sidebar calendário; dashboard adiciona bloco lateral de filtros (Modo/Período/Categoria/Pessoa) que mockup não tem.
- Botões "ver" inline por linha da timeline ausentes (mockup tem; dashboard tem só intensidade pílulas).
- Cruzamento com humor placeholder em vez de dados reais (limitação do mob).

**Classificação**: BAIXA. V-2.9 cumpriu spec; só polish.

---

## 23 — Memórias (sprint UX-V-2.11 — concluída)

**MIGUÉ ARQUITETURAL CRÍTICO**:

- Mockup `23-memorias.html` propõe **nova arquitetura**: cápsulas multimídia (foto/áudio/texto/vídeo) em grid 7+5 com gradientes coloridos, KPIs (Total/Por tipo/Vinculadas a eventos/Cápsulas para abrir), filtros chips (todos/foto/voz/texto/video).
- Dashboard real ainda usa **arquitetura antiga**: tabs Treinos / Fotos / Marcos com heatmap 91 dias na aba Treinos.
- Spec V-2.11 declarou paridade visual mas a transição estrutural NÃO aconteceu — quando dado mob aparecer, página seguirá com layout antigo.
- Decisão dono (resposta AskUserQuestion 2026-05-08): endurecer skeleton-mockup canônico agora.

**Classificação**: ALTA. Sprint UX-V-2.11-FIX para reescrita completa do layout (skeleton-mockup vs tabs antigas).

---

## 24 — Medidas (sprint UX-V-2.12 — concluída)

**Mesmo padrão Rotina/Skills D7**:

- Fallback texto puro ("MEDIDAS · SEM REGISTROS AINDA") + 6 KPIs com `--`.
- NÃO mostra skeleton-mockup do layout final (cards com sparkline curvada, delta variação 30d, tabela histórico semanal).
- Schema atual cobre PESO/CINTURA/PRESSÃO/FREQ/SONO/SPO2 mas NÃO cobre GORDURA % (sub-sprint V-2.12.A já reconhece e está em backlog).
- Toggle PESSOA A/B existe (não testado).

**Classificação**: ALTA. V-2.12 igual padrão Rotina: spec assumiu dado e não fez skeleton; data depende mob v1.0.0.

---

## 25 — Ciclo (sprint UX-V-2.13 — concluída)

**Skeleton parcial implementado** (única página de Bem-estar com placeholder não-trivial):

- Tem silhueta de meio-anel cinza + 4 KPIs (FASE/DIA/DURAÇÃO/PRÓXIMO) com `--`.
- Mas NÃO renderiza o anel SVG completo de 28 dias com 4 fases coloridas (menstrual/folicular/fértil/lútea) que a spec prometia.
- Cards laterais ausentes no skeleton: SINTOMAS HOJE escala 0-3 (8 sintomas) + CRUZAMENTO CICLO×HUMOR (12 ciclos com humor médio por fase).
- Texto fallback "CICLO · SEM REGISTROS AINDA" + explicação CTA mob.

**Classificação**: MÉDIA. V-2.13 entregou estrutura mínima; falta anel SVG completo no skeleton + cards laterais.

---

## 26 — Cruzamentos (sprint UX-V-2.14 — concluída)

**OK estrutural alta**:
- Builder com 3 dropdowns (métrica / cruzar com / janela) — implementado.
- 8 perguntas pré-prontas clicáveis em grid 2x4 — implementado.
- Insights desta query estruturados — implementado.
- Texto "CRUZANDO humor x evento em 90d" + indicação "amostra insuficiente" quando dado limitado — boa prática.

**Diferenças cosmesticas com mockup**:
- Título "CRUZAMENTOS" vs mockup "CRUZAMENTOS · HUMOR × EVENTOS × CICLO" (mais específico).
- Sem botão "Rodar" explícito (dashboard auto-executa?).
- Scatter plot real ausente porque sem dados — limitação esperada.

**Classificação**: BAIXA. V-2.14 cumpriu spec quase 100%. Única página de Bem-estar com paridade alta sem ressalvas críticas.

---

## 28 — Editor TOML (sprint UX-V-2.16 — backlog mas commitada)

**MIGUÉ ESTRUTURAL**:

- Spec V-2.16 prometia "Layout 3-col com lista arquivos + editor + preview ao vivo + validação inline".
- Dashboard real implementa apenas **2-col**: lista arquivos esquerda + editor direita.
- **AUSENTE**: preview ao vivo (mockup tem 3ª coluna com tabs Visual/Diff vs HEAD/Schema renderizando alarmes/tarefas/contadores).
- **AUSENTE**: badge MODIFICADO/SCHEMA OK no header do editor.
- **AUSENTE**: linhas numeradas + syntax-highlight no editor (textarea simples).
- **AUSENTE**: bloco VALIDAÇÃO inline (0 erros, 1 aviso por linha + sugestões).
- Frontmatter ainda diz `status: backlog` apesar do merge `6619e6f`.

**Classificação**: ALTA. V-2.16 é maior migué de funcionalidade depois da Validação Tripla.
