---
concluida_em: 2026-04-24
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 93a
  title: "Investigar dedup agressiva nos extratores bancários (família A)"
  depends_on:
    - sprint_id: 93
      artifact: "docs/auditoria_extratores_2026-04-23.md"
    - sprint_id: F
      artifact: "testes bancários diretos (recomendável antes de mexer no parser)"
  touches:
    - path: src/transform/deduplicator.py
      reason: "possível ajuste se encontrar hash colidindo tx legítimas"
    - path: src/extractors/itau_pdf.py
      reason: "análise do parser para linhas duplicadas vs deduplicáveis"
    - path: src/extractors/santander_pdf.py
      reason: "idem"
    - path: src/extractors/c6_cc.py
      reason: "idem"
    - path: src/extractors/nubank_cartao.py
      reason: "idem"
    - path: src/extractors/nubank_cc.py
      reason: "idem"
    - path: docs/auditoria_familia_A_2026-xx-xx.md
      reason: "relatório técnico com diagnóstico por banco + fix proposto"
  forbidden:
    - "Aplicar fix sem antes documentar a causa raiz no relatório"
    - "Mexer em 2 extratores em commits que se intercalam (commit atômico por banco)"
    - "Quebrar contrato smoke -- smoke 8/8 antes E depois"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/ -q"
    - cmd: "make smoke"
    - cmd: ".venv/bin/python scripts/auditar_extratores.py --tudo"
  acceptance_criteria:
    - "Relatório docs/auditoria_familia_A_2026-xx-xx.md explicando delta de cada um dos 5 bancos"
    - "Cada delta tem causa raiz identificada (dedup agressiva real vs bug de parser)"
    - "Se bug de parser: commit atômico por banco com fix + teste de regressão"
    - "Se dedup agressiva legítima: documentar no relatório e marcar como esperado"
    - "Após fix, rodar scripts/auditar_extratores.py novamente -- delta reduzido ou justificado"
    - "Baseline de testes >=1285 (pós-Sprint F) mantida ou cresce"
```

---

# Sprint 93a — investigar dedup agressiva (família A)

**Status:** BACKLOG
**Prioridade:** P1 (afeta confiabilidade dos totais por banco)
**Origem:** `docs/auditoria_extratores_2026-04-23.md` §Família A
**Dependência recomendada:** Sprint F primeiro (ter testes diretos facilita bisect)

## Problema

Sprint 93 detectou que 5 extratores bancários (itau_cc, santander_cartao, c6_cc, nubank_cartao, nubank_cc) têm delta não-zero entre soma bruta do extrator vs soma consolidada no XLSX:

| Banco | Bruto extrator | XLSX | Delta | Tipo |
|---|---:|---:|---:|:-:|
| itau_cc (single-file) | R$ 44.065 | R$ 44.065 | R$ 0,00 | OK |
| itau_cc (diretório) | 5 extratos × média | XLSX consolidado | ≠ 0 | **A** |
| santander_cartao | 1000 tx | 110 tx no XLSX | R$ 141.668 | **A** |
| c6_cc | 2023 tx | 560 tx no XLSX | R$ 739.192 | **A** |
| nubank_cartao | consolidado | XLSX | R$ 222.250 | **A** |
| nubank_cc | consolidado | XLSX | R$ 889.234 | **A** |

Hipótese: dedup agressiva (hash colidindo transações legítimas com mesma data+valor+descrição próxima) OU bug do parser (agrupando parcela como linha única).

## Escopo

### Fase 1 -- Diagnóstico por banco (~2h)

Para cada um dos 5 bancos:
1. Escolher 1 mês com delta alto.
2. Listar TODAS as linhas brutas do extrator para aquele mês.
3. Listar todas as linhas do XLSX para (banco + mes_ref).
4. Identificar diff (linhas no bruto que sumiram no XLSX).
5. Classificar cada linha sumida:
   - (a) **Dedup legítimo**: tx idêntica em outro banco/fonte (transferência real).
   - (b) **Bug parser**: tx com mesmo hash mas conteúdo distinto (parcela, estorno).
   - (c) **Consolidação intencional**: layout do extrator agrupa que o XLSX separa.

### Fase 2 -- Fixes atômicos (~3h estimado, dependente do diagnóstico)

Se (b) bug parser:
- Commit atômico por banco.
- Teste de regressão usa fixture sintética reproduzindo o bug.
- Smoke aritmético antes/depois -- delta precisa cair.

Se (a) ou (c): documentar no relatório e **não mexer**. Ajustar whitelist do `scripts/auditar_extratores.py` para não flagrar como divergência.

### Fase 3 -- Reexecutar auditoria automatizada

```bash
.venv/bin/python scripts/auditar_extratores.py --tudo
```

Delta esperado: todos os 5 bancos passam a exibir OK ou "divergência documentada" (com razão técnica).

## Armadilhas

- **Deduplicador da Sprint 68 é sofisticado**: usa nome canônico + hash composto. Mexer aqui pode quebrar TI-Vitória.
- **Sprint 87b introduziu `_hash_transacao`**: verificar se a coluna `identificador` do XLSX não está sendo usada como chave única antes do desambiguador.
- **Volume real 2022-2023** tem casos legítimos de Pix idêntico em datas próximas (PIX mensal para mesmo fornecedor) -- NÃO é dedup bug.
- **Testes indiretos** (`test_deduplicator.py`, `test_transferencia_interna.py`) não cobrem parser específico -- Sprint F cobre.

## Proof-of-work

- `docs/auditoria_familia_A_2026-xx-xx.md` com tabela banco × causa × ação.
- `scripts/auditar_extratores.py --tudo` pós-fix com delta reduzido.
- Commits atômicos (1 por banco ajustado).
- Baseline de testes mantida/crescente.

---

*"Dedup é útil até onde a similaridade é verdadeira; além disso, é perda silenciosa." -- princípio de dedup honesto*
