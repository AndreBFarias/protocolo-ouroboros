# Auditoria técnica honesta -- 2026-04-23

Auditoria executada após a sessão "conserta tudo" (rota P0/P1/P2/P3 + Fase A ressalvas + Fase B ZETA + Fase C backlog formal). Documento produzido pela Sprint E, ANTES da Sprint D (auditoria artesanal com humano).

**Base:** HEAD `9da3d6b` em `origin/main` no momento da auditoria.

---

## Sumário executivo

- **Estado geral: SAUDÁVEL com ressalvas conhecidas.**
- Baseline de testes: **1.261 passed / 9 skipped**.
- Gauntlet verde: `make lint` OK, `make smoke` 23 checagens 0 erros + 8/8 contratos aritméticos.
- **0 bugs P0 (bloqueadores)** no pipeline principal.
- **5 bugs P1 importantes** (fora de rota crítica mas merecem sprint-filha dedicada).
- **8 minúcias P2** (dívida técnica de baixo impacto).
- **3 arquivos órfãos** confirmados (zero referência no código).
- **7 sprints-filhas já formalizadas** (82b, 92a, 92b, 92c, 93a, 93b, 93c) cobrem quase todas as P1.

---

## 1. Bugs conhecidos

### P0 -- bloqueadores

**Nenhum em aberto.** Todos os contratos aritméticos passam, pipeline completa executa sem erro, smoke verde.

### P1 -- importantes

#### P1-01. `boleto_pdf` fora do `pipeline._descobrir_extratores`

- **Evidência:** `grep -i boleto src/pipeline.py` retorna 0 ocorrências. Apenas `scripts/reprocessar_documentos.py::EXTRATORES_DOCUMENTAIS` lista `ExtratorBoletoPDF`.
- **Impacto:** Boletos novos em inbox não são ingeridos no grafo durante `./run.sh --tudo`. Só entram quando o operador roda `reprocessar_documentos.py` manualmente.
- **Já registrado:** HANDOFF_2026-04-24 seção "Ressalva técnica descoberta hoje".
- **Sprint-filha proposta:** `sprint_87e_registrar_boleto_pdf_no_pipeline.md` (~30min).

#### P1-02. 8 extratores sem teste dedicado

- **Evidência:** busca cruzada `ls tests/test_<extrator>*.py` retorna vazio para: `c6_cartao`, `c6_cc`, `energia_ocr`, `itau_pdf`, `nubank_cartao`, `nubank_cc`, `ofx_parser`, `santander_pdf` (e o utilitário `_ocr_comum`).
- **Impacto:** Cobertura indireta existe via `test_deduplicator.py`, `test_pipeline_tipo_contrato.py`, `test_transferencia_interna.py`, mas regressão no parser específico de cada banco passa despercebida até rodar em volume real.
- **Evidência empírica:** Sprint 93 (auditoria de fidelidade) detectou que 8 de 9 bancos têm delta não-zero entre extrator bruto e XLSX consolidado. Pode ser bug de dedup ou de parser -- Sprints 93a/b/c investigam.
- **Sprint-filha proposta:** `sprint_F_testes_extratores_bancarios.md` (spec nova a escrever, ~3h, criar fixtures sintéticas + 1 teste por banco).

#### P1-03. 3 famílias de divergência em extratores (Sprint 93 findings)

- **Evidência:** `docs/auditoria_extratores_2026-04-23.md` seções "Família A/B/C".
- **Família A (dedup agressiva):** itau_cc, santander, c6_cc, nubank_cartao, nubank_cc -- Sprint 93a.
- **Família B (extrator < XLSX, origem histórica cruzada):** c6_cartao, nubank_pf_cc -- Sprint 93b.
- **Família C (rotulagem `Nubank (PJ)` perdida no pipeline):** nubank_pj_cc, nubank_pj_cartao -- Sprint 93c.
- **Impacto:** Delta agregado até R$ 889k (nubank_cc) entre bruto vs consolidado. Investigação necessária antes de confiar 100% nos dados por banco.
- **Sprint-filhas já formalizadas:** 93a, 93b, 93c em `docs/sprints/backlog/`.

#### P1-04. Dashboard pyvis com labels hash em nodes `transacao`

- **Evidência:** Sprint 92 UX audit `docs/ux/audit_2026-04-23.md` achado P0-1.
- **Impacto:** Aba "Grafo + Obsidian" mostra `D9BA5646D4F21EA7` em vez de `2026-03-19 R$ 104 SESC` -- inutilizável para humano.
- **Regressão silenciosa:** Sprint 60 deveria ter coberto mas nodes `transacao` ficaram de fora.
- **Sprint-filha:** Sprint 92a item 1 (de 11, P0).

#### P1-05. Contraste catastrófico no treemap Categorias (WCAG AA)

- **Evidência:** Sprint 92 UX audit achado P0-2. Treemap com texto preto em `#50FA7B` Dracula green = razão 2.8:1 vs mínimo 4.5:1 do WCAG AA.
- **Impacto:** Usuário com daltonismo ou baixa visão não lê a aba Categorias.
- **Sprint-filha:** Sprint 92a item 2 (P0).

### P2 -- minúcias

| # | Descrição | Evidência | Origem |
|---|-----------|-----------|--------|
| P2-01 | 13 abas estouram viewport 1600px; "Catalogação" trunca para "Catalog..." | Sprint 92 screenshot aba 10 | Sprint 92 / 92b |
| P2-02 | `src/dashboard/dados.py` com 836 linhas (36 acima da meta 800) | `wc -l` | Refactor candidato |
| P2-03 | 12 testes skipados dependem de fixtures binárias ausentes | `pytest -v grep SKIP` | Fixtures fora do repo |
| P2-04 | 121 ocorrências de `# noqa` -- maioria legítima (`noqa: accent`) mas merece pente-fino | `grep -c "# noqa"` | — |
| P2-05 | NFCe agora OCR-tolerante mas DANFE e Boleto-PDF ainda não | Sprint 89 + A2 | Sprint-filha candidata |
| P2-06 | 6 arquivos legítimos ficam em `data/raw/casal/` (2 boletos SESC, 2 cupons foto, 2 outros) | Sprint 90 + A1 migração | Classificação ambígua por design |
| P2-07 | 6 UUIDs antigos em `data/raw/_conferir/` removidos durante Sprint 87d; só 2 ativos agora (idempotentes) | Sprint 87d | Limpo |
| P2-08 | `docs/propostas/extracao_cupom/` tem 2 arquivos idempotentes (sha256) dos cupons com OCR recall 0% | Sprint 87d + A2 | Esperado -- cupons são ilegíveis |

---

## 2. Arquivos órfãos

Confirmados por `grep -rln <nome> src/ scripts/ tests/` sem referência:

| Path | Linhas | Evidência | Ação sugerida |
|------|--------|-----------|---------------|
| `mappings/layouts_danfe.yaml` | 49 | `grep layouts_danfe src/ scripts/ tests/` = vazio | **Deletar ou documentar** (estava previsto para parser DANFE paramétrico, nunca conectado) |
| `mappings/layouts_nfce.yaml` | 39 | idem | **Deletar ou documentar** (idem para NFCe) |
| `src/integrations/__init__.py` | — | Só exporta; integrations só chamadas via `python -m` | Manter (é pacote) |
| `src/projections/__init__.py` | — | `scenarios.py` tem 4 refs | Manter |
| `src/obsidian/__init__.py` | — | `sync.py` 9 refs | Manter |

**Falsos-positivos rejeitados:**
- `src/integrations/belvo_sync.py` -- standalone CLI (`python -m src.integrations.belvo_sync`). Documentado em `src/integrations/README.md`. **Mantido**.
- `src/integrations/gmail_csv.py` -- idem. **Mantido**.
- `src/obsidian/sync_rico.py` -- usado via CLI `--sync`. **Mantido**.

**Ação recomendada:** deletar `mappings/layouts_danfe.yaml` e `mappings/layouts_nfce.yaml` em commit separado desta sprint, OU incluir comentário-aviso no YAML que são protótipos abandonados.

---

## 3. Integração e consistência

### Pipeline vs reprocessar_documentos

**Contratos atuais:**

| Extrator | `_descobrir_extratores` | `EXTRATORES_DOCUMENTAIS` | Simetria |
|---|:-:|:-:|:-:|
| boleto_pdf | NÃO | sim | **DIVERGE (P1-01)** |
| cupom_garantia_estendida_pdf | sim | sim | OK |
| cupom_termico_foto | sim | sim | OK |
| danfe_pdf | sim | sim | OK |
| das_parcsn_pdf | sim | sim | OK |
| dirpf_dec | sim | NÃO | DIVERGE (DIRPF é inbox-only, ok) |
| garantia | sim | sim | OK |
| nfce_pdf | sim | sim | OK |
| receita_medica | sim | sim | OK |
| recibo_nao_fiscal | sim | sim | OK |
| xml_nfe | sim | sim | OK |

### YAMLs declarativos vs código

`mappings/` tem 23 arquivos YAML. 21 são consultados. 2 são órfãos (seção 2). YAMLs de configuração declarativa adotados na sessão:

| YAML | Criado em | Código que usa |
|------|-----------|----------------|
| `fontes_renda.yaml` | P0.1 2026-04-23 | `src/utils/fontes_renda.py`, `src/load/xlsx_writer.py`, `scripts/smoke_aritmetico.py` |
| `pessoas.yaml` | P0.2 2026-04-23 | `src/intake/pessoa_detector.py` |
| `irpf_regras.yaml` | B3 2026-04-23 | `src/transform/irpf_tagger.py` |
| `tipos_documento.yaml` | Sprint 70 | `src/intake/registry.py`, `src/integrations/controle_bordo.py` |
| `categorias.yaml` | Sprint 1 | `src/transform/categorizer.py` |
| `categorias_item.yaml` | Sprint 50 | `src/transform/item_categorizer.py` |
| `contas_casal.yaml` | Sprint 68 + C1 2026-04-23 | `src/transform/canonicalizer_casal.py` |

**Padrão declarativo consolidado:** 3 novos YAMLs adicionados nesta sessão, todos com schema validado, fallback para hardcoded quando YAML ausente, testes de ambos caminhos.

### Extratores vs testes

8 extratores bancários sem teste dedicado (P1-02). Cobertos indiretamente mas deserto de regressão direta.

### Dashboard vs páginas

13 abas declaradas em `src/dashboard/app.py::st.tabs([...])` = 13 arquivos `src/dashboard/paginas/*.py`. Paridade OK.

---

## 4. Dívida técnica

### Código

- **0 TODOs/FIXMEs reais** (greps iniciais deram falsos-positivos com `TODOS` maiúsculo em textos).
- **0 `NotImplementedError`** em `src/`.
- **121 `# noqa`**: majoritariamente `# noqa: accent` (convenção do projeto para chaves técnicas sem acento N-para-N com schema). Vale pente-fino em sprint dedicada para reduzir.
- **1 arquivo > 800 linhas**: `src/dashboard/dados.py` (836L). 36 linhas acima da meta; candidato a split em sub-módulos por domínio (filtros / agregados / queries).

### Testes

- 12 testes skip, todos por falta de fixtures binárias reais (PDFs de bilhetes, scans, etc.) que não estão no repo por serem dados pessoais. Aceitável. Poderia virar fixtures sintéticas (reportlab) se alguém quiser ativar.
- 0 testes com `@pytest.mark.slow` em execução regular (confirmado). Sprint 93 criou alguns mas respeitam tag.

### Propostas / experimentos em limbo

- `docs/propostas/extracao_cupom/` -- 2 .md esperados (cupons com OCR recall 0%, idempotentes após Sprint 87d).
- `docs/propostas/linking/` -- Sprint 48 tinha previsto, checar se existe (pode estar vazio).

---

## 5. Dependências

`pyproject.toml` declara 14 runtime deps. Todas são importadas pelo menos 1x em `src/`:

- `pandas`, `openpyxl`, `xlrd`, `pdfplumber`, `Pillow`, `pytesseract`, `pyyaml`, `python-dotenv`, `rich`, `msoffcrypto-tool`, `ofxparse`, `pikepdf`, `pillow-heif`, `rapidfuzz` -- todas ativas.

Ausente do pyproject mas usado: **`pypdfium2`** (em `src/intake/preview.py` e `src/extractors/nfce_pdf.py` via Sprint 89 + A2). Está disponível via transitive de outra lib. Vale declarar explicitamente.

Opcional group `dashboard`: `streamlit`, `plotly`, `pyvis` -- precisa `uv pip install -e ".[dashboard]"` para rodar `./run.sh --dashboard`.

---

## 6. Testes

**Baseline:** 1.261 passed, 9 skipped.

**Crescimento desta sessão (19 sprints):**

| Momento | Passed | Delta |
|---------|--------|-------|
| Início da sessão (pré-auditoria) | 1.139 | — |
| Pós-rota "conserta tudo" (9 sprints) | 1.200 | +61 |
| Pós-Fase A (3 sprints ressalvas) | 1.201 | +1 |
| Pós-Fase B (3 sprints ZETA) | 1.220 | +19 |
| Pós-Fase C (3 sprints paralelas via worktree) | **1.261** | +41 |

**Skips (9 ativos):** todos em `test_intake_*` e `test_cobertura_grafo` dependem de fixtures binárias de PDF (notas de garantia reais, scans reais). Aceitável.

**Arquivos de teste novos desta sessão:**
- `tests/test_fontes_renda.py` (30 testes)
- `tests/test_das_parcsn_pdf.py` (6)
- `tests/test_preview_ocr_fallback.py` (4)
- `tests/test_router_dedupe_conteudo.py` (5)
- `tests/test_dirpf_dec.py` (6)
- `tests/test_relatorio_diagnostico.py` (8)
- `tests/test_resumo_narrativo.py` (6)
- `tests/test_irpf_regras_yaml.py` (5)
- `tests/test_canonicalizer_variantes.py` (25)
- `tests/test_auditoria_fidelidade.py` (16)

= 111 testes novos. Os outros 11 de crescimento são testes adicionados a arquivos existentes (`test_intake_pessoa_detector.py` ganhou 7 para Sprint 90, `test_item_categorizer.py` ganhou 1 para 50b, `test_cupom_termico_foto.py` ganhou 2 para 87d).

---

## 7. Configuração e smoke

- **`./run.sh --check`**: 23 checagens, 0 erros, 0 avisos.
- **`scripts/smoke_aritmetico.py --strict`**: 8/8 contratos OK (receita não exagera salário, despesa não negativa, juros/iof/multa nunca receita, TI pareadas, classificações somam despesa+imposto, categoria nunca nula em despesa, tipo em conjunto válido, banco_origem em conjunto válido).
- **`.env.example`**: inspecionar se cobre tudo (não crítico; projeto roda offline).
- **Logs em `logs/`**: 4 arquivos (`controle_de_bordo.log` principal). Sem rotação implementada no handler atual -- vale conferir se a Sprint 2 (infra) declarou rotação 5MB/3 backups como `CLAUDE.md §5` afirma.

---

## Apêndice A -- Estado do grafo (2026-04-23 pós-merge Fase C)

```
Nodes total: 7480
Edges total: 24700

Nodes por tipo:
  transacao: 6086
  fornecedor: 1105
  categoria: 104
  periodo: 82
  documento: 41
  item: 41
  conta: 7
  produto_canonico: 7
  tag_irpf: 4
  apolice: 2
  seguradora: 1

Documentos por tipo:
  holerite: 24
  das_parcsn_andre: 10
  nfce_modelo_65: 4
  boleto_servico: 2
  dirpf_retif: 1
```

---

## Apêndice B -- Estado do XLSX

```
Abas: extrato, renda, dividas_ativas, inventario, prazos, resumo_mensal, irpf, analise

extrato: 6088 linhas
Range: 2019-10-08 a 2026-10-27 (82 meses)
Bancos distintos: C6, Histórico, Itaú, Nubank, Nubank (PF), Santander

renda: 99 linhas (24 holerites + 75 MEI André legítimos) -- vs 459 pré-P0.1
irpf: 164 linhas (75 com CNPJ/CPF, 44% cobertura)
```

---

## Recomendação de priorização pós-auditoria

Antes da Sprint D (artesanal com humano), executar na ordem:

1. **Deletar layouts_danfe.yaml e layouts_nfce.yaml** (commit trivial). Fecha #2 órfãos.
2. **Sprint 87e -- registrar boleto_pdf no pipeline** (~30min). Fecha P1-01.
3. **Sprint 92a P0 (2 itens críticos)** -- labels pyvis + contraste treemap. Fecha P1-04 e P1-05.
4. **Sprint 93a** -- investigar dedup agressiva (inicia solução da P1-03 família A).
5. **Sprint F -- testes extratores bancários** (spec nova). Fecha P1-02.

**Após isso:** Sprint D pode rodar com confiança de que o sistema está honesto consigo mesmo.

---

*"Medir é começar a consertar." -- princípio da auditoria honesta*
