---
id: META-TEMPLATE-FRONTMATTER-SPECS
titulo: Template canônico + script de normalização para 97 specs sem frontmatter
status: backlog
concluida_em: null
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
