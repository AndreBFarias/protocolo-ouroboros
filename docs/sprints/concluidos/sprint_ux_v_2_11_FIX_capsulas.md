---
id: UX-V-2.11-FIX
titulo: Memórias — substituir Treinos/Fotos/Marcos por grid de cápsulas multimídia + skeleton
status: concluída
concluida_em: 2026-05-08
commit: c400e72
prioridade: alta
data_criacao: 2026-05-08
fase: PARIDADE_VISUAL
depende_de: []
esforco_estimado_horas: 5
origem: docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-08.md M8 (migué arquitetural)
mockup: novo-mockup/mockups/23-memorias.html
---

# Sprint UX-V-2.11-FIX — Memórias com grid de cápsulas (mockup-canônico)

## Contexto

UX-V-2.11 declarou paridade mas dashboard ainda usa layout antigo (tabs Treinos / Fotos / Marcos com heatmap 91 dias). Mockup `23-memorias.html` propõe arquitetura totalmente diferente:

- 4 KPIs: Total 30D · Por tipo (5 fotos / 2 áudios / 3 textos / 2 vídeos) · Vinculadas a eventos · Cápsulas para abrir.
- Filtros chips: todos / foto / voz / texto / video.
- Grid 7+5 de cápsulas multimídia com gradientes coloridos, badge tipo (FOTO/ÁUDIO/TEXTO/VÍDEO), título, data/local, chips categoria.

Decisão dono 2026-05-08 (resposta AskUserQuestion): endurecer skeleton-mockup canônico agora.

## Objetivo

1. Reescrever `be_memorias.py` para nova arquitetura.
2. 4 KPIs no topo (counters reais quando dado existe; placeholder `--` quando vazio).
3. Filtros chips no topo (todos/foto/voz/texto/video).
4. Grid de cápsulas (placeholder `<div class="capsula-skeleton">` quando sem dados).
5. Quando dados mob existirem (`memorias.json`), popular grid real com gradientes por tipo.
6. Manter aba "Treinos" como sub-rota interna `?secao=treinos` (compat retro pra heatmap antigo).

## Validação ANTES (grep)

```bash
wc -l src/dashboard/paginas/be_memorias.py
grep -n "treinos\|fotos\|marcos\|capsula\|gradiente" src/dashboard/paginas/be_memorias.py | head
ls .ouroboros/cache/memorias.json 2>&1 | head
```

## Não-objetivos

- NÃO implementar player de áudio/vídeo nesta sprint.
- NÃO mexer no schema de dados — schema vem do mob (I-FOTO/I-AUDIO/I-VIDEO em todo).

## Proof-of-work

```bash
make lint && make smoke
.venv/bin/pytest tests/ -k be_memorias -q
```

Captura visual: cluster=Bem-estar&tab=Memórias com 4 KPIs + chips + grid de skeleton ou cápsulas reais.

## Critério de aceitação

1. 4 KPIs no topo.
2. Filtros chips funcionais.
3. Grid de cápsulas (skeleton ou real).
4. Sub-rota `?secao=treinos` mantém heatmap antigo (retrocompatível).
5. Lint + smoke + baseline pytest.

## Referência

- Mockup: `23-memorias.html`.
- Mob bloqueante: I-FOTO + I-AUDIO + I-VIDEO no Protocolo-Mob-Ouroboros.

*"Memórias são cápsulas, não heatmaps." — princípio V-2.11-FIX*
