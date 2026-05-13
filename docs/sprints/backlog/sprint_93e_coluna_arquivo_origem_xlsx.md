---
id: 93E-COLUNA-ARQUIVO-ORIGEM-XLSX
titulo: 0. SPEC (machine-readable)
status: backlog
concluida_em: null
prioridade: P2
data_criacao: '2026-04-24'
fase: OUTROS
epico: 0
depende_de: []
tipo_documental_alvo: null
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: "93e"
  title: "Propagar arquivo_origem para coluna dedicada na aba extrato do XLSX"
  depends_on:
    - sprint_id: 87b
      artifact: "coluna identificador no XLSX"
    - sprint_id: 93b
      artifact: "docs/auditoria_familia_B_2026-04-24.md (decisão de adiamento)"
  touches:
    - path: src/load/xlsx_writer.py
      reason: "Ler dict.get('_arquivo_origem') e escrever coluna 'arquivo_origem' na aba extrato"
    - path: src/dashboard/dados.py
      reason: "Expor coluna nova como opcional (usar .get('arquivo_origem', None))"
    - path: tests/test_xlsx_writer_arquivo_origem.py
      reason: "Testes de retrocompat + presença da coluna nova"
    - path: docs/MODELOS.md
      reason: "Documentar schema novo - SUPERVISOR consolida, executor não edita"
  forbidden:
    - "Renomear colunas existentes (retrocompat obrigatória)"
    - "Preencher arquivo_origem com valor fake quando ausente (usar None)"
    - "Mudar tipos de outras colunas"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_xlsx_writer_arquivo_origem.py -v"
    - cmd: ".venv/bin/python -c 'import pandas as pd; df=pd.read_excel(\"data/output/ouroboros_2026.xlsx\",sheet_name=\"extrato\"); assert \"arquivo_origem\" in df.columns'"
    - cmd: "make smoke"
  acceptance_criteria:
    - "Coluna `arquivo_origem` presente na aba extrato apos make process"
    - "XLSX antigo (sem a coluna) abre sem erro no dashboard"
    - "Transações sem _arquivo_origem no dict têm NaN na coluna"
    - "Transações com _arquivo_origem têm path absoluto OU relativo consistente"
    - "Dashboard continua funcional (testar page extrato + page categorias)"
```

---

# Sprint 93e — Coluna `arquivo_origem` no XLSX

**Status:** BACKLOG
**Prioridade:** P3
**Origem:** Sprint 93b (§Coluna arquivo_origem no XLSX — ADIADA)

## Problema

Durante o diagnóstico da família B, era tentador propagar o campo
interno `_arquivo_origem` (já presente nos dicts de transação em
memória) para uma coluna dedicada na aba `extrato` do XLSX. Isso
permitiria bisect linha-por-linha: dado um delta detectado pelo
auditor, saber qual arquivo bruto originou cada tx no XLSX.

Porém, a decisão formal da Sprint 93b foi **ADIAR**:

1. O XLSX já tem `identificador` (Sprint 87b) — hash canônico, bisect
   via grafo funciona.
2. Causas da família B foram mapeadas sem precisar de `arquivo_origem`
   explícito.
3. Mudar schema do XLSX tem alta superfície de regressão (dashboard,
   relatórios, sync_rico, dados.py).
4. A sprint 93b já entregou flags `--com-ofx` e `--ignorar-ti`
   suficientes para auditoria.

Esta sprint-filha formaliza o trabalho adiado para quando houver demanda
explícita.

## Escopo

### Fase 1 — Escrita no XLSX

- Em `xlsx_writer._escrever_aba_extrato`, adicionar coluna
  `arquivo_origem` (posição: imediatamente após `identificador`).
- Origem: `t.get('_arquivo_origem', None)` do dict.
- Se `None` ou ausente, célula fica vazia (NaN no pandas).

### Fase 2 — Leitura retrocompat

- Em `dashboard/dados.py`, tratar ausência da coluna (XLSX antigo):
  ```python
  if 'arquivo_origem' not in df.columns:
      df['arquivo_origem'] = None
  ```
- Colunas antigas preservadas na mesma ordem.

### Fase 3 — Testes

- `test_xlsx_escreve_coluna_arquivo_origem_quando_presente_no_dict`
- `test_xlsx_escreve_coluna_vazia_quando_dict_nao_tem_arquivo_origem`
- `test_dashboard_carrega_xlsx_antigo_sem_coluna_sem_erro`
- `test_modelos_md_documenta_coluna_nova` (grep no docs/MODELOS.md)

## Armadilhas

- **Path absoluto vs relativo:** Sprint 87.5 registrou
  `metadata.arquivo_original` no grafo como path tal como chegou do
  extrator (misto abs/rel). Padrão nesta sprint: converter para
  relativo-da-raiz-do-repo antes de gravar no XLSX.
- **Tamanho do XLSX:** paths longos (300+ chars) podem inflar o XLSX.
  Se ficar >20 MB, considerar hash curto + tabela de lookup separada.
- **Sync com grafo:** `backfill_arquivo_original.py` (Sprint 87.5)
  popula nodes; esta sprint popula XLSX. Manter contratos alinhados.

## Validação

```bash
# Rodar pipeline
make process

# Confirmar presença da coluna
.venv/bin/python -c "
import pandas as pd
df = pd.read_excel('data/output/ouroboros_2026.xlsx', sheet_name='extrato')
print('coluna presente:', 'arquivo_origem' in df.columns)
print('preenchidas:', df['arquivo_origem'].notna().sum(), 'de', len(df))
print('amostra:', df[df['arquivo_origem'].notna()]['arquivo_origem'].head(3).tolist())
"
```

Meta: >= 80% das tx modernas (2025+) têm `arquivo_origem` preenchido.
Tx de `banco_origem='Histórico'` ou do OFX consolidado podem ter célula
vazia — documentar isso como esperado.

---

*"O que é rastreado pode ser corrigido; o que é rastreado pode ser
auditado." — princípio de rastreabilidade*
