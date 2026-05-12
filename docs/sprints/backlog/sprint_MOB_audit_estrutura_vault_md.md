---
id: MOB-audit-estrutura-vault-md
titulo: Script audit_vault_md.py valida estrutura inbox/<area>/<subtipo>/, filename regex, frontmatter _schema_version=1 e zero binarios soltos
status: backlog
concluida_em: null
prioridade: P0
data_criacao: 2026-05-12
fase: BRIDGE_MOBILE
depende_de: []
esforco_estimado_horas: 3
origem: Plano 2026-05-12 secao Fase B; auditor C1 confirmou frontmatter _schema_version=1 obrigatorio (Onda Q12); sem auditoria estrutural, drift entre app e backend e silencioso.  <!-- noqa: accent -->
---

# Sprint MOB-audit-estrutura-vault-md -- auditoria estrutural do vault compartilhado

## Contexto

O app mobile (Protocolo-Mob-Ouroboros, Onda Q em 2026-05-12) sempre carimba frontmatter `_schema_version: 1` nos `.md` exportados (achado da auditoria C1 2026-05-12). Schema validado via Zod por tipo. Pasta vault: `~/Protocolo-Ouroboros/`. Estrutura: `inbox/{financeiro,saude,casa,outros}/{subtipo}/YYYY-MM-DD-HHmmss[-slug].<ext>` + companion `.md`.

Sem auditoria estrutural, drift silencioso entre app (Onda Q) e backend (MOB-bridge-4 que está chegando) é inevitável. Esta sprint cria a fiscal canônica.

## Objetivo

1. Criar `scripts/audit_vault_md.py` (read-only) que percorre `~/Protocolo-Ouroboros/inbox/` e verifica:
   - **Estrutura**: cada arquivo está em `<area>/<subtipo>/` (não na raiz, não em `inbox/<arquivo>`).
   - **Áreas válidas**: `financeiro`, `saude`, `casa`, `outros` (lista canônica derivada de `categorias.ts` do app).
   - **Subtipos válidos** por área (declarar mapping canônico em `mappings/areas_subtipos.yaml` novo).
   - **Filename regex**: `^\d{4}-\d{2}-\d{2}-\d{6}(-[a-z0-9-]+)?\.[a-z0-9]+$` (data-hora-slug-extensao).
   - **Frontmatter YAML do `.md` companion**: campo obrigatório `_schema_version: 1` + `tipo` + `data` + `area` + `subtipo`.
   - **Companion presente**: cada binário (jpg/png/pdf/m4a) tem `.md` ao lado com mesmo basename.
   - **Zero binários soltos** fora da subpasta canônica.
2. Saída: relatório `docs/auditorias/AUDITORIA_VAULT_MD_<data>.md` com:
   - Resumo: N arquivos auditados, M violações.
   - Lista detalhada por categoria (estrutura, filename, frontmatter, companion, soltos).
3. Exit code: 0 vault limpo / 1 vault com violações.
4. Testes em `tests/test_audit_vault_md.py` com vault sintético (5 arquivos bons + 5 arquivos quebrados).

## Validação ANTES (grep -- padrão (k))

```bash
ls ~/Protocolo-Ouroboros/inbox/ 2>/dev/null | head
ls ~/Controle\ de\ Bordo/ 2>/dev/null | head   # confirmar qual e o path real
cat ~/Desenvolvimento/Protocolo-Ouroboros/src/lib/share/categorias.ts | grep -A 2 "area:" | head
grep "_schema_version" ~/Protocolo-Ouroboros/inbox/**/*.md 2>/dev/null | head
ls scripts/ | grep -i "audit\|vault\|inbox"
```

Confirma: (a) path real do vault, (b) áreas declaradas no app, (c) frontmatter aparece nos `.md` existentes, (d) script novo não duplica trabalho.

## Não-objetivos (padrão (t))

- **NÃO** corrigir violações automaticamente — só relatar. Correção é manual ou sprint-filha.
- **NÃO** modificar arquivos do vault (Syncthing compartilhado).
- **NÃO** validar conteúdo dos `.md` além do frontmatter mínimo (corpo é livre por design).
- **NÃO** rodar OCR no audit; binários são verificados só por extensão/existência.
- **NÃO** assumir que vault está em `~/Protocolo-Ouroboros/` — deve aceitar `--vault-path` como argumento (config flexível).

## Spec de implementação

### CLI

```python
# scripts/audit_vault_md.py
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Auditoria estrutural do vault Ouroboros (read-only)")
    parser.add_argument("--vault-path", default=str(Path.home() / "Protocolo-Ouroboros"))
    parser.add_argument("--relatorio", default=None, help="Path do .md de saida (default: docs/auditorias/AUDITORIA_VAULT_MD_<data>.md)")
    parser.add_argument("--exit-zero-mesmo-com-violacao", action="store_true")
    args = parser.parse_args()

    vault = Path(args.vault_path).expanduser()
    if not vault.exists():
        print(f"[AUDIT] Vault nao encontrado: {vault}")
        return 1

    auditor = AuditorVault(vault)
    relatorio = auditor.executar()
    gerar_relatorio_md(relatorio, args.relatorio)

    if relatorio.violacoes and not args.exit_zero_mesmo_com_violacao:
        return 1
    return 0
```

### Mapeamento canônico `mappings/areas_subtipos.yaml`

```yaml
# Espelho canonico de INBOX_SUBTIPOS em src/lib/share/categorias.ts (app mobile)
# Drift entre este mapping e o app => sprint-filha imediata
financeiro:
  - pix
  - extrato
  - nota
saude:
  - exame
  - receita
casa:
  - garantia
  - contrato
outros:
  - outro
```

Fonte canônica verificada em 2026-05-12: `~/Desenvolvimento/Protocolo-Mob-Ouroboros/src/lib/share/categorias.ts` constante `INBOX_SUBTIPOS`. Total: **8 subtipos em 4 áreas**. Quando o app adicionar subtipo novo (ex: `boleto`), atualizar este YAML e o teste regressivo em `tests/test_audit_vault_md.py::test_areas_subtipos_alinhadas_com_app`.

### Regex filename canônico

`^\d{4}-\d{2}-\d{2}-\d{6}(-[a-z0-9-]+)?\.[a-z0-9]+$`

Exemplos válidos:
- `2026-05-12-153014-pix.jpg`
- `2026-05-12-153014-mercado-x.jpg`
- `2026-05-12-153014.pdf` (sem slug)

Exemplos inválidos (violação):
- `pix-2026-05-12.jpg` (ordem errada)
- `12-05-2026.jpg` (formato BR)
- `pix.jpg` (sem data)

### Schema do frontmatter `.md` companion

```yaml
---
_schema_version: 1
tipo: inbox_arquivo   # constante canonica do app (frontmatter.ts)
subtipo: <pix | extrato | nota | exame | receita | garantia | contrato | outro>
area: <financeiro | saude | casa | outros>
arquivo: 2026-05-12-153014-pix.jpg   # path relativo (campo canonico do app, NAO 'binario_companion')
mime_type: image/jpeg
tamanho_bytes: 142536
origem: share_intent | captura_camera | outros
revisar: true                          # flag para backend processar
data: 2026-05-12                       # opcional, mas presente quando captura tem timestamp
---
```

Campos obrigatórios (validados pelo audit): `_schema_version=1`, `tipo=inbox_arquivo`, `subtipo`, `area`, `arquivo`, `revisar`. Campos auxiliares: `mime_type`, `tamanho_bytes`, `origem`, `data`. Fonte canônica do schema: `src/lib/schemas/inbox_arquivo.ts` no app mobile + auditoria C1 (2026-05-12).

### Relatório markdown

```markdown
---
titulo: Auditoria estrutural do vault Ouroboros
data: 2026-05-12
auditor: scripts/audit_vault_md.py
escopo: ~/Protocolo-Ouroboros/inbox/
---

# Auditoria estrutural

## Resumo
- Total auditado: N
- Conformes: A (%)
- Violacoes: B (% por categoria)

## Categoria 1 -- Estrutura
- Inbox/raiz com binarios soltos: <lista path>
- Subpastas fora do mapping canonico: <lista>

## Categoria 2 -- Filename
- Filenames fora do regex: <lista>

## Categoria 3 -- Frontmatter
- .md sem _schema_version: <lista>
- .md com schema_version != 1: <lista>
- Campos obrigatorios ausentes: <lista>

## Categoria 4 -- Companion
- Binarios sem .md ao lado: <lista>
- .md sem binario ao lado: <lista>

## Recomendacoes
<5 bullets: o que fixar primeiro>
```

## Proof-of-work (padrão (u))

```bash
# 1. Vault sintetico para teste
mkdir -p /tmp/vault_teste/inbox/financeiro/pix
cat > /tmp/vault_teste/inbox/financeiro/pix/2026-05-12-153014-pix.md <<'EOF'
---
_schema_version: 1
tipo: inbox_arquivo
subtipo: pix
area: financeiro
arquivo: 2026-05-12-153014-pix.jpg
mime_type: image/jpeg
tamanho_bytes: 142536
origem: share_intent
revisar: true
---
EOF
touch /tmp/vault_teste/inbox/financeiro/pix/2026-05-12-153014-pix.jpg
# Caso quebrado: binario solto na raiz
touch /tmp/vault_teste/inbox/solto.jpg

# 2. Rodar audit
.venv/bin/python scripts/audit_vault_md.py --vault-path /tmp/vault_teste --relatorio /tmp/audit.md
echo "Exit: $?"
cat /tmp/audit.md | head -40

# 3. Rodar audit em vault real
.venv/bin/python scripts/audit_vault_md.py
# Esperado: relatorio gerado em docs/auditorias/AUDITORIA_VAULT_MD_<data>.md

# 4. Pytest
.venv/bin/pytest tests/test_audit_vault_md.py -v

# 5. Gauntlet
make lint && make smoke
```

## Critério de aceitação (gate (z))

1. `scripts/audit_vault_md.py` existe, exit 0 em vault limpo, exit 1 com violações.
2. `mappings/areas_subtipos.yaml` canônico criado.
3. Relatório markdown gerado em `docs/auditorias/` no formato declarado.
4. `tests/test_audit_vault_md.py` ≥ 8 testes (5 ok + 5 quebrados).
5. Pytest baseline cresce ≥ +8 testes.
6. Gauntlet verde.

## Referência

- Auditoria C1 (app mobile, 2026-05-12): `docs/auditorias/AUDITORIA_APP_MOBILE_2026-05-12.md` — confirma `_schema_version: 1`.
- Categorias do app: `~/Desenvolvimento/Protocolo-Mob-Ouroboros/src/lib/share/categorias.ts`.
- ADR-0014 mobile (Syncthing path): documentação interna do app.
- Plano de origem: `~/.claude/plans/preciso-que-use-o-crispy-stroustrup.md` Fase B.

*"Auditoria estrutural e o vacina contra drift; rodar uma vez por semana evita reescrever um trimestre depois." — princípio MOB-audit-estrutura-vault-md*
