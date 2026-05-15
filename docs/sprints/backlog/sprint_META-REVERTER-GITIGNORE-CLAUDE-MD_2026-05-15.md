---
id: META-REVERTER-GITIGNORE-CLAUDE-MD
titulo: Reverter entrada `CLAUDE.md` do `.gitignore` (Edit-pronto)
status: backlog
concluida_em: null
prioridade: P0
data_criacao: 2026-05-15
fase: SANEAMENTO
epico: 8
depende_de: []
esforco_estimado_horas: 0.1
origem: auditoria 2026-05-15. Diff do working tree do `.gitignore` adiciona linhas 105-107 "anti-IA (anonimato local) / CLAUDE.md". Isso REVERTERIA a onda META-ONBOARDING-NOVA-SESSAO (commit `d096f2f`, 2026-05-13) que trackeou o `CLAUDE.md` como parte do onboarding canônico. Provável resíduo de decisão anterior à onda META.
---

# Sprint META-REVERTER-GITIGNORE-CLAUDE-MD

## Contexto

A onda META-* recente (commits `d096f2f`, `6a86a06`, `d2622c0`, `8ce3764`, `bcfdbdb`, `9e091c2`, `738f95d`) consolidou:
- `CLAUDE.md` no root trackeado (constituição técnica pública)
- `docs/PADROES_CANONICOS.md` trackeado (rodapé canônico)
- `docs/PROMPT_NOVA_SESSAO.md` trackeado (sem PII)
- Hook SessionStart local que injeta estado vivo

O `.gitignore` no working tree tem 3 linhas pendentes que **invalidariam a decisão**:

```
+# --- anti-IA (anonimato local) ---
+CLAUDE.md
```

Se commitada, o tracking do `CLAUDE.md` é desfeito; próxima sessão Opus perde o ponto de entrada canônico.

## Hipótese e validação ANTES

H1: linhas adicionadas são resíduo, não decisão consciente do dono.

```bash
git log -1 --format="%H %s" -- .gitignore
# Esperado: commit antigo (anterior à onda META)

git log --oneline --all --grep="CLAUDE.md" | head -10
# Esperado: várias menções; onda META commits estão recentes
```

H2: `CLAUDE.md` atual não contém PII sensível:

```bash
grep -E "CPF|CNPJ|97737068|96470242|05127373122" CLAUDE.md
# Esperado: 0 hits
```

## Objetivo

Edit cirúrgico: remover as 3 linhas adicionadas no diff do `.gitignore`.

## Não-objetivos

- Não tocar outras entries do `.gitignore`.
- Não commitar `CLAUDE.md` modificado (já está limpo no HEAD).
- Não criar mecanismo "anti-IA" alternativo (decisão já tomada).

## Proof-of-work runtime-real

```bash
git checkout HEAD -- .gitignore
git diff --stat .gitignore
# Esperado: zero diff

grep -c "CLAUDE.md" .gitignore
# Esperado: 0 (CLAUDE.md NÃO no gitignore)

git ls-files | grep -c "^CLAUDE.md$"
# Esperado: 1 (tracked)
```

## Acceptance

- `.gitignore` revertido para HEAD.
- `CLAUDE.md` continua tracked.
- Working tree limpo da modificação espúria.
- Smoke 10/10. Lint exit 0.

## Padrões aplicáveis

- (a) Edit incremental — não rewrite.
- (m) Branch reversível — `git checkout HEAD -- file` é cirúrgico.

---

*"Reverter sem cerimônia é melhor que justificar o errado." — princípio do limpa-resíduo*
