---
id: INFRA-LINKING-NFE-TRANSACAO
titulo: '<!-- noqa: accent -->'
status: concluida
concluida_em: null
prioridade: P2
data_criacao: '2026-05-08'
fase: OUTROS
epico: 0
depende_de: []
tipo_documental_alvo: null
---

<!-- noqa: accent -->
---
id: INFRA-LINKING-NFE-TRANSACAO <!-- noqa: accent -->
titulo: Matcher massa transacao<->NF/cupom (valor + data + janela +-3d) para vincular transacoes a documentos <!-- noqa: accent -->
status: concluída
concluida_em: 2026-05-08
commit: d1413ba
prioridade: altissima
data_criacao: 2026-05-08
fase: CONCLUSAO_REAL
depende_de: [INFRA-PROCESSAR-INBOX-MASSA]
esforco_estimado_horas: 4
origem: docs/auditorias/VALIDACAO_END2END_2026-05-08.md (25/6086 vinculos transacao->documento; 0,4% cobertura) <!-- noqa: accent -->
---

# Sprint INFRA-LINKING-NFE-TRANSACAO <!-- noqa: accent --> — matcher em massa

## Contexto

Hoje há 25 vínculos `documento_de` entre transações e documentos (NF/cupom) em um universo de 6086 transações. Isso é 0,4% — distante da visão "cada gasto sabe qual NF gerou". Sprints anteriores (`linking_*`) implementaram o matcher, mas não foi rodado em massa após INFRA-PROCESSAR-INBOX-MASSA popular o grafo.

## Objetivo

1. Criar `scripts/linking_nfe_transacao_massa.py` que:
   - Lê todos nodes `transacao` do grafo.
   - Lê todos nodes `documento` com `tipo_documento` em {nfce_modelo_65, cupom_fiscal_foto, fatura_cartao, recibo_*, comprovante_pix}.
   - Para cada transação, busca documento candidato com:
     - `|valor_transacao - valor_documento| <= 0.05`
     - `|data_transacao - data_documento| <= 3 dias`
     - `categoria_compatível` (farmácia trans → cupom de farmácia, etc, via mapping `tipos_documento.yaml`).
   - Quando único candidato, cria edge `documento_de` com `peso=1.0`.
   - Quando múltiplos candidatos, cria com `peso=0.5` e flag `revisar_humano=true`.
   - Reporta totais.
2. Validar: testes em `tests/test_linking_massa.py` com fixtures.

## Validação ANTES

```bash
sqlite3 data/output/grafo.sqlite "SELECT COUNT(*) FROM edge WHERE tipo='documento_de'"
grep -rn "linking\|documento_de\|matcher" src/linking/ src/ 2>/dev/null | head
```

## Não-objetivos

- NÃO mover arquivos.
- NÃO inferir vínculos sem evidência (sem candidato → sem edge).
- NÃO sobrescrever vínculos manuais existentes (peso=1.0 humano).

## Proof-of-work

```bash
python scripts/linking_nfe_transacao_massa.py --dry-run
python scripts/linking_nfe_transacao_massa.py
sqlite3 data/output/grafo.sqlite "SELECT COUNT(*) FROM edge WHERE tipo='documento_de'"
# Esperado: subir de 25 -> >=500 vinculos
make lint && make smoke
.venv/bin/pytest tests/ -k linking -q
```

## Critério de aceitação

1. Edges `documento_de` passam de 25 para >=500 (depende da massa de docs gerada por INFRA-PROCESSAR-INBOX-MASSA).
2. Matches ambíguos flagueados com `revisar_humano=true` na evidência.
3. Drill-down farmácia: transação DROGASIL >R$ 50 tem cupom vinculado quando cupom existe no grafo.
4. Lint + smoke + pytest baseline.

## Referência

- Auditoria: `VALIDACAO_END2END_2026-05-08.md` casos 2+3.
- Sprints linking_* (concluídas anteriormente).

*"Match sem dado é heurística; match com dado é ouro." — princípio INFRA-LINKING-NFE-TRANSACAO <!-- noqa: accent -->*
