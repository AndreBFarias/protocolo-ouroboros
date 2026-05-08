---
id: UX-V-04.A
titulo: Acentuação periférica em be_*.py + ui.py + sync_rico.py
status: concluída
concluida_em: 2026-05-08
commit: 660ee6e
prioridade: baixa
data_criacao: 2026-05-07
fase: ZELO
depende_de: []
co_executavel_com: []
esforco_estimado_horas: 0.5
origem: achado colateral durante UX-V-04 (sync observabilidade)
---

# Sprint UX-V-04.A — Acentuação periférica residual

## Contexto

Durante UX-V-04 (sync observabilidade), o varredor de acentuação
(`~/.config/zsh/scripts/validar-acentuacao.py`) detectou 13 violações
**pré-existentes** (não introduzidas por V-04) em arquivos pareados:

| Arquivo | Linha | Violação |
|---|---|---|
| `src/dashboard/componentes/ui.py` | 219 | `descricao` → `descrição` (assinatura) |
| `src/dashboard/componentes/ui.py` | 230 | `descricao` → `descrição` |
| `src/dashboard/paginas/be_diario.py` | 26, 74, 88 | `periodo` → `período` |
| `src/dashboard/paginas/be_hoje.py` | 27, 67, 76, 91 | `periodo` → `período` |
| `src/dashboard/paginas/be_humor.py` | 17, 52, 65 | `periodo` → `período` |
| `src/obsidian/sync_rico.py` | 223 | `nao` → `não` (literal `"nao-classificado"`) |

## Por que NÃO foi corrigido inline em UX-V-04

Padrão `(l)` (achado colateral vira sprint-filha) + padrão `(b)` (acentuação
PT-BR é regra inviolável). Renomear parâmetro de assinatura pública (`periodo`,
`descricao`) é mudança de API que pode quebrar callers — exige sprint dedicada
com varredura de impacto via grep + atualização coordenada.

O literal `"nao-classificado"` em `sync_rico.py:223` aparece em metadata do
grafo (`categoria`); renomear pode invalidar dados gerados antes da mudança.
Avaliar migração compatível.

## Escopo

1. Renomear parâmetro `descricao` → `descricao` em `hero_titulo_html`
   (manter alias retrocompatível? avaliar grep de callers).
2. Renomear `periodo` → `período` em assinaturas `def renderizar(...)` das
   páginas Bem-estar (assinatura é convenção do contrato `paginas/`; varrer
   roteador de páginas para confirmar consistência).
3. Em `sync_rico.py:223`: avaliar se `"nao-classificado"` é literal de domínio
   estável (provavelmente vem de pipeline). Se sim, manter e adicionar comentário
   `# noqa: acento -- valor de domínio canônico`.

## Validação ANTES (grep)

```bash
rg "periodo: str" src/dashboard/paginas/ | wc -l
rg "descricao: str" src/dashboard/ | wc -l
rg '"nao-classificado"' src/ | wc -l
```

## Validação DEPOIS

```bash
python3 ~/.config/zsh/scripts/validar-acentuacao.py --paths \
  src/dashboard/componentes/ui.py \
  src/dashboard/paginas/be_diario.py \
  src/dashboard/paginas/be_hoje.py \
  src/dashboard/paginas/be_humor.py \
  src/obsidian/sync_rico.py
# Esperado: 0 violações

make lint && make smoke
.venv/bin/python -m pytest tests/ -q
```

## Critério de aceitação

- 0 violações de acentuação nos 5 arquivos.
- Suite mantém baseline (sem regressão).
- Callers de `descricao` / `periodo` atualizados se renomeação for adotada.

*"O que mede a si mesmo afia-se." — princípio do varredor"*
