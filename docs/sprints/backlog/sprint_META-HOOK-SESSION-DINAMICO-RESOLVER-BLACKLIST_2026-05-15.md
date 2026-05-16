---
id: META-HOOK-SESSION-DINAMICO-RESOLVER-BLACKLIST
titulo: "Conflito entre blacklist global do dono e tracking do `.claude/hooks/session-start-projeto.py`"
status: backlog
concluida_em: null
prioridade: P2
data_criacao: 2026-05-15
fase: SANEAMENTO
epico: 8
depende_de: []
esforco_estimado_horas: 0.5
origem: "achado da tentativa META-HOOK-SESSION-DINAMICO 2026-05-15. Hook pre-push global do dono em ~/.config/git/hooks/pre-push consulta ~/.config/git/anonymity-blacklist.txt que lista `.claude/` como path proibido. Qualquer commit que toque `.claude/<qualquer>` (incluindo arquivos previamente trackeados como `.claude/hooks/session-start-projeto.py`) é bloqueado. .gitignore local do repo tem exceções para preservar tracking de session-start-projeto.py + settings.json (sprint META-HOOK-SESSION-START-PROJETO original), mas o pre-push global é mais forte."
---

# Sprint META-HOOK-SESSION-DINAMICO-RESOLVER-BLACKLIST

## Contexto

Tentativa em 2026-05-15 de implementar META-HOOK-SESSION-DINAMICO falhou no
push: hook pre-push global do dono bloqueia qualquer commit que toque
`.claude/` por causa da blacklist global. O arquivo
`.claude/hooks/session-start-projeto.py` foi trackeado em commit `bcfdbdb`
da sprint anterior (META-HOOK-SESSION-START-PROJETO) que provavelmente
usou `--no-verify` para superar o hook.

Existe tensão arquitetural:
- O projeto considera o hook canônico e o tracka via exceções no
  `.gitignore` local.
- A blacklist global do dono considera `.claude/` privado e nunca aceita
  no tracking.

Enquanto a tensão não for resolvida, melhorias no hook ficam apenas
locais (arquivo no disco mas não no repo), o que é débito de
reprodutibilidade.

## Hipótese e validação ANTES

```bash
cat ~/.config/git/anonymity-blacklist.txt | grep ".claude"
# Esperado: .claude/

git ls-files .claude/
# Esperado: .claude/hooks/session-start-projeto.py, .claude/settings.json

# Tentar push tocando .claude/ falha:
echo "# noop" >> .claude/hooks/session-start-projeto.py
git add .claude/hooks/session-start-projeto.py
git commit -m "test: noop"
git push origin main  # Esperado: [pre-push] BLOQUEADO
git reset --keep HEAD~1
```

## Objetivo

Escolher uma das 3 rotas (decisão arquitetural do dono):

**Rota A — Remover exceções do `.gitignore`** (alinhar com blacklist global):
- Editar `.gitignore` removendo linhas 110-116 (exceções de `.claude/hooks/` e `.claude/settings.json`).
- `git rm --cached -r .claude/`.
- Commitar destrack via `--no-verify` (uma vez).
- Próximas modificações no hook ficam locais; cada dev/máquina mantém o seu próprio.

**Rota B — Adicionar exceção na blacklist global**:
- Editar `~/.config/git/anonymity-blacklist.txt` adicionando uma forma de excluir paths específicos.
- Mexer em config global do dono — autorização explícita necessária.
- Preserva tracking + permite atualizações futuras do hook.

**Rota C — Mover script para fora de `.claude/`**:
- `git mv .claude/hooks/session-start-projeto.py hooks/session-start-projeto.py`.
- Atualizar referência em `.claude/settings.json` (mas isso ainda toca `.claude/`).
- Solução parcial.

## Não-objetivos

- Não usar `--no-verify` recorrente (anti-padrão).
- Não duplicar o hook em local público + `.claude/`.

## Proof-of-work runtime-real

Para Rota A:
```bash
git ls-files .claude/ | wc -l  # esperado: 0 após destrack
git check-ignore .claude/hooks/session-start-projeto.py  # esperado: hit
git push origin main  # esperado: OK
```

## Acceptance

- Decisão de rota documentada em commit message.
- Push subsequente que NÃO toca `.claude/` continua passando.
- Modificações no hook local não geram conflito com pre-push.

## Padrões aplicáveis

- (l) Achado colateral vira sprint-filha.
- (q) Plano antes de agir — decisão arquitetural.

---

*"Política conflitante é débito invisível até o primeiro push." — princípio da política consistente*
