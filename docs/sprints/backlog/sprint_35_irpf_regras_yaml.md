## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 35
  title: "IRPF Regras YAML: migrar 21 regras hardcoded para loop supervisionado"
  touches:
    - path: src/transform/irpf_tagger.py
      reason: "refatorar para carregar regras via yaml.safe_load com cache em memória"
    - path: mappings/irpf_regras.yaml
      reason: "novo arquivo com as 21 regras migradas + bloqueios contextuais"
    - path: tests/test_irpf_tagger.py
      reason: "cobrir 21 regras migradas + casos negativos (armadilha CONSULT)"
  n_to_n_pairs:
    - [src/transform/irpf_tagger.py, mappings/irpf_regras.yaml]
  forbidden:
    - "deletar as 21 regras antigas antes do YAML carregar corretamente em testes"
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/test_irpf_tagger.py -x -q"
      timeout: 60
    - cmd: "make process"
      timeout: 300
  acceptance_criteria:
    - "mappings/irpf_regras.yaml contém as 21 regras com mesmo comportamento observável"
    - "tests/test_irpf_tagger.py passa com 21 cenários positivos e >= 21 negativos"
    - "Armadilha CONSULT coberta: 3 inputs positivos + 3 negativos explícitos"
    - "requer_cnpj: true só tagueia se CNPJ presente na descrição; senão vira revisao_humana"
    - "Cache em memória invalidado no startup do Streamlit"
    - ">= 3 regras novas adicionadas via supervisor (Sprint 34) sem editar .py"
    - "Acentuação PT-BR correta e zero emojis"
```

> Executar antes de começar: `make lint && ./run.sh --check`

---

# Sprint 35 -- IRPF Regras YAML: migrar 21 regras hardcoded para loop supervisionado

**Status:** PENDENTE
**Data:** 2026-04-18
**Prioridade:** MÉDIA
**Tipo:** Refactor
**Dependências:** Sprint 23 (CNPJ básico), Sprint 31 (Infra LLM)
**Desbloqueia:** --
**Issue:** --
**ADR:** --

---

## Como Executar

**Comandos principais:**
- `make lint`
- `.venv/bin/pytest tests/test_irpf_tagger.py -x -q`
- `make process` -- pipeline completo com regras IRPF em YAML

### O que NÃO fazer

- NÃO deletar as 21 regras hardcoded antes do YAML estar validado em teste.
- NÃO permitir LLM sobrescrever CNPJ extraído via regex determinística.
- NÃO deixar cache de regras entre sessões Streamlit sem invalidação no startup.
- NÃO alterar ordem de aplicação das regras ao migrar (ordem é significativa).

---

## Problema

`src/transform/irpf_tagger.py` tem 21 regras em Python puro. O supervisor (Sprints 31/34) não consegue propor novas regras IRPF sem que André edite código. Esse gargalo congela o loop de evolução.

Migrar para YAML desbloqueia:

- Supervisor propõe regras novas como YAML (já compatível com `mappings/proposicoes/`).
- Aprovar incorpora via append no arquivo.
- Sistema de bloqueios contextuais resolve armadilhas históricas (CONSULT).

---

## O que já existe (NÃO duplicar)

| Sistema | Arquivo | O que faz |
|---------|---------|-----------|
| IRPF tagger | `src/transform/irpf_tagger.py` | 21 regras hardcoded em 5 tipos |
| Extração CNPJ | `src/transform/irpf_tagger.py` | Regex CNPJ/CPF (Sprint 23) |
| Schemas LLM | `src/llm/schemas.py` | `SugestaoTagIRPF` já existe (Sprint 31) |
| Supervisor | `src/llm/supervisor.py` | Já propõe regras genéricas (Sprint 31) |

---

## Implementação

### Fase 1: schema YAML

**Arquivo:** `mappings/irpf_regras.yaml`

```yaml
versao: "1.0.0"
regras:
  - id: despesa_medica_plano
    tipo: dedutivel_medico
    padrao_local: "(?i)unimed|hapvida|amil|bradesco saude"
    requer_cnpj: true
    confianca_minima: 0.85
  - id: servicos_profissionais_consultoria
    tipo: servicos_profissionais
    padrao_local: "(?i)consult"
    requer_cnpj: true
    confianca_minima: 0.80
    bloqueios_contextuais:
      - "(?i)consulta medica"
      - "(?i)consulta odontologica"
      - "(?i)consulta veterinaria"
bloqueios_globais:
  - padrao: "(?i)transferencia interna"
    razao: "transferências entre contas próprias não são despesas dedutíveis"
```

### Fase 2: mapa 1:1 das 21 regras

Transferir cada regra do Python para YAML preservando exatamente o comportamento observável. Rodar `make process` antes e depois, comparar aba `irpf` do XLSX: 0 diferenças.

### Fase 3: refatoração do tagger

**Arquivo:** `src/transform/irpf_tagger.py`

```python
from functools import lru_cache

@lru_cache(maxsize=1)
def _carregar_regras() -> list[dict]:
    with open("mappings/irpf_regras.yaml", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data["regras"]

def aplicar_regras(row) -> dict | None:
    for regra in _carregar_regras():
        if any(re.search(b, row.local or "") for b in regra.get("bloqueios_contextuais", [])):
            continue
        if re.search(regra["padrao_local"], row.local or ""):
            if regra.get("requer_cnpj") and not row.cnpj_cpf:
                return {"tipo": regra["tipo"], "revisao_humana": True}
            return {"tipo": regra["tipo"], "revisao_humana": False}
    return None
```

### Fase 4: invalidação de cache

**Arquivo:** `src/dashboard/app.py`

No startup (`st.session_state` vazio), chamar `_carregar_regras.cache_clear()`. Garante que mudanças no YAML refletem sem reiniciar servidor.

### Fase 5: tests/test_irpf_tagger.py

**Arquivo:** `tests/test_irpf_tagger.py`

Para cada regra: 1 positivo + 1 negativo. Mínimo 42 parametrizações. Casos críticos:

```python
@pytest.mark.parametrize("local, esperado", [
    ("CONSULT LTDA ME", "servicos_profissionais"),
    ("CONSULTORIA TI S.A.", "servicos_profissionais"),
    ("CONSULT IMPORT EXPORT", "servicos_profissionais"),
    ("CONSULTA MEDICA DR X", None),      # bloqueio contextual
    ("CONSULTA ODONTOLOGICA Y", None),   # bloqueio contextual
    ("CONSULTA VETERINARIA Z", None),    # bloqueio contextual
])
def test_armadilha_consult(local, esperado):
    ...
```

### Fase 6: supervisor incorpora novas regras

**Arquivo:** `src/llm/supervisor.py`

Quando o LLM propõe `SugestaoTagIRPF`, a saída vai para `mappings/proposicoes/*.yaml`. Ao aprovar no dashboard, o código faz append em `mappings/irpf_regras.yaml` (não mais edição de `.py`).

---

## Armadilhas Conhecidas

| Ref | Armadilha | Como evitar |
|-----|-----------|-------------|
| A35.1 | Regex nova casa input que não deveria | Meta-regra 2: teste negativo obrigatório antes de aceitar nova regra |
| A35.2 | Cache em memória serve regra antiga entre sessões Streamlit | `cache_clear()` no startup; TTL por arquivo modificado |
| A35.3 | Ordem das regras importa; YAML embaralhado muda comportamento | Preservar ordem explícita na lista; validador de fixture verifica |
| A35.4 | LLM sugere CNPJ inventado | Regra absoluta: tagger IRPF nunca aceita CNPJ do LLM; só extrai via regex |
| A35.5 | Migração parcial: 15 regras em YAML + 6 em Python causa divergência | Tudo ou nada; migrar em 1 commit após testes passarem |

Referência: `docs/ARMADILHAS.md`

---

## Evidências Obrigatórias

- [ ] `make lint` passa sem erros
- [ ] `mappings/irpf_regras.yaml` contém 21 regras migradas
- [ ] `.venv/bin/pytest tests/test_irpf_tagger.py -v` passa com >= 42 cenários (positivo + negativo)
- [ ] Armadilha CONSULT tem 3 positivos + 3 negativos explícitos
- [ ] `make process` gera aba `irpf` sem diferença vs versão anterior
- [ ] Pelo menos 3 regras novas adicionadas via supervisor sem tocar `.py`
- [ ] Dashboard reinicia e reflete regras atualizadas sem restart

---

## Verificação end-to-end

```bash
make lint
.venv/bin/pytest tests/test_irpf_tagger.py -v
make process
python -c "import pandas as pd; df=pd.read_excel('data/output/extrato_consolidado.xlsx', sheet_name='irpf'); print(df.tipo.value_counts())"
```

---

*"A clareza é a cortesia do filósofo." -- Ortega y Gasset*
