## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 93f
  title: "Pipeline escanear data/raw/vitoria/nubank_pj_* e produzir Nubank (PJ) no XLSX"
  depends_on:
    - sprint_id: 93c
      artifact: "src/extractors/nubank_cartao.py::_rotular_banco_origem (já correto em teste unitário)"
    - sprint_id: 90
      artifact: "pessoa_detector com mappings/pessoas.yaml"
  touches:
    - path: src/pipeline.py
      reason: "investigar escaneamento e roteamento de data/raw/vitoria/nubank_pj_*"
    - path: src/extractors/nubank_cartao.py
      reason: "revisar pode_processar se filtrar por path"
    - path: src/extractors/nubank_cc.py
      reason: "idem"
    - path: tests/test_pipeline_vitoria_pj.py
      reason: "novo -- teste end-to-end com fixture PJ + assert em XLSX gerado"
  forbidden:
    - "Alterar contrato BANCOS_VALIDOS de scripts/smoke_aritmetico.py"
    - "Sobrescrever XLSX em producao durante teste -- usar tmp_path"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/ -q"
    - cmd: "make smoke"
    - cmd: ".venv/bin/python -c \"import pandas as pd; df=pd.read_excel('data/output/ouroboros_2026.xlsx', sheet_name='extrato'); assert (df['banco_origem']=='Nubank (PJ)').sum() > 0\""
  acceptance_criteria:
    - "Apos ./run.sh --tudo, XLSX aba extrato contem >=100 tx com banco_origem=Nubank (PJ)"
    - "Pessoa associada a essas tx e Vitoria"
    - "Fidelidade do script de auditoria: nubank_pj_cc e nubank_pj_cartao delta reduzido"
    - "Teste de regressao end-to-end cobre fixture PJ sintetica"
    - "Zero regressao nos 1416+ testes existentes"
```

---

# Sprint 93f — pipeline escanear arquivos PJ da Vitória

**Status:** BACKLOG P1 (blocker de visibilidade PJ no dashboard)
**Prioridade:** P1 — 562 + 294 = 856 transações PJ da Vitória invisíveis no XLSX consolidado mesmo após fix da Sprint 93c no extrator.
**Origem:** validação pessoal do supervisor pós-Sprint 93c + `./run.sh --tudo` em 2026-04-24. XLSX regenerado não contém `Nubank (PJ)` embora o extrator (unit-teste) produza.

## Problema

Sprint 93c corrigiu `src/extractors/nubank_cartao.py::_parse_linha` para emitir `banco_origem="Nubank (PJ)"` quando o path do arquivo contém `nubank_pj`. Teste unitário passa. Porém, runtime real de `./run.sh --tudo` produz `data/output/ouroboros_2026.xlsx` com **zero** transações `banco_origem="Nubank (PJ)"`.

Evidência empírica (2026-04-24):

```python
import pandas as pd
df = pd.read_excel("data/output/ouroboros_2026.xlsx", sheet_name="extrato")
df["banco_origem"].value_counts()
# Nubank (PF)    2310
# Nubank         1273
# C6             1185
# Histórico      1181
# Santander       110
# Itaú             29
# Nubank (PJ)        0   <-- AUSENTE
```

Arquivos físicos presentes:
- `data/raw/vitoria/nubank_pj_cc/cc_pj_vitoria.csv` (1 arquivo CC PJ)
- `data/raw/vitoria/nubank_pj_cartao/Nubank_*.csv` (6+ faturas PJ cartão)

Output de `./run.sh --tudo` não menciona `vitoria`, `nubank_pj`, `pj_cc`, nem `pj_cartao`. Pipeline pode estar:

1. Não escaneando `data/raw/vitoria/*` (apesar de `_escanear_arquivos(DIR_RAW)` ser recursivo).
2. Escaneando mas nenhum extrator tem `pode_processar(path)` retornando True para esses paths.
3. Processando mas rótulo sendo sobrescrito em etapa posterior (normalizer, dedup, xlsx_writer).

## Diagnóstico necessário

1. **Instrumentar logger** em `src/pipeline.py::_escanear_arquivos` e `_descobrir_extratores` para emitir path completo de cada arquivo candidato × extrator casado.
2. **Rodar `./run.sh --tudo`** com logger em DEBUG para capturar o fluxo.
3. **Confirmar** em qual etapa exata os arquivos PJ param:
   - Se em `_escanear_arquivos`: path não está sendo varrido.
   - Se em `pode_processar` dos extratores: filtro de path exclui PJ.
   - Se após extração: rótulo `"Nubank (PJ)"` está sendo normalizado para outra forma.

## Fix provável (hipótese)

O `pode_processar` do `ExtratorNubankCartao` provavelmente filtra por nome `Nubank_*.csv`, casando arquivos em `data/raw/andre/nubank_cartao/` e `data/raw/vitoria/nubank_pj_cartao/`. Mas a ordem de registro e algum early-return do pipeline pode pular o path PJ.

Hipótese secundária: há inbox_processor que roteia arquivos para `data/raw/<pessoa>/<banco>/` e o caminho PJ da Vitória caiu fora da tabela de roteamento.

## Armadilhas

- **Sprint 87e (recente)** registrou `ExtratorBoletoPDF` no pipeline. Ordem em `_descobrir_extratores` matters.
- **Sprint 93c (recente)** adicionou método `_rotular_banco_origem(caminho)` mas não modificou `pode_processar`. Se `pode_processar` nem casa, o método não é chamado.
- **Sprint 90 (pessoa_detector)** detecta pessoa por CNPJ/CPF/razão. Verificar se o roteamento `inbox_processor` usa esse detector para decidir destino, ou usa apenas padrão de nome de arquivo.

## Proof-of-work

- Após fix: `df["banco_origem"].value_counts()` inclui `Nubank (PJ)` com contagem >= 100.
- `scripts/auditar_extratores.py --banco nubank_pj_cc` retorna delta reduzido.
- Teste end-to-end `tests/test_pipeline_vitoria_pj.py` com fixture sintética em `tmp_path` valida que passando 1 CSV PJ pelo pipeline produz tx com rótulo correto.

## Considerações para sprint D (artesanal)

Essa investigação pode ser parte da Sprint D se o supervisor humano preferir inspeção manual de logs e dashboards. A sprint D já tem contrato de "mover tudo para inbox + reprocessar + revisar 1-a-1" que naturalmente atinge esses arquivos.

---

*"Um fix que passa no unit-teste mas não no runtime é uma promessa com letra miúda." -- princípio do fix end-to-end*
