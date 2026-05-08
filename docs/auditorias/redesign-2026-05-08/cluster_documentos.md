# Auditoria visual 2026-05-08 — Cluster Documentos

## 06 — Busca Global (sprint UX-V-2 não tem; precisa V-3.2)

**OK**: search-bar canônica + chips Tipos rápidos.

**Faltantes vs mockup**:
- Counters no subtítulo (`439 documentos, 2.847 transações, 1.284 sidecars`).
- Facet-card lateral com TIPO/PERÍODO/CONTA/CATEGORIA + counts.
- Grupos de resultados (TRANSAÇÕES + DOCUMENTOS) com snippet highlight `<mark>`.

**Classificação**: MÉDIA. Confirma UX-V-3.2-BUSCA-FACET.

---

## 07 — Catalogação (sprint UX-V-2 não tem; precisa V-3.3)

**MIGUÉ DE ROTEAMENTO CRÍTICO**: navegando para `?tab=Catalogac%C3%A3o` o conteúdo renderizado é **a página Busca Global** (mesmo título "BUSCA GLOBAL", mesmos chips Tipos rápidos). Apenas o breadcrumb dinâmico mostra "DOCUMENTOS / CATALOGAÇÃO".

Isso é bug funcional, não cosmético. A função `renderizar` da página Catalogação ou a tabela de roteamento em `app.py` está apontando errado.

**Mockup mostra**: grid 2x6 de thumbs com badges PDF/IMG/CSV/XLSX/OFX + sidebar lateral 3 facetas (TIPO/PERÍODO/FONTE com counts) + counter "12 de 439".

**Classificação**: ALTÍSSIMA. Sub-sprint imediata: UX-V-3.3-CATALOGACAO-FIX-ROTA.

---

## 08 — Completude (sprint UX-V-2.3 — concluída)

**MIGUÉ ALTO**: V-2.3 declarou paridade mas só implementou 4 KPIs no topo. Eixos do heatmap continuam errados:

- Eixo Y dashboard = **categorias de transação** (Aluguel, Condomínio, Educação, Energia, Farmácia, …).
- Eixo Y mockup = **tipos de documento** (OFX bancos, Faturas cartão, Comprovantes Pix, NF serviços, Recibos).

Isso muda completamente a semântica da feature. Cobertura mostra 0% / Lacunas 852 — números refletem o eixo errado.

Faltantes adicionais:
- Legenda visível "completo · parcial · ausente" (mockup tem chip-bar à direita do header).
- Símbolos `~` para parcial e `!` para ausente nas células (mockup tem; dashboard tem `!` mas inconsistente).

**Classificação**: ALTA. Precisa sprint UX-V-2.3-FIX-EIXOS.

---

## 09 — Revisor (sprint UX-V-2 não tem; auditoria 2026-05-07 marcou INVESTIGAR)

**Capturado via playwright (claude-in-chrome bloqueia iframe).**

**Mockup mostra arquitetura 4-way**:
- Lista lateral esquerda com transações (pílulas APURADO/DIVERGENTE/RASCUNHO + confiança%).
- Centro: 4 cards lado-a-lado para a transação selecionada: OFX banco (read-only) | RASCUNHO ETL | OPUS agentic | HUMANO (inputs editáveis).
- Tabs no topo: Mês atual / Só divergentes / Só rascunhos / Apurado.
- Rodapé com tabs Detalhes / Auditoria do Opus / Histórico / Hints + trace de raciocínio.
- Tag "APURAÇÃO 2026 · 15 TRANSAÇÕES · 2 DIVERGENTES".

**Dashboard real**:
- 4 KPIs (Pendências 29 / Revisadas 3 / Aguardando 26 / Fidelidade 0%).
- Sub-bloco "COMPARAÇÃO ETL × OPUS (0 DIVERGENTES de 296 marcações)" — sem dados de Opus pelo mesmo motivo de V-2.4.
- Filtro Tipo de pendência (chips grafo_sem_link, raw_classificar, raw_conferir) + paginação.
- **AUSENTE** o layout 4-pane por transação (essência da feature segundo mockup).
- **AUSENTE** tabs filtro por período.
- **AUSENTE** trace de raciocínio.

**Classificação**: ALTA. Precisa sprint UX-V-4-REVISOR para reescrever layout 4-pane. Bloqueada parcialmente por V-2.4-FIX (Opus precisa rodar).
