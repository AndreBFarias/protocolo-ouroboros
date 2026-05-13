# ADR-25-extensao — Formato `.capsula.md` canônico para Galeria de Memórias e Eventos

- **Status:** aceita
- **Data:** 2026-05-12
- **Sprint:** MOB-spec-galeria-memorias
- **Extende:** ADR-25 — Schema canônico do cache `memorias.json`
- **Cruzamento:** Brief do dono 2026-05-12 (galeria mobile read-only);
  auditoria C1 (`docs/auditorias/AUDITORIA_APP_MOBILE_2026-05-12.md`).

## Contexto

ADR-25 formalizou o **cache JSON** `vault/.ouroboros/cache/memorias.json`
gravado pelo app Mobile e lido pelo dashboard. O brief do dono
introduziu requisito novo: **galeria de Memórias/Eventos compartilhada
e read+edit** — cada item precisa ser visualizado e editável fora do
fluxo de captura.

O cache JSON resolve **leitura agregada** (KPIs, grid), mas não cobre
o **estado fonte editável**: cada memória/evento individual com texto
livre em markdown + binários (foto, áudio, vídeo) associados. O cache
é derivado; a fonte canônica precisa ser arquivo humano-editável,
similar a Recap.

Sem formato canônico de fonte, app e dashboard divergem: app grava em
formato A, dashboard espera formato B, e o casal perde memórias por
inconsistência silenciosa.

## Decisão

**Cada memória ou evento é um arquivo `.capsula.md` com frontmatter YAML
canônico (validado em `mappings/schema_memorias.json#/$defs/capsula_md`)
e corpo livre em markdown.**

Convenções:

1. **Nome do arquivo:** `<YYYY-MM-DD>-<HHmmss>-<slug>.capsula.md`.
2. **Pasta:** `<vault>/inbox/memorias/<YYYY>/<MM>/`.
3. **Binários companion:** mesmo basename do `.md`, sufixo binário
   (`.jpg`, `.mp4`, `.m4a`, …), na mesma pasta. Listados no
   frontmatter como `companions[]`.
4. **Frontmatter obrigatório:** `_schema_version: 1`, `tipo`
   (`memoria` ou `evento`), `data`, `titulo`, `slug`.
5. **Corpo:** markdown livre, multilinhas, pode referenciar
   companions pelo nome do arquivo.

### Frontmatter canônico

```yaml
---
_schema_version: 1
tipo: memoria              # ou "evento"
data: 2026-05-12
hora: "10:00:00"           # opcional
titulo: Aniversário da Vitória
slug: aniversario-vitoria
area: outros               # opcional
subtipo: memoria           # opcional
pessoas: [andre, vitoria]  # opcional
local:                     # opcional (objeto ou string legada)
  nome: Casa
  cidade: Maceió
  coordenadas: [-9.6498, -35.7089]
tags: [aniversario, casal] # opcional
emocao_principal: alegria  # opcional
intensidade: 9             # 0-10, opcional
companions:                # opcional, lista de mídias associadas
  - tipo: foto
    arquivo: 2026-05-12-100000-aniversario-vitoria-1.jpg
    legenda: bolo no balcão
  - tipo: audio
    arquivo: 2026-05-12-100000-parabens.m4a
    legenda: parabéns cantado
duracao_estimada_min: null
evento_vinculado_uuid: null
---

# Aniversário da Vitória

Corpo livre em markdown...
```

### Companion

Cada item de `companions[]`:

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `tipo` | string enum (foto/audio/texto/video) | sim | Categoria da mídia. Sem acento. |
| `arquivo` | string | sim | Basename relativo à mesma pasta do `.capsula.md`. Sem `/`, sem caminho absoluto. |
| `legenda` | string ou null | não | Legenda livre. |

### Componentes

| Arquivo | Papel |
|---|---|
| `mappings/schema_memorias.json` | Schema JSON com `$defs.capsula_md` e `$defs.companion` (estendido nesta sprint) |
| `src/dashboard/paginas/be_memorias.py::carregar_capsulas` | Leitor canônico do formato. Valida frontmatter contra schema. |
| `tests/fixtures/capsulas/*.capsula.md` | Fixtures de referência (aniversário e show). |
| `tests/test_capsula_md.py` | Suite de testes (parse, validação, ordenação, companions). |

### O que NÃO está nesta decisão

- **Edição no app Mobile:** sprint separada do lado mobile (`MOB-galeria-edit-*`).
- **Sincronização Syncthing:** fora do escopo; vault já sincroniza.
- **Filtros funcionais por chip:** mockup-canônico, sprint UX futura.
- **Cache JSON:** continua sendo derivado pelo app Mobile a partir das
  cápsulas (ADR-25 base permanece válido).

## Alternativas consideradas

1. **Tudo em JSON único:** rejeitado — corpo livre em markdown é
   essencial para narrativa do casal; YAML+markdown casa com o
   modelo de Recap já adotado em outras áreas.
2. **Frontmatter TOML:** rejeitado — YAML já é o padrão do repo
   (mockups, ADRs com frontmatter, specs de sprint).
3. **Pasta por cápsula (`memoria/<id>/index.md` + binários soltos):**
   rejeitado — explosão de pastas; nome canônico com slug já
   identifica unicamente.

## Consequências

### Positivas

- Casal pode editar memórias em qualquer editor de markdown.
- Schema único validado nos dois lados (mobile read-only por enquanto,
  dashboard read + futuro edit).
- Binários companion ficam ao lado do `.md` — backup é direto.
- Cache JSON permanece derivado; rebuild é determinístico.

### Negativas / riscos

- Parser YAML adiciona dependência (`yaml.safe_load`), mas já está
  em uso no projeto (specs, conftest).
- Validação por schema em runtime pode ficar lenta para galeria
  grande (>1000 cápsulas). Mitigação: cachear validação por
  mtime do arquivo (sprint futura, se necessário).

## Referências

- ADR-25 base: `docs/adr/ADR-25-memorias-schema.md`.
- Mockup canônico: `novo-mockup/mockups/M-memorias.html`,
  `novo-mockup/mockups/23-memorias.html`.
- Auditoria mobile: `docs/auditorias/AUDITORIA_APP_MOBILE_2026-05-12.md`.
- Spec da sprint: `docs/sprints/backlog/sprint_MOB_spec_galeria_memorias.md`.

---

*"A memória vive no arquivo de texto; o cache só conta quantas tem."* — princípio MOB-spec-galeria-memorias
