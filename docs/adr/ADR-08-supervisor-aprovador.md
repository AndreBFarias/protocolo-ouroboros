# ADR-08: Arquitetura Supervisor-Aprovador

## Status: Aceita (atualizada 2026-04-29 pela Sprint META-SUPERVISOR-01)

> **Leitura obrigatória antes de codar qualquer coisa baseada neste ADR**: este texto foi redigido assumindo um cliente Python `anthropic` programático. **Essa premissa foi substituída por ADR-13** (Supervisor Artesanal via Claude Code). Sempre que este texto disser "LLM", entenda **"Opus principal nesta sessão Claude Code interativa"** — não há cliente API, não há cost_tracker, não há `src/llm/`. O ciclo Supervisor-Aprovador permanece: o supervisor (Opus) propõe via arquivos `.md` em `docs/propostas/`, humano aprova, regra YAML é mergeada. Para detalhes operacionais ver `docs/SUPERVISOR_OPUS.md`. Specs LLM-*-V2 em `docs/sprints/backlog/` implementam o ciclo sob essa nova premissa.

---

## Contexto

O projeto lida com dinheiro real. Qualquer decisão automatizada de um LLM sobre categorização, classificação de despesa, tag IRPF ou extração de CNPJ tem consequências financeiras e fiscais diretas. Ao mesmo tempo, o pipeline determinístico (regex + overrides) tem lacunas reais: ~15% das transações caem em `Outros + Questionável`, 21 regras IRPF hardcoded não cobrem todos os padrões, e o OCR de energia acerta só 67% do consumo em kWh.

Alternativas consideradas para incorporar LLM:
- **LLM decide direto no pipeline**: rápido de implementar, mas introduz não-determinismo, risco de alucinação em dado financeiro e inviabiliza auditoria.
- **LLM roda offline gerando um relatório só-leitura**: seguro, porém inócuo — cada insight precisa ser manualmente transcrito para as regras determinísticas.
- **LLM propõe, humano aprova, aprovação incorpora ao pipeline determinístico**: mais trabalho inicial, mas preserva determinismo, cria trilha de auditoria e faz o pipeline ficar incrementalmente mais capaz a cada aprovação.

## Decisão

Adotar arquitetura Supervisor-Aprovador. LLM **nunca** escreve direto em produção:

1. Supervisor (`src/llm/supervisor.py`) lê casos de borda (fallback, baixa confiança, anomalias) e grava proposições estruturadas em `mappings/proposicoes/YYYY-MM-DD_HHMM.yaml`.
2. Proposições obedecem schema Pydantic fechado (`SugestaoRegra`, `SugestaoOverride`, `SugestaoTagIRPF`, `AuditoriaClassificacao`) com campos obrigatórios `evidencia_local`, `ocorrencias`, `justificativa`, `confianca`.
3. Dashboard exibe página "Inteligência Pendente" com preview de 3 exemplos reais por proposição. Humano aprova/rejeita individualmente.
4. Aprovação incorpora a regra determinística a `categorias.yaml`, `overrides.yaml` ou `mappings/irpf_regras.yaml` via PR automático (ou commit local).
5. Rejeição guarda hash SHA-256 da proposição; supervisor não reapresenta o mesmo caso.

## Consequências

**Positivas:**
- Determinismo preservado: pipeline em produção continua sendo regex + YAML auditável
- Trilha de auditoria completa: cada regra nova tem timestamp de aprovação e proposição original
- Pipeline fica mais capaz a cada aprovação sem aumentar dependência do LLM
- Risco de alucinação isolado: proposição rejeitada não afeta dados
- Humano mantém soberania sobre decisões financeiras

**Negativas:**
- Exige interface de aprovação no dashboard (trabalho adicional de UX)
- Latência entre identificar padrão novo e incorporar ao pipeline (aguarda aprovação)
- Estado de rejeições precisa ser persistido para não repetir propostas

---

*"Confie, mas verifique." -- Ronald Reagan*
