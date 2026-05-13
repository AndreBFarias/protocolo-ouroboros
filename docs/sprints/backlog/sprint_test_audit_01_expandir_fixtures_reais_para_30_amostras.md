---
id: TEST-AUDIT-01-EXPANDIR-FIXTURES-REAIS-PARA-30-AMOSTRAS
titulo: Sprint TEST-AUDIT-01 -- Expandir fixtures reais de 6 para 30+ (item 28 da
  auditoria honesta)
status: backlog
concluida_em: null
prioridade: P2
data_criacao: '2026-04-28'
fase: OUTROS
epico: 0
depende_de: []
tipo_documental_alvo: null
---

# Sprint TEST-AUDIT-01 -- Expandir fixtures reais de 6 para 30+ (item 28 da auditoria honesta)

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P1
**Onda**: 3
**Esforço estimado**: 8h
**Depende de**: nenhuma
**Fecha itens da auditoria**: item 28 da auditoria honesta 2026-04-29

## Problema

1.987 testes mas só 6 fixtures reais (PDF/PNG/XML) em tests/fixtures/. Resto é sintético via factory. Bug Sprint 55 (1.761 tx classificadas erradas) passou por 1.530 testes verdes porque nenhum cobria o caso real. Risco continua até hoje.

## Hipótese

Para cada extrator (22), incluir pelo menos 1 fixture real redactada (PII mascarada com sed). Total: ~30 fixtures. Cada uma com teste regressivo que carrega o arquivo e valida output.

## Implementação proposta

1. Coletar 1 amostra real por extrator (22 extratores).
2. Mascarar PII via script `scripts/mascarar_pii_fixture.py`.
3. Salvar em tests/fixtures/<extrator>/<amostra>.pdf.
4. tests/test_fixture_real_<extrator>.py com teste de carga + validação de campos extraídos.
5. CI roda fixture real em todo PR (CI-01 dependência).

## Proof-of-work (runtime real)

Cobertura de fixtures reais: 6 -> 30+. CI roda os 22 testes em <30s. Zero PII versionada (grep regex CPF/CNPJ vazio).

## Acceptance criteria

- 30+ fixtures reais redactadas.
- 22 testes regressivos em CI.
- Script de mascaramento PII auditado.
- Zero PII em git.

## Gate anti-migué

Para mover esta spec para `docs/sprints/concluidos/`:

1. Hipótese declarada validada com `grep` antes de codar.
2. Proof-of-work runtime real capturado em log.
3. `make conformance-<tipo>` exit 0 quando aplicável (>=3 amostras 4-way).
4. `make lint` exit 0.
5. `make smoke` 10/10 contratos.
6. `pytest` baseline mantida ou crescida.
7. Achados colaterais viraram sprint-ID OU Edit-pronto. Zero TODO solto.
8. Validador (humano ou subagent) APROVOU.
9. Frontmatter `concluida_em: YYYY-MM-DD` adicionado.
