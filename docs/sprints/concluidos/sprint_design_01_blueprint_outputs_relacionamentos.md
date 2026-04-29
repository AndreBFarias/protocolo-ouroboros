---
concluida_em: 2026-04-28
---

# Sprint DESIGN-01 -- Blueprint: outputs esperados + docs esperados + relacionamentos + aparência de relatórios

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P0
**Onda**: 0
**Esforço estimado**: 6h
**Depende de**: nenhuma
**Fecha itens da auditoria**: item AA da revisão 2026-04-29 (visão do dono)

## Problema

Antes de codar Onda 3-6, falta consolidar a visão de outputs em documento único: quais relatórios o sistema gera, quais documentos espera receber por pessoa, qual a aparência canônica de cada relatório, quais relações entre dados são primárias vs derivadas. Sem esse blueprint, cada sprint executa palpite isolado e a central de vida adulta vira agregado sem cara.

## Hipótese

Documento `docs/BLUEPRINT_VIDA_ADULTA.md` declarativo cobrindo: (1) catálogo de tipos de documento esperados por pessoa por domínio (financeiro, identidade, saúde, profissional, acadêmico); (2) outputs canônicos do dashboard (XLSX, JSON cache, ZIP IRPF, ZIP pacote anual de vida); (3) relacionamentos entre nodes do grafo com diagrama; (4) aparência de cada relatório (mockup ASCII ou wireframe link); (5) gaps de cobertura aceitáveis vs inaceitáveis.

## Implementação proposta

1. Criar `docs/BLUEPRINT_VIDA_ADULTA.md` (~400 linhas, 5 seções).
2. Mockup ASCII das 5 telas-âncora dos 5 clusters do dashboard.
3. Diagrama de classes do grafo (mermaid ou ASCII).
4. Tabela tipos esperados × pessoa × domínio × prioridade.
5. Sprints existentes ganham referência cruzada para o blueprint.

## Proof-of-work (runtime real)

Documento publicado e linkado de CLAUDE.md + SPRINTS_INDEX.md. Cada sprint da Onda 3-6 cita seção do blueprint que endereça.

## Acceptance criteria

- BLUEPRINT publicado.
- 5 mockups ASCII das telas-âncora.
- Tabela cobertura tipos × pessoa × domínio.
- Referência cruzada nas sprints DOC-* e OMEGA-*.

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
