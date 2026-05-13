---
id: AGENTIC-FALLBACK-01-EXTRACAO-PARA-TIPOS-SEM-EXTRATOR
titulo: Sprint AGENTIC-FALLBACK-01 -- Extração agentic estruturada para tipos sem
  extrator legacy
status: backlog
concluida_em: null
prioridade: P2
data_criacao: '2026-04-29'
fase: OUTROS
epico: 0
depende_de: []
tipo_documental_alvo: null
---

# Sprint AGENTIC-FALLBACK-01 -- Extração agentic estruturada para tipos sem extrator legacy

> **Slug ASCII para referência cruzada**: `agentic_fallback_01`. Em texto livre, usar "AGENTIC-FALLBACK-01".

**Origem**: prompt complementar do dono em 2026-04-29 (Gap 1 da sequência D7-extendida).
**Prioridade**: P1
**Onda**: 2 (ADR-08 supervisor Opus interativo)
**Esforço estimado**: 5h
**Depende de**: `VALIDAÇÃO-CSV-01` concluída (commit 9504d4a) -- reusa schema de status `{ok, erro, lacuna, pendente}`.
**Coexiste com (NÃO substitui)**: VALIDAÇÃO-CSV-01 (que continua para tipos COM extrator legacy).
**Fecha itens da auditoria**: gap P0 "8 documentos cotidianos sem regra YAML" (parcialmente -- destrava o caminho, não fecha cada tipo).

## Problema

Hoje, quando arquivo de tipo novo cai no inbox (ex: declaração de imposto de transporte, recibo de doação, carteirinha plano de saúde, RG/CNH escaneado, diploma):

1. `src/intake/classifier.py` retorna `tipo=None`.
2. Pipeline em `src/pipeline.py` não tem extrator para invocar.
3. Arquivo fica em `data/inbox/` indefinidamente.
4. `/validar-arquivo` exige `valor_etl` registrado via `registrar_extracao()`. Sem extrator, sem `registrar_extracao()`, sem `/validar-arquivo`.

A meta de "central completa de vida adulta" exige absorver tipos novos sem cada um virar sprint nova de extrator. Precisamos de um caminho onde **EU (Opus interativo, supervisor ADR-13)** extraio estruturado e o resultado fica registrado, mesmo sem cobertura legacy.

## Hipótese

A infraestrutura do CSV de validação (`src/load/validacao_csv.py`) já tem `registrar_extracao(arquivo, tipo_arquivo, campos)` -- o módulo NÃO assume que existe extrator legacy, apenas que algum agente registrou os campos. Logo, posso reusar o mesmo módulo escrevendo `tipo_arquivo="agentic:<tipo_proposto>"` ou similar, e adicionar uma flag `tem_extrator_legacy: bool` para distinguir os dois caminhos no dashboard e nas auditorias.

**Validar antes de codar** (Fase ANTES item 4):
- `grep -n "tem_extrator_legacy\|agentic_only" src/load/validacao_csv.py` -- esperado: zero ocorrências hoje.
- `grep -rn "ExtracaoAgentica\|sidecar.*agentic" src/` -- esperado: zero.
- Confirmar que `src/intake/classifier.py` retorna `None` documentado para tipos não reconhecidos (ler módulo).

## Implementação proposta

### Etapa 1 -- Schema canônico (~30min)

Criar `src/intake/extracao_agentica.py` com:

```python
class ExtracaoAgentica(TypedDict):
    sha8_arquivo: str
    tipo_proposto: str          # ex: "carteirinha_plano_saude_v1"
    tem_extrator_legacy: bool   # False para fallback agentic
    campos: dict[str, object]   # mesmo formato de registrar_extracao()
    confidence_opus: Literal["alta", "media", "baixa"]
    observacoes_opus: str
    timestamp_opus: str         # ISO 8601
```

### Decisão pendente do dono

Schema canônico do TypedDict acima é apenas proposta -- 5-10 linhas decisivas. O dono pode editar antes de implementar (modo learning):

- Faltam campos obrigatórios? (ex: `caminho_arquivo`, `sha256_completo`, `motivo_fallback`)
- `confidence_opus` deve ser enum ou float [0,1]?
- Quero versionar `tipo_proposto` (`_v1`) ou aceitar string livre?
- Devo guardar `nome_skill_origem` para rastrear de onde veio o sidecar?

### Etapa 2 -- Sidecar persistido (~1h)

Função `salvar_sidecar_agentic(extracao: ExtracaoAgentica) -> Path`:

- Path: `data/inbox/.agentic_only/<sha8>.json`.
- Formato: JSON UTF-8, 2 espaços de indentação, ordenado por chave.
- Atomicidade: tmp + replace (mesmo padrão de `validacao_csv.py`).
- Retorna path absoluto.

Função `listar_sidecars(filtro_tipo: str | None = None) -> list[ExtracaoAgentica]` para o dashboard.

### Etapa 3 -- Skill `/extrair-orfao` (~1h)

`.claude/skills/extrair-orfao/SKILL.md` -- Opus interativo lê arquivo via Read multimodal, propõe schema, salva sidecar, registra entrada no CSV de validação com `tipo_arquivo="agentic:<tipo_proposto>"`.

### Etapa 4 -- Aba dashboard "Documentos Órfãos" (~1h)

`src/dashboard/paginas/documentos_orfaos.py`:

- Lê `listar_sidecars()`.
- Tabela com colunas: sha8, tipo_proposto, confidence, data_extracao, link para arquivo original.
- Filtros: `confidence` (alta/media/baixa) e `tipo_proposto` (multiselect).
- Botão "Promover a extrator legacy" -- gera draft de spec em `docs/sprints/backlog/sprint_extrator_<tipo>.md` reusando template de `/propor-extrator`.
- Mascaramento PII (CPF/CNPJ) consistente com aba de Validação por Arquivo.

### Etapa 5 -- Integração no pipeline (~30min)

Em `src/pipeline.py`, após loop de extratores legacy:

```python
# Sidecars agentic ainda em data/inbox/.agentic_only/ continuam la --
# nao sao processados automaticamente. Apenas listados no dashboard
# e via skill /extrair-orfao.
```

NÃO automatizar processamento. ADR-13: supervisor é EU, manual, interativo.

### Etapa 6 -- Testes (~1h)

`tests/test_extracao_agentica.py`:

1. `test_schema_typed_dict_aceita_campos_canonicos`.
2. `test_salvar_sidecar_atomico` (tmp + replace funciona em fs lento).
3. `test_listar_sidecars_filtro_tipo`.
4. `test_sidecar_nao_substitui_extracao_legacy` (se sha8 já tem `tipo_arquivo` non-agentic, recusa overwrite).
5. `test_promover_a_extrator_gera_spec_draft`.
6. `test_pii_mascarada_no_dashboard`.

## Proof-of-work (runtime real)

Sequência demonstrada em log:

1. Coloco arquivo novo (ex: `recibo_doacao.pdf`) em `data/inbox/`.
2. Rodo `./run.sh --inbox` -- classifier retorna `tipo=None`, pipeline não toca.
3. Invoco `/extrair-orfao` -- Opus lê arquivo, propõe schema, salva sidecar.
4. `ls data/inbox/.agentic_only/` mostra `<sha8>.json` novo.
5. Abro dashboard, aba "Documentos Órfãos" -- arquivo aparece.
6. Clico "Promover a extrator legacy" -- gera `docs/sprints/backlog/sprint_extrator_recibo_doacao.md` draft.

## Acceptance criteria

- `src/intake/extracao_agentica.py` criado com TypedDict + 2 funções.
- Schema do TypedDict revisado pelo dono (ver "Decisão pendente").
- Skill `/extrair-orfao` registrada e funcional.
- Aba "Documentos Órfãos" no cluster Documentos do dashboard.
- 6 testes passando + baseline pytest crescida.
- `make lint` exit 0, `make smoke` 10/10.
- Proof-of-work runtime capturado em commit body.
- Spec movida para `concluidos/` com `concluida_em: YYYY-MM-DD`.

## Gate anti-migué

1. Hipótese declarada validada com `grep` (ver Hipótese acima).
2. Proof-of-work runtime real em log.
3. `make conformance-<tipo>` -- não aplicável (não é extrator novo, é fallback).
4. `make lint` exit 0.
5. `make smoke` 10/10.
6. `pytest tests/ -q` baseline mantida ou crescida.
7. Achados colaterais viraram sprint-ID OU Edit-pronto.
8. Validador (humano OU subagent) APROVOU. Auto-aprovação proibida.
9. Spec movida com frontmatter `concluida_em` + link commit.

## Não-objetivos (escopo creep)

- **Não fazer**: implementar processamento automático de sidecars (viola ADR-13).
- **Não fazer**: Opus extrair em background (sem cron, sem job).
- **Não fazer**: substituir VALIDAÇÃO-CSV-01 -- caminho paralelo.
- **Não fazer**: tocar em nenhum extrator legacy existente.

---

*"Tudo é visível. Nada bloqueia."* -- princípio D7.
