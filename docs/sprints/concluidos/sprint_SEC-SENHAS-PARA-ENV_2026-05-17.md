---
id: SEC-SENHAS-PARA-ENV
titulo: "Migrar `mappings/senhas.yaml` (PII real) para `.env` + python-dotenv"
status: concluída
concluida_em: 2026-05-17
prioridade: P1
data_criacao: 2026-05-17
fase: SEGURANCA
epico: 2
depende_de: []
esforco_estimado_horas: 1.5
origem: "auditoria independente 2026-05-17. `mappings/senhas.yaml` contém senhas reais de PDFs (CPF parcial, datas) + identificação bancária (agências, contas). Apesar de `.gitignore` tracá-lo, formato YAML é frágil: backup local, herança de worktree, ou clone com `--mirror` exporiam dados sensíveis. Convenção segura é `.env` + `python-dotenv` (já é dependência via streamlit?)."
---

# Sprint SEC-SENHAS-PARA-ENV

## Contexto

`mappings/senhas.yaml` armazena:
- Senhas de PDFs Itaú/Santander (uso por `extractors/itau_pdf.py` etc).
- Possivelmente CPF/CNPJ identificadores.

`.gitignore` cobre `mappings/senhas.yaml`, mas:
- Worktree agente pode herdar (já houve incidente similar com `.ouroboros/cache/last_sync.json`).
- Backup local sem cuidado expõe.
- Log info pode vazar conteúdo se houver `logger.info(f"yaml carregado: {senhas}")`.

Padrão canônico para credenciais é `.env` + carregamento via `os.environ.get()`:
```python
PDF_SENHA_ITAU = os.environ.get("OUROBOROS_PDF_SENHA_ITAU", "")
```

`.env` é o padrão de mercado, mais auditável (1 linha por chave), grep-able.

## Hipótese e validação ANTES

```bash
ls -la mappings/senhas.yaml
# Esperado: arquivo existe (não trackeado)

cat mappings/senhas.yaml | head -5
# Esperado: estrutura YAML com chaves tipo `itau:`, `santander:`

grep -rln "senhas.yaml\|carregar_senhas\|PDF_SENHA" src/ scripts/
# Identificar consumidores

git ls-files mappings/senhas.yaml
# Esperado: vazio (gitignored)
```

## Objetivo

1. **Criar `.env.example`** trackeado (sem PII real):
   ```bash
   # Senhas de PDFs bancários (Sprint SEC-SENHAS-PARA-ENV)
   OUROBOROS_PDF_SENHA_ITAU=
   OUROBOROS_PDF_SENHA_SANTANDER=
   # ... etc
   ```

2. **Criar `src/utils/segredos.py`** (NOVO):
   ```python
   """Carregamento de credenciais via .env (Sprint SEC-SENHAS-PARA-ENV)."""
   import os
   from pathlib import Path

   _ENV_CARREGADO = False

   def _carregar_env_uma_vez():
       global _ENV_CARREGADO
       if _ENV_CARREGADO:
           return
       env_path = Path(__file__).resolve().parents[2] / ".env"
       if env_path.exists():
           for linha in env_path.read_text(encoding="utf-8").splitlines():
               if "=" in linha and not linha.startswith("#"):
                   k, _, v = linha.partition("=")
                   os.environ.setdefault(k.strip(), v.strip())
       _ENV_CARREGADO = True

   def senha_pdf(banco: str) -> str:
       """Devolve senha do PDF do banco (vazio se não configurada)."""
       _carregar_env_uma_vez()
       return os.environ.get(f"OUROBOROS_PDF_SENHA_{banco.upper()}", "")
   ```

3. **Refatorar consumidores** (extractors/itau_pdf.py etc):
   ```python
   from src.utils.segredos import senha_pdf
   senha = senha_pdf("itau")
   ```

4. **Migrar `mappings/senhas.yaml` → `.env` (local, gitignored)** com `scripts/migrar_senhas_yaml_para_env.py`:
   - Lê YAML existente.
   - Gera `.env` com mesmo conteúdo.
   - Mantém YAML como `senhas.yaml.OBSOLETO` por 1 sprint (fallback).

5. **Atualizar `.gitignore`**: adicionar `.env` (provavelmente já está, validar).

6. **Atualizar `docs/BOOTSTRAP.md`**: novo passo de setup de `.env`.

## Não-objetivos

- Não usar `python-dotenv` (dep adicional — implementação `_carregar_env_uma_vez` interna basta).
- Não trackear `.env` no git (apenas `.env.example`).
- Não tocar PDFs em si.

## Proof-of-work runtime-real

```bash
# Setup local:
cp .env.example .env
echo "OUROBOROS_PDF_SENHA_ITAU=valor_real" >> .env

.venv/bin/python -c "
from src.utils.segredos import senha_pdf
print(repr(senha_pdf('itau')))  # esperado: 'valor_real'
print(repr(senha_pdf('inexistente')))  # esperado: ''
"
```

## Acceptance

- `.env.example` trackeado.
- `src/utils/segredos.py` criado.
- ≥3 consumidores refatorados.
- Migração de YAML para `.env` funcional.
- BOOTSTRAP.md atualizado.
- Lint exit 0. Pytest baseline mantida.

## Padrões aplicáveis

- (e) PII never in INFO — `.env` é convenção segura.
- (n) Defesa em camadas — `.env` + `.gitignore`.

---

*"Senha em YAML é senha confiada na disciplina; senha em .env é senha confiada na convenção." — princípio do segredo isolado*
