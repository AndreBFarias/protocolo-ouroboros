---
id: META-PROPOSTAS-DASHBOARD
titulo: Dashboard "Propostas pendentes" para `docs/propostas/`
status: backlog
concluida_em: null
prioridade: P2
data_criacao: 2026-05-15
fase: DX
epico: 5
depende_de: []
esforco_estimado_horas: 1.5
origem: auditoria 2026-05-15. 4 propostas .md aguardando decisão humana em `docs/propostas/` (categoria_item × 2 + linking × 2). Sem cron/dashboard, dono não sabe que estão lá. Mecanismo de notificação ausente. Padrão `(jj/kk/ll)` "produto final na hora" não funciona sem visibilidade.
---

# Sprint META-PROPOSTAS-DASHBOARD

## Contexto

Sistema gera propostas em dois fluxos:
- `src/transform/item_categorizer.py` (sprint 50) → `docs/propostas/categoria_item/*.md`
- `src/graph/linking_heuristico.py` (sprint 48) → `docs/propostas/linking/*.md`

Cada proposta tem `status: aberta` e campos "Decisão humana" vazios. Hoje:
- Não-trackeadas (gitignored)
- Sem alerta visual
- Sem mecanismo de "expira após N dias"
- Dono precisa lembrar de rodar `find docs/propostas/ -name "*.md"`

## Hipótese e validação ANTES

H1: 4 propostas pendentes atualmente:

```bash
find docs/propostas/ -name "*.md" -exec grep -l "status: aberta" {} \;
# Esperado: 4 paths
```

H2: `gc_propostas_linking.py` existe mas é para limpeza de obsoletos:

```bash
.venv/bin/python scripts/gc_propostas_linking.py --help 2>&1 | head
# Esperado: subcomandos --auditar-atual, --mover-obsoletos
```

## Objetivo

1. Criar `src/dashboard/paginas/propostas_pendentes.py`:
   - Tabela com colunas: `id`, `tipo` (categoria_item/linking), `criado_em` (mtime ou frontmatter), `idade_dias`, `link_md` (abre inline).
   - Filtros: tipo, idade > 7d, idade > 30d (alerta vermelho).
   - Botão "abrir inline" mostra MD renderizado.
   - Botão "decisão tomada → aplicar" lê preenchimento da decisão humana e:
     - Para categoria_item: adiciona entry em `mappings/categorias_item.yaml`.
     - Para linking: cria aresta `documento_de` no grafo via `dossie_tipo.py` ou similar.
     - Move proposta para `docs/propostas/_aprovadas/<data>/`.
   - Botão "rejeitar" move para `docs/propostas/_rejeitadas/<data>/` com motivo.
2. Wirar em cluster Sistema do dashboard.
3. KPI "X propostas pendentes" no topo (visível mesmo sem entrar na página).

## Não-objetivos

- Não tocar geração de propostas (mecanismo upstream estável).
- Não auto-aprovar propostas (decisão humana sempre).
- Não criar notificação por email/Telegram (fora do escopo local-first).

## Proof-of-work runtime-real

```bash
# 1. Página carrega
.venv/bin/streamlit run src/dashboard/app.py &
PID=$!
sleep 5
curl -s http://localhost:8501/propostas_pendentes | grep -c "categoria_item\|linking"
# Esperado: ≥2 ocorrências
kill $PID

# 2. KPI count correto
.venv/bin/python -c "
from src.dashboard.paginas.propostas_pendentes import _contar_pendentes
n = _contar_pendentes()
print(f'{n} propostas pendentes')
assert n >= 4, f'esperado ≥4, veio {n}'
"
```

## Acceptance

- `src/dashboard/paginas/propostas_pendentes.py` criado e wireado.
- KPI "propostas pendentes" no topo do app.
- 4 propostas atuais visíveis.
- Botões aprovar/rejeitar funcionais.
- 4 testes em `tests/test_propostas_dashboard.py`.
- Pytest > 3019. Smoke 10/10. Lint exit 0.

## Padrões aplicáveis

- (kk) Sprint encerra com produto final.
- (l) Achado colateral — propostas eram o achado da auditoria; dashboard é o produto.

---

*"Decisão guardada na pasta é decisão sumida da memória; decisão na tela é decisão a um clique de virar regra." — princípio do balcão de aprovações*
