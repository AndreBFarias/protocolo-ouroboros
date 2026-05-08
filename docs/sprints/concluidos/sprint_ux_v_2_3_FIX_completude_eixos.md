---
id: UX-V-2.3-FIX
titulo: Completude — corrigir eixo Y (tipos doc, não categorias trans) + legenda
status: concluída
concluida_em: 2026-05-08
commit: 82274a2
prioridade: alta
data_criacao: 2026-05-08
fase: PARIDADE_VISUAL
depende_de: []
esforco_estimado_horas: 4
origem: docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-08.md (página 08)
mockup: novo-mockup/mockups/08-completude.html
---

# Sprint UX-V-2.3-FIX — Completude com eixos canônicos do mockup

## Contexto

Spec UX-V-2.3 declarou paridade mas o heatmap real continua com eixo Y de categorias de transação (Aluguel, Condomínio, Energia...). Mockup `08-completude.html` mostra eixo Y de **tipos de documento** (OFX bancos, Faturas cartão, Comprovantes Pix, NF serviços, Recibos).

A diferença é semântica: cobertura documental por mês, não cobertura categórica.

Resultado atual: Cobertura Global 0%, 852 lacunas críticas — números reflexo do eixo errado.

## Objetivo

1. Substituir agregação por categoria de transação por agregação por tipo de documento extraído (consultando `tipos_documento.yaml` + grafo SQLite).
2. Eixo Y = tipos de documento canônicos (5-7 tipos esperados/mês).
3. Eixo X = últimos 12 meses.
4. Cores: verde=completo, amarelo=parcial (~), vermelho=ausente (!).
5. Legenda chip-bar à direita do título: `completo · parcial · ausente`.

## Validação ANTES (grep)

```bash
grep -n "categorias\|aluguel\|condominio\|tipos_documento" src/dashboard/paginas/completude.py | head
ls mappings/tipos_documento.yaml
```

## Não-objetivos

- NÃO mexer nos 4 KPIs do topo (já implementados V-2.3 original).
- NÃO substituir agregação para sub-categoria.
- NÃO inventar dados quando documento não foi processado.

## Proof-of-work

```bash
make lint && make smoke
.venv/bin/pytest tests/ -k completude -q
```

Captura visual: heatmap mostra eixo Y com `OFX bancos / Faturas cartão / Comprovantes Pix / NF serviços / Recibos`, e legenda no header.

## Critério de aceitação

1. Eixo Y do heatmap mostra tipos de documento (não categorias de transação).
2. Cobertura Global recalcula com base nova e mostra valor real (não 0%).
3. Legenda chip-bar visível no header.
4. Símbolos `~`/`!` aparecem em células parciais/ausentes.
5. Lint + smoke + baseline pytest.

## Referência

- Spec original: `sprint_ux_v_2_3_completude.md`.
- Mockup: `08-completude.html`.

*"Cobertura é o que se prometeu menos o que está faltando — e isso depende de saber o que é unidade." — princípio V-2.3-FIX*
