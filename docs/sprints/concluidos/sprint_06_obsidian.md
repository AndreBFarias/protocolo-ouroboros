---
concluida_em: 2026-04-19
---

# Sprint 06 -- Integração Obsidian

## Status: Código integrado, validação pendente (issue #6 reaberta)
Issue: #6 (reaberta)

## Objetivo

Integrar o pipeline financeiro com o vault Obsidian em ~/Controle de Bordo/. Relatórios financeiros devem aparecer no vault com backlinks, frontmatter e queries Dataview.

## Entregas

- [x] Sync automático: copia relatórios MD para vault após execução
- [x] Frontmatter YAML em cada relatório (tipo, mês, receita, despesa, saldo, tags)
- [x] 44 relatórios sincronizados para ~/Controle de Bordo/Pessoal/Financeiro/Relatórios/
- [x] 7 notas de metas criadas em ~/Controle de Bordo/Pessoal/Financeiro/Metas/
- [x] MOC "Dashboard Financeiro" com Dataview queries
- [x] `run.sh --sync` integrado
- [ ] Corrigir idempotência (campo created)
- [ ] Corrigir nomes de arquivo (PF/PJ -> Pf/Pj)
- [ ] Validar frontmatters em massa
- [ ] Testar Dataview no Obsidian real

## Bugs identificados na análise de código

### Bug 1: Idempotência quebrada
- **Arquivo:** `src/obsidian/sync.py` linha 101
- **Problema:** `created: date.today().isoformat()` é recalculado em toda execução. Rodar sync 2x altera o campo `created` de todos os 44 relatórios.
- **Correção:** Antes de escrever, verificar se o arquivo destino já existe. Se sim, extrair o `created` original do frontmatter e preservá-lo.
- **Nota:** O gauntlet já testa idempotência mas ignora o campo created. Após o fix, deve ser idempotência total.

### Bug 2: Nomes de arquivo com siglas minúsculas
- **Arquivo:** `src/obsidian/sync.py` linhas 119-126 e 214
- **Problema:** `nome.title()` converte siglas incorretamente:
  - "Quitar dívida Nubank PF (Vitória)" -> "Quitar Dívida Nubank Pf (Vitória)"
  - "CNH (André + Vitória)" -> "Cnh (André + Vitória)"
- **Correção:** Criar `_formatar_nome_arquivo()` que preserve siglas conhecidas (PF, PJ, CNH, IRPF, PIX).

### Bug 3: Frontmatter sem verificação em massa
- **Problema:** Só 1 de 44 frontmatters foi verificado (2026-04).
- **Correção:** Após sync, amostrar 5 relatórios de datas diferentes e validar que receita/despesa/saldo estão presentes e numéricos.

### Observação sobre Dataview
- MOC usa `FROM "Pessoal/Financeiro/Relatorios"` -- correto para o vault ~/Controle de Bordo/
- Frontmatter usa `mes: "2026-04"` (string) e receita/despesa/saldo (float) -- compatível com Dataview
- Vault tem plugin Dataview instalado (confirmado em .obsidian/community-plugins.json)

## Assinaturas importantes

- `sincronizar_relatorios(diretorio_output: Path) -> list[Path]`
  Usa constantes de módulo (RELATORIOS_PATH, METAS_YAML etc.), patcháveis em testes.
- `criar_notas_metas() -> list[Path]`
- `criar_moc_financeiro() -> Path`
- `executar_sincronizacao() -> None` (orquestra os 3 acima)

## Gauntlet

Fase `obsidian` cobre: sync relatórios (1 arquivo), frontmatter (campos obrigatórios), notas de metas (3 criadas), idempotência ignorando created (4/4 OK).

## Arquivos a modificar

| Arquivo | Mudança |
|---------|---------|
| `src/obsidian/sync.py` | Preservar created existente, _formatar_nome_arquivo(), validação |

## Critério de sucesso

- [ ] Rodar sync 2x produz arquivos idênticos (idempotente total)
- [ ] Nomes de arquivo: "Nubank PF" (não "Pf"), "CNH" (não "Cnh")
- [ ] 5 frontmatters amostrados com valores corretos
- [ ] Dataview queries funcionais no Obsidian (Chrome MCP se possível)

## Dependências

Sprint 05 (relatórios automáticos completos).
