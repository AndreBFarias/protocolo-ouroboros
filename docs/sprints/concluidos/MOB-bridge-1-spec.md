---
concluida_em: 2026-05-01
escopo_refinado_por: padrão (k) BRIEF -- spec original assumia ~17 ocorrências cosméticas; grep revelou 51 em src/ + 154 em tests/ atravessando schema XLSX vivo + UI dashboard + dados persistidos
entrega_real: src/utils/pessoas.py (resolver canônico), schema XLSX coluna quem migra para pessoa_a/pessoa_b/casal, dashboard local-first com display via nome_de() em runtime, scripts/check_anonimato.sh, ADRs 23 e 24
commits: 6cc49ab, fc73def, bb4a94a, b1531b1, 60f2f89, 3c6733b, afcc240
seguimento: nenhum (achado colateral sobre data/raw/andre/ -> data/raw/pessoa_a/ documentado em ADR-23 como decisão deliberada de adiamento)
---

# Sprint MOB-bridge-1 — Refactor pessoa_a/pessoa_b no Backend Python

```
REPO ALVO:  ~/Desenvolvimento/protocolo-ouroboros/
DEPENDE:    nada (pode rodar em paralelo às sprints Mobile)
BLOQUEIA:   MOB-bridge-2 (geração dos caches readonly)
            indiretamente Mobile M10 (Mini Humor) e M14 (Mini Financeiro)
ESTIMATIVA: 2-3h
```

> Esta spec descreve trabalho a ser executado no repositório
> `~/Desenvolvimento/protocolo-ouroboros/`. O arquivo vive aqui no
> Mobile como prompt direto para a próxima sessão que abrir o backend.
> Quando chegar o momento, o Opus deve copiar o conteúdo para
> `docs/sprints/MOB-bridge-1-spec.md` no repositório backend ou ler
> daqui mesmo via path absoluto.

## 1. Objetivo

Eliminar nomes reais hardcoded do código Python do backend. Toda
identidade de pessoa passa a ser resolvida em runtime a partir do
`mappings/pessoas.yaml`, que já existe e já contém o schema completo
(CPFs, CNPJs, razões sociais, aliases). Os 22 extratores existentes
continuam funcionando sem regressão. Um script de validação espelho
do Mobile (`scripts/check_anonimato.sh`) entra no pre-commit para
travar futuras violações. O resultado: o repositório backend pode ir
público sem expor nome próprio em arquivos `.py`.

## 2. Entregáveis

### Arquivos novos (no repo backend)

- `~/Desenvolvimento/protocolo-ouroboros/src/utils/pessoas.py` —
  Módulo único de resolução de identidade. Exporta:
  - `carregar_pessoas() -> dict` — lê `mappings/pessoas.yaml` uma
    vez e cacheia em memória.
  - `resolver_pessoa(cpf: str | None, cnpj: str | None, razao_social:
    str | None, alias: str | None, fallback: str = "casal") -> str`
    — retorna `"pessoa_a"`, `"pessoa_b"` ou `"casal"`, na ordem de
    casamento já documentada no header de `pessoas.yaml`.
  - `nome_de(pessoa_id: str) -> str` — retorna o display name do
    yaml apenas para uso em prosa de log ou xlsx (nunca em
    nomes de arquivo, nunca em código persistido em git).
  - `pessoa_id_de_pasta(path: str) -> str | None` — fallback layer 2
    quando o detector não consegue casar via CPF/CNPJ/razão social
    (lê o nome da pasta-pai e mapeia `data/raw/<pessoa_a|pessoa_b|
    casal>/`).
- `~/Desenvolvimento/protocolo-ouroboros/scripts/check_anonimato.sh`
  — Espelho do `scripts/check_anonimato.sh` que existe no Mobile.
  Falha o pre-commit se algum arquivo `.py` em `src/` ou `tests/`
  contiver `Andr[eé]|Vit[oó]ria|Maria|Jo[aã]o` fora de
  `mappings/pessoas.yaml`, `mappings/cpfs_pessoas.yaml.example`, do
  próprio script ou de docs históricos. Aceita marker
  `# anonimato-allow: <razao>` na mesma linha do token quando a
  palavra é substantivo comum (raro no Python; mais comum em prosa
  de docstring).
- `~/Desenvolvimento/protocolo-ouroboros/docs/adr/ADR-23-pessoa-a-b-no-backend.md`
  — ADR cruzado, sucessor da ADR-0011 do Mobile. Texto análogo ao
  Mobile mas adaptado: identidades genéricas em todo código Python,
  resolução via `mappings/pessoas.yaml`, contrato cruzado com Mobile.
- `~/Desenvolvimento/protocolo-ouroboros/tests/test_pessoas_resolver.py`
  — Testes do módulo `src/utils/pessoas.py`:
  - resolução por CPF formatado e não formatado;
  - resolução por CNPJ raiz 8 dígitos sem `/0001-XX`;
  - resolução por razão social case-insensitive;
  - resolução por alias;
  - fallback para `"casal"` quando nada casa;
  - `pessoa_id_de_pasta()` cobrindo `data/raw/pessoa_a/`,
    `data/raw/pessoa_b/`, `data/raw/casal/`.

### Arquivos modificados (no repo backend)

- `~/Desenvolvimento/protocolo-ouroboros/src/extractors/base.py` —
  Remover `if .. return "André"` / `return "Vitória"`. Substituir
  pela chamada a `resolver_pessoa()` ou `pessoa_id_de_pasta()`.
  Retornar sempre `"pessoa_a"` / `"pessoa_b"` / `"casal"`.
- `~/Desenvolvimento/protocolo-ouroboros/src/extractors/c6_cartao.py`
  — Trocar `pessoa="André"` por `pessoa=resolver_pessoa(...)` ou
  pelo identificador genérico apropriado.
- `~/Desenvolvimento/protocolo-ouroboros/src/extractors/santander_pdf.py`
  — Idem.
- `~/Desenvolvimento/protocolo-ouroboros/src/extractors/itau_pdf.py`
  — Idem. Cuidado especial com o comentário sobre Itaú e a string
  `"Vitória"` (parece ser uma menção a cidade, não pessoa) — manter
  marker `# anonimato-allow: cidade Vitoria-ES` se confirmado, mas
  preferir reescrever o comentário sem o nome.
- `~/Desenvolvimento/protocolo-ouroboros/src/pipeline.py` — Comentários
  internos com nomes reais (ex: `"Vitória" no Itaú`) viram
  `pessoa_b` ou explicação genérica.
- `~/Desenvolvimento/protocolo-ouroboros/src/intake/pessoa_detector.py`
  — Já usa `mappings/pessoas.yaml`. Auditar para garantir que os
  retornos são genéricos (`"pessoa_a"` / `"pessoa_b"` / `"casal"`)
  e não nomes reais. Caso ainda emita strings com nomes próprios,
  adaptar.
- `~/Desenvolvimento/protocolo-ouroboros/mappings/pessoas.yaml` —
  Adicionar campo `display_name` em cada bloco de pessoa para uso
  em prosa de relatório (sem alterar `cpfs`, `cnpjs`, `razao_social`,
  `aliases`). Renomear chaves de topo `andre` → `pessoa_a` e
  `vitoria` → `pessoa_b`. Os valores reais (CPFs etc.) permanecem
  e o arquivo continua no `.gitignore`.
- `~/Desenvolvimento/protocolo-ouroboros/mappings/cpfs_pessoas.yaml.example`
  — Atualizar o `.example` com chaves genéricas `pessoa_a` e
  `pessoa_b` no lugar de `andre` e `vitoria`.
- `~/Desenvolvimento/protocolo-ouroboros/hooks/check_anonymity.py` —
  Estender (ou substituir) para também rodar
  `scripts/check_anonimato.sh` no pre-commit. Manter o hook Python
  existente que cobre vazamento de IA (Claude, OpenAI, etc.).
- `~/Desenvolvimento/protocolo-ouroboros/docs/CONTEXT.md` —
  Adicionar Seção curta "Identidade de Pessoas" apontando para a
  ADR-23 (deste backend) e para a ADR-0011 do Mobile.
- `~/Desenvolvimento/protocolo-ouroboros/CHANGELOG.md` — Entrada
  `[Unreleased]` em `### Refactored` documentando a remoção dos
  nomes hardcoded e a introdução do resolver genérico.

## 3. APIs reutilizáveis

- `~/Desenvolvimento/protocolo-ouroboros/mappings/pessoas.yaml` —
  Schema canônico de identidade. **Não recriar.** Apenas estender
  com `display_name` e renomear chaves de topo.
- `~/Desenvolvimento/protocolo-ouroboros/src/intake/pessoa_detector.py`
  — Já implementa parte da lógica de resolução por CPF/CNPJ/razão
  social. Mover a parte reutilizável para
  `src/utils/pessoas.py` e fazer o detector consumir o módulo novo.
- `~/Desenvolvimento/protocolo-ouroboros/hooks/check_anonymity.py` —
  Padrão de hook pre-commit existente. O `check_anonimato.sh` novo
  vira sub-passo do hook ou step paralelo do pre-commit.
- `~/Desenvolvimento/Protocolo-Mob-Ouroboros/scripts/check_anonimato.sh`
  — Referência canônica do shell script. Adaptar para Python
  (`--include='*.py'`) mantendo as exclusões de marker
  `anonimato-allow:`, de `mappings/pessoas.yaml` e do próprio
  script.

## 4. Restrições

- **Regra −1 (Anonimato):** zero referência a IA ("Claude",
  "Anthropic", "OpenAI", "GPT", "by AI", "ai-generated"). Zero nomes
  reais ("André", "Vitória", "Maria", "João") em qualquer arquivo
  `.py` em `src/`, `tests/`. Únicas exceções:
  `mappings/pessoas.yaml` (sensível, no `.gitignore`),
  `mappings/cpfs_pessoas.yaml.example` (template com placeholders
  numéricos), o próprio `scripts/check_anonimato.sh` (que define os
  padrões proibidos) e docs históricos em `docs/auditorias/` e
  `docs/HISTORICO_SESSOES.md`.
- Sem emojis em código, docs ou commits.
- Comentários e docstrings em código `.py` **sem acento** (convenção
  shell/CI espelha a de commit messages).
- Mensagens de commit em PT-BR **sem acento**.
- Sem `print()` novos em código de produção (o backend tem
  `hooks/check_new_prints.py` que trava o pre-commit).
- Atomic write não se aplica nesta sprint (sem geração de cache);
  isso é problema da MOB-bridge-2.
- Não mexer em arquivos sob `data/raw/` ou `data/processed/`. Esta
  sprint é só refactor de código e config.
- Não rodar `git rm` em `mappings/pessoas.yaml`. O arquivo continua
  fora do versionamento (já está no `.gitignore`).
- Os 22 extratores existentes precisam continuar passando 100%.

## 5. Procedimento sugerido

1. Verificar baseline:
   ```bash
   cd ~/Desenvolvimento/protocolo-ouroboros
   git status
   git log --oneline -3
   ./venv/bin/pytest tests/ -q --tb=line
   ```
   Capturar contagem de testes passando como FAIL_BEFORE = 0.
2. Auditar o estado atual com grep:
   ```bash
   grep -rE 'Andr[eé]|Vit[oó]ria' src/ --include='*.py'
   grep -rE 'Andr[eé]|Vit[oó]ria' tests/ --include='*.py'
   ```
   Anotar a lista de arquivos e linhas (deve haver ~10-15
   ocorrências em `src/extractors/` e algumas em `src/pipeline.py`,
   `src/integrations/controle_bordo.py`).
3. Criar `src/utils/pessoas.py` com as 4 funções públicas. Adicionar
   docstrings sem acento. Reaproveitar lógica existente do
   `src/intake/pessoa_detector.py`. Validar em REPL:
   ```python
   from src.utils.pessoas import resolver_pessoa
   resolver_pessoa(cpf="051.273.731-22") == "pessoa_a"
   resolver_pessoa(razao_social="vitoria maria silva dos santos") == "pessoa_b"
   resolver_pessoa(alias="desconhecido") == "casal"
   ```
4. Renomear chaves de topo no `mappings/pessoas.yaml`:
   - `andre` → `pessoa_a`
   - `vitoria` → `pessoa_b`
   Adicionar campo `display_name` por pessoa para usos legítimos em
   relatórios (xlsx, log de auditoria). O arquivo continua no
   `.gitignore`. Atualizar `mappings/cpfs_pessoas.yaml.example` com
   chaves genéricas.
5. Refatorar os extratores em ordem:
   `src/extractors/base.py` → `c6_cartao.py` → `santander_pdf.py` →
   `itau_pdf.py`. A cada arquivo: rodar `pytest tests/ -k <extrator>`
   antes e depois. Não passar para o próximo até o teste do anterior
   passar.
6. Refatorar `src/pipeline.py`. Trocar comentários com nomes reais
   por explicação genérica (`pessoa_a`/`pessoa_b`).
7. Refatorar `src/integrations/controle_bordo.py`. O Vault humano
   (`~/Controle de Bordo/`) era citado pelo nome do dono na
   docstring; reescrever sem citar pessoa.
8. Atualizar `src/intake/pessoa_detector.py` para consumir
   `src/utils/pessoas.py` e remover duplicação. Garantir que o
   detector retorna `"pessoa_a"`/`"pessoa_b"`/`"casal"` (string
   genérica) e nunca o display name.
9. Criar `scripts/check_anonimato.sh` adaptado do Mobile:
   ```bash
   #!/usr/bin/env bash
   # check_anonimato.sh -- Regra -1 no backend Python
   # Trava commits que reintroduzem nome real em src/ ou tests/.
   set -euo pipefail
   PROIBIDO_IA='claude|anthropic|openai|gpt-[0-9]|chatgpt|by ai|ai-generated'
   NOMES_REAIS='Andr[eé]|Vit[oó]ria|Maria|Jo[aã]o'
   VIOLACOES_IA=$(grep -rniE "$PROIBIDO_IA" src/ tests/ scripts/ 2>/dev/null \
     --include='*.py' \
     | grep -viE 'api_key|provider|model|config|client|engine' || true)
   if [[ -n "$VIOLACOES_IA" ]]; then
     echo "ERRO: anonimato IA violado em src/, tests/ ou scripts/:"
     echo "$VIOLACOES_IA"
     exit 1
   fi
   VIOLACOES_NOMES=$(grep -rE "$NOMES_REAIS" src/ tests/ 2>/dev/null \
     --include='*.py' \
     | grep -v 'mappings/pessoas.yaml' \
     | grep -v 'cpfs_pessoas.yaml.example' \
     | grep -v 'anonimato-allow' || true)
   if [[ -n "$VIOLACOES_NOMES" ]]; then
     echo "ERRO: nome real hardcoded fora de mappings/:"
     echo "$VIOLACOES_NOMES"
     exit 1
   fi
   echo "OK: anonimato preservado (Regra -1)"
   ```
10. Plugar `scripts/check_anonimato.sh` no pre-commit do backend.
    Editar `hooks/pre_push_protect_main.sh` ou criar
    `hooks/check_anonimato.sh` que chama o script e exige exit 0.
    Conferir que o hook é configurado em `.git/hooks/` ou via
    `core.hooksPath`.
11. Criar `docs/adr/ADR-23-pessoa-a-b-no-backend.md` com cabeçalho
    Status / Data / Sprint / Contexto / Decisão / Consequências /
    Sucessor (cita ADR-0011 do Mobile como par cruzado). Texto
    análogo ao Mobile, adaptado para Python.
12. Adicionar `tests/test_pessoas_resolver.py` cobrindo os 6 cases
    listados na seção 2. Rodar:
    ```bash
    ./venv/bin/pytest tests/test_pessoas_resolver.py -v
    ```
13. Validação final:
    ```bash
    grep -rE 'Andr[eé]|Vit[oó]ria' src/ --include='*.py'
    grep -rE 'Andr[eé]|Vit[oó]ria' tests/ --include='*.py'
    ./scripts/check_anonimato.sh
    ./venv/bin/pytest tests/ -q
    ```
    Os dois greps devem retornar vazio (com saída exit 1, padrão
    `grep` sem matches). O `check_anonimato.sh` exit 0. O pytest
    com 131+ testes passando (exatamente o mesmo total de antes,
    mais os novos 6 do `test_pessoas_resolver.py`).
14. Atualizar `CHANGELOG.md` com entrada `### Refactored` em
    `[Unreleased]`.
15. Commit:
    ```
    refactor: pessoa_a_b mapeamento via mappings/pessoas.yaml
    ```

## 6. Verificação runtime-real

```bash
cd ~/Desenvolvimento/protocolo-ouroboros

# 1. Anonimato (Regra -1) no Python
./scripts/check_anonimato.sh

# 2. Nenhum nome real fora de mappings/
grep -rE 'Andr[eé]|Vit[oó]ria' src/ --include='*.py'
grep -rE 'Andr[eé]|Vit[oó]ria' tests/ --include='*.py'
# espera: ambos retornam vazio (exit 1 do grep, ok)

# 3. Lint completo (ruff + acentuacao + cobertura)
make lint

# 4. Testes (131+ passando)
make test

# 5. Smoke aritmetico
make smoke

# 6. Anti-migue (gate de 9 checks)
make anti-migue

# 7. Resolver em REPL como sanity check
./venv/bin/python -c "from src.utils.pessoas import resolver_pessoa; \
  print(resolver_pessoa(cpf='051.273.731-22')); \
  print(resolver_pessoa(razao_social='vitoria maria silva dos santos')); \
  print(resolver_pessoa(alias='desconhecido'))"
# espera: pessoa_a / pessoa_b / casal
```

Todos exit 0. Se algum quebrar, parar e reportar com output literal.

## 7. Commit

```
refactor: pessoa_a_b mapeamento via mappings/pessoas.yaml
```

## 8. Checkpoint visual

Não aplicável. Sprint backend de refactor puro, sem UI.

## 9. Definição de Pronto

- [ ] `src/utils/pessoas.py` exporta 4 funções públicas; testes
      cobrem 6 cases.
- [ ] `mappings/pessoas.yaml` chaves topo renomeadas para
      `pessoa_a`/`pessoa_b` com `display_name` por pessoa.
- [ ] Todos extratores em `src/extractors/` retornam genéricos.
- [ ] `pipeline.py`, `controle_bordo.py` sem nomes reais nem em
      comentários.
- [ ] `scripts/check_anonimato.sh` no backend ativo no pre-commit.
- [ ] ADR-23 do backend formalizada citando cruzamento com ADR-0011
      do Mobile.
- [ ] `make test` 131+ testes passando (sem regressão); +6 testes
      novos do `test_pessoas_resolver.py`.
- [ ] `make lint` + `make smoke` + `make anti-migue` exit 0.
- [ ] `grep` por nomes reais em `src/` e `tests/` retorna vazio.

## 10. Decisões tomadas

- **ADR-23 mantida:** numeração local do backend; cruzamento com
  ADR-0011 Mobile citado explicitamente no header.
- **Renomeação `andre`/`vitoria` → `pessoa_a`/`pessoa_b` no yaml:**
  feita com auditoria prévia em `pessoa_detector.py` e
  `controle_bordo.py` antes de commitar.
- **Pre-commit roda ambos os hooks:** Python (`check_anonymity.py`
  para IA com regex sofisticada) e shell (`check_anonimato.sh`
  para nomes reais com regra estrita).
- **Comentário Itaú "Vitória-ES":** reescrever sem citar
  toponimo (ex: `# evita falso-positivo com nome de cidade`).
  Manter limpeza absoluta.

Sprint pronta para execução sem perguntas pendentes.
