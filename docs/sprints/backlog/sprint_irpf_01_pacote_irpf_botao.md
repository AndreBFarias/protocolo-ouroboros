# Sprint IRPF-01 -- Botão 'Gerar pacote IRPF <ano>' → ZIP completo on-demand

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P1
**Onda**: 4
**Esforço estimado**: 5h
**Depende de**: MICRO-01
**Fecha itens da auditoria**: nenhum

## Problema

Pacote IRPF requer hoje compilar manualmente NFs, holerites, comprovantes, parcelamentos, DAS.

## Hipótese

Botão consulta grafo e empacota ZIP com: tabela XLSX (transações + fontes), pasta NFs/, pasta holerites/, pasta DAS/, pasta médico/, summary.md com totais por categoria IRPF.

## Implementação proposta

src/analysis/pacote_irpf.py + UI no dashboard.

## Proof-of-work (runtime real)

Gerar pacote 2025 → ZIP com 100% das fontes vinculadas.

## Acceptance criteria

- Botão funcional.
- ZIP estruturado.
- Summary com totais.

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
