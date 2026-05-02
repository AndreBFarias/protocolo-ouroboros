# Histórico de Mudanças

Todas as alterações relevantes do projeto estão documentadas aqui.

---

## [Unreleased]

### Investigated

- **Sprint MICRO-01a-FOLLOWUP-NFCE-REAIS: validação executada em 2026-05-01,
  spec permanece em backlog com escopo refinado.**
  Ciclo `./run.sh --full-cycle` rodado com 3 PDFs em
  `data/raw/andre/nfs_fiscais/nfce/`. Achados que invalidam parcialmente
  a premissa original e identificam o gap real:
  (1) Os 2 NFCe nodes no grafo (id 7557 e 7558) NÃO são placeholders
  PoC como a spec dizia: `arquivo_origem` confirma origem em
  `nfce_americanas_compra.pdf` (R$ 629.98) e `nfce_americanas_supermercado.pdf`
  (R$ 595.52), com `data_emissao=2026-04-19`. Cada NFCe tem 33 items
  granulares linkados via `contem_item`.
  (2) `transacoes_com_items` continua em `0` porque `linking.py` não
  encontrou transação bancária em janela `±1 dia` com diferença de valor
  `<= 1%` para nenhum dos 2 NFCe (pagamento provavelmente em dinheiro,
  cartão crédito sem fatura fechada, ou PIX/voucher fora do OFX).
  (3) `fornecedor_cnpj` ficou `None` nos NFCe — extrator não recuperou
  via OCR, degradando recall mesmo se transação CNPJ-Americanas existisse.
  (4) Achado colateral: o 3º PDF `NFCE_2026-04-19_6c1cc203.pdf` foi
  capturado pelo `ExtratorCupomGarantiaEstendida` ao invés do
  `ExtratorNfcePDF` ("2 bilhete(s) ingerido(s)" em vez de 1 NFC-e) —
  misclassificação do roteador de extrator. Sub-sprint candidata
  `MICRO-01a-FOLLOWUP-2_NFCE_VS_GARANTIA_CLASSIFICADOR` registrada como
  achado, não aberta automaticamente (aguarda decisão do dono).
  Spec atualizada em `docs/sprints/backlog/sprint_micro_01a_followup_nfce_reais.md`
  com seção "Atualização 2026-05-01" detalhando achados. Mantemos config
  estrita do linking NFCe (janela 1d, diff 1%, confidence 85%) por
  precisão > recall — a spec original proíbe tuning prematuro sem
  evidência empírica.

### Fixed

- **Sprint GARANTIA-EXPIRANDO-01: warning intermediário de proximidade no ingestor.**
  Diagnóstico revelou bug duplo no teste `test_ingestor_loga_warning_quando_expirando`
  (não no extrator/ingestor como a spec hipotetizou): (a) o caplog capturava
  o logger `graph.ingestor_documento`, mas após Sprint ANTI-MIGUE-08 a função
  `ingerir_garantia` migrou para `src.graph.ingestor_especiais` (re-exportada
  por contrato público), e logger real é `graph.ingestor_especiais`; (b) o
  teste chamava `extrair_garantias()` sem congelar `hoje`, e a fixture
  `garantia_expirando.txt` (data_fim 2026-04-30) já era EXPIRADA em runtime
  real (2026-05-01), nunca disparando o branch `if garantia.get("expirando")`
  que já existia no ingestor (`ingestor_especiais.py:354-360`). Fix cirúrgico
  no teste: parsear via `_parse_garantia(_ler(EXPIRANDO), hoje=date(2026, 4, 20))`
  diretamente, depois invocar `ingerir_garantia(grafo_temp, parsed, ...)` —
  garante `expirando=True` independente da data do runner. Logger ajustado
  para `graph.ingestor_especiais`. `@pytest.mark.xfail(strict=True)` removido.
  Cobertura adicional: novo `test_ingestor_nao_loga_warning_quando_vigente_acima_30d`
  com fixture Electrolux 12m (data_fim ~2027) confirma silêncio quando
  `expirando=False` (acceptance #3 da sub-sprint). Spec movida de
  `docs/sprints/backlog/` para `docs/sprints/concluidos/`. Total: `2.177 →
  2.179 passed`, `2 → 1 xfailed`.

- **Sprint IRPF-02.x: ranking top-1 do `linking_medico` desempata por `tag_irpf`.**
  Quando duas candidatas para a mesma receita médica tinham `quem_bate=True`,
  ambas saturavam em score `1.0` por causa do clamp upper, e o sort estável
  devolvia a primeira inserida — sem nunca dar preferência à candidata com
  `tag_irpf=dedutivel_medico` (sinal forte do `irpf_tagger`). Fix cirúrgico
  em `src/transform/linking_medico.py::_calcular_score`: removido o teto
  do clamp (`if score > 1.0: score = 1.0` apagado), mantido apenas o floor
  `>= 0`. Bonus extras agora criam separação real no ranking. O contrato
  externo do grafo é preservado: o `peso` gravado na aresta continua
  clampado em `[0, 1]` via `min(top_evidencia["confidence"], 1.0)` no
  ponto de gravação (`db.adicionar_edge`), e a evidência registra o
  `confidence` cru para auditoria. Docstring atualizada com a nova
  semântica. Teste `test_dois_candidatos_pega_o_de_score_mais_alto`
  perdeu o `@pytest.mark.xfail(strict=True)` e agora passa em runtime
  real, validando `assert arestas[0].dst_id == tx_forte.id`. Spec
  movida de `docs/sprints/backlog/` para `docs/sprints/concluidos/`.
  Total: `2.176 → 2.177 passed`, `3 → 2 xfailed`.

### Added

- **Sprint MOB-bridge-3: marcos auto-gerados pelo backend Python.**
  Pacote novo `src/marcos_auto/` com cinco módulos: `dedup.py`
  (`hash_marco` via SHA-256 truncado em 12 chars sobre
  `tipo|data|descricao`, idempotente), `parser.py` (lê frontmatter
  YAML do Vault Mobile com fallback defensivo a YAML malformado),
  `escrita.py` (`write_md_atomic` reaproveita o padrão `.tmp` +
  `os.replace` da MOB-bridge-2 adaptado para Markdown com
  frontmatter), `heuristicas.py` (cinco funções puras:
  `tres_treinos_em_sete_dias`, `retorno_apos_hiato`,
  `sete_dias_humor`, `trinta_dias_sem_trigger`,
  `primeira_vitoria_da_semana`), e
  `__init__.py::gerar_marcos_auto(vault_root)` que aplica todas as
  heurísticas em sequência, calcula hash de cada marco e grava
  `marcos/<data>-auto-<hash>.md` apenas se o arquivo não existe
  (skip silencioso para idempotência). Plugado em
  `mobile_cache.gerar_todos` como passo anterior aos caches; falha
  em marcos não derruba caches (defesa em depth). Cooperação
  client/backend (M11): mesmo algoritmo de hash garante que arquivos
  nunca duplicam quando ambos rodam. Marcos manuais existentes
  (filename sem `-auto-`) nunca são sobrescritos. Descrições secas
  conforme ADR-0005 (sem motivacional, sem comparativos negativos).
  32 testes novos: 8 cobrindo hash dedup determinístico, 16 cobrindo
  as cinco heurísticas (incluindo separação por pessoa, ausência de
  disparo prematuro, idempotência por autor), e 8 cobrindo
  orquestração com vault sintético em `tmp_path` (preservação de
  marcos manuais, robustez a YAML quebrado, casamento entre filename
  e hash do frontmatter). Validado em runtime real no Vault em
  `~/Protocolo-Ouroboros/`: 3 treinos em janela curta geraram 1
  marco `tres_treinos_em_sete_dias`; diário emocional `modo: vitoria`
  gerou 1 marco `primeira_vitoria_da_semana`; segunda execução de
  `make sync` manteve contagem total estável (idempotência
  confirmada). Baseline 2.144 → 2.176 passed (+32, zero regressão).
- **Sprint MOB-bridge-2: geradores de cache JSON para o Mobile.** Pacote
  novo `src/mobile_cache/` com três módulos: `atomic.py`
  (`write_json_atomic` via `.tmp` + `os.replace`), `humor_heatmap.py`
  (cobre 90 dias retroativos lendo `daily/` e `inbox/mente/humor/`,
  agrega células por data+autor, calcula `media_humor_30d`,
  `registros_30d`, `registros_total` por pessoa) e `financas_cache.py`
  (semana ISO atual a partir do XLSX consolidado, `top_categorias` top
  5 com percentual, `delta_textual` heurístico vs média de 12 semanas,
  20 últimas transações). Função `gerar_todos(vault_root, xlsx_path)`
  orquestra ambos. Saídas em `<vault>/.ouroboros/cache/` com
  `schema_version: 1` conforme contrato cruzado da ADR-0012 (Mobile).
  Identidade canônica `pessoa_a`/`pessoa_b`/`casal` em todos os campos
  `autor` (Regra -1). Integrado ao `--full-cycle` no `run.sh` como
  passo final com falha-soft; nova flag `--mobile-cache` standalone
  dispara apenas o gerador. Targets `make sync` (alias de
  `--full-cycle`) e `make mobile-cache` (apenas caches) adicionados.
  33 testes novos cobrindo atomic write, humor heatmap, finanças
  semanais, idempotência e CLI.

### Refactored

- **Sprint MOB-bridge-1: identidade genérica `pessoa_a` / `pessoa_b` no
  backend.** Schema do XLSX (coluna `quem`), normalizer, 5 extratores
  bancários, detector e dashboard passam a operar sobre identificadores
  genéricos. Nomes reais ficam apenas em `mappings/pessoas.yaml`
  (gitignored, campo `display_name`) e são resolvidos em runtime via
  `src.utils.pessoas.nome_de` para apresentação local-first (ADR-24).
  Resolver canônico em `src/utils/pessoas.py` substitui as cópias de
  lógica de identidade espalhadas. XLSX já gerados migrados in-place
  via `scripts/migrar_quem_generico.py` (idempotente, com backup
  automático). `scripts/check_anonimato.sh` adicionado para travar
  regressões. ADR-23 e ADR-24 formalizam a decisão (cruzamento com
  ADR-0011 do companion mobile).

---

## [1.0.1] - 2026-04-15

### Adicionado
- Código de Conduta (Contributor Covenant v2.1)
- Política de Segurança (SECURITY.md)
- Templates de issue e PR para GitHub
- Workflow CI (lint + testes)
- .mailmap para unificação de identidade git
- Badge CI no README

### Corrigido
- Licença MIT corrigida para GPLv3 em pyproject.toml e README
- pyproject.toml modernizado com [build-system], classifiers e URLs

---

## [Sprint 4] - 2026-04-14

### Adicionado
- Sistema de overrides manuais para correção de categorização pós-pipeline
- IRPF tagger automático com 21 regras de classificação fiscal
- 79 transações tagueadas automaticamente para declaração de imposto de renda
- Validador de integridade com 6 checks (totais, categorias, classificações, duplicatas, receita, despesa)

---

## [Sprint 3] - 2026-04-14

### Adicionado
- Dashboard Streamlit interativo com tema dark
- Página de visão geral com métricas consolidadas e gráficos de evolução
- Página de categorias com drill-down por tipo de gasto e classificação
- Página de extrato com filtros dinâmicos e busca textual
- Página de contas fixas com status de pagamento mensal

---

## [Sprint 2] - 2026-04-14

### Adicionado
- Categorização automática 100% funcional com 111 regras regex
- Makefile com alvos padronizados (check, lint, run, install)
- Script pre-commit check para validação antes de commits
- Extrator OCR para contas de energia via Tesseract

### Melhorado
- Cobertura de categorização sem lacunas em transações conhecidas

---

## [Sprint 1] - 2026-04-14

### Adicionado
- Pipeline ETL completo com orquestração via `src/pipeline.py`
- 6 extratores implementados (Itaú PDF, Nubank CSV, C6 CSV, C6 XLS, Santander PDF, Neoenergia OCR)
- 2.859 transações extraídas e processadas
- XLSX final com 8 abas (extrato, renda, dívidas_ativas, inventário, prazos, resumo_mensal, irpf, análise)
- 44 relatórios mensais gerados automaticamente
- Importação de histórico do XLSX antigo (ago/2022 a jul/2023)
- Scaffold completo do projeto (estrutura de pastas, pyproject.toml, install.sh, run.sh)
- Sistema de categorização por regex com mapeamento YAML
- Deduplicação de transferências internas entre contas

---

<!-- "Nós somos o que fazemos repetidamente. Excelência, portanto, não é um ato, mas um hábito." -- Aristóteles -->
