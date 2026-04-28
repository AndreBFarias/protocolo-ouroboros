# ADR-13: Supervisor Artesanal via Claude Code (sem API programática)

## Status: Aceita (atualizada 2026-04-28 com Sprint 108: automações encadeadas)

## Update 2026-04-28 (Sprint 108) -- Automações Opus em fluxo canônico

A decisão original "supervisor humano + Claude Code interativo" continua
vigente para CRIAÇÃO/REVISÃO de regras. Mas operações cíclicas que repetem
limpeza+migração+backfill foram extraídas para automação não-interativa.

`run.sh` ganhou helper `run_passo()` que encadeia comandos com falha-soft
e log estruturado em `logs/auditoria_opus.log`. Em `--full-cycle` e
`--reextrair-tudo`, a sequência roda sem intervenção humana:

```
[passo 0] inbox processing
[passo 1] dedup_classificar         (Sprint INFRA-DEDUP)
[passo 2] migrar_pessoa_via_cpf     (Sprint 105)
[passo 3] backfill_arquivo_origem   (Sprint 98a)
[passo 4] pipeline --tudo
```

Princípio canônico (q): "Automação no fluxo canônico OU não está resolvido".
Lições da fase Opus que viraram operação manual repetida são falsas
conclusões. Doc completo: `docs/AUTOMACOES_OPUS.md`.

## Contexto

A visão de 2026-04-19 expandiu o projeto para um "catalogador universal artesanal" onde o usuário joga qualquer arquivo do dia a dia (cupom fiscal, DANFE, XML NFe, recibo, receita médica, garantia, holerite, extrato, boleto, conta de luz, HEIC do celular) numa inbox e o sistema cataloga, extrai, linka e classifica tudo.

Parte essencial desse loop é o **supervisor**: alguém (ou algo) que lê cada arquivo original, compara com o output do pipeline determinístico, e propõe regras novas para `mappings/*.yaml` quando detecta discrepâncias. A Sprint 31 original previa esse supervisor como código programático que chamaria a Anthropic API com cliente Python `anthropic`, cache de prompts, cost tracker, retries, schemas Pydantic.

O usuário informou que:
- Assina Claude Max via browser
- Roda Claude Code (esta sessão) como ferramenta de trabalho
- Não quer chamadas programáticas à Anthropic API
- Quer o papel de supervisor desempenhado pelo próprio Claude Code atuando interativamente com ele

Alternativas avaliadas:
- **Cliente `anthropic` em produção:** maior overhead de infra (API key, cache, cost tracker, rate limits), introduz dependência remunerada separada da assinatura já paga.
- **LLM local (Ollama/llama.cpp):** qualidade insuficiente para leitura de NF/cupom e sugestão de regras; latência alta; infra ainda precisa de cache próprio.
- **Claude Code como supervisor interativo:** usa assinatura já existente, sem custo marginal; histórico das sessões fica no próprio projeto (logs + propostas); humano aprova proposta a proposta via conversa.

## Decisão

O supervisor artesanal é **workflow humano + Claude Code via browser**, não código programático. Consequências práticas:

1. **Nenhuma dependência Python `anthropic`.** `pyproject.toml` permanece sem essa lib.
2. **Nenhum `src/llm/`.** Nada de cliente, cache, cost tracker, schemas Pydantic remotos.
3. **Convenção de pasta `docs/propostas/`:** o Claude Code deposita propostas de regras novas como arquivos `.md` com frontmatter, diff e justificativa. O humano revisa e aprova.
4. **Script `scripts/supervisor_contexto.sh`:** dumpa estado atual do projeto em formato legível (stats do XLSX, pendências em `docs/propostas/`, últimas armadilhas, últimos commits) para que o Claude Code consiga se situar rapidamente no início de cada sessão sem ter que vasculhar a árvore toda.
5. **`docs/DIARIO_MELHORIAS.md`:** log cronológico de propostas aprovadas, rejeitadas e motivos. Memória de médio prazo.
6. **Cada sprint de feature exige seção "Conferência Artesanal Opus"** no arquivo `.md` da sprint — checklist do que o Claude Code deve ler, comparar e apresentar como relatório final antes da sprint ser fechada.

## Consequências

**Positivas:**
- Custo marginal zero (assinatura já paga).
- Auditabilidade máxima — cada proposta é um arquivo versionado no git.
- Loop de aprendizado claro: proposta → diff → revisão humana → merge → regra nova em `mappings/`.
- Simplicidade arquitetural: remove de uma vez cache, cost tracker, retries, schemas remotos.
- O sistema cresce em direção à autossuficiência — quando `mappings/*.yaml` cobrir tudo, o supervisor deixa de ser necessário.

**Negativas:**
- Processamento em lote não é automatizável (não dá para chamar Claude Code em batch via cron).
- Latência depende da disponibilidade humana (sessão precisa ser aberta).
- Se um dia o usuário cancelar Claude Max, o supervisor deixa de existir sem fallback automático — risco aceito explicitamente.
- Proposições ficam limitadas à janela de contexto do modelo usado na sessão.

## Relações com outras decisões

- **Substitui parte da Sprint 31 original** (Infra LLM + Supervisor Modo 1) — Sprint 31 vai para `arquivadas/` com ponteiro para Sprint 43 (Workflow Supervisor Artesanal).
- **Compatível com ADR-08 (Supervisor Aprovador):** aquele ADR define o ciclo "LLM propõe, humano aprova, pipeline determinístico absorve". Este ADR-13 especifica que o LLM é Claude Code interativo, não cliente programático.
- **Compatível com ADR-07 (Local First):** não adiciona dependência externa nova; tudo roda local mais a sessão do Claude Code.

---

*"A ferramenta melhor é aquela que já está na mão."* -- princípio de artesão
