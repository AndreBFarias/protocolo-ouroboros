---
id: INFRA-MEMORIAS-SCHEMA
titulo: Definir schema canônico vault/.ouroboros/cache/memorias.json (cápsulas multimídia)
status: backlog
prioridade: media
data_criacao: 2026-05-08
fase: CONCLUSAO_REAL
depende_de: []
esforco_estimado_horas: 3
origem: docs/auditorias/INVENTARIO_REAL_VS_MOCKUP_2026-05-08.md (be_memorias skeleton com schema em aberto)
mockup: novo-mockup/mockups/23-memorias.html
---

# Sprint INFRA-MEMORIAS-SCHEMA — schema canônico das cápsulas

## Contexto

Página `be_memorias` (UX-V-2.11-FIX) renderiza grid de cápsulas multimídia conforme mockup `23-memorias.html`, mas o schema JSON do cache `vault/.ouroboros/cache/memorias.json` ainda está em aberto. Mob (`Protocolo-Mob-Ouroboros`) precisa de schema canônico para começar a gravar (I-FOTO/I-AUDIO/I-VIDEO no roadmap golden-zebra estão `[todo]`).

## Objetivo

1. Definir schema v1 em `mappings/schema_memorias.json` (JSON Schema oficial).
2. Documentar em `docs/adr/ADR-XX-memorias-schema.md` (próximo número livre).
3. Validar leitura no mob_cache: criar `src/mobile_cache/memorias.py` espelhando padrão de `humor_heatmap.py`.
4. Fixture sintética em `tests/fixtures/vault_sintetico/.ouroboros/cache/memorias.json` com 12 cápsulas (5 fotos / 2 áudios / 3 textos / 2 vídeos).
5. Atualizar `be_memorias.py` para popular grid real quando JSON existe.

## Schema proposto

```json
{
  "$schema": "ouroboros/schemas/memorias/v1",
  "vault_id": "uuid",
  "gerado_em": "ISO",
  "items": [
    {
      "id": "uuid",
      "tipo": "foto|audio|texto|video",
      "titulo": "string",
      "data": "YYYY-MM-DD",
      "local": "string|null",
      "duracao_seg": "int|null",
      "tags": ["string", ...],
      "evento_vinculado": "uuid|null",
      "diario_vinculado": "uuid|null",
      "preview_path": "string (relativo ao vault)",
      "media_path": "string (relativo ao vault)",
      "para_abrir": "bool"
    }
  ]
}
```

## Validação ANTES (grep)

```bash
ls vault/.ouroboros/cache/memorias.json 2>&1
grep -n "memorias\|capsula" src/mobile_cache/ -r | head -10
ls mappings/schema_*.json 2>&1 | head
```

## Não-objetivos

- NÃO implementar gravação no mob (responsabilidade do Protocolo-Mob).
- NÃO mexer no layout `be_memorias.py` (UX-V-2.11-FIX entregou).

## Proof-of-work

```bash
test -f mappings/schema_memorias.json
test -f src/mobile_cache/memorias.py
test -f tests/fixtures/vault_sintetico/.ouroboros/cache/memorias.json
make lint && make smoke
.venv/bin/pytest tests/ -k memorias -q
```

Validação visual: rodar dashboard com fixture sintética; cluster=Bem-estar&tab=Memórias deve mostrar grid 7+5 com cápsulas reais (não skeleton).

## Critério de aceitação

1. Schema JSON v1 documentado em ADR.
2. Validador `validate_memorias.py` (jsonschema).
3. Fixture sintética com 12 itens.
4. `be_memorias.py` lê e renderiza com gradientes corretos por tipo.
5. Lint + smoke + pytest baseline.

## Referência

- Inventário: `docs/auditorias/INVENTARIO_REAL_VS_MOCKUP_2026-05-08.md`.
- Mockup: `23-memorias.html`.
- Sprint dependente no mob: I-FOTO + I-AUDIO + I-VIDEO (golden-zebra).

*"Schema é contrato; sem ele cada lado inventa o seu." — princípio INFRA-MEMORIAS-SCHEMA*
