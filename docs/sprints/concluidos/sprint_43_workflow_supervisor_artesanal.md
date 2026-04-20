## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 43
  title: "Workflow Supervisor Artesanal: scripts, templates e diário"
  touches:
    - path: scripts/supervisor_contexto.sh
      reason: "dumpa estado do projeto (XLSX stats, grafo stats, propostas pendentes, armadilhas recentes, últimos commits) para Claude Code consumir no início de sessão"
    - path: scripts/supervisor_proposta_nova.sh
      reason: "cria esqueleto de proposta nova em docs/propostas/<tipo>/<yyyy-mm-dd>_<slug>.md usando template"
    - path: scripts/supervisor_aprovar.sh
      reason: "move proposta aprovada para docs/propostas/_aprovadas/ e registra em DIARIO_MELHORIAS.md"
    - path: scripts/supervisor_rejeitar.sh
      reason: "move proposta para docs/propostas/_rejeitadas/ com motivo"
    - path: docs/templates/PROPOSTA_REGRA.md
      reason: "template de proposta com frontmatter, diff, justificativa, teste"
    - path: docs/templates/PROPOSTA_CLASSIFICACAO.md
      reason: "template específico para arquivos em data/raw/_classificar/"
    - path: docs/templates/PROPOSTA_LINKING.md
      reason: "template para propostas de linking documento <-> transação"
    - path: docs/DIARIO_MELHORIAS.md
      reason: "log cronológico de propostas aprovadas/rejeitadas"
    - path: docs/propostas/README.md
      reason: "documenta a convenção da pasta (tipos, ciclo de vida, aprovação)"
    - path: run.sh
      reason: "adiciona flag --supervisor que chama scripts/supervisor_contexto.sh"
  n_to_n_pairs:
    - [docs/templates/PROPOSTA_REGRA.md, docs/templates/PROPOSTA_CLASSIFICACAO.md]
  forbidden:
    - src/llm/  # não criar cliente programático (ADR-13)
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: "scripts/supervisor_contexto.sh > /tmp/ctx.txt && grep -q 'Estado do Projeto' /tmp/ctx.txt"
      timeout: 30
    - cmd: "bash scripts/supervisor_proposta_nova.sh regra teste-proposta && ls docs/propostas/regra/*teste-proposta*.md"
      timeout: 30
  acceptance_criteria:
    - "scripts/supervisor_contexto.sh imprime seções {Estado do Projeto, Propostas Pendentes, Últimas Armadilhas, Últimos Commits, Sprints em Andamento}"
    - "docs/templates/PROPOSTA_REGRA.md tem frontmatter com campos obrigatórios (id, tipo, data, status, autor_proposta)"
    - "docs/propostas/README.md documenta ciclo: aberta -> aprovada|rejeitada -> arquivada"
    - "run.sh --supervisor executa scripts/supervisor_contexto.sh com saída legível"
    - "docs/DIARIO_MELHORIAS.md criado com cabeçalho e primeira entrada (esta sprint)"
    - "Acentuação PT-BR correta"
    - "Zero emojis"
```

> Executar antes de começar: `make lint && ./run.sh --check`

---

# Sprint 43 -- Workflow Supervisor Artesanal

**Status:** CONCLUÍDA
**Data:** 2026-04-19
**Prioridade:** CRÍTICA
**Tipo:** Infra
**Dependências:** Sprint 42 (grafo já existe para supervisor_contexto.sh consultar)
**Desbloqueia:** Sprints 44-53 (todas dependem do workflow de proposta aprovada)
**Issue:** --
**ADR:** ADR-13 (Supervisor Artesanal via Claude Code), ADR-08 (Supervisor Aprovador)

---

## Como Executar

**Comandos principais:**
- `./run.sh --supervisor` -- snapshot rápido do projeto
- `bash scripts/supervisor_proposta_nova.sh <tipo> <slug>` -- cria esqueleto de proposta
- `bash scripts/supervisor_aprovar.sh <caminho_proposta>` -- aprova e absorve

### O que NÃO fazer

- NÃO criar `src/llm/` nem cliente programático (veta ADR-13)
- NÃO adicionar dep nova; tudo é bash + markdown + git
- NÃO tentar automatizar aprovação -- revisão humana é do workflow

---

## Problema

Sem um workflow formal, propostas de regras novas para `mappings/*.yaml` ficam:
- Em mensagens de chat do Claude Code (perdidas ao fechar sessão)
- Em commits soltos (difícil auditar, impossível rejeitar depois)
- Em TODOs inline (anti-padrão do CLAUDE.md)

O objetivo é institucionalizar o ciclo:
1. Claude Code detecta padrão repetitivo no pipeline
2. Cria proposta em `docs/propostas/<tipo>/<slug>.md`
3. Humano revisa, aprova ou rejeita
4. Proposta aprovada vira commit + entrada em `mappings/*.yaml`
5. Proposta rejeitada vai pra `_rejeitadas/` com motivo

## O que já existe (NÃO duplicar)

| Sistema | Arquivo | O que faz |
|---------|---------|-----------|
| Template de sprint | `docs/templates/SPRINT_TEMPLATE.md` | Padrão canônico (já tem seção Conferência Artesanal) |
| Validador de sprints | `scripts/ci/validate_sprint_structure.py` | Valida sprints -- ideia similar para propostas |
| Hook auto-move | `hooks/sprint_auto_move.py` | Move sprint ao mudar status -- pode inspirar hook de proposta |
| ARMADILHAS.md | `docs/ARMADILHAS.md` | Fonte de "últimas armadilhas" para o supervisor_contexto.sh |

## Implementação

### Fase 1: criar `docs/propostas/README.md`

Explica:
- Tipos de proposta (`regra`, `classificacao`, `linking`, `resolver`, `categoria_item`)
- Ciclo de vida: `abertas/` → `_aprovadas/` | `_rejeitadas/`
- Como abrir uma proposta (bash helper)
- Como aprovar (bash helper + commit)
- Estrutura do frontmatter YAML

### Fase 2: criar templates

`docs/templates/PROPOSTA_REGRA.md`:

```markdown
---
id: <yyyy-mm-dd>_<slug>
tipo: regra  # regra | classificacao | linking | resolver | categoria_item
data: 2026-04-19
status: aberta
autor_proposta: claude-code-opus
sprint_contexto: 41  # sprint em que a proposta surgiu
---

## Contexto

(Descreve o padrão que motivou a proposta, com referência a arquivo:linha)

## Diff proposto

```diff
# mappings/categorias.yaml
+ neoenergia_v2:
+   regex: "NEOEN\\s*S.?A|NEOENERGIA.*"
+   categoria: "Energia"
+   classificacao: "Obrigatório"  # noqa: accent
```

## Justificativa

(Por que esta mudança? Quantas transações ela acerta? Risco de falso-positivo?)

## Teste de regressão

(Comando que prova que a regra aprovada cobre os casos-alvo e não quebra nada)

```bash
.venv/bin/pytest tests/test_categorizer.py::test_neoenergia_v2_casa_tres_formatos
```

## Decisão humana

**Aprovada em:** (preencher ao aprovar)
**Rejeitada em:** (preencher ao rejeitar)
**Motivo:** (se rejeitada)
```

`docs/templates/PROPOSTA_CLASSIFICACAO.md`: frontmatter idêntico + seções específicas para arquivos em `_classificar/` (tipo detectado sugerido, regra nova sugerida, pasta destino).

`docs/templates/PROPOSTA_LINKING.md`: para propor ligar um documento a uma transação quando heurísticas ficaram ambíguas.

### Fase 3: `scripts/supervisor_contexto.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "## Estado do Projeto ($(date -I))"
echo
echo "### XLSX"
test -f data/output/ouroboros_2026.xlsx && \
  python3 -c "
import pandas as pd
df = pd.read_excel('data/output/ouroboros_2026.xlsx', sheet_name='extrato')
print(f'Transações: {len(df)}')
print(f'Meses: {df.mes_ref.nunique()}')
print(f'Bancos: {df.banco_origem.nunique()}')
"

echo
echo "### Grafo"
test -f data/output/grafo.sqlite && \
  sqlite3 data/output/grafo.sqlite "SELECT tipo, COUNT(*) FROM node GROUP BY tipo;"

echo
echo "### Propostas Pendentes"
find docs/propostas -maxdepth 2 -type f -name "*.md" ! -path "*_aprovadas*" ! -path "*_rejeitadas*" ! -name "README.md" 2>/dev/null | head -20

echo
echo "### Últimas Armadilhas"
grep -E "^## \d+\." docs/ARMADILHAS.md | tail -5

echo
echo "### Últimos Commits"
git log --oneline -10

echo
echo "### Sprints em Andamento"
grep -l "^\*\*Status:\*\* EM ANDAMENTO" docs/sprints/producao/*.md 2>/dev/null || echo "(nenhuma)"

echo
echo "### Arquivos em data/raw/_classificar/ (pendentes)"
ls data/raw/_classificar/ 2>/dev/null | head -5 || echo "(nenhum)"
```

### Fase 4: `scripts/supervisor_proposta_nova.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail
TIPO="${1:-regra}"
SLUG="${2:?Uso: supervisor_proposta_nova.sh <tipo> <slug>}"
DATA=$(date -I)
ID="${DATA}_${SLUG}"
DESTINO="docs/propostas/${TIPO}/${ID}.md"
TEMPLATE="docs/templates/PROPOSTA_$(echo "$TIPO" | tr a-z A-Z).md"

mkdir -p "$(dirname "$DESTINO")"
test -f "$TEMPLATE" || TEMPLATE="docs/templates/PROPOSTA_REGRA.md"
cp "$TEMPLATE" "$DESTINO"

# substitui placeholders
sed -i "s|<yyyy-mm-dd>_<slug>|$ID|g; s|2026-04-19|$DATA|g" "$DESTINO"

echo "Proposta aberta: $DESTINO"
```

### Fase 5: `scripts/supervisor_aprovar.sh` e `supervisor_rejeitar.sh`

Aprovar:
1. Valida proposta (frontmatter existe, sections obrigatórias)
2. Copia para `docs/propostas/<tipo>/_aprovadas/`
3. Atualiza `docs/DIARIO_MELHORIAS.md` com entrada nova
4. Remove original
5. Imprime guidance de próximo passo ("rode `./run.sh --tudo` e commite com mensagem `feat: absorve proposta <id>`")

Rejeitar: idem, mas move para `_rejeitadas/` e exige motivo como argumento.

### Fase 6: `docs/DIARIO_MELHORIAS.md`

```markdown
# Diário de Melhorias -- Protocolo Ouroboros

Log cronológico de propostas submetidas pelo supervisor artesanal
(Claude Code) e suas decisões.

---

## 2026-04-19

### Sprint 43 (aprovada)

- **Workflow supervisor criado** -- primeira entrada do diário.
- Scripts `supervisor_contexto.sh`, `supervisor_proposta_nova.sh`,
  `supervisor_aprovar.sh`, `supervisor_rejeitar.sh` operantes.
- Templates de proposta (regra, classificacao, linking) prontos.

---

(entradas novas cronologicamente acima desta linha)
```

### Fase 7: integração em `run.sh`

```bash
# em run.sh, junto dos outros --flags
    --supervisor)
        bash scripts/supervisor_contexto.sh
        ;;
```

## Armadilhas Conhecidas

| Ref | Armadilha | Como evitar |
|-----|-----------|-------------|
| A43-1 | Scripts bash em projeto Python sem `#!/usr/bin/env bash` ou sem `set -euo pipefail` | Padronizar header em todo script novo |
| A43-2 | `sqlite3` command line não está no PATH em minimal installs | Guard: `command -v sqlite3 >/dev/null || echo "(sqlite3 não disponível)"` |
| A43-3 | Propostas sem frontmatter quebram parsers futuros | `supervisor_aprovar.sh` valida antes de aceitar |
| A43-4 | Mover proposta e esquecer de atualizar diário | Script orquestra: move + diário + remove original ATÔMICO (uma falha desfaz tudo) |
| A43-5 | Claude Code pode criar propostas demais sem foco | CLAUDE.md reforça: supervisor_contexto.sh é pedido explícito; Claude só propõe sob demanda ou no final de uma sprint |

Referência: `docs/ARMADILHAS.md`

## Evidências Obrigatórias

- [ ] `make lint` passa
- [ ] `./run.sh --supervisor` retorna texto estruturado com pelo menos 5 seções
- [ ] `bash scripts/supervisor_proposta_nova.sh regra teste` cria arquivo válido
- [ ] `docs/DIARIO_MELHORIAS.md` existe com cabeçalho e entrada inicial
- [ ] Ciclo aberta -> aprovada -> no diário funciona em sample real

## Verificação end-to-end

```bash
make lint
./run.sh --supervisor > /tmp/ctx.txt
grep -c "^###" /tmp/ctx.txt  # pelo menos 5 seções

bash scripts/supervisor_proposta_nova.sh regra teste_dummy
ls docs/propostas/regra/*teste_dummy*.md

# simula aprovação
bash scripts/supervisor_aprovar.sh docs/propostas/regra/*teste_dummy*.md
grep "teste_dummy" docs/DIARIO_MELHORIAS.md  # entrada registrada
ls docs/propostas/regra/_aprovadas/*teste_dummy*.md  # movido corretamente

# cleanup do teste
rm docs/propostas/regra/_aprovadas/*teste_dummy*.md
```

## Conferência Artesanal Opus

Esta sprint é META -- cria a infra da conferência, então a "conferência" aqui é validar que os próprios scripts funcionam.

**Arquivos originais a ler:**

- `scripts/supervisor_contexto.sh`
- Output real de `./run.sh --supervisor`
- `docs/templates/PROPOSTA_REGRA.md`

**Checklist:**

1. O output do contexto é legível para humano e Claude de forma intercambiável?
2. Os templates têm todos os campos necessários para auditoria futura?
3. O ciclo aberta -> aprovada -> diário é idempotente? Rodando duas vezes o approve gera duplicata?
4. `supervisor_proposta_nova.sh` aceita slugs com espaço? (deve rejeitar ou normalizar)

**Relatório esperado em `docs/propostas/sprint_43_conferencia.md`**: este arquivo é o primeiro teste completo do ciclo -- a sprint "aprova a si mesma" via workflow criado.

---

*"O mestre não se serve sem ritual, nem o aprendiz sem calma." -- princípio de artesão*
