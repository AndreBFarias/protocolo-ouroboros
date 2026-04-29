---
concluida_em: 2026-04-24
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: "82b"
  title: "Conta-espelho de cartão: emissão de linha TI virtual em pagamento de fatura"
  touches:
    - path: src/extractors/nubank_cartao.py
      reason: "detectar e emitir contraparte virtual (entrada) em linhas 'Pagamento recebido'"
    - path: src/extractors/c6_cartao.py
      reason: "substituir `return None` em REGEX_PAGAMENTO por emissão de linha virtual com flag _virtual"
    - path: src/extractors/santander_pdf.py
      reason: "capturar linhas de PAGAMENTO RECEBIDO e emitir espelho virtual"
    - path: src/transform/deduplicator.py
      reason: "ignorar linhas marcadas `_virtual=True` no somatório para evitar dupla contagem"
    - path: tests/test_conta_espelho_cartao.py
      reason: "garantir que espelho virtual não contamina totais e pareia com saída em CC"
  n_to_n_pairs:
    - ["flag `_virtual=True` no dict de Transacao", "deduplicator.marcar_transferencias_internas"]
  forbidden:
    - "Emitir linha virtual sem flag `_virtual` (contamina totais)"
    - "Contar valor virtual no KPIs receita/despesa do dashboard"
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/test_conta_espelho_cartao.py tests/test_transferencia_interna.py -v"
      timeout: 60
    - cmd: ".venv/bin/python scripts/smoke_aritmetico.py --strict"
      timeout: 30
  acceptance_criteria:
    - "Linhas virtuais carregam flag `_virtual=True` no dict e não aparecem em somatório de receita/despesa"
    - "Par saida-em-CC + espelho-no-cartão é marcado como Transferência Interna pelo deduplicator"
    - "Zero regressão em 47 testes TI Sprint 68b + 25 testes Sprint 82"
    - "Redução adicional da taxa de órfãos documentada em log da rodada"
  proof_of_work_esperado: |
    .venv/bin/python -c "
    import pandas as pd
    df = pd.read_excel('data/output/ouroboros_2026.xlsx', sheet_name='extrato')
    tis = df[df['tipo'] == 'Transferência Interna']
    # Depois desta sprint, nenhuma TI virtual aparece nos somatórios
    assert (~df['obs'].astype(str).str.contains('_virtual', na=False)).all()
    print('OK')
    "
```

---

# Sprint 82b — Conta-espelho de cartão

**Status:** BACKLOG
**Prioridade:** P2 (ganho marginal vs Sprint 82)
**Dependências:** Sprint 82 (canonicalizer variantes curtas)
**Origem:** Fase 4 da spec Sprint 82 adiada por auditoria empírica do executor

## Motivação

A Sprint 82 original previa 5 fases; apenas 4 foram implementadas (variantes curtas + testes). A Fase 4 (conta-espelho) foi adiada porque a auditoria do codebase mostrou que os três extratores de cartão descartam ou não capturam linhas de pagamento de fatura:

- **`nubank_cartao.py`**: CSVs de fatura (`date,title,amount`) não listam linha de pagamento recebido. Formato não contém esse dado na fonte.
- **`c6_cartao.py:146-148`**: detecta `REGEX_PAGAMENTO` e faz `return None` (descarte explícito).
- **`santander_pdf.py`**: REGEX_TRANSACAO não captura linhas de PAGAMENTO RECEBIDO (apenas compras).

Emitir a linha virtual exige:
1. Mudar o contrato do extrator: deixar de descartar + emitir linha com flag `_virtual=True`.
2. Propagar a flag pelo pipeline sem perder nas etapas intermediárias.
3. Ensinar o `deduplicator.marcar_transferencias_internas` a parear virtual(entrada) + real(saída).
4. Ensinar todos os consumers (KPIs, soma de categorias, smoke aritmético) a ignorar `_virtual` no somatório.

É uma sprint INFRA de 5 arquivos e alto risco de regressão — merece isolamento dedicado após Sprint 82 estabilizar em produção.

## Armadilhas conhecidas

| Ref | Armadilha | Mitigação |
|---|---|---|
| A82b-1 | Valor virtual soma na receita/despesa e infla KPI | Flag `_virtual` obrigatória + deduplicator filtra antes de agregar |
| A82b-2 | Espelho sem data precisa faz deduplicator falhar pareamento | Usar data do pagamento original, não data de fechamento da fatura |
| A82b-3 | Emitir 1 espelho por fatura mensal vs por linha de pagamento | Definir explicitamente: 1 espelho por valor pago (mesmo que 2 pagamentos no mesmo mês) |

## Validação

Ao final, roda comparação ANTES/DEPOIS na taxa de órfãos:

```bash
.venv/bin/python -c "
import pandas as pd
from src.transform.canonicalizer_casal import e_transferencia_do_casal
df = pd.read_excel('data/output/ouroboros_2026.xlsx', sheet_name='extrato')
tis = df[df['tipo'] == 'Transferência Interna']
casou = tis.apply(lambda r: e_transferencia_do_casal(str(r['local'])), axis=1)
print(f'órfãs: {(~casou).sum()} de {len(tis)} ({(~casou).mean()*100:.1f}%)')
"
```

Meta: <20% órfãs após Sprint 82b.

---

*"Uma coisa bem feita é feita duas vezes: uma vez no plano, outra vez na coisa." -- Sêneca*
