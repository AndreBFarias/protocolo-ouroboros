# Sprint DASH-01 -- Botão 'Gerar pacote anual de vida <ano>' (não só IRPF)

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P2
**Onda**: 6
**Esforço estimado**: 4h
**Depende de**: IRPF-01, OMEGA-94a, OMEGA-94b, OMEGA-94c, OMEGA-94d
**Fecha itens da auditoria**: item AB da revisão 2026-04-29 (visão do dono)

## Problema

Visão do dono: pacote IRPF é só 1 dos pacotes anuais. Pessoa também precisa: pacote Saúde (todas consultas, exames, despesas), pacote Profissional (contratos, certificados, holerites), pacote Acadêmico (histórico, diplomas, atividades), pacote Identidade (estado dos documentos com alertas de validade).

## Hipótese

Generalizar IRPF-01: botão único 'Pacote anual de vida <ano>' gera ZIP com 5 pastas (financeiro/saude/profissional/academico/identidade), cada uma com summary.md + arquivos vinculados via grafo. Filtro por pessoa (André/Vitória/Casal).

## Implementação proposta

1. src/analysis/pacote_anual_vida.py reusa IRPF-01 + adiciona agregadores por domínio.
2. Aba dashboard 'Pacote anual' com seletor (pessoa, ano, domínios marcados).
3. summary.md por domínio + summary geral cross-domínio.
4. ZIP estruturado: pacote_<pessoa>_<ano>.zip.

## Proof-of-work (runtime real)

Gerar pacote 2025 do casal → ZIP com 5 pastas + 5 summaries + todos arquivos vinculados via grafo.

## Acceptance criteria

- Botão funcional.
- ZIP estruturado.
- 5 summaries por domínio.
- Filtro por pessoa.

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
