## 0. SPEC (machine-readable)

```yaml
sprint:
  id: "93g"
  title: "Cartão PJ da Vitória colide via dedup fuzzy com cópias mal-roteadas em andre/nubank_cartao/"
  depends_on:
    - sprint_id: 93f
      artifact: "src/transform/normalizer.py:158-159 + src/extractors/nubank_cartao.py::_gerar_hash"
    - sprint_id: 93d
      artifact: "scripts/reprocessar_cronologico.py (preservação forte)"
  touches:
    - path: data/raw/andre/nubank_cartao/BANCARIO_NUBANK_CARTAO_*.csv
      reason: "Cópias mal-roteadas pelo inbox passado contendo conteúdo idêntico aos arquivos de data/raw/vitoria/nubank_pj_cartao/"
    - path: src/extractors/nubank_cartao.py
      reason: "Considerar detecção contextual via conteúdo (CNPJ na descrição) para reclassificar PF para PJ quando cabível"
    - path: src/intake/orchestrator.py
      reason: "Roteamento atual envia faturas PJ para andre/nubank_cartao/ se sem marcador explícito"
  forbidden:
    - "Apagar arquivos sem garantir cópia em data/raw/originais/ (ADR-18)"
    - "Sobrescrever rotulagem da Sprint 93c sem preservar contrato `Nubank (PJ)`"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/ -q"
    - cmd: ".venv/bin/python -c \"import pandas as pd; df=pd.read_excel('data/output/ouroboros_2026.xlsx', sheet_name='extrato'); assert (df['banco_origem']=='Nubank (PJ)').sum() >= 200\""
    - cmd: "make smoke"
  acceptance_criteria:
    - "XLSX consolidado contém >=200 tx com banco_origem='Nubank (PJ)' (cartão + CC) após reprocessamento"
    - "Pessoa associada é 'Vitória' em 100% das tx PJ"
    - "Cópias em andre/nubank_cartao/ que clonam conteúdo PJ são identificadas e movidas para vitoria/nubank_pj_cartao/ ou marcadas como _envelopes/originais/"
    - "Mesmo achado para CC PJ: arquivos BANCARIO_NUBANK_CC_*.csv em vitoria/nubank_cc/ que são na verdade extratos PJ"
    - "Zero regressão nos 1537+ testes existentes"
```

---

# Sprint 93g -- Dedup fuzzy engole cartão PJ por cópias mal-roteadas em andre/nubank_cartao/

**Status:** BACKLOG P1 (bloqueador residual de visibilidade PJ)
**Prioridade:** P1 -- 856 tx PJ continuam invisíveis no XLSX mesmo após Sprint 93f corrigir hash + normalizer.
**Origem:** investigação pessoal do supervisor durante Sprint 93f.

## Problema

Sprint 93f resolveu duas dimensões do bug PJ no normalizer e no hash do extrator. Validação runtime mostrou que:

- `Nubank (PF)` 2310 tx agora corretamente atribuídas a Vitória (eram Casal). Ganho real e mensurável.
- `Nubank (PJ)` ainda zero no XLSX consolidado.

Diagnóstico runtime via simulação de pipeline isolado (commits da 93f):

1. Extratores produzem 841 tx PJ (275 cartão + 566 CC). OK.
2. Dedup nível 1 (`_identificador`) -- após fix do hash:
   - **Cartão PJ:** 275 sobrevivem (hash agora inclui `banco_origem`).
   - **CC PJ:** 0 sobrevivem (UUID nativo do CSV colide com cópias em `data/raw/vitoria/nubank_cc/`).
3. Dedup nível 2 fuzzy (`data|valor|local`):
   - **Cartão PJ remanescente:** 275 -> 0 (colide com `data/raw/andre/nubank_cartao/BANCARIO_NUBANK_CARTAO_*.csv`).

Causa raiz: **arquivos PJ originais foram clonados para diretórios PF no passado** pelo `inbox_orchestrator` (ou movidos manualmente). Os clones têm:

- Para CC: prefixo `BANCARIO_NUBANK_CC_*.csv` em `data/raw/vitoria/nubank_cc/` (sem `_pj`). Conteúdo idêntico ao `cc_pj_vitoria.csv` (ID UUID idêntico -> dedup nível 1 elimina PJ).
- Para cartão: prefixo `BANCARIO_NUBANK_CARTAO_*.csv` em `data/raw/andre/nubank_cartao/`. Conteúdo idêntico aos arquivos `Nubank_*.csv` em `data/raw/vitoria/nubank_pj_cartao/` (mesmo `data|valor|local` -> dedup fuzzy elimina PJ).

Como os caminhos PF são processados ANTES (ordem alfabética, `andre/` < `vitoria/`), todas as 841 PJ são descartadas no dedup.

## Diagnóstico necessário

1. Listar arquivos `data/raw/andre/nubank_cartao/BANCARIO_*.csv` cujo conteúdo é cópia exata de `data/raw/vitoria/nubank_pj_cartao/Nubank_*.csv`. Comparar via SHA-256.
2. Idem para `data/raw/vitoria/nubank_cc/BANCARIO_NUBANK_CC_*.csv` vs `data/raw/vitoria/nubank_pj_cc/cc_pj_vitoria.csv` (provavelmente um arquivo grande contém múltiplos meses).
3. Investigar histórico do `inbox_orchestrator` para entender quando o roteamento errado aconteceu (provavelmente antes da Sprint 90 / pessoa_detector).

## Fix possível

### Opção A -- limpeza operacional (preferida)
Mover os clones mal-roteados para `data/raw/_envelopes/originais/` ou deletar (com cópia em `data/raw/originais/` via Sprint 93d). Pipeline passará a ver apenas a versão PJ canônica.

### Opção B -- detecção contextual no pipeline
`src/extractors/nubank_cartao.py::_rotular_banco_origem` poderia inspecionar a primeira linha do CSV para detectar CNPJ PJ explícito ou fallback para path. Mais arriscado: pode rotular faturas PF como PJ se a Vitória aparece em alguma compra do casal.

## Armadilhas

- **Idempotência via Sprint 93d:** `data/raw/originais/<sha256>.ext` precisa estar populado antes de qualquer move/delete em `data/raw/`.
- **Histórico git PII:** descrições de PIX em logs anteriores podem citar CNPJ MEI Vitória -- não vazar em commits novos.
- **Ordem de processamento:** se opção B, considerar mudar `sorted(arquivos)` no `_escanear_arquivos` para priorizar `vitoria/nubank_pj_*` sobre cópias.

## Proof-of-work esperado

```python
import pandas as pd
df = pd.read_excel('data/output/ouroboros_2026.xlsx', sheet_name='extrato')
pj = df[df['banco_origem']=='Nubank (PJ)']
assert len(pj) >= 200, f"PJ esperado >=200 pos-93g, got {len(pj)}"
assert (pj['quem']=='Vitória').all(), "Toda tx PJ deve ser Vitória"
```

---

*"Um arquivo na pasta errada é um dado fora de lugar; um dado fora de lugar é uma decisão errada esperando para acontecer." -- princípio do roteamento canônico*
