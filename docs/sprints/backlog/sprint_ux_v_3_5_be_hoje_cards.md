---
id: UX-V-3.5
titulo: Bem-estar Hoje — cards laterais Status casal + Próximos alarmes + Registros do dia
status: backlog
prioridade: media
data_criacao: 2026-05-08
fase: PARIDADE_VISUAL
depende_de: []
esforco_estimado_horas: 4
origem: docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-08.md (página 17)
mockup: novo-mockup/mockups/17-bem-estar-hoje.html
---

# Sprint UX-V-3.5 — cards laterais canônicos do Bem-estar Hoje

## Contexto

Inspeção 2026-05-08: dashboard tem cards laterais com counters Diários/Eventos/Medidas do dia. Mockup tem outros 3 cards mais ricos:
1. **ESSE REGISTRO É PARA...** com 3 botões (para mim / para Pessoa B / para o casal).
2. **STATUS DO CASAL · ÚLTIMOS 7 DIAS** com Pessoa A 3.8/5 + Pessoa B 3.2/5 + barras horizontais por dia.
3. **PRÓXIMOS · ALARMES & TAREFAS** com 5 itens (alarme medicação 22:00, tarefa pagar fatura, treino A, evento jantar, contador dias sem fumar).

Tags como inputs simples vs pílulas multi-seleção do mockup.

## Objetivo

1. Substituir 3 cards laterais por: SELETOR PARA QUEM + STATUS CASAL 7D + PRÓXIMOS.
2. STATUS CASAL: ler humor médio Pessoa A + Pessoa B dos últimos 7 dias do cache, mostrar barras pequenas.
3. PRÓXIMOS: agregar próximos 5 itens de alarmes + tarefas pendentes hoje + 1 evento próximo + 1 contador.
4. Tags como pílulas multi-seleção (`st.pills` ou HTML+JS).

## Validação ANTES (grep)

```bash
grep -n "STATUS DO CASAL\|para_quem\|proximos_alarmes\|st.pills" src/dashboard/paginas/be_hoje.py | head
```

## Não-objetivos

- NÃO mexer nos 4 sliders.
- NÃO duplicar lógica de Rotina (Próximos lê do mesmo cache).

## Proof-of-work

```bash
make lint && make smoke
.venv/bin/pytest tests/ -k be_hoje -q
```

Captura visual: 3 cards laterais canônicos visíveis.

## Critério de aceitação

1. Card "ESSE REGISTRO É PARA..." com 3 botões.
2. Card "STATUS DO CASAL · 7D" com Pessoa A + B e barras.
3. Card "PRÓXIMOS · ALARMES & TAREFAS" com >=3 itens reais (caso vault populado).
4. Tags como pílulas multi-seleção.
5. Lint + smoke + baseline pytest.

## Referência

- Mockup: `17-bem-estar-hoje.html`.

*"Hoje é o agora do casal — não só o seu humor." — princípio V-3.5*
