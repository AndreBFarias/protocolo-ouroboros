---
titulo: Auditoria estrutural do vault Ouroboros
data: 2026-05-13
auditor: scripts/audit_vault_md.py
escopo: /home/andrefarias/Protocolo-Ouroboros/inbox/
---

# Auditoria estrutural

## Resumo
- Total auditado: 1
- Conformes: 0
- Violações: 3
- Companions (.md): 1
- Binários: 0

## Categoria 1 -- Estrutura
- `inbox/mente/diario/2026-04-29-1430-vit.md` -- área 'mente' fora do mapping canônico ['casa', 'financeiro', 'outros', 'saude']

## Categoria 2 -- Filename
- `inbox/mente/diario/2026-04-29-1430-vit.md` -- filename '2026-04-29-1430-vit.md' fora do regex YYYY-MM-DD-HHmmss[-slug].<ext>

## Categoria 3 -- Frontmatter
- `inbox/mente/diario/2026-04-29-1430-vit.md` -- campos obrigatórios ausentes: ['_schema_version', 'area', 'subtipo', 'arquivo', 'revisar']

## Categoria 4 -- Companion
- nenhuma violação

## Recomendações
- (1 caso) Mover arquivos para `inbox/<area>/<subtipo>/` conforme mapping canônico.
- (1 caso) Renomear binários para o regex `YYYY-MM-DD-HHmmss[-slug].<ext>`.
- (1 caso) Reescrever frontmatter dos .md companions com `_schema_version=1` + campos obrigatórios.
- (sem mais categorias com violação)
- (sem mais categorias com violação)
