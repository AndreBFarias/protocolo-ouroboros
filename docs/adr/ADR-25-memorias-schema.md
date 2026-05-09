# ADR-25 — Schema canônico do cache `memorias.json` (cápsulas multimídia)

- **Status:** aceita
- **Data:** 2026-05-08
- **Sprint:** INFRA-MEMORIAS-SCHEMA
- **Sucessor de:** —
- **Cruzamento:** roadmap golden-zebra do `Protocolo-Mob-Ouroboros`
  (sprints I-FOTO / I-AUDIO / I-VIDEO marcadas `[todo]`)

## Contexto

A página `be_memorias` (cluster Bem-estar / aba Memórias), entregue
pela sprint UX-V-2.11-FIX, renderiza um grid de cápsulas multimídia
conforme o mockup `novo-mockup/mockups/23-memorias.html`. O grid
consome `vault/.ouroboros/cache/memorias.json`, mas o contrato JSON
do cache não estava formalizado: o leitor (`be_memorias.py`)
infere campos pelo nome (`tipo`, `titulo`, `tags`, `vinculo`) e
cai em skeleton quando o JSON está ausente, enquanto o gravador
(app Mobile, repositório companion) ainda não decidiu o formato.

Sem schema canônico, cada lado inventaria o seu próprio
contrato e teríamos divergência silenciosa: o mob gravando
`tipo: "audio_curto"`, o dashboard esperando `tipo: "audio"`, e
nenhum CI capaz de detectar a discrepância antes do usuário ver
a tela quebrada.

## Decisão

**O cache `vault/.ouroboros/cache/memorias.json` segue o JSON Schema
versionado em `mappings/schema_memorias.json` (`$id:
ouroboros/schemas/memorias/v1`).**

Estrutura canônica:

```json
{
  "schema_version": 1,
  "vault_id": "<uuid v4 do vault>",
  "gerado_em": "2026-05-08T20:30:00-03:00",
  "items": [
    {
      "id": "<uuid v4 da cápsula>",
      "tipo": "foto|audio|texto|video",
      "titulo": "Praia ao amanhecer",
      "data": "2026-04-22",
      "local": "Itacaré, BA",
      "duracao_seg": null,
      "tags": ["viagem", "casal"],
      "evento_vinculado": "<uuid|null>",
      "diario_vinculado": "<uuid|null>",
      "preview_path": ".ouroboros/preview/<id>.jpg",
      "media_path": "memorias/2026-04-22/praia.heic",
      "para_abrir": false
    }
  ]
}
```

Regras canônicas:

1. **`tipo` sem acento** no JSON (`audio`, `video`). A UI
   traduz para `áudio` / `vídeo` ao exibir (compatível com o
   tradutor já existente em `be_memorias._LABEL_TIPO`).
2. **`preview_path` e `media_path` relativos ao vault** — nunca
   absolutos, nunca `file://`. O dashboard resolve via
   `vault_root / path`.
3. **`para_abrir = true`** marca cápsulas que aguardam contexto
   humano (sem `evento_vinculado` nem `diario_vinculado`). É o
   KPI exibido como "cápsulas para abrir" na UI.
4. **`gerado_em` em ISO 8601 com timezone explícito** (canônico
   `-03:00`), espelhando o padrão de `humor_heatmap.json`.
5. **`schema_version` é inteiro `1`** nesta versão. Bumps
   exigem ADR sucessora.

### Componentes desta decisão

| Arquivo | Papel |
|---|---|
| `mappings/schema_memorias.json` | JSON Schema oficial (Draft 2020-12) |
| `src/mobile_cache/memorias.py` | Leitor + validador (`carregar` / `validar`) |
| `tests/fixtures/vault_sintetico/.ouroboros/cache/memorias.json` | Fixture sintética com 12 cápsulas (5 fotos / 2 áudios / 3 textos / 2 vídeos) |
| `src/dashboard/paginas/be_memorias.py` | Consumidor real (substitui leitura ad-hoc) |

### O que NÃO está nesta decisão

- Geração do cache: responsabilidade exclusiva do app Mobile.
  O backend Python neste repo apenas **lê e valida**.
- Schema de mídia binária: `preview_path` / `media_path` apontam
  para arquivos no vault, mas o backend não decodifica conteúdo.
- Filtros funcionais por chip (todos / foto / voz / texto /
  video): mockup-canônico declarado, sprint futura.

## Alternativas consideradas

1. **Schema embutido no `be_memorias.py`** — rejeitada: cria
   acoplamento UI ↔ contrato de dados; nenhuma validação CI.
2. **Reaproveitar schema de `eventos.json`** — rejeitada: eventos
   têm campos próprios (participantes, lugar como objeto), e
   cápsulas são primariamente mídia anexada.
3. **YAML em vez de JSON Schema** — rejeitada: o cache é JSON
   nativo; manter schema na mesma linguagem evita conversão.

## Consequências

### Positivas

- Mob e dashboard convergem para o mesmo contrato versionado.
- Leitor `mobile_cache.memorias.carregar()` falha alto e
  cedo (não silencioso) quando o JSON viola o schema.
- Fixture sintética permite teste de integração sem mob real.
- ADR cruzada com sprints `I-FOTO` / `I-AUDIO` / `I-VIDEO` no
  repo mobile congela a parte do contrato do nosso lado.

### Negativas / riscos

- Bump de schema requer ADR + atualização coordenada dos dois
  repos. Mitigação: `schema_version` permite leitor tolerar
  versões antigas (rejeitar com mensagem clara).
- `tipo` sem acento no JSON quebra eventual mob legado que
  gravasse `audio_voz`. Mitigação: nenhum mob produtivo
  ainda grava memórias (sprint mob `[todo]`).

## Referências

- Sprint `INFRA-MEMORIAS-SCHEMA` em
  `docs/sprints/concluidos/sprint_INFRA_memorias_schema.md`.
- Mockup canônico: `novo-mockup/mockups/23-memorias.html`.
- Inventário gerador da sprint:
  `docs/auditorias/INVENTARIO_REAL_VS_MOCKUP_2026-05-08.md`.
- Padrão de irmão: `src/mobile_cache/humor_heatmap.py`
  (estrutura de docstring + constante de versão + módulo de
  cache atômico).

---

*"Schema é contrato; sem ele cada lado inventa o seu."* — princípio INFRA-MEMORIAS-SCHEMA
