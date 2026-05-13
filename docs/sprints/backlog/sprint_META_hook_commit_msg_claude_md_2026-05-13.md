---
id: META-HOOK-COMMIT-MSG-CLAUDE-MD
titulo: Refinar regex AI_MENTION_RE para não bloquear nome de arquivo CLAUDE.md no subject
status: backlog
concluida_em: null
prioridade: P3
data_criacao: 2026-05-13
fase: SANEAMENTO
epico: 8
depende_de: []
tipo_documental_alvo: null
afeta_toolchain_global_dono: true
---

# Sprint META-HOOK-COMMIT-MSG-CLAUDE-MD

## Contexto

Em 2026-05-13 (Sprint META-ONBOARDING-NOVA-SESSAO), o executor A precisou commitar criação de `CLAUDE.md` na raiz do repo. O hook commit-msg global (`~/.config/git/hooks/commit-msg` chamando `~/.config/git/hooks/_lib.sh`) bloqueou o subject porque o regex `AI_MENTION_RE` casa o token case-insensitive `[Cc]laude` -- pegando o nome de arquivo `CLAUDE.md`.

Executor adaptou o subject para "constituicao tecnica" e o commit passou. Funcional mas chato -- nomes de arquivo canônicos (CLAUDE.md, GEMINI.md, AGENTS.md) podem aparecer em subjects legítimos: "feat: cria CLAUDE.md", "fix: ajusta link de CLAUDE.md".

## Escopo

**ATENÇÃO**: o regex vive em arquivo **fora do repositório** (~/.config/git/hooks/_lib.sh, toolchain pessoal do dono). Modificá-lo afeta TODOS os projetos do dono. Esta sprint serve para o dono executar manualmente em sessão fora do escopo do protocolo-ouroboros. Não há executor automatizável.

## Hipótese

Adicionar negative lookahead PCRE para excluir o padrão `CLAUDE.md` (e variações).

## Solução proposta

### Mudança 1 -- regex em `~/.config/git/hooks/_lib.sh` linha 20

Trocar `[Cc]laude` por `[Cc]laude(?!\.md\b)` e idem para `[Gg]emini` e qualquer outro token que tenha nome de arquivo canônico equivalente. Requer migrar consumidores de `grep -E` para `grep -P` (PCRE).

### Mudança 2 -- consumidores do regex (`~/.config/git/hooks/commit-msg` ~3 ocorrências)

Trocar `grep -qiE` por `grep -qiP` e `grep -viE` por `grep -viP` nos pontos que usam `AI_MENTION_RE`.

## Alternativa minimalista (se PCRE não estiver disponível em todos os sistemas)

Antes do bloqueio do subject, neutralizar nomes de arquivo canônicos via `sed` e re-testar:

```bash
SUBJECT_SEM_ARQUIVOS=$(echo "$SUBJECT" | sed -e 's|CLAUDE\.md||g' -e 's|GEMINI\.md||g' -e 's|AGENTS\.md||g')
if echo "$SUBJECT_SEM_ARQUIVOS" | grep -qiE "$AI_PATTERN"; then
    # bloqueia apenas se sobrou menção a IA depois de neutralizar nomes de arquivo
fi
```

## Validação ANTES

```bash
echo "feat(docs): cria CLAUDE.md" | ~/.config/git/hooks/commit-msg /dev/stdin
# Esperado: bloqueio HOJE (antes do fix)
# Esperado pós-fix: passa (subject só tem nome de arquivo)

echo "feat: assistente de IA melhorou o codigo" | ~/.config/git/hooks/commit-msg /dev/stdin
# Esperado: bloqueio sempre (palavra substantiva)
```

## Acceptance

- `git commit -m "feat(docs): cria CLAUDE.md"` passa sem auto-fix nem bloqueio.
- Outras menções substantivas continuam bloqueando.
- Outros projetos do dono que usam o mesmo hook não regridem.

## Padrão canônico aplicável

- (n) Defesa em camadas: hook continua bloqueando menções substantivas; apenas afina sensibilidade para nomes de arquivo canônicos.

## Nota operacional

Sprint não é executável por executor-sprint porque toca arquivo fora do repo. Dono executa manualmente quando achar adequado.

---

*"Hook é defesa, não tirano. Nomes próprios não são ofensas." -- princípio da defesa proporcional*
