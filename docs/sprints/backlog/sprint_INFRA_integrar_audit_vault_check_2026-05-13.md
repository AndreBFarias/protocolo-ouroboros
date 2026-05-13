---
id: INFRA-INTEGRAR-AUDIT-VAULT-CHECK
titulo: Integrar audit_vault_md.py ao ./run.sh --check como verificação periódica
status: backlog
concluida_em: null
prioridade: P3
data_criacao: 2026-05-13
fase: SANEAMENTO
depende_de:
  - MOB-audit-estrutura-vault-md (concluída em 2026-05-13)
esforco_estimado_horas: 1
origem: auditoria de integração ETL em 2026-05-13. O script scripts/audit_vault_md.py é executável standalone mas não tem trigger automático -- drift do vault Syncthing entre o app mobile e o backend pode passar despercebido sem rodar o auditor manualmente.
---

# Sprint INFRA-INTEGRAR-AUDIT-VAULT-CHECK

## Contexto

A sprint MOB-audit-estrutura-vault-md (concluída em 2026-05-13, commit 1ae3a79) entregou `scripts/audit_vault_md.py` — auditoria read-only do vault Syncthing compartilhado com o app mobile. Verifica estrutura, regex de filename, frontmatter `_schema_version=1` e companions.

Hoje o script só roda manualmente. **Drift do vault** (app adiciona subtipo novo, ou usuário coloca arquivo no lugar errado) só é detectado quando alguém pensa em rodar o auditor.

## Objetivo

Integrar o auditor ao `./run.sh --check` como uma das checagens canônicas. Exit code não-zero quando vault tem violações; warning informativo (não bloqueia outras checagens).

## Decisão

`./run.sh --check` hoje roda 23 checagens de ambiente (dependências, dirs, mappings). Adicionar:

```bash
# Em run.sh, dentro de --check
if test -d "$HOME/Protocolo-Ouroboros/inbox"; then
    msg_info "Auditando estrutura do vault Syncthing..."
    if python -m scripts.audit_vault_md --exit-zero-mesmo-com-violacao; then
        msg_ok "Vault sem violações estruturais"
    else
        msg_aviso "Vault com violações -- veja docs/auditorias/AUDITORIA_VAULT_MD_*.md"
    fi
fi
```

Alternativa: rodar antes do `--inbox` (mas pode atrasar workflow comum).

## Proof-of-work esperado

```bash
./run.sh --check 2>&1 | grep -iE "vault|audit"
# Esperado: linha extra "Auditando estrutura..." + OK ou aviso
```

## Padrão canônico aplicável

(s) Validação ANTES: roda ANTES de cada `--inbox` (ou periodicamente via `--check`).
(l) Achado de auditoria vira sprint-filha.

---

*"Auditor sem trigger é checklist no fundo da gaveta." -- princípio da automação preventiva*
