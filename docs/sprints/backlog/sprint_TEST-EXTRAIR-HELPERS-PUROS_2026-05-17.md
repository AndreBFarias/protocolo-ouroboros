---
id: TEST-EXTRAIR-HELPERS-PUROS
titulo: "Extrair helpers puros das páginas dashboard para `src/utils/` (10+ testes importam Streamlit desnecessariamente)"
status: backlog
concluida_em: null
prioridade: P3
data_criacao: 2026-05-17
fase: SANEAMENTO
epico: 8
depende_de: []
esforco_estimado_horas: 2
origem: "auditoria independente 2026-05-17. 10+ testes em `tests/` importam `streamlit` para testar helpers puros (funções sem dependência de session_state ou widgets). Streamlit inicializa runtime que pesa em pytest (3181 testes; CI lento). Helpers como `_mascarar_pii`, `_parse_data_iso`, `_classificar_idade` deveriam estar em `src/utils/` testáveis isoladamente."
---

# Sprint TEST-EXTRAIR-HELPERS-PUROS

## Contexto

Testes pesados detectados (importam `streamlit`):
- `test_be_diario_eventos.py`
- `test_busca_global.py`
- `test_dashboard_revisor.py`
- `test_propostas_dashboard.py` (parcialmente — só testa helpers)
- `test_categorizer_sugestoes_dashboard.py`
- `test_tipos_pendentes_dashboard.py`

Cada `import streamlit` carrega ~50 módulos (gRPC, watchdog, click, altair...). Acumula em pytest paralelo.

Helpers candidatos a extrair:
- `propostas_pendentes.py::_classificar_idade` → `src/utils/idade_alertas.py`
- `propostas_pendentes.py::_parse_frontmatter_yaml` → `src/utils/yaml_simple.py`
- `categorizer_sugestoes.py::_aplicar_filtros` → função pura, mover para `src/transform/`
- `tipos_pendentes.py::_aceitar_proposta` → `src/utils/yaml_append.py`

## Hipótese e validação ANTES

```bash
# Quais testes importam streamlit:
grep -rln "import streamlit\|from streamlit" tests/ | wc -l
# Esperado: 10+

# Helpers puros em paginas/ (sem `st.*` no corpo):
grep -A 10 "^def _[a-z]" src/dashboard/paginas/*.py | grep -B 1 "return\|raise" | head -20
```

## Objetivo

1. Para cada helper candidato:
   - **Identificar** funções sem dependência de `st.*` (puras)
   - **Mover** para `src/utils/` ou `src/transform/`
   - **Re-importar** na página original
   - **Atualizar testes** para importar do novo path

2. **Reduzir tempo de pytest** medível:
   ```bash
   .venv/bin/pytest --collect-only -q | tail -1
   # Pytest baseline = 3181
   
   time .venv/bin/pytest tests/test_propostas_dashboard.py -q
   # Antes vs depois: tempo de import deve diminuir
   ```

3. **Cuidado: NÃO mover** funções com:
   - `st.cache_data` decorator (esses ficam na página).
   - Acesso a `st.session_state` (mesmo indireto).

## Não-objetivos

- Não criar novo pacote `dashboard_helpers/` (mover para `src/utils/` existente).
- Não tocar comportamento (refactor puro: mesma função, novo path).
- Não mover funções de render (`_renderizar_*`).

## Proof-of-work runtime-real

```bash
# Antes:
grep -c "import streamlit" tests/*.py | grep -v ":0$" | wc -l

# Apos refactor:
time .venv/bin/pytest tests/test_propostas_dashboard.py -q
# Esperado: tempo total menor (sem import streamlit)
```

## Acceptance

- 3+ helpers movidos para `src/utils/` ou `src/transform/`.
- 3+ testes deixam de importar `streamlit`.
- Pytest baseline ≥ 3181 mantida.
- Tempo de pytest dos testes afetados reduzido (medível com `time`).
- Lint exit 0.

## Padrões aplicáveis

- (a) Edit cirúrgico — mover sem alterar.
- (cc) Refactor revela teste frágil — pode expor mocks indevidos.

---

*"Teste de Streamlit é teste de Streamlit; teste de função é teste de função." — princípio do isolamento*
