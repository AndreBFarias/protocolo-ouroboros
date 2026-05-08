# Auditoria visual 2026-05-08 — Cluster Sistema/Inbox

## 14 — Skills D7 (sprint UX-V-2.8 — concluída)

**MIGUÉ identificado** (mesmo padrão de Rotina):

- Spec V-2.8 prometeu "5 KPIs no topo + Inventário 18 skills + Distribuição por estado + Cobertura por cluster".
- Dashboard cai em fallback de texto puro: "SKILLS D7 AINDA NÃO INICIALIZADO" + 4 KPIs (não 5) com `--`.
- Causa: `data/output/skill_d7_log.json` não existe — `./run.sh --tudo` não rodou nesta instalação.
- Fallback NÃO mostra skeleton-mockup do layout final como UX-V-03 prometeu (mockup tem inventário 18 skills, distribuição, cobertura por cluster).
- CSS dedicado `skills_d7.css` existe mas não é consumido (página entra em fallback antes).

**Classificação**: ALTA. V-2.8 igual Rotina: layout funcional só vai aparecer quando dado existir; spec assumia dado e não fez skeleton.

---

## 16 — Inbox (sprint UX-V-2 não tem; auditoria 2026-05-07 marcou BAIXA)

**OK**:
- 5 KPIs estruturados (Aguardando, Extraído, Falhou, Pulado, Total).
- Dropzone "Arraste arquivos aqui" + 9 chips de tipo (PDF, CSV, XLSX, OFX, JPG, PNG, HTML, TXT, JSON).
- Botão Upload + 200MB per file.
- Bloco "Fila" presente (vazio porque dados zerados — comportamento correto).

**Faltantes (cosmetics)**:
- Tag "CLUSTER NOVO" no header.
- Botões "Filtros" + "agrupar por sha8" só aparecem quando há dados na fila — não testados.

**Classificação**: BAIXA. Inbox OK estrutural; testar com dados reais é gate antes de validar fila.
