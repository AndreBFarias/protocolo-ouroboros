# ADR-29 — Catálogo de exercícios canônico compartilhado app+dashboard

## Status

Proposto, 2026-05-12.

## Contexto

O dono solicitou que o app mobile (Protocolo-Mob-Ouroboros) exiba grupos de treino, cada exercício com seu gif de execução, e ofereça um botão "Iniciar Treino" que mostra um exercício por vez com timer de execução/descanso. O dashboard Streamlit (página Bem-estar > Treinos) precisa ler o mesmo catálogo para apresentar evolução, histórico de sessões e indicadores agregados.

Sem um contrato canônico, app e dashboard divergem em formato, nomes de campos e enums (exatamente o que ocorreu com cápsulas de memória antes da ADR-25).

Restrições:

- ADR-07: soberania local; sem dependência de banco externo.
- ADR-25: precedente recente de schema JSON compartilhado app→dashboard com leitura somente.
- App mobile já consome JSON em outros caches (`humor-heatmap.json`, `eventos.json`, `memorias.json`).
- Catálogo cresce devagar (dezenas, não milhões, de registros) — SQLite seria overkill.

## Decisão

1. **Formato**: JSON Schema Draft-2020-12 em `mappings/schema_exercicios.json` (no repositório do dashboard, fonte da verdade do contrato).
2. **Localização do catálogo runtime**: `~/Protocolo-Ouroboros/catalogo/exercicios.json`. Sincronizado entre dispositivos via Syncthing (mesmo volume usado pelos outros caches).
3. **Mídia**: gifs em `~/Protocolo-Ouroboros/midia/gifs/<exercicio_id>.gif`. O campo `gif_path` é relativo a `~/Protocolo-Ouroboros/`.
4. **Sessões (instâncias de treino)**: persistidas em `~/Protocolo-Ouroboros/sessoes/<YYYY-MM>/<id_sessao>.json` quando volume crescer; opcionalmente embutidas em `exercicios.json` na fase inicial via campo `sessoes[]` declarado no schema.
5. **Propriedade editorial**: o app mobile é o único autor de catálogo e sessões (cria, edita, deleta).
6. **Dashboard backend**: leitura somente; nunca escreve catálogo nem sessões.
7. **Validação**: dashboard valida o JSON contra o schema antes de consumir; se inválido, falha rápido com mensagem clara (mesmo padrão de `schema_memorias.json`).
8. **Schema versionado**: campo `schema_version` (const 1 hoje); bumpar quando contrato mudar.

## Estrutura mínima do catálogo

```json
{
  "schema_version": 1,
  "gerado_em": "2026-05-12T08:00:00",
  "grupos": [
    {"id": "grupo_a", "nome": "Treino A — Peito + Tríceps", "cor_hex": "#FF6B6B", "ordem": 1}
  ],
  "exercicios": [
    {"id": "supino_reto", "grupo_id": "grupo_a", "nome": "Supino reto", "musculo_principal": "peito", "gif_path": "midia/gifs/supino_reto.gif", "series_default": 4, "reps_default": 10, "descanso_seg": 90, "dificuldade": 3}
  ]
}
```

Três exemplos canônicos vivem em `mappings/exemplos_exercicios/`:

- `grupo_a_peito_triceps.json`
- `grupo_b_costas_biceps.json`
- `grupo_c_pernas_ombros.json`

## Consequências

### Positivas

- Soberania local mantida (ADR-07): nada sai do volume Syncthing.
- Contrato explícito impede divergência app↔dashboard (mesma lição da ADR-25).
- Migração futura para SQLite continua possível (chaves estáveis em `id` e `grupo_id`).
- Validação automática no dashboard via `jsonschema.validate()` (mesmo helper já usado para cápsulas).

### Negativas

- Cresce um schema a manter; bumps de `schema_version` exigem coordenação app↔dashboard (idem ADR-25).
- Sem transações: edições concorrentes do mesmo arquivo dependem do Syncthing (na prática há apenas um editor, o dono, então é aceitável).

### Riscos mitigados

- Enum fixo de `musculo_principal` (12 valores) evita explosão de strings livres.
- Pattern `^[a-z0-9_]+$` em `id` e `grupo_id` evita colisões case-sensitive entre filesystems Linux/macOS.
- Campo `tempo_execucao_seg` permite exercícios isométricos (prancha) sem confundir com `reps_default`.

## Não-decisões (escopo de sprints futuras)

- UI mobile completa (botão "Iniciar Treino", seletor, timer): sprint própria no repositório do app.
- Página dashboard Bem-estar > Treinos: sprint UI dedicada após existir catálogo populado.
- Persistência de sessões em SQLite (grafo): sprint INFRA quando volume justificar.
- Ingestão de catálogos externos (Strong, Hevy): fora de escopo permanente — soberania local.

## Referências

- Auditoria C1 (app): `docs/auditorias/AUDITORIA_APP_MOBILE_2026-05-12.md`.
- ADR-07: soberania local de dados.
- ADR-25: schema canônico de cápsulas de memória (mesmo padrão).
- Sprint MOB-spec-exercicios-gif-timer: `docs/sprints/backlog/sprint_MOB_spec_exercicios_gif_timer.md`.

*"Contrato bem escrito poupa o ego do executor; nada do tipo 'imagino que ele entenda'."*
