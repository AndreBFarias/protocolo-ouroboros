---
id: LINK-AUDIT-01-INVESTIGAR-DOCUMENTOS-SEM-ARESTA-DOCUMENTO-DE
titulo: Sprint LINK-AUDIT-01 -- Investigar documentos catalogados sem aresta documento_de
  (linking heuristico falha)
status: concluída
concluida_em: '2026-05-15'
prioridade: P2
data_criacao: '2026-04-28'
fase: OUTROS
epico: 0
depende_de: []
tipo_documental_alvo: null
esforco_estimado_horas: 4
origem: plan pure-swinging-mitten (auditoria honesta 2026-04-29)
relatorio_auditoria: docs/auditorias/link_audit_01_diagnostico_2026-05-15.md
sprint_filha_proposta: LINK-AUDIT-02 (boost diff_valor em _calcular_score)
---

# Sprint LINK-AUDIT-01 -- Investigar documentos catalogados sem aresta documento_de (linking heuristico falha)

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P0
**Onda**: 4
**Esforço estimado**: 4h
**Depende de**: nenhuma
**Fecha itens da auditoria**: achado da auditoria de banco 2026-04-29

## Contexto

O grafo SQLite tem 52 documentos e 6086 transações, mas apenas 25 arestas
`documento_de` (linking_pct = 0,41 % das transações, 48 % dos documentos).
Auditoria 2026-04-29 marcou tipos com vinculação baixa (das_parcsn 26 %,
boleto 0 %, nfce 0 %) sem inspeção empírica do motor. Esta sprint executa
o diagnóstico via análise direta do grafo `data/output/grafo.sqlite` e
aplica ajustes cirúrgicos em `mappings/linking_config.yaml` apenas onde
houver ganho mensurável.

## Hipótese ou Validação ANTES

Antes de codar: rodar `grep` em `src/graph/linking.py` para confirmar
identificadores e ler 4-5 propostas de conflito existentes em
`docs/propostas/linking/*_conflito.md` para confirmar que o gargalo
está no `margem_empate` global de 0,05 (e não em janela/tolerância
por tipo, como sugere a auditoria 2026-04-29).

3 hipóteses a validar empiricamente:
(a) janela temporal do linker está apertada para alguns tipos.
(b) tolerância de valor (diff_valor) esta rígida.
(c) pessoa do documento não casa com pessoa da transação (documento marcado como 'andre' mas transação como 'casal' por exemplo).

## Não-objetivos

- **NÃO alterar `src/graph/linking.py`** -- mudança de motor (heurística
  de score, `margem_empate_por_tipo`, boost por `diff_valor=0`) fica para
  sprint-filha LINK-AUDIT-02.
- **NÃO modificar `pipeline.py`** -- risco de quebrar produção.
- **NÃO catalogar novos documentos** -- escopo é apenas linking dos 52
  documentos existentes no grafo.
- **NÃO alvejar a meta de 30 % de roadmap** -- estruturalmente
  inalcançável com 52 docs no grafo (teto = 0,85 %). Alvo realista:
  linking_pct (docs) > 48 %.

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
