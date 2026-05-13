---
id: META-TEMPLATE-FRONTMATTER-SPECS
titulo: Template canônico + script de normalização para 97 specs sem frontmatter
status: concluida  # noqa: accent
concluida_em: 2026-05-13
prioridade: P1
data_criacao: 2026-05-13
fase: SANEAMENTO
epico: 8
depende_de:
  - META-ONBOARDING-NOVA-SESSAO (referencia o template)
origem: auditoria 2026-05-13. 97/119 specs em backlog/ NÃO têm frontmatter YAML. Tooling (auditor, índice, dashboard) não parseia uniformemente. Inconsistência massiva.
---

# Sprint META-TEMPLATE-FRONTMATTER-SPECS

## Contexto

`docs/sprints/backlog/` tem 119 .md. Só 22 (18%) têm frontmatter YAML. Os outros 97 são markdown solto -- impossível extrair `id`, `prioridade`, `epico`, `status` programaticamente.

Próxima sessão que tenta auditar backlog automaticamente bate em parser inconsistente.

## Entregável

1. **`docs/sprints/_TEMPLATE_SPRINT.md`** -- template canônico com frontmatter obrigatório:
   ```yaml
   ---
   id: <SLUG-EM-CAIXA-ALTA>
   titulo: <descricao em uma linha>
   status: backlog | concluida | em_andamento
   concluida_em: null  # ou YYYY-MM-DD
   prioridade: P0 | P1 | P2 | P3
   data_criacao: YYYY-MM-DD
   fase: <ETL | DASHBOARD | SANEAMENTO | MOBILE | INTELIGENCIA | OUTROS>
   epico: <1..8 do ROADMAP>
   depende_de: []  # IDs de outras sprints
   tipo_documental_alvo: null  # ou <tipo do mappings/tipos_documento.yaml>
   ---
   ```

2. **`scripts/normalizar_specs.py`** -- CLI que:
   - `--auditar`: lista quais specs estão fora do template.
   - `--normalizar`: aplica frontmatter inferindo campos (id do nome do arquivo; epico=0 se não classificado).
   - `--validar`: garante que frontmatter de TODAS as specs em backlog/ é parseável.

3. **Testes** em `tests/test_normalizar_specs.py` com ≥6 casos (specs OK, sem frontmatter, frontmatter parcial, etc.).

4. Rodar o normalizador sobre as 97 specs faltantes (commit separado).

## Acceptance

- `scripts/normalizar_specs.py --validar` exit 0 sobre todo backlog/.
- 119/119 specs com frontmatter parseável.
- ≥6 testes verdes.
- Lint zero.

## Padrão canônico aplicável

(o) Subregra retrocompatível -- frontmatter é adição que não muda comportamento existente. Specs antigas continuam legíveis.

---

*"Sem frontmatter, spec é diário; com frontmatter, é registro." -- princípio do parseável*

## Conclusão (2026-05-13)

Entregue por executor em worktree `agent-aa48c926d3a1fb3cb`.

- **Template canônico criado**: `docs/sprints/_TEMPLATE_SPRINT.md` com frontmatter YAML obrigatório e seções padrão (Contexto, Objetivo, Validação ANTES, Não-objetivos, Touches, Plano, Acceptance, Proof-of-work, Padrão canônico).
- **CLI criado**: `scripts/normalizar_specs.py` com 3 subcomandos (`auditar`, `normalizar`, `validar`) + flag global `--excluir <arquivo>` repetível. Comentários HTML inline (`<!-- noqa: accent -->`) são removidos antes do parse YAML para tolerar diretivas legítimas do projeto.
- **Testes**: `tests/test_normalizar_specs.py` com 9 casos verdes (≥6 exigidos), cobrindo OK / sem frontmatter / parcial / idempotência / exclusão / inferência de id / YAML inválido.
- **Normalização aplicada**:
  - Specs sem frontmatter antes: 97 em `backlog/` + 3 em `concluidos/` = 100.
  - Specs sem frontmatter depois: 0 (excluindo as 2 P1 reservadas).
  - 3 specs com frontmatter YAML inválido corrigidas manualmente (quote em valores com `:` literal):
    - `backlog/sprint_FASE_A_completar_validacao_artesanal_2026-05-13.md`
    - `concluidos/MOB-bridge-3-spec.md`
    - `concluidos/sprint_MOB_bridge_4_inbox_subtipos_reader.md`
  - `validar` global retorna `449 specs OK` exit 0 (excluindo as 2 P1 reservadas para próxima onda paralela).
- **Baseline pytest preservada**: 23 failed / 2923 passed pré-existente (sprint não introduz regressão); +9 testes novos verdes em `tests/test_normalizar_specs.py`.
- **Pendências residuais conhecidas** (não bloqueantes — fora do escopo de "parseável"): ~345 specs com campos opcionais faltantes (principalmente `epico`). Auditor sinaliza para futura classificação manual pelo supervisor.
