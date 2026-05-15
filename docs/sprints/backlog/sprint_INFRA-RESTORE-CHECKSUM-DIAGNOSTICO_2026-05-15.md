---
id: INFRA-RESTORE-CHECKSUM-DIAGNOSTICO
titulo: Diagnóstico diferenciado em `_restaurar_grafo_de_backup` (truncamento vs corrupção)
status: backlog
concluida_em: null
prioridade: P3
data_criacao: 2026-05-15
fase: SANEAMENTO
epico: 2
depende_de:
  - INFRA-BACKUP-GRAFO-AUTOMATIZADO (concluída em d97df41)
esforco_estimado_horas: 0.5
origem: auditoria 2026-05-15. `src/pipeline.py:749-755` em `_restaurar_grafo_de_backup` loga "Checksum inválido: gravado=X atual=Y (backup corrompido)" sem distinguir entre `.sha256` truncado (write parcial em disco cheio), `.sha256` malformado (algum char não-hex), ou conteúdo do backup corrompido. Admin não sabe qual cenário tratar.
---

# Sprint INFRA-RESTORE-CHECKSUM-DIAGNOSTICO

## Contexto

Conduta atual é SEGURA (rejeita restore) mas mensagem genérica:

```python
sha_gravado = sha_path.read_text(encoding="utf-8").split()[0].strip()
sha_atual = _sha256_arquivo(backup)
if sha_gravado != sha_atual:
    logger.error("Checksum inválido: gravado=%s atual=%s (backup corrompido).", sha_gravado[:12], sha_atual[:12])
    return 1
```

3 cenários distintos hoje mapeiam pra mesma mensagem:
1. `sha_gravado` tem ≠64 chars → arquivo `.sha256` truncado/malformado
2. `sha_gravado` tem caracteres não-hex → arquivo `.sha256` corrompido  
3. `sha_gravado` válido mas ≠ `sha_atual` → conteúdo do backup corrompido

Cada um exige resposta diferente:
1. Regenerar `.sha256` a partir do backup (se backup OK): `sha256sum backup > backup.sha256`
2. Reportar corrupção do `.sha256`, tentar backup anterior.
3. Backup inutilizável, tentar versão anterior.

## Hipótese e validação ANTES

H1: código atual não distingue:

```bash
sed -n '745,760p' src/pipeline.py
# Esperado: bloco como descrito acima, sem ifs
```

H2: re para hash SHA-256 válido:

```bash
echo "abc" | sha256sum | grep -cE "^[a-f0-9]{64}\s"
# Esperado: 1
```

## Objetivo

1. Refatorar trecho em `_restaurar_grafo_de_backup`:
   ```python
   sha_gravado = sha_path.read_text(encoding="utf-8").split()[0].strip()
   if len(sha_gravado) != 64:
       logger.error(
           "Checksum malformado: .sha256 tem %d chars (esperado 64). "
           "Provável write parcial. Regenere com `sha256sum %s > %s`.",
           len(sha_gravado), backup, sha_path
       )
       return 1
   if not re.match(r"^[0-9a-f]{64}$", sha_gravado):
       logger.error(
           "Checksum corrompido: caracteres inválidos. "
           "Arquivo .sha256 pode estar comprometido. Tente backup anterior."
       )
       return 1
   sha_atual = _sha256_arquivo(backup)
   if sha_gravado != sha_atual:
       logger.error(
           "Conteúdo do backup corrompido: sha gravado=%s vs sha calculado=%s. "
           "Backup inutilizável. Tente versão anterior.",
           sha_gravado[:12], sha_atual[:12]
       )
       return 1
   ```
2. 3 testes regressivos em `tests/test_backup_grafo.py` (cobrem cada cenário).

## Não-objetivos

- Não auto-recuperar (regenerar .sha256 ou pular para anterior) — só diagnóstico.
- Não tocar `_executar_backup_grafo` ou `_aplicar_retencao_backups_grafo`.

## Proof-of-work runtime-real

```bash
# 1. Truncado
echo "abc123" > /tmp/teste.sqlite.sha256
touch /tmp/teste.sqlite
.venv/bin/python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from src.pipeline import _restaurar_grafo_de_backup
from pathlib import Path
r = _restaurar_grafo_de_backup('00000000_000000', Path('/tmp/teste.sqlite'), Path('/tmp'))
" 2>&1 | grep -i "malformado"
# Esperado: hit

# 2. Caracteres inválidos
python -c "print('z' * 64)" > /tmp/teste.sqlite.sha256
.venv/bin/python -c "from src.pipeline import _restaurar_grafo_de_backup; from pathlib import Path; _restaurar_grafo_de_backup('00000000_000000', Path('/tmp/teste.sqlite'), Path('/tmp'))" 2>&1 | grep -i "corrompido"
# Esperado: hit

# 3. Conteúdo corrompido (sha válido mas calc diferente)
python -c "print('a' * 64)" > /tmp/teste.sqlite.sha256
.venv/bin/python -c "from src.pipeline import _restaurar_grafo_de_backup; from pathlib import Path; _restaurar_grafo_de_backup('00000000_000000', Path('/tmp/teste.sqlite'), Path('/tmp'))" 2>&1 | grep -i "inutiliz"
# Esperado: hit
```

## Acceptance

- 3 mensagens distintas para 3 cenários.
- 3 testes regressivos.
- Pytest > 3019. Smoke 10/10. Lint exit 0.

## Padrões aplicáveis

- (a) Edit incremental — só trocar o bloco de log.
- (y) Anti-cosmético — diagnóstico útil > mensagem genérica.

---

*"Erro com diagnóstico é metade da solução; erro sem diagnóstico é tempo perdido em hipótese." — princípio do log informativo*
