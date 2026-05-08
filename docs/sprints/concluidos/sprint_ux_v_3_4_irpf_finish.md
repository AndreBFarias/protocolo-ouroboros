---
id: UX-V-3.4
titulo: IRPF — completar 2 categorias + barras coloridas + botões expand/baixar + checklist
status: concluída
concluida_em: 2026-05-08
commit: 424fd44
prioridade: media
data_criacao: 2026-05-08
fase: PARIDADE_VISUAL
depende_de: []
esforco_estimado_horas: 2
origem: docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-08.md (página 15)
mockup: novo-mockup/mockups/15-irpf.html
---

# Sprint UX-V-3.4 — IRPF com 8 categorias canônicas

## Contexto

Inspeção 2026-05-08:
- Dashboard mostra 5 categorias visíveis. Mockup tem 8: rendimento_tributavel, rendimento_isento, dedutivel_medico, dedutivel_educacional, previdencia_privada, imposto_pago, inss_retido, doacao_dedutivel.
- Barra de completude monocromática — mockup tem cores `>=90%` verde / `70-90%` amarelo + badge.
- Botões expand/baixar inline ausentes (mockup tem chevron + ícone documento por linha).
- Dropdown "Ano-calendário" muito proeminente acima do título — mockup tem ano no título "IRPF 2026".
- Checklist lateral menor que mockup (5 itens estruturados com marcadores OK/aviso).

## Objetivo

1. Mover ano para o título: `IRPF {ano}` (ler do filtro global ou padrão ano corrente).
2. Renderizar 8 categorias canônicas (sempre — mesmo se sem dados, mostrar `0 arquivos · 0%`).
3. Barra de completude colorida: verde >=90%, amarelo 70-90%, vermelho <70%.
4. Botões expand+baixar inline por categoria.
5. Checklist lateral com 5 itens (8/8 tags compiladas, X/Y arquivos validados, X confiança<70%, totais batem, X fornecedores não cruzados).

## Validação ANTES (grep)

```bash
grep -n "rendimento_tributavel\|inss_retido\|doacao_dedutivel\|categorias_canonicas" src/dashboard/paginas/irpf.py | head
```

## Não-objetivos

- NÃO implementar geração real do PDF/XLSX (já existe em backend).
- NÃO mexer no botão "Gerar pacote".

## Proof-of-work

```bash
make lint && make smoke
.venv/bin/pytest tests/ -k irpf -q
```

Captura visual: 8 categorias visíveis com barra colorida + botões.

## Critério de aceitação

1. Título "IRPF {ano}" sem dropdown proeminente.
2. 8 categorias renderizadas.
3. Barras coloridas conforme thresholds.
4. Botões inline por categoria.
5. Checklist lateral com 5 itens.
6. Lint + smoke + baseline pytest.

## Referência

- Mockup: `15-irpf.html`.

*"IRPF é checklist anual — todos campos sempre listados." — princípio V-3.4*
