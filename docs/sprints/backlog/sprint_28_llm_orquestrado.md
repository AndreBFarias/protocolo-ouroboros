## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 28
  title: "LLM Orquestrado: índice dos 3 modos de uso"
  touches:
    - path: docs/adr/ADR-08-supervisor-aprovador.md
      reason: "formalizar arquitetura provedor-de-IA-nunca-escreve-direto"
    - path: docs/llm_architecture.md
      reason: "diagrama dos 3 modos e links para sprints implementadoras"
    - path: CLAUDE.md
      reason: "seção de arquitetura LLM referenciando ADR-08"
  n_to_n_pairs:
    - [docs/adr/ADR-08-supervisor-aprovador.md, docs/llm_architecture.md]
    - [docs/llm_architecture.md, CLAUDE.md]
  forbidden:
    - src/llm/*  # esta sprint é só consolidação documental
    - mappings/*.yaml  # não mexe em regras determinísticas
  tests:
    - cmd: "make lint"
      timeout: 60
  acceptance_criteria:
    - "ADR-08 publicado em docs/adr/"
    - "docs/llm_architecture.md com diagrama dos 3 modos e links para Sprints 31-35 e 29a"
    - "Custo acumulado documentado, consistente com < $10/mês"
    - "Acentuação PT-BR correta"
    - "Zero emojis e zero menções a IA"
```

> Executar antes de começar: `make lint`

---

# Sprint 28 -- LLM Orquestrado: índice dos 3 modos de uso

**Status:** PENDENTE
**Data:** 2026-04-18
**Prioridade:** ALTA
**Tipo:** Documentação/Infra
**Dependências:** Sprint 31 (supervisor), Sprint 32 (OCR vision), Sprint 33 (narrativa), Sprint 34 (auditor), Sprint 35 (IRPF yaml), Sprint 29a (busca + pergunte)
**Desbloqueia:** Sprint 36 (audit final)
**Issue:** #13
**ADR:** ADR-08

---

## Como Executar

Esta sprint é **consolidadora**. Não implementa código de provedor de IA; formaliza a arquitetura que as Sprints 31-35 e 29a implementam em fatias.

**Comandos principais:**
- `make lint` -- validar markdown/acentuação
- Revisar `data/output/llm_costs.jsonl` gerado pelas sprints anteriores
- Ler `src/llm/` completo (entregue por Sprints 31-35)

### O que NÃO fazer

- NÃO escrever código de provedor nesta sprint (todo em Sprints 31-35)
- NÃO propor novos modos além dos 3 formalizados
- NÃO remover referências existentes ao supervisor nos docs

---

## Problema

A Sprint 28 original (proposta 2026-04-16) tentava entregar infraestrutura + 3 modos de uso de LLM numa única janela de 3-4 semanas. O plano 30/60/90 mostra que cada modo precisa de sprint própria:

- **Modo 1 (classificação e melhoria contínua)**: Sprint 31 entrega o supervisor inicial (Fase 1, §1.6 do plano); Sprint 34 entrega o auditor (Fase 2, §2.4).
- **Modo 2 (enriquecimento)**: Sprint 32 entrega OCR via visão (Fase 2, §2.2); Sprint 33 entrega narrativa mensal (Fase 2, §2.3); Sprint 35 entrega IRPF em YAML carregável (Fase 2, §2.5).
- **Modo 3 (consulta natural)**: Sprint 29a entrega busca global + "Pergunte ao sistema" (Fase 3, §3.2 e §3.3).

Também absorve o escopo residual da **Sprint 26 (Ingestão Universal)**: ingestão universal pós-90d passa a ser coberta pela Sprint 27b + sprints específicas por tipo de documento quando houver volume que justifique.

O deliverable concreto desta sprint é documental: **formalizar a arquitetura Supervisor-Aprovador** em ADR, e deixar claro como os 3 modos se encaixam.

---

## O que já existe (NÃO duplicar)

| Sistema | Arquivo | O que faz |
|---------|---------|-----------|
| Provedor abstrato | `src/llm/provider.py` | interface entregue pela Sprint 31 |
| Cache de respostas | `src/llm/cache.py` | SQLite + hash entregue pela Sprint 31 |
| Rastreador de custo | `src/llm/cost_tracker.py` | tokens e gasto entregues pela Sprint 31 |
| Schemas Pydantic | `src/llm/schemas.py` | contratos entregues pela Sprint 31 |
| Prompts versionados | `src/llm/prompts/*.md` | entregues por Sprints 31-35 |
| Auditor | `src/llm/auditor.py` | entregue pela Sprint 34 |

---

## Implementação

### Fase 1: ADR-08 -- Arquitetura Supervisor-Aprovador

**Arquivo:** `docs/adr/ADR-08-supervisor-aprovador.md`

Seções obrigatórias:
- **Contexto**: por que nenhum provedor de IA escreve direto em `mappings/*.yaml`, `categorias.yaml`, `overrides.yaml` ou no XLSX de produção.
- **Decisão**: todo output de IA é uma *proposição* em `mappings/proposicoes/YYYY-MM-DD_HHMM.yaml`. Humano aprova via dashboard. Aprovação gera PR/commit que atualiza os arquivos reais.
- **Consequências**: menor velocidade, maior confiança; taxa de regras determinísticas cresce com o tempo (meta: 85% -> 98% em 90 dias); o sistema fica **menos** dependente do provedor a cada ciclo.
- **Rejeitadas**: (a) IA escreve direto; (b) IA roda em tempo de extração; (c) IA substitui regex sem fallback.
- **Salvaguardas**: prompt caching obrigatório, kill switch por orçamento (`ANTHROPIC_MONTHLY_BUDGET_USD`), mascaramento de PII, versionamento de prompt.

### Fase 2: `docs/llm_architecture.md`

Diagrama textual dos 3 modos, com links para as sprints implementadoras:

```
Modo 1 (classificação/melhoria contínua)
  ├── Sprint 31 -- Supervisor inicial (fase 1 do plano)
  └── Sprint 34 -- Auditor de outputs (fase 2 do plano)

Modo 2 (enriquecimento)
  ├── Sprint 32 -- OCR via visão para contas de energia
  ├── Sprint 33 -- Narrativa mensal diagnóstica
  └── Sprint 35 -- IRPF via mappings/irpf_regras.yaml

Modo 3 (consulta natural)
  └── Sprint 29a -- Busca global + página "Pergunte ao sistema"
```

### Fase 3: Atualizar `CLAUDE.md`

Adicionar seção "Arquitetura LLM" com link para ADR-08 e `docs/llm_architecture.md`. Marcar Sprint 28 como "consolidadora" no Contexto Ativo.

---

## Armadilhas Conhecidas

| Ref | Armadilha | Como evitar |
|-----|-----------|-------------|
| A28-1 | Prompt drift invalidando cache retroativamente | Versão de prompt no frontmatter; migração via script de diff |
| A28-2 | Custo explodindo | Cache obrigatório + kill switch por orçamento mensal + modelos menores quando viável |
| A28-3 | PII vazando para provedor | Mascarar CPF, números de conta e senhas antes de enviar; teste unitário valida |
| A28-4 | Auditor propondo as mesmas regras rejeitadas | Hash de sugestão guardado; rejeição permanente |
| A28-5 | Humano aprovando sem olhar | Dashboard mostra 3 exemplos + taxa histórica de falso positivo por regra |
| A28-6 | Sprint 28 inchando de novo | Esta sprint é documental. Qualquer código entra em 31-35 ou 29a |

Referência: `docs/ARMADILHAS.md`

---

## Evidências Obrigatórias

- [ ] `make lint` passa
- [ ] `docs/adr/ADR-08-supervisor-aprovador.md` publicado
- [ ] `docs/llm_architecture.md` com diagrama dos 3 modos
- [ ] `CLAUDE.md` atualizado
- [ ] Custo acumulado em `data/output/llm_costs.jsonl` somado e documentado (meta: < $10/mês)
- [ ] Links em `ROADMAP.md` consistentes com as sprints 31-35 e 29a

---

## Verificação end-to-end

```bash
make lint
ls docs/adr/ADR-08-supervisor-aprovador.md docs/llm_architecture.md
grep -c "ADR-08" CLAUDE.md
```

---

*"A inteligência é saber qual pergunta fazer." -- adaptado de Lévi-Strauss*
