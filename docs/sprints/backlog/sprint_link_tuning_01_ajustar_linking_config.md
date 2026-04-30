# Sprint LINK-TUNING-01 -- Ajustar linking_config.yaml para subir cobertura de docs

**Origem**: achado colateral da auditoria `docs/auditorias/linking_2026-04-29.md` (Fase 0 do plano `glittery-munching-russell`).
**Prioridade**: P2
**Onda**: independente (não bloqueia Onda 4; complementa)
**Esforço estimado**: 3h
**Depende de**: nenhuma
**Fecha itens da auditoria**: hipóteses H1, H2, H3, H4 do relatório `linking_2026-04-29.md`

## Problema

22 dos 47 documentos no grafo estão sem aresta `documento_de` (47% órfãos). Distribuição:

- 14 DAS PARCSN (5/19 vinculados; âncora `vencimento` com janela 3d apertada)
- 4 holerites 13º (G4F adiantamento + integral, Infobase integral; janela temporal anômala vs holerite mensal)
- 2 NFCe modelo 65 (CNPJ do varejo não casa contraparte da transação cartão)
- 2 boleto_servico (mesma hipótese)

`make smoke` 10/10, mas o gap silencioso reduz cobertura de qualquer feature que dependa de `documento_de` (Onda 4 inteira).

## Hipótese

Tuning de `mappings/linking_config.yaml` consegue subir cobertura de docs vinculados de 25/47 (53%) para ≥40/47 (≥85%) sem mudar código de motor:

- Ampliar `janela_dias` de 3 para 14 em DAS PARCSN (âncora `vencimento`).
- Ampliar `janela_dias` de 3 para 14 em holerite (cobre 13º com pagamento antecipado).
- Reduzir `confidence_minimo` de 0.85 para 0.75 em nfce_modelo_65 quando CNPJ não casa contraparte.
- Adicionar entrada para `boleto_servico` com janela 7d, diff 5%.

## Implementação proposta

1. Editar `mappings/linking_config.yaml` adicionando/ajustando 4 blocos.
2. Rodar `./run.sh --reextrair-tudo --sim` em ambiente isolado para regenerar grafo com novo config.
3. Conferir cobertura via query do relatório `linking_2026-04-29.md`.
4. Capturar baseline antes/depois em commit body.

## Proof-of-work (runtime real)

Cobertura de docs vinculados sobe de 25/47 (53%) para ≥40/47 (≥85%) após reextração.

## Acceptance criteria

- 4 blocos editados em `linking_config.yaml`.
- Reextração regenera grafo sem erro.
- Cobertura sobe ≥85% docs vinculados.
- Smoke 10/10, lint OK, pytest baseline mantida.
- Testes de regressão: `tests/test_linking.py` continua verde.

## Gate anti-migué

Para mover esta spec para `docs/sprints/concluidos/`:

1. Hipótese declarada validada com query SQL antes de codar.
2. Proof-of-work runtime real capturado em log (cobertura antes/depois).
3. `make conformance-<tipo>` quando aplicável (não — não é extrator novo).
4. `make lint` exit 0.
5. `make smoke` 10/10 contratos.
6. `pytest` baseline mantida ou crescida.
7. Achados colaterais viraram sprint-ID OU Edit-pronto. Zero TODO solto.
8. Validador (humano ou subagent) APROVOU.
9. Frontmatter `concluida_em: YYYY-MM-DD` adicionado.
