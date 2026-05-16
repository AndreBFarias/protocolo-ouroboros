# hooks/_arquivado/ -- Scripts desativados

Scripts arquivados pela sprint META-HOOKS-AUDITAR-E-WIRAR (2026-05-15).
Mantidos no repositório para referência histórica e possível reativação
futura, mas NÃO são executados pelo `.pre-commit-config.yaml` nem por
`scripts/pre-commit-check.sh`.

## Inventário

| Script | Motivo do arquivamento | Reativável? |
|--------|------------------------|-------------|
| `check_complexity.py` | Métrica de complexidade ciclomática (>15 bloqueia, >10 avisa). Decisão da auditoria 2026-05-15: over-engineering para projeto pessoal de uma pessoa. Faz sentido em equipes grandes onde múltiplos devs precisam de guardrails objetivos contra funções monstruosas. Aqui o supervisor humano já controla isso na revisão. | Sim -- se o projeto crescer para equipe ou virar SaaS multi-tenant, ativar de volta apontando para `hooks/_arquivado/check_complexity.py`. |
| `check_file_size.py` | Limite de 800 linhas por `.py`. A regra (h) "800L máximo" foi formalmente REVOGADA em 2026-05-12 (sessão 14 do supervisor; MEMORY.md item correspondente). Motivo: refactors mecânicos por contagem de linhas produziam módulos artificiais sem coesão semântica. Coesão > tamanho. | Possivelmente -- só se uma regra revisada de tamanho ressurgir com critério semântico (ex: limite por classe ou por função). |

## Como reativar

Caso seja decidido reativar:

1. Mover o script de volta para `hooks/` com `git mv`.
2. Adicionar entry correspondente em `.pre-commit-config.yaml` no bloco `repos: - repo: local`.
3. Atualizar `hooks/README.md` removendo a entrada de "arquivado" e voltando para "ativo".
4. Atualizar este README removendo o script da tabela.

## Notas históricas

- `check_complexity.py` foi portado da infra Luna em 2026-XX. Originalmente T2 (avisa, não bloqueia).
- `check_file_size.py` foi portado da infra Luna em 2026-XX com limite elevado de 300 para 800 (CLAUDE.md Ouroboros seção 6, então vigente).

# "O que é necessário deve ser feito, o que é supérfluo é fardo." -- pragmático
