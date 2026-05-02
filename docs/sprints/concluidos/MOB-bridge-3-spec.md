---
concluida_em: 2026-05-01
escopo_refinado_por: pacote interno em src/marcos_auto/ (coerência com src/mobile_cache/), dedup via sha256(tipo|data|descricao)[:12] simétrico com M11 do Mobile, plug em mobile_cache.gerar_todos antes dos caches
entrega_real: src/marcos_auto/ (5 módulos: __init__, dedup, parser, escrita, heuristicas) + tests/marcos_auto/ (32 testes), 2 marcos gerados em runtime real (tres_treinos_em_sete_dias e primeira_vitoria_da_semana), idempotência confirmada
commits: ef20366
seguimento: nenhum (Vault tem volume baixo de dailies/diario/eventos -- 3 das 5 heurísticas não dispararam mas a infraestrutura está pronta para quando volume crescer)
---

# Sprint MOB-bridge-3 — Marcos Auto-Gerados pelo Backend Python

```
REPO ALVO:  ~/Desenvolvimento/protocolo-ouroboros/
DEPENDE:    MOB-bridge-1 (resolver pessoa_a/b ativo) +
            MOB-bridge-2 (atomic write helper reusável)
BLOQUEIA:   M11 (consome marcos auto-gerados via Vault sincronizado;
            tem fallback heurístico no client se backend não rodar)
ESTIMATIVA: 2-3h
```

> Esta spec descreve trabalho a ser executado em
> `~/Desenvolvimento/protocolo-ouroboros/`. O arquivo vive aqui no
> Mobile como prompt direto para a próxima sessão que abrir o
> backend. Ao chegar o momento, copiar para
> `docs/sprints/MOB-bridge-3-spec.md` no repo backend ou ler
> daqui mesmo.

## 1. Objetivo

Gerar **marcos automáticos** em `~/Protocolo-Ouroboros/marcos/` a
partir de heurísticas que correm sobre `treinos/`,
`daily/` e `inbox/mente/diario/`. Ex: 3 treinos numa semana,
retorno após hiato de 5+ dias, 7 dias consecutivos com humor
registrado, 30 dias sem trigger, etc. Cada marco é idempotente via
hash do conteúdo (não duplica) e cooperativo com o client (M11
implementa heurística simétrica para garantir cobertura offline).

## 2. Entregáveis

### Arquivos novos (no repo backend)

- `~/Desenvolvimento/protocolo-ouroboros/src/protocolo_ouroboros/marcos_auto/__init__.py`
  — Pacote. Exporta `gerar_marcos_auto(vault_root)` que dispara
  todas as heurísticas em sequência.
- `~/Desenvolvimento/protocolo-ouroboros/src/protocolo_ouroboros/marcos_auto/heuristicas.py`
  — Cada heurística é função pura
  `(eventos: list[dict]) -> list[Marco]`:
  - `tres_treinos_em_sete_dias`: rolling window de 7 dias.
    Detecta primeira ocorrência por pessoa.
  - `retorno_apos_hiato`: gap >= 5 dias entre treinos consecutivos.
  - `sete_dias_humor`: 7 dias consecutivos com `daily/` registrado.
  - `trinta_dias_sem_trigger`: 30 dias consecutivos sem
    `diario_emocional.modo == 'trigger'`.
  - `primeira_vitoria_da_semana`: primeira ocorrência de
    `evento.modo == 'positivo'` ou `diario.modo == 'vitoria'` na
    semana ISO.
- `~/Desenvolvimento/protocolo-ouroboros/src/protocolo_ouroboros/marcos_auto/dedup.py`
  — `hash_marco(meta) -> str` que combina `tipo`, `data`,
  `descricao` em SHA-256 truncado para 12 chars. Usado como
  filename: `<data>-auto-<hash>.md`. Mesmo hash → mesma file →
  idempotente.
- `~/Desenvolvimento/protocolo-ouroboros/tests/marcos_auto/test_heuristicas.py`
  — Testes determinísticos por heurística.
- `~/Desenvolvimento/protocolo-ouroboros/tests/marcos_auto/test_dedup.py`
  — Hash estável; idempotência sob re-execução.
- `~/Desenvolvimento/protocolo-ouroboros/tests/marcos_auto/conftest.py`
  — Fixtures: Vault temporário com 14 dias de dailies + 5 treinos.

### Arquivos modificados (no repo backend)

- `~/Desenvolvimento/protocolo-ouroboros/src/protocolo_ouroboros/mobile_cache/__init__.py`
  — `gerar_todos(vault_root)` chama
  `marcos_auto.gerar_marcos_auto(vault_root)` antes dos caches
  (caches ignoram marcos por design; só executar para escrita
  cumulativa).
- `~/Desenvolvimento/protocolo-ouroboros/run.sh` — `--full-cycle`
  já invoca `gerar_todos`; nada a alterar aqui.
- `~/Desenvolvimento/protocolo-ouroboros/CHANGELOG.md` — entrada
  `[Unreleased]` em `### Added`.

## 3. APIs reutilizáveis

- `src/utils/pessoas.py` (MOB-bridge-1) — resolver de pessoa.
- `src/protocolo_ouroboros/mobile_cache/atomic.py` (MOB-bridge-2)
  — `write_json_atomic` reaproveitado para gravar `.md` de marco
  via wrapper que serializa frontmatter YAML.

## 4. Restrições

- **Schema do marco** segue `MarcoSchema` Mobile:
  ```yaml
  ---
  tipo: marco
  data: <ISO 8601>
  autor: <pessoa_a | pessoa_b | casal>
  descricao: <texto sem nome real>
  tags: [auto, treino|humor|emocional]
  auto: true       # flag que distingue de marcos manuais
  origem: backend  # backend | client
  hash: <12 chars>
  ---
  ```
- **Idempotência via hash:** mesma combinação `tipo + data + descricao`
  produz mesmo hash; arquivo já existente não é regravado.
- **Sem palavras motivacionais** (ADR-0005). Descrições secas:
  - `"Tres treinos nesta semana."`
  - `"Voltou apos N dias parados."`
  - `"Sete dias acompanhando."`
  - `"Trinta dias sem registrar trigger."`
  - `"Primeira vitoria desta semana."`
- Comentários e docstrings sem acento.
- Mensagens de commit sem acento.

## 5. Procedimento sugerido

1. Verificar baseline: testes passando, `make sync` rodando OK
   após MOB-bridge-2.
2. Implementar `marcos_auto/dedup.py` com `hash_marco`. Testes
   pure-function.
3. Implementar `heuristicas.py` com 5 funções. Cada uma recebe
   lista pré-parseada de eventos e devolve `list[Marco]`.
4. Implementar `marcos_auto/__init__.py` com `gerar_marcos_auto`
   que:
   - Lista `treinos/`, `daily/`, `inbox/mente/diario/` no
     vault_root.
   - Parseia frontmatter YAML.
   - Aplica cada heurística.
   - Para cada marco gerado: calcula hash, verifica se arquivo
     já existe em `marcos/<data>-auto-<hash>.md`, escreve via
     `write_md_atomic` (wrapper sobre o atomic da MOB-bridge-2)
     se não existe.
5. Plugar em `mobile_cache/__init__.py`.
6. Escrever testes em `tests/marcos_auto/`.
7. Smoke runtime: rodar `make sync` em Vault real, conferir que
   `marcos/` ganhou novos `.md` esperados.
8. Validação cruzada: rodar 2x consecutivos; segunda execução
   não cria nada novo (idempotência).
9. Commit.

## 6. Verificação runtime-real

```bash
cd ~/Desenvolvimento/protocolo-ouroboros

./scripts/check_anonimato.sh
make lint
make test
make smoke

# Sanity dos marcos
make sync
ls "$HOME/Protocolo-Ouroboros/marcos/" | grep -- '-auto-'
# espera: pelo menos 1 arquivo se Vault tem 7+ dias de dailies

# Idempotencia
COUNT_BEFORE=$(ls "$HOME/Protocolo-Ouroboros/marcos/" | wc -l)
make sync
COUNT_AFTER=$(ls "$HOME/Protocolo-Ouroboros/marcos/" | wc -l)
[[ "$COUNT_BEFORE" == "$COUNT_AFTER" ]] && echo OK || echo FAIL
```

Todos exit 0.

## 7. Commit

```
feat: marcos-auto heuristicas backend e dedup por hash
```

## 8. Checkpoint visual

Não aplicável — backend.

## 9. Definição de Pronto

- [ ] 5 heurísticas implementadas e testadas.
- [ ] Hash dedup funcional (idempotente sob re-execução).
- [ ] Plugado em `mobile_cache.gerar_todos`.
- [ ] `make sync` em Vault real produz marcos esperados.
- [ ] Marcos cooperam com client (M11 dedup também via hash).
- [ ] Testes 12+ passando.

## 10. Decisões tomadas

- **5 heurísticas iniciais:** treinos (3 em 7d), retorno após
  hiato, humor consecutivo (7d), trinta dias sem trigger,
  primeira vitória da semana. Lista expansível via PR sem
  bloqueio.
- **Hash de 12 chars SHA-256:** colisão astronomicamente baixa;
  filename legível.
- **Cooperação client/backend:** Mobile (M11) implementa as
  mesmas heurísticas no client com mesmo algoritmo de hash.
  Ambos podem rodar; arquivos nunca duplicam.
- **Marcos secos sem motivacional:** ADR-0005 vale aqui também.

Sprint pronta para execução sem perguntas pendentes.
