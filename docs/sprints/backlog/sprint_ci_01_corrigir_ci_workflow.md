# Sprint CI-01 -- Corrigir CI: pytest com fallback silencioso + falta smoke + falta acentuação

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P0
**Onda**: 0
**Esforço estimado**: 1h
**Depende de**: nenhuma
**Fecha itens da auditoria**: achado da auditoria visual+devops 2026-04-29

## Problema

.github/workflows/ci.yml tem 3 problemas críticos:
1. `pytest tests/ -v --tb=short || echo 'Nenhum teste'` — o `||` MASCARA falha. CI nunca falha por causa de teste vermelho.
2. Não roda `make smoke` (10 contratos aritméticos).
3. Não roda `scripts/check_acentuacao.py` (regra inviolável #1).
Resultado: CI verde dá falsa segurança. Sprint 55 (1.761 tx classificadas erradas) passou direto pelo CI antigo.

## Hipótese

Remover `||` do passo de pytest. Adicionar steps para `make smoke` e `python scripts/check_acentuacao.py --all`. CI passa a falhar de verdade quando regressão é introduzida.

## Implementação proposta

1. Editar .github/workflows/ci.yml: trocar pytest por linha sem `||`.
2. Adicionar step 'Smoke aritmético': `make smoke` (precisa do XLSX, rodar `make process` com fixture sintética antes OU pular se não houver XLSX e marcar como warning).
3. Adicionar step 'Acentuação PT-BR': `python scripts/check_acentuacao.py --all`.
4. Adicionar status badge no README.

## Proof-of-work (runtime real)

Forçar PR com teste falhando → CI vermelho. Forçar PR com 'funcao' sem acento → CI vermelho.

## Acceptance criteria

- ci.yml sem `||` em pytest.
- Step de smoke + acentuação.
- Badge no README.
- PR de teste forçado falha o CI.

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
