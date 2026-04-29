# Sprint LINK-AUDIT-01 -- Investigar documentos catalogados sem aresta documento_de (linking heuristico falha)

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P0
**Onda**: 4
**Esforço estimado**: 4h
**Depende de**: nenhuma
**Fecha itens da auditoria**: achado da auditoria de banco 2026-04-29

## Problema

Auditoria do grafo SQLite 2026-04-29 detectou taxas de vinculação muito baixas em alguns tipos:
- holerite: 20/24 = 83% (aceitável)
- das_parcsn_andre: 5/19 = 26% (RUIM)
- boleto_servico: 0/2 = 0% (CRITICO)
- nfce_modelo_65: 0/2 = 0% (CRITICO)
Documentos sem documento_de não aparecem no Extrato com Doc=ok, e o pacote IRPF (IRPF-01) não os incluirá. Perda silenciosa.

## Hipótese

3 hipóteses a validar empiricamente:
(a) janela temporal do linker está apertada para alguns tipos.
(b) tolerância de valor (diff_valor) esta rígida.
(c) pessoa do documento não casa com pessoa da transação (documento marcado como 'andre' mas transação como 'casal' por exemplo).

## Implementação proposta

1. Para cada tipo problemático, listar os documentos sem aresta.
2. Para cada um, buscar transação candidata (mesmo mês ±1, valor +-5%, qualquer pessoa).
3. Se encontrar, identificar qual critério bloqueia o linking.
4. Ajustar mappings/linking_config.yaml por tipo (boleto: janela 75d 0.005; nfce: janela 5d 0.001 estrita; das: já tem 60d).
5. Re-rodar linker e validar 80%+ vinculação por tipo.

## Proof-of-work (runtime real)

Após fix: das_parcsn 26%->=70%; boleto 0%->=80%; nfce 0%->=80%.

## Acceptance criteria

- Diagnóstico documentado por tipo.
- Config ajustada por tipo.
- Linker re-rodado com vinculação melhorada.
- Teste regressivo cobrindo o cenário detectado.

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
