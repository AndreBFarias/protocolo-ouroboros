# Mapa de features Mobile → Desktop

Sintese executiva do que existe nos dois repos (`protocolo-ouroboros` desktop em
Streamlit, `ouroboros-mobile` Expo/RN) e como cada coisa atravessa para a versao
desktop nova (HTML/JS, dark Dracula, JetBrains Mono).

---

## 1. Arquitetura macro

| Camada | Mobile (Expo/RN) | Desktop hoje (Streamlit) | Desktop novo (HTML mockups) |
|---|---|---|---|
| Captura ativa | Bottom sheets nativos | — | Modal + drag&drop file API |
| Vault | `/sdcard/Documents/Ouroboros/` | `~/Protocolo-Ouroboros/` | mesmo Vault, leitura via FS API ou backend |
| Pipeline ETL | — | 22 extratores Python + tesseract OCR | mesmo backend, UI consome JSON cache |
| Dashboard | — | Streamlit 13 paginas, tema Dracula | 16 mockups HTML, mesmo tema |
| Sync | Syncthing P2P | Syncthing P2P | mesmo |

---

## 2. Telas mobile — fonte de verdade visual

`ouroboros-mobile/app/`:

- `index.tsx` (Tela 01 — Hoje): humor do dia + diarios + eventos do dia
- `humor-rapido.tsx` (Tela 15): sheet 70%, 4 sliders 1-5 (humor/energia/ansiedade/foco) + medicacao + horas sono + chips multi 8 tags + textarea frase. Persiste `daily/YYYY-MM-DD.md`.
- `diario-emocional.tsx` (Tela 18): sheet 90%, modo trigger/vitoria com borda esquerda colorida (red/green), chips emocao, slider intensidade 1-5, textarea, com-quem (pessoa_a/pessoa_b/amigos/sozinho), em trigger tem estrategia + funcionou? toggle. Persiste `inbox/mente/diario/...md`.
- `eventos.tsx` (Tela 20): sheet 80%, modo positivo/negativo, lugar+bairro (geo), quando, com-quem, categoria fechada, fotos cap 6, slider 1-5. Persiste `eventos/...md`.
- `medidas/*` (Telas 12-13): peso/cintura/quadril/peito/braco/coxa + comparativo + slider de fotos comparativas frente/lado/costas.
- `exercicios/*` (Telas 02/07/08): galeria CRUD, GIF/foto opcional, grupo muscular, historico+stats.
- `alarmes/*`: CRUD com recorrencia (unica/diaria/semanal/mensal), categoria (medicacao/treino/outro), som CC0, soneca, channel Android v2.
- `contadores/[slug].tsx`: "Dias sem X", reset preserva historico, mensagens em 6 faixas (0/<5/<30/<100/<365/≥365).
- `ciclo/*`: calendario menstrual com fases (menstrual/folicular/ovulatoria/lutea), sintomas opcionais. Tom sobrio.
- `scanner.tsx` (Tela 16): camera multipagina + ML Kit OCR -> `financas/notas/...md` + imagem original.
- `calendario/*` (Tela 25): grid mensal estilo heatmap mas com mídia. Cada dia com conquista mostra thumbnail.
- `memoria.tsx` (Telas 09-11): 3 abas — Treinos (heatmap 13×7 = 91 dias), Fotos (galeria agregada), Marcos (manuais + auto-gerados).
- `humor.tsx` (Tela 21): mini painel com heatmap 13×7 sobreposto pessoa_a/b 50% opacity, stats 30d, modal detalhe.
- `financas.tsx` (Tela 22, DESLIGADO em v1.0): hero gasto da semana + top categorias + lista virtualizada.
- `onboarding.tsx`: 3 frames, nomes+fotos, vault auto-criado, modo solo/duo/amigos.
- `settings/*`: som+vibracao mestre+contextual, pessoa, opcionais (6 toggles), privacidade, midia, dados.

---

## 3. Schemas YAML canonicos (18 ativos)

| Schema | Path tipico |
|---|---|
| humor | daily/YYYY-MM-DD.md |
| diario_emocional | diario/YYYY-MM-DD/<slug>.md |
| evento | eventos/YYYY-MM-DD/<slug>.md |
| treino_sessao | treinos/YYYY-MM-DD/<slug>.md |
| medidas | medidas/YYYY-MM-DD.md |
| exercicio | exercicios/<slug>.md |
| marco | marcos/<slug>.md |
| tarefa | tarefas/<slug>.md |
| alarme | alarmes/<slug>.md |
| contador | contadores/<slug>.md |
| ciclo_menstrual | ciclo/YYYY-MM-DD.md |
| financeiro_nota | financas/notas/YYYY-MM-DD-<slug>.md |
| inbox_arquivo | inbox/<data>-<slug>.md |
| midia | companion de binarios |
| pessoa | SecureStore |
| para | discriminatedUnion compartilhada |
| humor_heatmap_cache | .ouroboros/cache/humor-heatmap.json |
| financas-cache | .ouroboros/cache/financas-cache.json |

---

## 4. Pipeline desktop ETL (`src/intake/`)

Sequencia real:
1. **expandir_pdf_multipage** (pikepdf) — splitta PDF compilado em pgN.pdf + diagnostica nativo/scan/misto por pagina (pdfplumber)
2. **expandir_zip** / **extrair_anexos_eml** — abre envelopes
3. **gerar_preview** (pdfplumber + pytesseract) — texto para classifier
4. **classifier** (regex + heuristicas) — decide tipo (NFCe, holerite, extrato_nubank_pf, etc)
5. **router** — move para pasta canonica em `data/raw/<tipo>/`
6. **extractors_envelope** — 22 extratores especializados
7. **transform/** — normalizacao, deduplicacao, categorizacao (111 regras)
8. **load/** — XLSX 8 abas + relatorios MD + Obsidian sync

**Para a tela de extracao tripla**: o usuario quer comparar (a) texto bruto extraido pelo ETL deterministico, (b) extracao agentic via Opus (LLM), (c) input humano como ground truth.

---

## 5. Mapeamento desktop novo

### 5.1 Cluster Bem-estar (NOVO — adicionar)

Inserir entre Documentos e Analise:
- **Hoje** — agregador do dia (humor + diarios + eventos), espelho da Tela 01 mobile
- **Humor** — heatmap 13x7 + form de registro rapido (dois-pessoas overlay)
- **Diario emocional** — lista cronologica com filtros (trigger/vitoria, periodo)
- **Eventos** — timeline com mapa de bairros + fotos
- **Medidas** — comparativo + slider de fotos
- **Treinos** — heatmap 91 dias + CRUD sessoes
- **Marcos** — lista cronologica
- **Alarmes** — CRUD com recorrencia
- **Contadores** — "Dias sem X"
- **Ciclo** — calendario menstrual com fases (toggle on/off em Settings)
- **Tarefas** — to-do leve
- **Recap** — 7/30/90 dias

### 5.2 Substituicao 10-validacao-arquivos -> 10-extracao-tripla

Layout 3 colunas:
- **Esquerda**: lista de arquivos por tipo (PDF/CSV/imagem/Excel/OFX/HTML), com tipo + botao baixar original + estado (extraido/conflito/validado)
- **Centro**: viewer do arquivo selecionado (PDF page nav, imagem zoom, CSV preview)
- **Direita** (3 sub-colunas):
  - col 1: Tabela ETL (deterministica, read-only)
  - col 2: Tabela Opus (agentic, read-only)
  - col 3: Tabela User (editavel) — pre-preenchida com consenso ETL∩Opus, celulas em divergencia destacadas em laranja, usuario corrige/confirma e clica "Validar" -> registra flag `validado_por: pessoa_a` + `validado_em: <iso>` + score paridade

Banco de tipos de arquivo a cobrir:
- PDF nativo (extrato Nubank/C6/Itau, holerite)
- PDF scan (cupom garantia, recibo medico)
- CSV (export bancario)
- XLSX (planilhas, energia)
- Imagem JPG/PNG (cupom fiscal, recibo manuscrito)
- OFX/QIF (Nubank PF/PJ)
- HTML (extrato salvo do internet banking)
- XML (NFe)
- ZIP / EML (envelopes — expandir antes de mostrar)

### 5.3 Outros encaixes

- **scanner OCR mobile (M09)** -> desktop equivalente: drop zone na tela de extracao tripla aceita imagem direta, ja roda OCR + classifier do mesmo pipeline
- **share intent mobile (M08)** -> desktop equivalente: watch folder + drag-drop batch + file picker no Inbox (16-inbox.html)
- **microfone mobile (M06.5)** -> desktop equivalente: Web Audio API + Whisper local (futuro, P2)
- **widget Android (M20)** -> desktop equivalente: tray icon + mini-painel (futuro, P2)
- **Google Calendar (M37)** -> desktop equivalente: OAuth via redirect URI (paridade direta)

---

## 6. Plano de execucao

### Fase 1 — Extracao tripla (substitui 10-validacao-arquivos)
- 1 mockup novo: `10-extracao-tripla.html`
- Layout 3 colunas conforme 5.2
- Dados mock realistas (3 arquivos de tipos diferentes pre-carregados)
- Render JS modular: `_extracao-data.js` + `_extracao-render.js`

### Fase 2 — Cluster Bem-estar
- Adicionar ao shell.js a entrada do cluster
- Mockups novos:
  - `17-bem-estar-hoje.html`
  - `18-humor.html`
  - `19-diario-emocional.html`
  - `20-eventos-timeline.html`
  - `21-medidas.html`
  - `22-treinos-heatmap.html`
  - `23-marcos.html`
  - `24-alarmes.html`
  - `25-contadores.html`
  - `26-ciclo.html`
  - `27-tarefas.html`
  - `28-recap.html`

### Fase 3 — Conexoes internas
- Cards do Visao Geral apontam para clusters certos
- Dados de Bem-estar puxam do mesmo Vault que o mobile escreve

### Fase 4 — FEATURES-CANONICAS.md
- Atualizar com cluster Bem-estar + extracao tripla
- Sincronizar §17 (schemas) e §19 (implicacoes desktop)
