---
id: META-PROMPT-NOVA-SESSAO-TRACKEADO
titulo: Migrar conteúdo público de PROMPT_NOVA_SESSAO.md para arquivo trackeado pelo git
status: concluída
concluida_em: 2026-05-13
prioridade: P1
data_criacao: 2026-05-13
fase: SANEAMENTO
epico: 8
depende_de:
  - META-ONBOARDING-NOVA-SESSAO
origem: auditoria 2026-05-13. contexto/PROMPT_NOVA_SESSAO.md está gitignored (contexto/* exceto whitelist). Onboarding canônico para nova sessão NÃO viaja com o repo. Dono precisa manualmente entregar o conteúdo a cada nova máquina/clone.
---

# Sprint META-PROMPT-NOVA-SESSAO-TRACKEADO

## Contexto

`contexto/PROMPT_NOVA_SESSAO.md` (gitignored) é o prompt canônico que o dono usa para iniciar nova sessão com contexto. Hoje é local. Em máquina nova, o conteúdo precisa ser recriado ou copiado manualmente.

Solução: separar PII (mantém local) de conteúdo público (vai pro git).

## Entregável

1. **`docs/PROMPT_NOVA_SESSAO.md`** (trackeado, sem PII):
   - Header explicando função do arquivo.
   - Bloco "leia nesta ordem" apontando para os 5 docs canônicos.
   - Comandos básicos do projeto (`./run.sh --check`, `dossie_tipo.py --listar-tipos`).
   - Resumo de 1 parágrafo da filosofia.
   - SEM nomes/CPFs/CNPJs reais.

2. **`contexto/PROMPT_NOVA_SESSAO.md` (local, gitignored)**:
   - Mantém versão pessoal do dono com PII (nomes, contas bancárias, contexto familiar).
   - Aponta para `docs/PROMPT_NOVA_SESSAO.md` como fonte pública.

3. **README.md atualizado** (já tem após META-ONBOARDING):
   - Adicionar link para `docs/PROMPT_NOVA_SESSAO.md` na seção "Para colaboradores AI".

## Acceptance

- `git ls-files docs/PROMPT_NOVA_SESSAO.md` retorna o arquivo.
- Conteúdo do arquivo trackeado NÃO contém PII (validar com grep CPF/CNPJ).
- `contexto/PROMPT_NOVA_SESSAO.md` segue gitignored mas referencia o trackeado.
- Lint zero.

## Padrão canônico aplicável

(e) data/ no .gitignore -- mesma lógica para PII em contexto/. Distinção pública vs privada.

---

*"Onboarding sem PII viaja; onboarding com PII se hospeda." -- princípio da clivagem*

---

## Fechamento (2026-05-13)

Entregue por executor-sprint F (worktree `agent-ace58a5dc3a776fcf`):

- Criado `docs/PROMPT_NOVA_SESSAO.md` trackeado, sem PII (grep CPF/CNPJ retornou 0).
- `contexto/PROMPT_NOVA_SESSAO.md` permanece gitignored (whitelist em `.gitignore`
  não inclui o arquivo; mantém PII na máquina do supervisor).
- README.md NÃO modificado neste pacote (executor A já tocou na onda anterior;
  evita conflito futuro). Item 3 do entregável deve ser absorvido em sprint
  consolidadora se ainda não estiver no README.
- Acceptance:
  - `git ls-files docs/PROMPT_NOVA_SESSAO.md` -- OK após commit.
  - Grep CPF/CNPJ em `docs/PROMPT_NOVA_SESSAO.md` -- 0 ocorrências.
  - `contexto/PROMPT_NOVA_SESSAO.md` segue ignored (whitelist `.gitignore` linha 16-21).
  - `make lint` -- exit 0.
