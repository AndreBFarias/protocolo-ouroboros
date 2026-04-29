---
concluida_em: 2026-04-27
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 99
  title: "Redactor de PII em logs INFO (CPF, CNPJ, razao social)"
  prioridade: P1
  estimativa: 1h
  origem: "auditoria 2026-04-26 -- pessoa_detector loga 'razao social NOME_COMPLETO_REAL' em INFO"
  touches:
    - path: src/utils/logger.py
      reason: "filter customizado mascara CPF/CNPJ/RS antes de emit"
    - path: src/intake/pessoa_detector.py
      reason: "trocar log INFO de razao social por hash[:8]"
    - path: tests/test_logger_redactor.py
      reason: "regressao: log com CPF/CNPJ aparece mascarado"
  forbidden:
    - "Mascarar em log DEBUG (esse pode ter PII -- so DEBUG)"
    - "Bypassar logger.info diretamente -- todo log passa pelo filter"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_logger_redactor.py -v"
    - cmd: "make smoke"
  acceptance_criteria:
    - "Filter no logger nivel INFO mascara CPF como XXX.XXX.XXX-XX, CNPJ como XX.XXX.XXX/0001-XX"
    - "Razao social referenciada por hash[:8] em vez de nome completo"
    - "Nivel DEBUG mantem PII (uso interno do dev)"
    - "Pelo menos 6 testes regressivos: CPF, CNPJ-PJ, CNPJ-MEI, razao social literal, mensagem sem PII (regression), debug com PII"
  proof_of_work_esperado: |
    # Antes (em runtime real)
    .venv/bin/python -c "
    from src.intake.pessoa_detector import detectar_pessoa
    from pathlib import Path
    p = Path('inbox/2.jpeg')
    detectar_pessoa(p, texto_preview='CNPJ 52.488.753 VITORIA MARIA SILVA DOS SANTOS ...')"
    # log INFO: razao social 'VITORIA MARIA SILVA DOS SANTOS' (PII vazada)
    
    # Depois
    [mesmo comando]
    # log INFO: pessoa detectada via razao social hash=a4f2c891 (mascarado)
```

---

# Sprint 99 -- Redactor de PII em logs

**Status:** CONCLUÍDA (commit `92860af`, 2026-04-27)

Auditoria 2026-04-26 detectou em runtime real: `INFO: razão social 'NOME_REAL_VITORIA'`. Sprint cria filter de logging que mascara CPF/CNPJ/razao social antes de emit em nivel INFO. DEBUG continua exibindo (uso dev). Filter aplicado globalmente via `configurar_logger`.

Implementação trivial -- regex `\d{3}\.\d{3}\.\d{3}-\d{2}` -> `XXX.XXX.XXX-XX`, `\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}` -> `XX.XXX.XXX/0001-XX`. Para razao social, substituir pelo SHA-256[:8] do nome.

---

*"Log eh artefato persistente. PII não pode vazar nele." -- principio de privacy by default*
