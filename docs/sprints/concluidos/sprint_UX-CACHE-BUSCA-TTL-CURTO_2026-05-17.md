---
id: UX-CACHE-BUSCA-TTL-CURTO
titulo: "Cache `_indice_cached` em busca.py com TTL=300s causa dados obsoletos por 5min"
status: concluída
concluida_em: 2026-05-17
prioridade: P2
data_criacao: 2026-05-17
fase: UX
epico: 5
depende_de: []
esforco_estimado_horas: 1
origem: "auditoria independente 2026-05-17. `src/dashboard/paginas/busca.py:554` usa `@st.cache_data(ttl=300)` para o índice de busca. Como Busca Global é entrada primária do dashboard (acessada N vezes por sessão), e dados podem atualizar com `./run.sh --tudo`, dono recém-importa documento e não acha na busca por até 5 minutos. Extrato usa `ttl=30` (decisão arquitetural mais correta)."
---

# Sprint UX-CACHE-BUSCA-TTL-CURTO

## Contexto

```python
# busca.py:554
@st.cache_data(ttl=300)  # 5 minutos
def _indice_cached(...):
    ...
```

Cenário:
1. Dono importa novo PDF para `inbox/` e roda `./run.sh --inbox`.
2. Dashboard aberto em outra aba.
3. Busca por nome do documento → "Não encontrado".
4. Dono espera 5min → busca de novo → encontrado.

UX ruim. Alternativas:
- `ttl=60`: dados frescos em 1min.
- Invalidação explícita: detectar mtime do XLSX/grafo e bustar cache.
- Botão "Recarregar" na UI.

## Hipótese e validação ANTES

```bash
grep -n "cache_data\|ttl=" src/dashboard/paginas/busca.py
# Confirmar: ttl=300

# Comparar com extrato:
grep -n "cache_data\|ttl=" src/dashboard/paginas/extrato.py
# Esperado: ttl=30
```

## Objetivo

1. **Reduzir ttl** para 60s (default Streamlit razoável):
   ```python
   @st.cache_data(ttl=60)
   def _indice_cached(...):
       ...
   ```

2. **Invalidação por mtime do XLSX** (defesa em camadas):
   ```python
   from pathlib import Path
   _PATH_XLSX = Path("data/output/ouroboros_2026.xlsx")

   @st.cache_data(ttl=60)
   def _indice_cached(mtime_xlsx: float):  # key inclui mtime
       ...

   # Uso:
   mtime = _PATH_XLSX.stat().st_mtime if _PATH_XLSX.exists() else 0
   indice = _indice_cached(mtime)
   ```

   Quando XLSX é regerado, mtime muda → key diferente → bust automático.

3. **Botão "Recarregar índice"** opcional no topo da Busca Global:
   ```python
   if st.button("Recarregar índice", help="Força refresh do cache"):
       _indice_cached.clear()
       st.rerun()
   ```

4. **Testes regressivos**:
   - `test_indice_cached_key_inclui_mtime`
   - `test_indice_invalida_apos_mtime_change`

## Não-objetivos

- Não tocar outras páginas (Extrato já tem ttl=30 OK).
- Não criar invalidador global (overkill — só XLSX importa para busca).

## Proof-of-work runtime-real

```bash
# Simular update do XLSX e ver cache bust:
.venv/bin/python -c "
from src.dashboard.paginas.busca import _indice_cached
from pathlib import Path
import os
mtime1 = Path('data/output/ouroboros_2026.xlsx').stat().st_mtime
i1 = _indice_cached(mtime1)
# Simula update:
os.utime('data/output/ouroboros_2026.xlsx', None)
mtime2 = Path('data/output/ouroboros_2026.xlsx').stat().st_mtime
assert mtime2 > mtime1
i2 = _indice_cached(mtime2)
# Como key diferente, cache nao foi reusado:
print('OK invalidacao por mtime')
"
```

## Acceptance

- `ttl=60` em `busca.py`.
- Cache key inclui mtime do XLSX.
- 2 testes regressivos verdes.
- Pytest baseline mantida.

## Padrões aplicáveis

- (n) Defesa em camadas — TTL + invalidação mtime.

---

*"Cache de 5min é cache de 5min de mentira." — princípio do dado fresco*
