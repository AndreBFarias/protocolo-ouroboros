# Sprint MOB-bridge-2 — Geração dos Caches Mobile (humor-heatmap e financas-cache)

```
REPO ALVO:  ~/Desenvolvimento/protocolo-ouroboros/
DEPENDE:    MOB-bridge-1 fechada (resolver pessoa_a/pessoa_b ativo)
BLOQUEIA:   Mobile M10 (Mini Humor) e Mobile M14 (Mini Financeiro)
ESTIMATIVA: 3-4h
```

> Esta spec descreve trabalho a ser executado no repositório
> `~/Desenvolvimento/protocolo-ouroboros/`. O arquivo vive aqui no
> Mobile como prompt direto para a próxima sessão que abrir o backend.
> Quando chegar o momento, o Opus deve copiar o conteúdo para
> `docs/sprints/MOB-bridge-2-spec.md` no repositório backend ou ler
> daqui mesmo via path absoluto.

## 1. Objetivo

Gerar dois arquivos JSON de cache no Vault Mobile que alimentam as
Telas 21 (Mini Humor) e 22 (Mini Financeiro) do app. O backend Python
calcula as agregações pesadas (varredura de 90 daily files, classificação
de transações via os 22 extratores) uma única vez por execução do
pipeline e serializa o resultado em JSONs versionados, gravados de
forma atômica em `~/Protocolo-Ouroboros/.ouroboros/cache/`. O Mobile
**só lê** os JSONs e nunca os escreve (ADR-0012). Quando o cache não
existe, o Mobile mostra empty state explicando como rodar o pipeline.

## 2. Entregáveis

### Arquivos novos (no repo backend)

- `~/Desenvolvimento/protocolo-ouroboros/src/protocolo_ouroboros/mobile_cache/__init__.py`
  — Pacote Python novo. Exporta `gerar_todos()` que dispara os dois
  geradores em sequência.
- `~/Desenvolvimento/protocolo-ouroboros/src/protocolo_ouroboros/mobile_cache/humor_heatmap.py`
  — Gerador do `humor-heatmap.json` (Tela 21).
  - `gerar_humor_heatmap(vault_root: Path, periodo_dias: int = 90,
    saida: Path | None = None) -> Path`
  - Lê todos os `.md` em `<vault_root>/daily/` e
    `<vault_root>/inbox/mente/humor/` cuja data caia nos últimos 90
    dias.
  - Parser de frontmatter YAML lê `data`, `autor`, `humor`,
    `energia`, `ansiedade`, `foco`.
  - Agrega por `(data, autor)` em estrutura `celulas: list[dict]`
    conforme schema da ADR-0012.
  - Calcula `estatisticas` por pessoa: `media_humor_30d`,
    `registros_30d`, `registros_total`.
  - Serializa via `json.dumps(..., ensure_ascii=False, indent=2)` e
    escreve em `<vault_root>/.ouroboros/cache/humor-heatmap.json`
    com atomic write (`<...>.tmp` + `os.replace`).
- `~/Desenvolvimento/protocolo-ouroboros/src/protocolo_ouroboros/mobile_cache/financas_cache.py`
  — Gerador do `financas-cache.json` (Tela 22).
  - `gerar_financas_cache(vault_root: Path, xlsx_path: Path,
    referencia: date | None = None, saida: Path | None = None) -> Path`
  - Roda APÓS o pipeline de classificação. Lê o XLSX consolidado da
    semana de `referencia` (default: semana atual ISO).
  - Calcula `gasto_semana`, `gasto_semana_anterior` (semana ISO
    anterior), `delta_textual` ("acima da média", "abaixo da média",
    "dentro da média" via heurística simples sobre média de 12
    semanas).
  - `top_categorias`: top 5 categorias por valor absoluto da semana,
    com `nome`, `valor`, `percentual` (sobre `gasto_semana`).
  - `ultimas_transacoes`: 20 transações mais recentes por
    `data` desc (do XLSX inteiro, não só da semana).
  - Serializa e atomic write em
    `<vault_root>/.ouroboros/cache/financas-cache.json`.
- `~/Desenvolvimento/protocolo-ouroboros/src/protocolo_ouroboros/mobile_cache/atomic.py`
  — Helper `write_json_atomic(path: Path, payload: dict) -> None`
  reutilizável pelos dois geradores. Implementa o padrão
  `path.tmp` + `os.replace(path.tmp, path)`. Garante que o Mobile
  jamais lê arquivo parcial.
- `~/Desenvolvimento/protocolo-ouroboros/tests/mobile_cache/__init__.py`
  — Pacote de testes.
- `~/Desenvolvimento/protocolo-ouroboros/tests/mobile_cache/conftest.py`
  — Fixtures comuns: `tmp_vault_with_dailies(n_days=5,
  pessoa=pessoa_a)` e `tmp_vault_with_xlsx(transacoes=[...])`.
- `~/Desenvolvimento/protocolo-ouroboros/tests/mobile_cache/test_humor_heatmap.py`
  — Testes do gerador de humor:
  - 5 daily files em sequência → 5 células no JSON;
  - frontmatter incompleto (faltando `humor`) é silenciosamente
    pulado, não quebra o gerador;
  - estatísticas batem com cálculo manual em fixture pequeno;
  - `schema_version == 1`;
  - atomic write: arquivo final aparece de uma vez (mockando
    `os.replace`).
- `~/Desenvolvimento/protocolo-ouroboros/tests/mobile_cache/test_financas_cache.py`
  — Testes do gerador financeiro:
  - XLSX fixture com 30 transações em 4 semanas → top_categorias
    correto, percentuais somando ~100%, ultimas_transacoes ordenadas
    desc;
  - `delta_textual` correto em três cenários (acima, abaixo, dentro);
  - sem transações na semana → cache mostra `gasto_semana = 0` e
    `top_categorias = []` (não quebra);
  - autor em transações é `pessoa_a`/`pessoa_b`/`casal` (validar
    integração com MOB-bridge-1).
- `~/Desenvolvimento/protocolo-ouroboros/tests/mobile_cache/test_atomic.py`
  — Testes do helper:
  - escrita atômica produz arquivo final;
  - se falhar no meio, `.tmp` fica e arquivo final não é tocado;
  - `os.replace` é chamado no caminho feliz.

### Arquivos modificados (no repo backend)

- `~/Desenvolvimento/protocolo-ouroboros/run.sh` — A flag
  `--full-cycle` no fim chama o módulo novo:
  ```bash
  python -m protocolo_ouroboros.mobile_cache
  ```
  Antes do `exit 0`. Sem alterar comportamento de `--inbox`,
  `--tudo`, `--mes` (só `--full-cycle` invoca o gerador). A flag
  `--mobile-cache` extra dispara apenas o gerador, sem rodar o
  pipeline (útil para regenerar caches sem reprocessar dados).
- `~/Desenvolvimento/protocolo-ouroboros/Makefile` — Adicionar
  target `sync` como alias canônico de `--full-cycle`:
  ```
  sync: ## Pipeline completo + caches Mobile (alimenta o app)
      ./run.sh --full-cycle
  ```
  Manter targets `process`, `inbox`, `tudo` intactos.
- `~/Desenvolvimento/protocolo-ouroboros/src/protocolo_ouroboros/__init__.py`
  — Garantir que o pacote `mobile_cache` é importável a partir do
  CLI principal. Adicionar entry point se necessário.
- `~/Desenvolvimento/protocolo-ouroboros/CHANGELOG.md` — Entrada
  `[Unreleased]` em `### Added` documentando os geradores e os
  schemas dos caches (linkando ADR-0012).
- `~/Desenvolvimento/protocolo-ouroboros/docs/CONTEXT.md` — Adicionar
  seção curta "Caches Mobile" apontando para a ADR cruzada
  (ADR-0012 do Mobile) e listando os dois caches gerados.

## 3. APIs reutilizáveis

- `~/Desenvolvimento/protocolo-ouroboros/mappings/pessoas.yaml` —
  Schema de identidade (já estendido em MOB-bridge-1 com chaves
  `pessoa_a`/`pessoa_b`).
- `~/Desenvolvimento/protocolo-ouroboros/src/utils/pessoas.py` —
  Resolver de identidade introduzido em MOB-bridge-1. Os geradores
  consomem para garantir que o campo `autor` no JSON é sempre
  `"pessoa_a"`/`"pessoa_b"`/`"casal"`.
- `~/Desenvolvimento/protocolo-ouroboros/src/transform/` — Módulos
  existentes de transformação. Usar a função que normaliza datas
  ISO se já existe.
- `~/Desenvolvimento/protocolo-ouroboros/src/load/` — Leitor de XLSX
  consolidado já existente. Reaproveitar para `financas_cache.py`.
- `~/Desenvolvimento/protocolo-ouroboros/src/analysis/` — Funções
  de agregação por categoria. Reaproveitar para `top_categorias`.
- `~/Desenvolvimento/Protocolo-Mob-Ouroboros/docs/ADRs/0012-cache-mobile-readonly.md`
  — Schema canônico dos dois JSONs. Os campos, tipos e valores
  exemplo são contrato; mudanças de shape exigem ADR sucessor com
  `Status: Supersedes ADR-0012`.

## 4. Restrições

- **Schema cruzado é contrato:** os dois JSONs gerados por esta
  sprint são consumidos pelo Mobile. Toda mudança de shape exige
  ADR sucessor da ADR-0012 com bump em `schema_version`. Mobile
  valida com zod e cai em empty state explícito quando schema é
  incompatível.
- **Atomic write obrigatório:** escrever em `<arquivo>.tmp` e mover
  via `os.replace`. Garante que o Mobile, lendo o JSON via SAF
  enquanto o pipeline roda, jamais vê arquivo parcial. Crash no
  meio da escrita deixa `.tmp` e mantém versão anterior intacta.
- **Determinismo:** o gerador deve ser idempotente. Rodar duas
  vezes seguidas com mesmo Vault produz arquivos byte-a-byte
  iguais (exceto `gerado_em`). Útil para testes e diff.
- **Regra −1 (Anonimato):** zero referência a IA, zero nomes reais.
  O campo `autor` no JSON usa exclusivamente os identificadores
  genéricos `"pessoa_a"`, `"pessoa_b"`, `"casal"`. Nunca display
  name.
- Sem emojis em código, docs ou commits.
- Comentários e docstrings em código `.py` sem acento.
- Mensagens de commit em PT-BR sem acento.
- O `gerado_em` deve ser ISO 8601 com timezone (`-03:00` ou
  equivalente local). Formato: `YYYY-MM-DDTHH:MM:SS-03:00`.
- O `humor-heatmap.json` cobre exatos 90 dias retroativos a partir
  da data de execução. Dias sem registro **não** entram no array
  `celulas` (Mobile renderiza ausência como cor `bg-elev`).
- O `financas-cache.json` cobre semana ISO atual de `referencia`,
  com `gasto_semana_anterior` da semana ISO anterior. Sem
  transações naquela semana → `gasto_semana = 0` e
  `top_categorias = []`. Nunca lançar exceção por ausência de
  dados.
- Não tocar em UI, dashboard Streamlit ou outros consumidores
  internos. Esta sprint cria infraestrutura para o Mobile
  exclusivamente.
- Não regravar caches que já existem se nada mudou no Vault. O
  gerador deve detectar idempotência via comparação de payload e
  só escrever quando o JSON serializado difere do existente
  (ignorando `gerado_em`). Otimização opcional: implementar em
  uma sub-sprint se o tempo apertar; nesta primeira passada,
  sempre regravar é aceitável.

## 5. Procedimento sugerido

1. Verificar baseline:
   ```bash
   cd ~/Desenvolvimento/protocolo-ouroboros
   git status
   git log --oneline -3
   ./venv/bin/pytest tests/ -q --tb=line
   ```
   Confirmar que MOB-bridge-1 já está fechada (resolver
   `src/utils/pessoas.py` existe). Se não, parar e priorizar
   MOB-bridge-1.
2. Criar pacote `src/protocolo_ouroboros/mobile_cache/` com
   `__init__.py`. Definir `gerar_todos(vault_root: Path)` que
   chama os dois geradores em sequência e devolve a lista de paths
   gravados.
3. Implementar `mobile_cache/atomic.py`:
   ```python
   import json
   import os
   from pathlib import Path
   def write_json_atomic(path: Path, payload: dict) -> None:
       """Atomic JSON write. Tmp file + os.replace.
       Garante que leitor jamais ve arquivo parcial.
       """
       path.parent.mkdir(parents=True, exist_ok=True)
       tmp = path.with_suffix(path.suffix + '.tmp')
       data = json.dumps(payload, ensure_ascii=False, indent=2)
       tmp.write_text(data, encoding='utf-8')
       os.replace(tmp, path)
   ```
   Testar isoladamente em `tests/mobile_cache/test_atomic.py`.
4. Implementar `humor_heatmap.py`:
   - Função auxiliar `_listar_dailies(vault_root, periodo_dias)`
     que devolve lista de `Path` ordenada.
   - Função auxiliar `_parse_frontmatter(md_path)` que devolve
     dict com `data`, `autor`, `humor`, `energia`, `ansiedade`,
     `foco`. Pular silenciosamente se algum campo obrigatório
     ausente.
   - Função auxiliar `_calcular_estatisticas(celulas, pessoas)` que
     devolve dict por pessoa com `media_humor_30d`,
     `registros_30d`, `registros_total`. Considerar apenas dias
     com registro para a média.
   - `gerar_humor_heatmap` orquestra: lista dailies, parseia, monta
     `celulas`, calcula stats, monta payload conforme schema
     ADR-0012, chama `write_json_atomic`.
5. Implementar `financas_cache.py`:
   - Reaproveitar leitor de XLSX existente em `src/load/`. Anotar
     o path exato (provavelmente `src/load/xlsx_loader.py` ou
     similar).
   - Função auxiliar `_semana_iso_atual(ref: date) -> tuple[date, date]`
     que devolve `(segunda, domingo)` da semana ISO de `ref`.
   - Função auxiliar `_filtrar_semana(transacoes, inicio, fim) -> list`
     que devolve subconjunto filtrado.
   - Função auxiliar `_agregar_categorias(transacoes_semana) -> list`
     ordenado desc por valor, top 5, com percentual.
   - Função auxiliar `_delta_textual(gasto, media_12s) -> str` com
     heurística: dentro de ±15% da média = "dentro da média"; mais
     que 15% acima = "acima da média"; mais que 15% abaixo = "abaixo
     da média".
   - `gerar_financas_cache` orquestra e chama `write_json_atomic`.
6. Plugar no CLI principal. Editar `run.sh`:
   ```bash
   --full-cycle)
       # ...etapas existentes...
       python -m protocolo_ouroboros.mobile_cache
       ;;
   ```
   E adicionar `--mobile-cache` como flag standalone que dispara
   apenas o gerador.
7. Adicionar target `sync` no Makefile como alias.
8. Escrever os testes em `tests/mobile_cache/`. Cada arquivo de
   teste cobre o respectivo gerador. Fixtures em `conftest.py`
   criam Vault temporário com dailies controlados e XLSX sintético.
9. Rodar testes incrementalmente:
   ```bash
   ./venv/bin/pytest tests/mobile_cache/ -v
   ./venv/bin/pytest tests/ -q
   ```
   O total deve ser FAIL_BEFORE + 12-15 (depende de quantos cases
   foram escritos). Nenhum teste anterior pode regredir.
10. Smoke runtime-real com Vault real:
    ```bash
    cd ~/Desenvolvimento/protocolo-ouroboros
    make sync
    ls "$HOME/Protocolo-Ouroboros/.ouroboros/cache/"
    # espera: financas-cache.json humor-heatmap.json
    jq . "$HOME/Protocolo-Ouroboros/.ouroboros/cache/humor-heatmap.json" | head -40
    jq . "$HOME/Protocolo-Ouroboros/.ouroboros/cache/financas-cache.json" | head -40
    ```
    Conferir manualmente que o JSON tem `schema_version: 1` e a
    estrutura bate com a ADR-0012.
11. Validar atomic write em produção:
    ```bash
    # Rodar em loop e listar .tmp
    for i in $(seq 1 5); do
      make sync &
    done
    wait
    ls "$HOME/Protocolo-Ouroboros/.ouroboros/cache/"
    # nunca deve aparecer humor-heatmap.json.tmp ou financas-cache.json.tmp
    # depois do wait, mesmo sob concorrencia
    ```
12. Atualizar `CHANGELOG.md` com entrada `### Added` em
    `[Unreleased]`.
13. Commit:
    ```
    feat: mobile-cache geradores humor-heatmap e financas-cache
    ```

## 6. Verificação runtime-real

```bash
cd ~/Desenvolvimento/protocolo-ouroboros

# 1. Anonimato (Regra -1) no Python
./scripts/check_anonimato.sh

# 2. Lint completo
make lint

# 3. Testes (131 + 12-15 novos passando)
make test

# 4. Smoke aritmetico
make smoke

# 5. Anti-migue (gate de 9 checks)
make anti-migue

# 6. Pipeline completo + caches gerados
make sync

# 7. Caches presentes e validos
ls "$HOME/Protocolo-Ouroboros/.ouroboros/cache/"
# espera: financas-cache.json  humor-heatmap.json

jq -e '.schema_version == 1 and (.celulas | type) == "array"' \
   "$HOME/Protocolo-Ouroboros/.ouroboros/cache/humor-heatmap.json"
jq -e '.schema_version == 1 and (.top_categorias | type) == "array"' \
   "$HOME/Protocolo-Ouroboros/.ouroboros/cache/financas-cache.json"

# 8. Atomic write robusto (5 invocacoes simultaneas, nenhum .tmp residual)
for i in $(seq 1 5); do make sync & done; wait
ls "$HOME/Protocolo-Ouroboros/.ouroboros/cache/" | grep '\.tmp$' && \
  echo 'FAIL: tmp residual' || echo 'OK: sem tmp residual'

# 9. Idempotencia: rodar duas vezes seguidas, diff deve ser so o gerado_em
make sync
cp "$HOME/Protocolo-Ouroboros/.ouroboros/cache/humor-heatmap.json" /tmp/h1.json
make sync
diff <(jq 'del(.gerado_em)' /tmp/h1.json) \
     <(jq 'del(.gerado_em)' "$HOME/Protocolo-Ouroboros/.ouroboros/cache/humor-heatmap.json")
# espera: vazio (idempotente)
```

Todos exit 0. Se algum quebrar, parar e reportar com output literal.

## 7. Commit

```
feat: mobile-cache geradores humor-heatmap e financas-cache
```

## 8. Checkpoint visual

Não aplicável diretamente. Sprint backend de geração de cache, sem
UI. Mas o checkpoint visual do Mobile (Sprints M10 e M14) **depende**
desta sprint estar fechada. Documentar em ambas as specs Mobile que
elas só podem completar checkpoint visual com dados reais após
MOB-bridge-2.

## 9. Definição de Pronto

- [ ] Pacote `src/protocolo_ouroboros/mobile_cache/` exporta
      `gerar_todos`.
- [ ] `humor_heatmap.py` cobre 90 dias; estatísticas validadas em
      fixture pequeno.
- [ ] `financas_cache.py` cobre semana ISO atual + delta textual
      + top 5 categorias + 20 últimas transações.
- [ ] `atomic.py` garante atomic write via `os.replace`.
- [ ] `make sync` gera ambos os JSONs.
- [ ] `--mobile-cache` flag standalone funcional.
- [ ] `--no-mobile-cache` flag desativa quando aplicável.
- [ ] Caches presentes nos paths canônicos com `schema_version: 1`.
- [ ] Idempotência: rodar 2x produz JSON idêntico (exceto
      `gerado_em`).
- [ ] Atomic write robusto sob 5 invocações simultâneas.
- [ ] 12-15 testes novos passando; nenhum legado regrediu.

## 10. Decisões tomadas

- **XLSX loader em `src/load/`:** confirmar path exato no início;
  criar camada fina se não existir.
- **Semana ISO referência default:** corrente. Se
  `gasto_semana == 0`, fallback automático para semana anterior
  (decisão da §10 anterior).
- **Outliers da média 12 semanas:** ignorar semanas com 0 ou
  < 10% da mediana (férias, hiatos).
- **Geração em todas as rotas:** `--full-cycle`, `--inbox`,
  `--mes` invocam o gerador. Flag `--no-mobile-cache` desativa
  pontualmente.
- **Pasta cache criada pelo gerador:** `write_json_atomic` faz
  `path.parent.mkdir(parents=True, exist_ok=True)`. Mobile mostra
  empty state quando ausente.
- **Performance (escala real):** sprint cobre o caminho simples
  (sempre regravar). Cacheamento incremental via comparação de
  payload **entrega na MOB-bridge-2.1 sob demanda**, não nesta
  passada — entra como sub-sprint apenas se medirmos > 5s em
  produção. Não é "v2": é critério de evolução baseada em medição.

Sprint pronta para execução sem perguntas pendentes.
