# BOOTSTRAP — Setup de uma cópia fresca do protocolo-ouroboros

> **Origem:** Sprint ANTI-MIGUE-10 do plan `pure-swinging-mitten`.
> **Para quem:** desenvolvedor (ou IA) que acabou de clonar o repositório e precisa rodar testes, lint e o pipeline pela primeira vez.
> **Prerequisito:** Linux com `python3 >= 3.11`, `git`, `make`, `apt` (Debian/Ubuntu) ou equivalente.

---

## 1 — Clone e setup mínimo

```bash
git clone git@github.com-personal:AndreBFarias/protocolo-ouroboros.git
cd protocolo-ouroboros
./install.sh
```

`install.sh` cria `.venv`, instala deps, verifica `tesseract-ocr` + `_bz2`, cria estrutura de diretórios. **Não copia hooks git** (ver §4). Em ambiente novo, ele exige `sudo apt` para libs nativas; aceite ou aborte e rode manualmente as linhas indicadas.

## 2 — Validação de saúde do clone

```bash
make smoke           # ./run.sh --check (23 checagens) + smoke aritmético (10 contratos)
make lint            # ruff + check_acentuacao
.venv/bin/pytest -q  # baseline esperada >= 2.030 passed
```

Resultado esperado em fresh clone:
- `make smoke` exit 0 com aviso "XLSX não encontrado" (esperado — você ainda não rodou o pipeline).
- `make lint` exit 0.
- `pytest` exit 0.

Qualquer um falhar: revisite §1 (deps faltando) antes de mexer em código.

## 3 — Primeiro pipeline com dados reais

1. Coloque arquivos brutos (PDFs bancários, NFs, holerites) em `inbox/`.
2. Rode `./run.sh --inbox` — classifier roteia para `data/raw/<pessoa>/<tipo>/`.
3. Rode `./run.sh --tudo` — pipeline completo gera `data/output/ouroboros_2026.xlsx`.
4. Rode `./run.sh --dashboard` — dashboard Streamlit em `localhost:8501`.

PDFs protegidos exigem senha em `.env` (gitignored). Template em `.env.example`:

```bash
cp .env.example .env
# Edite .env e preencha PDF_SENHA_PRIMARIA, PDF_SENHA_SECUNDARIA, PDF_SENHA_CPF
```

Sprint SEC-SENHAS-PARA-ENV (2026-05-17) migrou `mappings/senhas.yaml` (legado) para `.env`. YAML continua funcionando como fallback durante transição. Para migrar local: copiar valores de `senhas.yaml::senhas_pdf` para `.env` como `PDF_SENHA_*`.

## 4 — Hooks git (opcional, mas recomendado)

> **Atenção:** os hooks deste projeto (`commit-msg`, `pre-commit`, `pre-push`) **dependem da infraestrutura pessoal do dono** (`~/.config/git/hooks/_lib.sh` + variáveis `ZSH_IDENTITY_*` em `~/.config/zsh/config.local.zsh`). Eles **não são distribuídos** com o repo nem copiados pelo `install.sh` — incluí-los seria forçar acoplamento com configuração privada (CLAUDE.md ARMADILHA #9).

Quem é o dono e quer manter hooks ativos:

```bash
# Em maquina nova do mesmo dono, restaurar hooks via dotfiles pessoais
ln -sf ~/.config/git/hooks/commit-msg .git/hooks/commit-msg
ln -sf ~/.config/git/hooks/pre-commit .git/hooks/pre-commit
ln -sf ~/.config/git/hooks/pre-push   .git/hooks/pre-push
```

Quem **não** é o dono (colaborador externo, fresh VM, CI):

```bash
# Use o script local standalone como alternativa (sem dependencia de _lib.sh ou ZSH_IDENTITY)
./scripts/pre-commit-check.sh    # roda ruff + check_acentuacao
```

Integre `scripts/pre-commit-check.sh` ao seu workflow (ex: `git config core.hooksPath .githooks/` se criar uma pasta local). O CI no `.github/workflows/ci.yml` já roda lint + smoke + acentuação + pytest a cada push, então mesmo sem hook local, regressões são detectadas no push.

## 5 — Verificação final do bootstrap

```bash
make anti-migue           # entry point unico do gate (Sprint MAKE-AM-01)
```

Esse alvo encadeia `lint`, `smoke`, `test` e `check_concluida_em.py`. Exit 0 = clone limpo e operacional.

## 6 — Referências para problemas comuns

| Sintoma | Solução | Origem |
|---------|---------|--------|
| `_bz2` ImportError | `sudo apt install libbz2-dev xz-utils && pyenv install 3.12.1` | install.sh:35 |
| pyvis sem mostrar grafo | falta `_bz2`; mesma fix acima | Sprint 86.1 |
| C6 XLS não abre | `pip install msoffcrypto-tool` (já em deps) | ARMADILHA #1 |
| Itaú PDF protegido | senha em `mappings/senhas.yaml` (gitignored) | ARMADILHA #2 |
| `pytest --collect-only` muda contagem | provavelmente novo test adicionado; atualizar baseline em `contexto/ESTADO_ATUAL.md` | ANTI-MIGUE-03 |
| `git push` rejeitado por SSH | usar alias `github.com-personal` (não `github.com`) | ARMADILHA #8 |

## 7 — Onboarding canônico para sessão Claude Code

Para uma sessão de Claude Code (Opus principal ou subagent), o ponto de entrada canônico é `contexto/PROMPT_NOVA_SESSAO.md` que lista a ordem de leitura (POR_QUE → ESTADO_ATUAL → COMO_AGIR → CLAUDE.md → spec da sprint).

---

*"Antes de zarpar, conferir que o casco não tem furos." — princípio do bootstrap honesto*
