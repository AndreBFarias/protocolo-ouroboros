# Diário de Melhorias -- Protocolo Ouroboros

Log cronológico de propostas submetidas pelo supervisor artesanal
(Claude Code rodando em sessão interativa -- ADR-13) e suas decisões.

Entradas NOVAS ficam no topo (imediatamente abaixo do "# Diário..."). O
rodapé é pegada histórica que não muda.

Cada entrada contém: data, ação (aprovada|rejeitada), id da proposta,
referência ao arquivo original em `docs/propostas/<tipo>/_aprovadas/` ou
`docs/propostas/<tipo>/_rejeitadas/`, e resumo de 1 linha.

Para histórico completo de uma proposta, sempre ler o arquivo em
`_aprovadas/` ou `_rejeitadas/`.

---

## 2026-04-20

### Sprint 43 encerrada -- workflow supervisor artesanal institucionalizado

- **tipo:** infra  **status:** aprovada (sprint meta, aprova a si mesma)
- **entregas:**
  - `docs/propostas/README.md` documenta tipos, ciclo de vida e frontmatter.
  - Templates em `docs/templates/`: `PROPOSTA_REGRA.md`,
    `PROPOSTA_CLASSIFICACAO.md`, `PROPOSTA_LINKING.md`.
  - Scripts em `scripts/supervisor_*.sh`: contexto, nova, aprovar, rejeitar.
  - `./run.sh --supervisor` imprime snapshot do projeto.
  - Este diário inaugurado.
- **referência:** `docs/propostas/sprint_43_conferencia.md`

---

(entradas novas cronologicamente acima desta linha)
