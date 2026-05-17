---
id: INFRA-DESCOBRIR-EXTRATORES-REFATORA
titulo: "Refatorar `_descobrir_extratores()` 166L com 23 try/except idênticos"
status: backlog
concluida_em: null
prioridade: P2
data_criacao: 2026-05-17
fase: SANEAMENTO
epico: 8
depende_de: []
esforco_estimado_horas: 2
origem: "auditoria independente 2026-05-17. `src/pipeline.py:43-209` (166 linhas) tem 23 blocos try/except idênticos: `try: from src.extractors.X import ExtratorX; extratores.append(ExtratorX); except ImportError as e: logger.warning(...)`. Padrão repetitivo. Adicionar extrator novo exige editar bloco de N+5 linhas. Sem flexibilidade para desabilitar extrator via env var ou config."
---

# Sprint INFRA-DESCOBRIR-EXTRATORES-REFATORA

## Contexto

`_descobrir_extratores()` retorna lista de classes extractor para o pipeline. Implementação atual:

```python
def _descobrir_extratores() -> list:
    extratores = []
    try:
        from src.extractors.nubank_cartao import ExtratorNubankCartao
        extratores.append(ExtratorNubankCartao)
    except ImportError as e:
        logger.warning("Extrator nubank_cartao indisponível: %s", e)
    # ... repetido 22 vezes
```

Problemas:
1. 166 linhas para o que poderia ser 30.
2. Adicionar extrator novo → editar pipeline.py (anti-pattern: dependência inversa).
3. Não suporta `OUROBOROS_EXTRATORES_DESABILITADOS=das_parcsn_pdf,nfce_pdf` para debug.
4. Ordem dos blocos importa? Aparentemente não, mas não está documentado.

## Hipótese e validação ANTES

```bash
wc -l src/pipeline.py
grep -c "from src.extractors" src/pipeline.py
ls src/extractors/*.py | grep -v "^_" | grep -v __init__ | wc -l
# Esperado: 23 extratores em pipeline.py = N arquivos em extractors/
```

## Objetivo

1. **Estratégia A — Descoberta dinâmica via `pkgutil`**:
   ```python
   import importlib
   import pkgutil
   import src.extractors

   def _descobrir_extratores(desabilitados: set[str] | None = None) -> list:
       desabilitados = desabilitados or set()
       extratores = []
       for finder, name, ispkg in pkgutil.iter_modules(src.extractors.__path__):
           if name.startswith("_") or name in desabilitados:
               continue
           try:
               mod = importlib.import_module(f"src.extractors.{name}")
               # Convenção: classe ExtratorX por arquivo X
               for attr in dir(mod):
                   if attr.startswith("Extrator") and not attr.startswith("_"):
                       cls = getattr(mod, attr)
                       if isinstance(cls, type):
                           extratores.append(cls)
                           break
           except ImportError as e:
               logger.warning("Extrator %s indisponivel: %s", name, e)
       return extratores
   ```

2. **Suporte a env var** `OUROBOROS_EXTRATORES_DESABILITADOS`:
   ```python
   desab = set(os.environ.get("OUROBOROS_EXTRATORES_DESABILITADOS", "").split(","))
   classes = _descobrir_extratores(desab)
   ```

3. **Testes regressivos**:
   - `test_descobrir_extratores_acha_22_classes`
   - `test_descobrir_extratores_pula_desabilitados_via_env`
   - `test_descobrir_extratores_ignora_arquivos_underscore`

4. **Validação**: pytest baseline mantida (mesmas classes em mesma ordem).

## Não-objetivos

- Não tocar extratores em si.
- Não alterar pipeline downstream.
- Não criar registry YAML (estratégia B — fica para outra sprint se necessário).

## Proof-of-work runtime-real

```bash
.venv/bin/python -c "
from src.pipeline import _descobrir_extratores
classes = _descobrir_extratores()
print(f'Descobertos: {len(classes)}')
for c in classes:
    print(f'  {c.__name__}')
"
# Esperado: 22-23 classes (mesmas de antes)

OUROBOROS_EXTRATORES_DESABILITADOS=das_parcsn_pdf \
  .venv/bin/python -c "
from src.pipeline import _descobrir_extratores
import os
desab = set(os.environ.get('OUROBOROS_EXTRATORES_DESABILITADOS','').split(','))
print(len(_descobrir_extratores(desab)))
"
# Esperado: 21 (1 a menos)
```

## Acceptance

- Linhas de `_descobrir_extratores` reduzidas de 166 → ~30L.
- Suporte a env var `OUROBOROS_EXTRATORES_DESABILITADOS`.
- 3 testes regressivos verdes.
- Pytest baseline mantida ≥ 3181.

## Padrões aplicáveis

- (a) Edit incremental — função isolada.
- (n) Defesa em camadas — fallback `try/except ImportError` preservado.

---

*"Repetição idêntica é despesa; abstração mínima é juro pago." — princípio do DRY honesto*
