---
id: MOB-spec-exercicios-gif-timer
titulo: Contrato JSON mappings/schema_exercicios.json para grupo + exercicios + gif + timer (consumido pelo app mobile)
status: backlog
concluida_em: null
prioridade: P2
data_criacao: 2026-05-12
fase: BRIDGE_MOBILE
depende_de: []
esforco_estimado_horas: 2
origem: Plano 2026-05-12 secao Fase B; brief do dono pediu app exibir grupo de exercicios, exercicio com gif de execucao, botao iniciar treino com timer. App implementa em outra sessao a partir deste contrato.  <!-- noqa: accent -->
mockup: novo-mockup/mockups/T-exercicios.html  <!-- noqa: accent -->
adr_associada: ADR-29 (proposta -- catalogo de exercicios canonico compartilhado app+dashboard)  <!-- noqa: accent -->
---

# Sprint MOB-spec-exercicios-gif-timer -- contrato JSON do catalogo de exercicios

## Contexto

Brief do dono: "Crio o grupo de exercicios. Crio cada exercicios com cada gif de execução. Aí eu tenho que ter um botão de Iniciar Treino. Seleciono o grupo de Exercicios sei lá B. Aí aparece um tipo de exericios por vez com timer".

Esta sprint não implementa o app. Cria o **contrato canônico** (schema JSON + ADR + 3 exemplos) para que a próxima sessão Claude Code que tocar o app mobile possa implementar isolada. ADR-29 sugerido.

## Objetivo

1. Criar `mappings/schema_exercicios.json` (JSON Schema Draft-2020-12) com:
   - **Grupo**: `id`, `nome` (ex: "Treino B"), `descricao`, `cor_hex` (token visual), `ordem`.
   - **Exercicio**: `id`, `grupo_id`, `nome`, `descricao`, `gif_path` (path relativo no vault), `series_default`, `reps_default`, `descanso_seg`, `tempo_execucao_seg`, `equipamento`, `musculo_principal` (enum), `dificuldade` (1-5).
   - **Sessão (instância de treino)**: `id`, `data_hora_inicio`, `data_hora_fim`, `grupo_id`, `exercicios_completados[]` com `{exercicio_id, series_feitas, reps_por_serie[], peso_kg, observacao}`.
2. Criar 3 exemplos canônicos em `mappings/exemplos_exercicios/`:
   - `grupo_a_peito_triceps.json`
   - `grupo_b_costas_biceps.json`
   - `grupo_c_pernas_ombros.json`
3. ADR-29 em `docs/adr/ADR-29-catalogo-exercicios-canonico.md`:
   - Por que JSON (vs YAML, vs SQLite): app mobile já consome JSON (`humor-heatmap.json` etc.).
   - Onde mora: `~/Protocolo-Ouroboros/catalogo/exercicios.json` (sincronizado via Syncthing).
   - Quem escreve: app mobile (criação/edição). Backend lê para popular página Bem-estar > Treinos do dashboard.
   - Gifs: pasta `~/Protocolo-Ouroboros/midia/gifs/<exercicio_id>.gif`.
4. Spec do app mobile: o que ele precisa implementar (botão "Iniciar Treino", seletor de grupo, tela um-exercício-por-vez com timer countdown, persistência de sessão). **Esta parte vira sprint própria no repositório do app**.

## Validação ANTES (grep -- padrão (k))

```bash
ls mappings/ | grep -i "exercicio\|treino\|workout"
ls ~/Protocolo-Ouroboros/catalogo/ 2>/dev/null
grep -rn "exercicios\|treino" ~/Desenvolvimento/Protocolo-Mob-Ouroboros/app/exercicios/ 2>/dev/null | head
ls docs/adr/ | grep -i "ADR-3"
```

Confirma: (a) sem schema canônico atual, (b) sem catálogo em vault, (c) app já tem pasta `app/exercicios/` (parcial), (d) ADR-29 não conflita com ADRs existentes (até ADR-25 declarado).

## Não-objetivos (padrão (t))

- **NÃO** implementar a UI do app mobile (outra sessão).
- **NÃO** criar gifs reais; só declarar onde eles vivem.
- **NÃO** implementar timer/cronômetro no dashboard backend (responsabilidade do app).
- **NÃO** persistir sessões no grafo SQLite ainda — primeiro estabilizar schema, depois sprint INFRA dedicada.
- **NÃO** depender de banco de dados de exercícios externo (mantém soberania local, ADR-07).

## Spec de implementação

### Schema `mappings/schema_exercicios.json`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Catalogo de exercicios -- protocolo-ouroboros",
  "type": "object",
  "required": ["schema_version", "gerado_em", "grupos", "exercicios"],
  "properties": {
    "schema_version": {"const": 1},
    "gerado_em": {"type": "string", "format": "date-time"},
    "grupos": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "nome", "ordem"],
        "properties": {
          "id": {"type": "string", "pattern": "^[a-z0-9_]+$"},
          "nome": {"type": "string"},
          "descricao": {"type": "string"},
          "cor_hex": {"type": "string", "pattern": "^#[0-9A-Fa-f]{6}$"},
          "ordem": {"type": "integer", "minimum": 1}
        }
      }
    },
    "exercicios": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "grupo_id", "nome", "musculo_principal"],
        "properties": {
          "id": {"type": "string", "pattern": "^[a-z0-9_]+$"},
          "grupo_id": {"type": "string"},
          "nome": {"type": "string"},
          "descricao": {"type": "string"},
          "gif_path": {"type": "string", "pattern": "^midia/gifs/.+\\.gif$"},
          "series_default": {"type": "integer", "minimum": 1, "maximum": 10},
          "reps_default": {"type": "integer", "minimum": 1, "maximum": 100},
          "descanso_seg": {"type": "integer", "minimum": 0},
          "tempo_execucao_seg": {"type": ["integer", "null"]},
          "equipamento": {"type": "string"},
          "musculo_principal": {
            "type": "string",
            "enum": ["peito", "costas", "ombro", "biceps", "triceps", "pernas_quadriceps", "pernas_posterior", "gluteo", "panturrilha", "core", "cardio", "mobilidade"]
          },
          "dificuldade": {"type": "integer", "minimum": 1, "maximum": 5}
        }
      }
    }
  }
}
```

### Exemplo `mappings/exemplos_exercicios/grupo_a_peito_triceps.json`

```json
{
  "schema_version": 1,
  "gerado_em": "2026-05-12T00:00:00",
  "grupos": [
    {"id": "grupo_a", "nome": "Treino A — Peito + Tríceps", "cor_hex": "#FF6B6B", "ordem": 1, "descricao": "Peito + tríceps + core"}
  ],
  "exercicios": [
    {"id": "supino_reto", "grupo_id": "grupo_a", "nome": "Supino reto", "gif_path": "midia/gifs/supino_reto.gif", "series_default": 4, "reps_default": 10, "descanso_seg": 90, "tempo_execucao_seg": null, "equipamento": "barra livre + banco", "musculo_principal": "peito", "dificuldade": 3},
    {"id": "supino_inclinado", "grupo_id": "grupo_a", "nome": "Supino inclinado halteres", "gif_path": "midia/gifs/supino_inclinado.gif", "series_default": 3, "reps_default": 12, "descanso_seg": 90, "equipamento": "halteres + banco inclinado", "musculo_principal": "peito", "dificuldade": 3},
    {"id": "triceps_corda", "grupo_id": "grupo_a", "nome": "Tríceps corda", "gif_path": "midia/gifs/triceps_corda.gif", "series_default": 3, "reps_default": 15, "descanso_seg": 60, "equipamento": "polia + corda", "musculo_principal": "triceps", "dificuldade": 2}
  ]
}
```

### ADR-29

```markdown
# ADR-29 — Catálogo de exercícios canônico compartilhado app+dashboard

## Status
Proposto, 2026-05-12.

## Contexto
Dono pediu app mobile com grupo > exercício > gif > "Iniciar Treino" + timer.
Dashboard backend precisa ler o mesmo catálogo para mostrar evolução em Bem-estar > Treinos.

## Decisão
- Catálogo em `~/Protocolo-Ouroboros/catalogo/exercicios.json` (JSON Schema Draft-2020-12).
- Gifs em `~/Protocolo-Ouroboros/midia/gifs/<id>.gif`.
- App mobile é a fonte editorial (cria, edita, deleta).
- Sessões persistidas em `~/Protocolo-Ouroboros/sessoes/<YYYY-MM>/<id_sessao>.json` (uma sessão = uma execução de grupo).
- Backend só lê; nunca escreve catálogo nem sessões.

## Consequências
- Soberania local mantida (ADR-07).
- Syncthing sincroniza via volume `~/Protocolo-Ouroboros/`.
- Migração para banco SQLite no futuro é possível (catálogo cresce devagar).
```

## Proof-of-work (padrão (u))

```bash
# 1. Validar schema
.venv/bin/python -c "
import jsonschema, json
schema = json.load(open('mappings/schema_exercicios.json'))
jsonschema.Draft202012Validator.check_schema(schema)
print('schema valido')
"

# 2. Validar exemplos
.venv/bin/python -c "
import jsonschema, json, glob
schema = json.load(open('mappings/schema_exercicios.json'))
for e in glob.glob('mappings/exemplos_exercicios/*.json'):
    jsonschema.validate(json.load(open(e)), schema)
    print(f'  OK: {e}')
"
# Esperado: 3 exemplos passam.

# 3. ADR-29 existe e valido
ls docs/adr/ADR-29-*.md

# 4. Gauntlet
make lint && make smoke
```

## Critério de aceitação (gate (z))

1. `mappings/schema_exercicios.json` Draft-2020-12 válido.
2. 3 exemplos em `mappings/exemplos_exercicios/` passam validação.
3. `docs/adr/ADR-29-catalogo-exercicios-canonico.md` redigida.
4. `tests/test_schema_exercicios.py` ≥ 6 testes (validação positiva/negativa).
5. Pytest baseline cresce ≥ +6.
6. Gauntlet verde.
7. App mobile pode começar implementação em outra sessão sem questões em aberto.

## Referência

- Auditoria C1 (app): `docs/auditorias/AUDITORIA_APP_MOBILE_2026-05-12.md`.
- Plano de origem: `~/.claude/plans/preciso-que-use-o-crispy-stroustrup.md` Fase B.

*"Contrato bem escrito poupa o ego do executor; nada do tipo 'imagino que ele entenda'." — princípio MOB-spec-exercicios-gif-timer*
