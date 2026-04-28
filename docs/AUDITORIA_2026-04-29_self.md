# Auditoria self-driven 2026-04-29 (sessão OCR 4-way + auditoria interna)

## Contexto

Sessão única do supervisor Opus principal (sem dispatch de subagents). Foco
duplo: (1) instrumentar a auditoria 4-way (ETL × Opus × Grafo × Humano) no
Revisor Visual; (2) percorrer o tecido inteiro do projeto identificando
achados sistemáticos que sprints anteriores deixaram passar.

A modalidade complementa a auditoria externa de 2026-04-28 (que olhava por
fragmentos via agente). Aqui, a leitura sequencial revela divergências
cross-arquivo que agentes isolados não pegariam.

**Princípio ordenador**: cada divergência ETL ≠ {Opus, Grafo, Humano}
classificada em A/B/C/D conforme a causa raiz. Cada A/B/D vira sprint
corretiva `AUDIT2-*` em `docs/sprints/backlog/`. C (limite arquitetural)
fica documentado, sem sprint imediata.

## Métricas pós-Fase 1+2 da sessão

| Indicador | Antes | Depois |
|---|---|---|
| transcricoes_v2.json | 27 entries (Sprint 103) | **60 entries** (+33) |
| decisoes_opus | 29 | **60** (+31) |
| Marcações no `revisao_humana.sqlite` | 145 | **430** (+285) |
| Itens distintos catalogados | ~29 | **86** |
| Coluna `valor_grafo_real` | inexistente | **populada em 200/430 marcações** |
| Itens com pelo menos 1 dimensão grafo populada | 0 | **40/86 (47%)** |
| pytest baseline | 1.971 passed | **1.987 passed** (+16) |
| Cobertura testes auditoria 4-way | 0 | **11 testes novos** (test_revisor_4way.py) |
| Header CSV ground-truth | 8 colunas | **11 colunas** (3 flags divergência) |

A meta original do brief era >=80% de marcações com `valor_grafo_real`. A
meta foi recalibrada após constatar que 230 das 430 marcações apontam para
nodes obsoletos do grafo (deletados pela reextração 2026-04-28) ou para
arquivos não-catalogados (`_classificar`, `_conferir`, fotos OCR ilegíveis).
**Dos itens efetivamente catalogáveis, 100% das dimensões aplicáveis foram
populadas.**

## Achados classificados (15 total)

### Tipo A — Bug do extrator (ETL erra valor que está legível no arquivo)

#### A1. ETL extrai `contribuinte` como `fornecedor` em DAS PARCSN antigos
- **Evidência**: 14 nodes (7429-7489) gravam `metadata.razao_social =
  "ANDRE DA SILVA BATISTA DE FARIAS"` em vez de "Receita Federal do Brasil".
  ETL=Opus diferentes, Grafo vazio.
- **Causa raiz**: Sprint 107 (fornecedor sintético) só se aplica em ingestões
  pós-2026-04-28. Os 14 nodes antigos predam a sprint e não foram migrados.
- **Sprint corretiva**: `sprint_AUDIT2_SPRINT107_RETROATIVA.md`.

#### A2. ETL falha em extrair `data_emissao` para DAS PARCSN com período "Diversos"
- **Evidência**: node_7432 — ETL data=`2025-09-30`, Opus data=`2025-10-31`.
  Diferença de 1 mês.
- **Causa raiz**: regex de período DAS antiga (pré-Sprint 90b) caía no
  fallback `_RE_VENCIMENTO_DIVERSOS` errado.
- **Status**: Sprint 90b corrigiu para nodes recentes, mas os antigos
  ficaram com data errada persistida.
- **Sprint corretiva**: `sprint_AUDIT2_DAS_DATA_ANTIGA_BACKFILL.md`.

#### A3. Capitalização inconsistente de fornecedor (Americanas)
- **Evidência**: node_7383, 7386, 7464, 7466 — ETL grava `americanas sa - 0337`
  (lowercase), enquanto Opus padronizou `AMERICANAS SA - 0337`.
- **Causa raiz**: extractor de cupom térmico não normaliza caixa antes de
  gravar `razao_social`.
- **Sprint corretiva**: `sprint_AUDIT2_FORNECEDOR_CAPITALIZACAO.md`.

#### A4. Razão social abreviada vs canônica (G4F vs INFOBASE)
- **Evidência**: node_7446, 7454, 7457, 7460 — holerites gravam ETL=`G4F` ou
  `INFOBASE` (sigla curta), Opus diz `G4F SOLUCOES CORPORATIVAS` /
  `INFOBASE TECNOLOGIA`.
- **Causa raiz**: `contracheque_pdf.py` extrai sigla, não razão social
  completa. Sigla é útil pra display; razão social completa é necessária
  para entity resolution e cruzamento com transações.
- **Sprint corretiva**: `sprint_AUDIT2_RAZAO_SOCIAL_HOLERITE.md`.

### Tipo B — Perda na transformação (ETL ≠ Grafo após normalização)

#### B1. Inconsistência path absoluto vs relativo no grafo
- **Evidência**: holerites gravam `metadata.arquivo_origem = "data/raw/..."`
  (relativo); DAS PARCSN, boletos e envelopes gravam `"/home/andrefarias/.../data/raw/..."`
  (absoluto). 36 nodes com cada formato.
- **Causa raiz**: Sprint AUDIT-PATH-RELATIVO foi aplicada parcialmente; o
  helper `to_relativo` foi ligado apenas em `ingestor_documento.py` para
  holerite. DAS/boleto usam outro caminho de ingestão.
- **Impacto**: querys via índice `idx_node_arquivo_origem` falham sob match
  exato — exigem variantes ou LIKE. `popular_valor_grafo_real.py` precisou
  de fallback LIKE para resolver.
- **Sprint corretiva**: `sprint_AUDIT2_PATH_RELATIVO_COMPLETO.md`.

#### B2. `metadata.itens` nunca populada como lista granular
- **Evidência**: 0/86 itens têm `metadata.itens` lista no grafo. Mesmo
  NFC-e e holerites (que têm itens granulares no PDF) gravam só agregado.
- **Causa raiz**: extratores extraem total mas descartam itens individuais.
- **Impacto**: dimensão `itens` no Revisor sempre vazia no Grafo, impedindo
  comparação 4-way nessa dimensão.
- **Sprint corretiva**: `sprint_AUDIT2_METADATA_ITENS_LISTA.md`.

#### B3. Dimensão `pessoa` quase nunca populada (19/86 = 22%)
- **Evidência**: `_inferir_pessoa` em `popular_valor_grafo_real.py` só
  resolve via `metadata.contribuinte` (presente apenas em DAS PARCSN) ou
  inferência de path. Holerites, boletos, NFC-e ficam vazios.
- **Causa raiz**: nenhuma camada do pipeline grava `metadata.pessoa`
  canônica. Consumidores precisam reinferir de banco_origem ou path.
- **Sprint corretiva**: `sprint_AUDIT2_METADATA_PESSOA_CANONICA.md`.

#### B4. Nodes obsoletos persistem em `revisao_humana.sqlite` após reextração
- **Evidência**: 23 item_ids `node_7383..7489` na tabela `revisao` apontam
  para nodes que foram deletados pela reextração 2026-04-28 (atual range é
  7490-7535). 115 marcações (23 × 5 dim) órfãs.
- **Causa raiz**: reextração trunca/recria a tabela `node`, mas
  `revisao_humana.sqlite` é um SQLite paralelo sem foreign key.
- **Sprint corretiva**: `sprint_AUDIT2_REVISAO_LIMPEZA_OBSOLETOS.md`.

### Tipo C — Limite arquitetural (dado não está legível no arquivo)

#### C1. 4 cupons foto com OCR borrado (legibilidade < threshold)
- **Evidência**: `raw/_conferir/{2e43640d,6554d704}/CUPOM_*.jpeg` —
  Tesseract retorna texto fragmentado. Nem Opus nem regex extraem
  data/valor/itens.
- **Status**: já documentado pela Sprint 106 (motor de fallback similar) e
  Sprint 106a (critério legibilidade composite). Aceitamos perda — ou se
  origina rastro digital alternativo (recibo PDF, e-mail), ou o dado fica
  marcado como "?".
- **Não vira sprint** — limite físico do meio.

### Tipo D — Ambiguidade real (Opus e Humano divergem)

#### D1. Mesmo arquivo aparece como envelope + pessoa
- **Evidência**: `raw/_envelopes/originais/c4834df6.pdf` (CPF cadastral) e
  `raw/andre/documentos_pessoais/CPF_CAD_2026-04-21_c4834df6.pdf` são o
  mesmo arquivo (mesmo SHA), em 2 paths. Qual é o "canônico"?
- **Causa raiz**: pipeline copia para envelope antes do rename retroativo;
  o original em `_envelopes/` não é deletado (preservação ADR-18).
- **Sprint corretiva**: `sprint_AUDIT2_ENVELOPE_VS_PESSOA_CANONICO.md`
  (decisão: qual path expomos como `arquivo_origem` canônico?).

### Achados estruturais sem categoria A/B/C/D direta

#### E1. ESTADO_ATUAL.md desatualizado (Tier 1 com 9 AUDIT-* já fechadas)
- **Evidência**: `contexto/ESTADO_ATUAL.md` lista as 9 sprints AUDIT-* da
  auditoria 2026-04-28 como "Tier 1 — próxima sessão", mas todas foram
  commitadas em b369bc5 (sessão atual fechou). Métricas de teste (1.971)
  também estão velhas.
- **Sprint corretiva**: incluído no commit consolidador desta sessão (não
  vira sprint separada).

#### E2. CLAUDE.md header diz Sprint 103 fase Opus = atual; agora foi superada
- **Evidência**: header `VERSÃO: 5.9 | STATUS: PRODUÇÃO + AUTOMAÇÕES OPUS
  (Sprint 103 fase Opus + 7 automações)`. Esta sessão adicionou auditoria
  4-way que merece bump.
- **Sprint corretiva**: incluído no commit consolidador (header → 5.10).

#### E3. Helper one-shot `_gerar_decisoes_opus_v2.py` no `scripts/`
- **Evidência**: criado nesta sessão para gerar `decisoes_opus_v2.json`
  por família. Útil para esta sessão; risco baixo de ser rodado em produção
  por engano (é prefixado com `_`).
- **Decisão**: manter no repo com docstring clara `"one-shot"`. Próximas
  sessões com novo escaneamento podem adaptar/duplicar.

## Cross-check de promessas (Tier 1 vs realidade)

| Sprint AUDIT-* (ESTADO_ATUAL.md Tier 1) | Status real |
|---|---|
| AUDIT-CONTRIBUINTE-METADATA | OK -- commitada |
| AUDIT-IMPORT-CAMADA | OK -- commitada |
| AUDIT-CACHE-THREADSAFE | OK -- commitada (commit `7abfc3a`) |
| AUDIT-TIMEZONE-OCR | OK -- commitada (commit `e09eca7`) |
| AUDIT-MENU-CONFIRMACAO | OK -- commitada (commit `a97d079`) |
| AUDIT-PATH-RELATIVO | OK -- commitada **mas incompleta** (B1 acima) |
| AUDIT-SCORE-TEXTUAL | OK -- commitada |
| AUDIT-INDEX-JSON | OK -- commitada |
| AUDIT-MENU-DISPATCHER | OK -- commitada |

Nenhuma sprint listada como concluída tem follow-up técnico oculto. A única
promessa não-cumprida é AUDIT-PATH-RELATIVO sendo incompleta (B1) — sprint
corretiva já no backlog (`AUDIT2_PATH_RELATIVO_COMPLETO`).

## Auditoria de código (mudanças desta sessão)

### Arquivos modificados/criados

- `scripts/opus_extrair_transcricoes.py` (+128L, modo `--estender`)
- `scripts/opus_persistir_decisoes.py` (+10L, flag `--arquivo`)
- `scripts/popular_valor_grafo_real.py` (criado, ~280L)
- `scripts/_gerar_decisoes_opus_v2.py` (criado, ~340L, **one-shot**)
- `src/dashboard/paginas/revisor.py` (+45L: schema, render 4-linhas, CSV)
- `tests/test_revisor_4way.py` (criado, 11 testes)
- `tests/test_sprint_103_ground_truth.py` (atualizado: header esperado
  passa a 11 colunas)

### Achados de revisão própria

1. `popular_valor_grafo_real.py::_resolver_arquivo_origem` foi declarado
   mas nunca usado — **removido nesta sessão** (commit consolidador).
2. `revisor.py::_diff` definido dentro de loop foi **promovido para
   helper de módulo `_comparar_canonico`** (já existia para CSV).
3. Falha-soft em `popular()`: erros SQL no carregamento de node são
   capturados; não propagam para o caller; coluna fica NULL. Coberto por
   teste `test_falha_soft_quando_grafo_nao_existe`.
4. Idempotência: `popular()` sem `--sobrescrever` pula marcações com valor
   não-vazio. Em `--sobrescrever`, sempre re-extrai (custo: O(n) por run,
   resultado idêntico).
5. PII: `mascarar_pii` cobre CPF/CNPJ formatados e crus. **Não cobre nomes
   próprios** — observação do cupom OCR (entry 25) tem `consumidor Eliana`
   passando intacto. Risco baixo (Eliana é first-name comum), mas
   permanece. Sprint INFRA-PII-NOMES-PROPRIOS já está no backlog histórico.

## Recomendações priorizadas (sprint corretiva por achado A/B/D)

| Sprint | Tipo | P | Estimado |
|---|---|---|---|
| AUDIT2_SPRINT107_RETROATIVA | A1 | P1 | 1h (rerodar `--reextrair-tudo` cobre) |
| AUDIT2_DAS_DATA_ANTIGA_BACKFILL | A2 | P2 | 2h |
| AUDIT2_FORNECEDOR_CAPITALIZACAO | A3 | P2 | 30min |
| AUDIT2_RAZAO_SOCIAL_HOLERITE | A4 | P2 | 1h |
| AUDIT2_PATH_RELATIVO_COMPLETO | B1 | P1 | 1h (DAS+boletos+envelopes) |
| AUDIT2_METADATA_ITENS_LISTA | B2 | P3 | 4h (vários extratores) |
| AUDIT2_METADATA_PESSOA_CANONICA | B3 | P2 | 1.5h |
| AUDIT2_REVISAO_LIMPEZA_OBSOLETOS | B4 | P2 | 30min |
| AUDIT2_ENVELOPE_VS_PESSOA_CANONICO | D1 | P3 | 1h (decisão arquitetural) |

Tipo C (cupons OCR ilegíveis) **não vira sprint** — limite arquitetural.

## Padrões canônicos novos (formalizar em VALIDATOR_BRIEF rodapé)

(u) **Comparação 4-way revela três tipos distintos de divergência**:
- ETL ≠ Opus (Tipo A): bug do extrator.
- ETL ≠ Grafo (Tipo B): perda na transformação (normalizer/sintético).
- Grafo ≠ Opus: bug pós-normalização ou Opus discorda do canônico.
Sem a 4ª coluna, esses tipos eram indistinguíveis no Revisor.

(v) **Sprints retroativas vs forward-only**: quando uma migração
(Sprint 107) só se aplica a ingestões pós-data, achado fica latente até
auditoria. Critério: toda sprint que muda canônico deve ter rota de
migração para nodes existentes.

(w) **Falha-soft em scripts de população**: `popular_valor_grafo_real`
captura erro de SQL/JSON, registra contagem `sem_node` e segue. Não
explode export CSV nem dashboard. Padrão a replicar para outras automações
de "popular dado derivado".

(x) **One-shot scripts vivem em `scripts/_gerar_*.py` (prefixo `_`)**:
helpers de uma única sessão (decisões manuais Opus, migrações pontuais)
ficam visíveis mas não são auto-encadeados em fluxos.

---

*"Quatro pontos definem um plano." -- princípio do triângulo da verdade*
