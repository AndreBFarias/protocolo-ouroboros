# Sprint VALIDAÇÃO-CSV-01 -- Tracking de validação por arquivo (ETL × Opus × Humano)

> **Slug ASCII para referência cruzada**: `validacao_csv_01`. Em texto livre, usar "VALIDAÇÃO-CSV-01".

**Origem**: pedido do dono em 2026-04-29: "vamos marcando num csv da vida pra verificar se o pdf, xsx, csx, imagem e os valores extraidos estão certos. Aí isso resolve pra gente".
**Prioridade**: P1 (ferramenta de retrabalho -- bloqueia META-COBERTURA-TOTAL-01 fechar de verdade)
**Onda**: independente (cross-cutting)
**Esforço estimado**: 5h
**Depende de**: nenhuma (Revisor 4-way já existe, mas é por transação; este CSV é por arquivo)
**Fecha itens da auditoria**: complementa Revisor 4-way (Sprint D2/103) na granularidade arquivo-origem

## Problema

Revisor 4-way em `src/dashboard/paginas/revisor.py` valida transações individuais (ETL × Opus × Grafo × Humano). Mas hoje não há tracking por **arquivo de origem**: dado um PDF de holerite, foto de cupom, XML de NFe, CSV de extrato, o sistema não sabe **quais valores daquele arquivo foram extraídos, quais o Opus leu (visão multimodal), quais o humano confirmou ou corrigiu**.

Pedido do dono: ferramenta CSV simples onde cada linha = (arquivo, valor potencialmente extraível, valor real extraído por ETL, valor lido pelo Opus, valor confirmado pelo humano, status). Arquivo permite triagem manual em massa, descoberta de gaps de extração e priorização de retrabalho.

## Hipótese

CSV `data/output/validacao_arquivos.csv` com schema canônico cobre o caso. Ferramenta complementa (não substitui) o Revisor 4-way. Pipeline emite uma linha por valor potencial detectado em cada arquivo; Opus + Humano marcam status na sessão de validação.

## Schema canônico do CSV

```
sha8_arquivo, tipo_arquivo, caminho_relativo, ts_processado,
campo, valor_etl, valor_opus, valor_humano,
status_etl, status_opus, status_humano,
observacoes_humano
```

Onde:
- `sha8_arquivo`: 8 primeiros caracteres do SHA-256 do arquivo (deduplicação).
- `tipo_arquivo`: tipo declarado em `mappings/tipos_documento.yaml` (ex: `holerite`, `nfce_modelo_65`, `extrato_bancario`).
- `caminho_relativo`: caminho a partir da raiz do repo.
- `ts_processado`: timestamp ISO 8601 do processamento ETL.
- `campo`: nome canônico do campo (ex: `valor_total`, `salario_base`, `inss`, `data_emissao`, `cnpj_emissor`).
- `valor_etl`: o que o extrator capturou.
- `valor_opus`: o que eu (Opus interativo) leio quando abro o arquivo via Read multimodal.
- `valor_humano`: confirmação do dono na validação.
- `status_etl`, `status_opus`, `status_humano`: `ok` | `erro` | `lacuna` | `pendente`.
- `observacoes_humano`: livre, opcional.

## Como começar (operacional)

```bash
# Passo 1 -- conferir se o caminho de output já é usado
ls data/output/ | grep -i csv

# Passo 2 -- ver o que o Revisor 4-way já tem para evitar duplicar
grep -rn "ground.truth\|revisao_humana" src/dashboard/paginas/revisor.py | head

# Passo 3 -- listar tipos canônicos para cobrir
grep "^  - id:" mappings/tipos_documento.yaml | sort -u
```

## Implementação proposta

1. **Geração ETL** (`src/load/validacao_csv.py`):
   - Hook no pipeline: cada extrator que retorna items chama `registrar_no_csv(arquivo, items)`.
   - Append-only com header idempotente.
   - Deduplicação por `(sha8_arquivo, campo)` -- atualiza valor_etl se mudou, preserva valor_opus + valor_humano.

2. **Comando dedicado para Opus** (`scripts/validar_arquivo.py`):
   - `python scripts/validar_arquivo.py --sha8 <sha8>` abre arquivo via Read multimodal, compara com linhas existentes do CSV, atualiza coluna `valor_opus` + `status_opus`.
   - Modo batch: `--todos-pendentes` itera todas linhas com `status_opus=pendente`.

3. **UI dashboard** (aba "Validação por Arquivo" em `src/dashboard/paginas/validacao_arquivos.py`):
   - Filtro por tipo + status.
   - Edição inline de `valor_humano` + `status_humano` + `observacoes_humano`.
   - Persistência via overwrite controlado do CSV (lock + backup automático do estado anterior).
   - Indicador agregado: "% campos com 3 status concordantes" por tipo.

4. **Skill `/validar-arquivo`**: alias para `python scripts/validar_arquivo.py`.

5. **Integração no gate ANTI-MIGUE-01** (`make conformance-<tipo>`): cobertura mínima do CSV para aprovar extrator novo (ex: ≥3 amostras com 100% campos `status_humano=ok`).

## Proof-of-work (runtime real)

- Rodar `./run.sh --tudo` em ambiente isolado.
- Resultado: `data/output/validacao_arquivos.csv` populado com ≥100 linhas (cobrindo holerites + DAS + NFCe existentes).
- Rodar `python scripts/validar_arquivo.py --sha8 <sha8_de_um_holerite>` -- coluna `valor_opus` preenchida.
- Aba dashboard renderiza CSV com filtros funcionais.
- Sessão humana de validação (10 min): dono marca 10 linhas como `ok` ou `erro`.

## Acceptance criteria

- `data/output/validacao_arquivos.csv` gerado pelo pipeline com schema canônico.
- Script `validar_arquivo.py` funcional para lookup individual + batch.
- Aba dashboard "Validação por Arquivo" navegável, com filtros.
- Persistência humana funciona sem corromper CSV (lock + backup).
- ≥8 testes cobrindo: schema, deduplicação, lookup, lock, integração com extrator existente.
- Smoke 10/10, lint OK, baseline pytest crescida.

## Como saber que terminou

1. `data/output/validacao_arquivos.csv` existe após `./run.sh --tudo`.
2. CSV tem ≥1 linha por (arquivo × campo) para todos os 47 documentos atualmente no grafo.
3. `python scripts/validar_arquivo.py --sha8 <X>` consome ≤30s para 1 arquivo.
4. Aba dashboard renderiza ≤2s.
5. Skill `/validar-arquivo` declarada em `docs/SUPERVISOR_OPUS.md §3` (tabela pergunta → skill).
6. Frontmatter `concluida_em: <data>`.

## Achados colaterais durante execução

- Se Revisor 4-way precisar refactor para consumir este CSV → criar `sprint_revisor_consome_validacao_csv.md`.
- Se descobrir que algum tipo precisa schema customizado (ex: holerite tem N verbas variáveis) → criar `sprint_validacao_csv_<tipo>.md`.
- Se PII vazar no CSV (CPF/CNPJ pessoal) → criar `sprint_validacao_csv_pii_redactor.md` urgente.

## Gate anti-migué

1. Hipótese validada com grep antes de codar (Passo 2 de "Como começar").
2. Proof-of-work runtime real capturado em log.
3. `make conformance-<tipo>` quando aplicável (não -- não é extrator novo).
4. `make lint` exit 0.
5. `make smoke` 10/10.
6. `pytest` baseline crescida em ≥8 testes.
7. Achados colaterais viraram sprint-ID.
8. Validador (humano ou subagent) APROVOU.
9. Frontmatter `concluida_em: <data>`.

## Referências

- Pedido literal do dono em 2026-04-29.
- Sprint D2 + 103 (Revisor 4-way).
- META-COBERTURA-TOTAL-01 (sprint irmã, define o invariante).
- RETRABALHO-EXTRATORES-01 (consome este CSV para auditar cada extrator).
- ADR-13 (sem chamada Anthropic API: Opus = Claude Code interativo).
