# Sprint AUDIT2-ENVELOPE-VS-PESSOA-CANONICO -- Decidir path canonico em duplicatas

> **superseded_by**: `ADR-23-DRAFT` (`docs/sprints/backlog/sprint_adr_23_draft_adr_23_envelope_vs_pessoa_canonico.md`).
> Esta spec foi absorvida em ADR-23-DRAFT do plan pure-swinging-mitten (2026-04-29).
> Mantida em backlog/ como referência histórica até a ADR-23 ser publicada.

**Origem**: Auditoria self-driven 2026-04-29, achado D1 (ambiguidade real).
**Prioridade**: P3 (decisao arquitetural).
**Estimado**: 1h (planejamento) + tempo de execução depende da decisao.

## Problema

ADR-18 manda preservar `_envelopes/originais/` como rastro digital
imutavel. Pos-rename retroativo (Sprint 98), o mesmo arquivo (mesmo SHA)
existe em 2 paths:

- `data/raw/_envelopes/originais/c4834df6.pdf`
- `data/raw/andre/documentos_pessoais/CPF_CAD_2026-04-21_c4834df6.pdf`

`metadata.arquivo_origem` aponta para o primeiro (envelope) em alguns
casos, segundo (pessoa) em outros — sem regra clara.

Impacto: queries por `arquivo_origem` retornam path inconsistente.
Revisor 4-way mostra dimensao `pessoa` como inferencia do path, que
varia conforme qual eh o gravado.

## Hipoteses para decidir

1. **Manter envelope como canonico**: rastro original imutavel.
   Consumidores que precisam de path "humano" usam `metadata.arquivo_original`
   como secundario. (Mais conservador, sem rename do canonico.)

2. **Path da pessoa como canonico**: nome legivel facilita debug humano e
   inferencia de pessoa. Envelope vira `metadata.arquivo_envelope`.
   (Mais ergonomico para humano.)

3. **Ambos campos**: gravar ambos `arquivo_origem_envelope` e
   `arquivo_origem_pessoa`. Consumidor escolhe. (Mais completo, mais código.)

## Decisao a tomar

Discutir com supervisor humano. Spec atual não decide — registra a
ambiguidade.

## Acceptance

- ADR escrita decidindo entre as 3 hipoteses.
- Pipeline + grafo padronizam o canonico decidido.
- 0 nodes com `arquivo_origem` divergente da decisao da ADR.
