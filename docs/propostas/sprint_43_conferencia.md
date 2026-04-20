# Sprint 43 -- Conferência Artesanal Opus (sprint META)

**Data:** 2026-04-20
**Escopo:** Workflow Supervisor Artesanal -- scripts bash + templates + diário
**Status da implementação:** CONCLUÍDA
**Testes:** 288 passando (0 novos testes Python -- sprint é infra bash+markdown)
**Lint:** `ruff` limpo, `check_acentuacao.py` com 21 avisos pré-existentes (fora do escopo).

Esta sprint é **meta**: cria a infra do ciclo de propostas. A "conferência"
é validar que os próprios scripts funcionam end-to-end. E eles funcionam --
esta sprint testou seu próprio workflow plantando 5 propostas reais.

---

## 1. Entregas

| Caminho | Linhas | Propósito |
|---------|--------|-----------|
| `docs/propostas/README.md` | 128 | Documenta tipos, ciclo de vida, frontmatter, anti-padrões |
| `docs/templates/PROPOSTA_REGRA.md` | 50 | Template genérico (cobre regra, resolver, categoria_item) |
| `docs/templates/PROPOSTA_CLASSIFICACAO.md` | 46 | Template para arquivos em `_classificar/` |
| `docs/templates/PROPOSTA_LINKING.md` | 58 | Template para linking documento↔transação ambíguo |
| `docs/DIARIO_MELHORIAS.md` | 25 | Log cronológico de decisões |
| `scripts/supervisor_contexto.sh` | 115 | Snapshot estado do projeto (XLSX + grafo + propostas + commits + armadilhas) |
| `scripts/supervisor_proposta_nova.sh` | 75 | Cria esqueleto a partir de template |
| `scripts/supervisor_aprovar.sh` | 115 | Move para `_aprovadas/` + atualiza diário atômico |
| `scripts/supervisor_rejeitar.sh` | 95 | Move para `_rejeitadas/` + motivo |
| `run.sh` | +3 | Flag `--supervisor` |

5 pastas com `_aprovadas/` e `_rejeitadas/` criadas:
`regra/`, `classificacao/`, `linking/`, `resolver/`, `categoria_item/`.

## 2. Validação end-to-end do workflow

### Ciclo de vida testado

```bash
# 1. Abrir proposta
bash scripts/supervisor_proposta_nova.sh regra teste_dummy
# -> docs/propostas/regra/2026-04-20_teste_dummy.md (esqueleto a partir do template)

# 2. Aprovar
bash scripts/supervisor_aprovar.sh docs/propostas/regra/2026-04-20_teste_dummy.md
# -> move para _aprovadas/, registra no DIARIO_MELHORIAS.md, imprime guidance

# 3. Idempotência (rodar aprovar 2x)
bash scripts/supervisor_aprovar.sh docs/propostas/regra/_aprovadas/2026-04-20_teste_dummy.md
# -> detecta status terminal, não re-aprova
```

Validações feitas:

| Cenário | Resultado |
|---------|-----------|
| `proposta_nova` com tipo inválido | Rejeita com mensagem clara |
| `proposta_nova` com slug com espaço | Normaliza para kebab-case |
| `proposta_nova` para arquivo já existente | Rejeita (evita sobrescrita silenciosa) |
| `aprovar` sem frontmatter | Rejeita (campo obrigatório ausente) |
| `aprovar` sem seções obrigatórias | Rejeita (estrutura mínima não bate) |
| `aprovar` 2x no mesmo arquivo | Detecta status terminal, não duplica no diário |
| `rejeitar` sem motivo | Rejeita o rejeitar |
| `rejeitar` registra motivo no diário | OK |
| `--supervisor` imprime 6 seções canônicas | OK |

## 3. Primeira aplicação real (5 propostas plantadas)

O supervisor plantou 5 propostas reais das armadilhas acumuladas das
Sprints 47c + 44b:

| ID | Tipo | Origem | Resumo |
|----|------|--------|--------|
| `2026-04-20_enrich-yaml-sobrescreve-glyph` | regra | ARMADILHA #22 | Trocar `setdefault` por sobrescrita quando CNPJ bate YAML canônico |
| `2026-04-20_item-nome-canonico-legivel` | regra | Feedback 44b | Adicionar view SQL `v_item_legivel` sem mudar `nome_canonico` |
| `2026-04-20_notas-garantia-scan-nfce` | classificacao | Inbox pendente | PDF escaneado heterogêneo (4 pgs, 2 NFC-e + 2 bilhetes) aguarda Sprint 41e ou quebra manual |
| `2026-04-20_cardif-sem-bilhete-mapeado` | resolver | Feedback 47c | Cardif ociosa no YAML -- manter (A) ou remover (B)? |
| `2026-04-20_apolice-item-heuristica-threshold` | linking | Caso-de-ouro 44b | Formalizar threshold rapidfuzz=82 como regressão-lock |

`./run.sh --supervisor` lista todas 5 na seção "Propostas Pendentes".
Cada proposta tem diff proposto, justificativa com contagem/impacto,
teste de regressão e decisão-humana em branco.

## 4. Decisões de design

### 4.1. Zero Python no workflow

ADR-13 veta cliente LLM programático. O workflow é 100% bash + markdown +
git. O Python só aparece indireto quando `supervisor_contexto.sh` consulta
o XLSX via `pandas`. Todo script bash tem `set -euo pipefail` (Armadilha
A43-1).

### 4.2. Diário inserção atômica no topo da data

Entradas novas vão DENTRO do bloco `## YYYY-MM-DD` mais recente (se já
existir) ou criam novo bloco acima do primeiro `---`. Awk faz isso numa
pass única, preservando resto do arquivo. Testado com 2 aprovações no
mesmo dia -- mantém ordem cronológica correta.

### 4.3. Frontmatter como contrato validável

`supervisor_aprovar.sh` valida 4 campos obrigatórios (`id`, `tipo`, `data`,
`status`) + 3 seções (`## Contexto`, `## Justificativa`, `## Decisão
humana`). Se falhar, aborta antes de mover -- arquivo original fica intacto.

### 4.4. Templates compartilhados por família

5 tipos de proposta, 3 templates:
- `regra` / `resolver` / `categoria_item` compartilham `PROPOSTA_REGRA.md`
  (estrutura `Contexto/Diff/Justificativa/Teste`)
- `classificacao` tem seu próprio (bloco sobre arquivo + tipo sugerido)
- `linking` tem seu próprio (entidades + evidência a favor/contra)

Tipos com mesmo template são intercambiáveis -- `supervisor_proposta_nova.sh`
força o campo `tipo:` correto na cópia do template.

### 4.5. Idempotência por verificação de status

Aprovar/rejeitar verifica `status: aberta` antes de agir. Se status já for
terminal, imprime aviso e exit 0 (não é erro). Permite rodar scripts sem
medo de corromper estado.

## 5. Pendências + follow-ups

| Item | Onde | Quando |
|------|------|--------|
| Hook que valida frontmatter em pre-commit (opcional) | `.git/hooks/` ou `scripts/pre-commit-check.sh` | Se houver drift de schema |
| Dashboard com seção "Propostas Abertas" | `src/dashboard/app.py` | Quando dashboard for refeito |
| Exportar diário para Obsidian (vault pessoal) | `src/obsidian/sync.py` | Sprint 29a |
| Auto-renomear proposta se slug duplicar data | `supervisor_proposta_nova.sh` | Se surgir colisão |

## 6. Observações da conferência

1. **Sprint meta aprova-se a si mesma.** A primeira entrada do diário é
   a própria Sprint 43. Isso não é truque -- é o teste mais honesto:
   se o workflow funciona para ela, funciona para o resto.

2. **5 armadilhas reais em fila.** Não é por acaso. Sem o workflow, elas
   ficariam soltas em comentários de código ou em conversas de sessão
   perdidas ao fechar a janela. Agora cada uma tem arquivo, diff, teste
   e destino.

3. **O humano é quem aprova.** Os scripts não tomam decisão de mérito --
   só validam estrutura e mantêm estado. A aprovação/rejeição é
   irredutivelmente humana. ADR-08/ADR-13 preservados.

4. **`classificacao` sem cedilha = identificador.** Decisão pragmática:
   nome de tipo é identificador (URL-path, CLI arg, chave de dict). Fica
   sem acento. `# noqa: accent` catalogado nos 3 pontos onde aparece
   (frontmatter do template + 2 linhas de help no script). Mesma filosofia
   da Sprint 47c com `Transacao`.

---

*"O mestre não se serve sem ritual, nem o aprendiz sem calma." -- princípio de artesão*
