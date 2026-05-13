# Padrões canônicos do projeto

Padrões canônicos do projeto -- letras `(a)..(ll)`. Cada padrão é uma lição empírica destilada. Specs e validações citam letra (ex: padrão `(k)`).

Versão trackeada (pública, sem PII). `VALIDATOR_BRIEF.md` local pode espelhar com anotações pessoais.

> **Fonte única dos padrões `(a)..(ll)` referenciados em `CLAUDE.md`, `docs/SUPERVISOR_OPUS.md` e specs de sprint.**
>
> Migrado de `VALIDATOR_BRIEF.md` (local, gitignored) em 2026-05-13 pela sprint META-VALIDATOR-BRIEF-TRACKEADO.

---

## Disciplina técnica

- **(a) Edit incremental, não rewrite** -- preserve histórico. Nunca apague código funcional sem autorização. Edit cirúrgico beats Write inteiro.
- **(b) Acentuação PT-BR completa** -- em código, commits, docs, comentários. `nao` -> `não`. `funcao` -> `função`. `concluida` -> `concluída`. Lint catch via `scripts/check_acentuacao.py`.
- **(c) Zero emojis** em código, commits, docs, respostas. Hook commit-msg bloqueia.
- **(d) Zero menções a IA** em commits e código (Claude, GPT, Anthropic). Hook bloqueia.
- **(e) `data/` no `.gitignore`** -- dados financeiros nunca no repo. PII (CPF/CNPJ pessoal) nunca em log INFO.
- **(f) Paths relativos via `Path`** -- nunca hardcoded absolutos.
- **(g) Citação de filósofo** como comentário final de todo arquivo `.py` novo.
- **(h) Limite 800 linhas por arquivo -- REVOGADA em 2026-05-12** (ver seção "Padrões revogados" abaixo).
- **(i) Sem `# TODO`/`# FIXME`** inline -- criar sprint-filha formal ou Edit-pronto.

## Workflow operacional

- **(j) Disciplina de worktree** -- sprint substantiva trabalha em worktree (`isolation: "worktree"`). Sempre `git rev-parse --show-toplevel` antes de cada commit.
- **(k) Hipótese da spec não é dogma** -- `grep` antes de codar. Se grep contraria a spec, escrever achado-bloqueio e consultar supervisor antes de prosseguir.
- **(l) Achado colateral vira sprint-filha OU Edit-pronto** -- nunca "TODO depois", nunca issue informal.
- **(m) Branch reversível** -- toda mudança não-trivial em branch isolada; commit atômico que pode `git revert`.
- **(n) Defesa em camadas** -- invariante crítica validada em >=2 lugares (ex: regex YAML + teste regressivo).
- **(o) Subregra retrocompatível** -- quando estende invariante, default mantém comportamento antigo.

## Supervisão

- **(p) Supervisor valida pessoalmente** -- você lê diff, roda proof-of-work, julga aprovado/ressalvas/reprovado. NÃO despache `validador-sprint` por reflexo. Subagent só entra quando trabalho é >5min, isolado e verificável por amostragem.
- **(q) Plano antes de agir** -- para mudança >3 passos, escrever plan + apresentar antes de codar. ExitPlanMode é o gate.
- **(r) Auto-aprovação proibida** -- sprint-filha redigida pelo executor não pode ser auto-aprovada por ele mesmo.

## Spec/documentação

- **(s) Specs com "Validação ANTES" obrigatória** -- grep que confirma hipótese antes de codar. Sem isso, sprint nasce frágil.
- **(t) Specs com "Não-objetivos" explícitos** -- fechar escopo evita creep dentro da execução.
- **(u) Specs com "Proof-of-work runtime-real"** -- comando `python -m ...` ou `./run.sh ...` que mostra efeito esperado em dados reais.
- **(v) Spec retroativa** -- se sprint fechou direto via commit sem spec, criar retroativa em `concluidos/` com `concluida_em: YYYY-MM-DD` + link commit.

## Anti-padrões proibidos

- **(w) JS runtime global afetando todas páginas** -- `setProperty('important')` em seletores Streamlit genéricos (`stColumn`, `stVerticalBlock`) afeta TODAS as páginas. Preferir CSS estático escopado (UX-M-04). Caso de erro: commit `928628c` (revertido em `2817706`).
- **(x) Monolito sem subdivisão** -- sprint que mexe em >1 cluster ou >5 arquivos sem dividir é REPROVADA por escopo creep.
- **(y) Validação cosmética** -- "rodei e está bom" sem proof-of-work é auto-engano. Sempre log literal.

## Convenções específicas

- **(z) Gate 4-way operacional** -- para extrator novo, `make conformance-<tipo>` >=3 amostras verdes é hard gate antes de mover spec para `concluidos/`.
- **(aa) Cobertura total D7** -- extrair tudo dos arquivos (PDF, imagem, XML, CSV) e catalogar cada valor. Sem amostragem, sem filtro silencioso.
- **(bb) PII em 4 sítios** -- quando mascarar PII (CPF/CNPJ/email), aplicar nos 4 sítios canônicos: UI, dataframe, export, log INFO.
- **(cc) Refactor revela teste frágil** -- se seu fix expõe bug em teste regressivo antigo, abrir sprint-filha (não tente "consertar" sem spec).
- **(dd) Stash chain hazard** -- agente background com worktree compartilhado que faz `git stash` pode dropar trabalho do supervisor. Solução: forçar `cd $WORKTREE` antes de cada Bash; nunca usar paths absolutos para o main; nunca `git stash` sem `git stash pop` na mesma rodada. (Descoberto em 2026-05-12 -- sessão Fase A.)
- **(ee) Schema-extension precede validation** -- nunca crie test ou fixtures que dependam de schema antes do schema estar gravado e validado. (Sessão 2026-05-12.)
- **(ff) Auditoria automática vs supervisor** -- auditoria automática lê texto da spec; supervisor lê texto contra grep no código real. Discrepância prova que padrão (s) "Validação ANTES" só funciona se executado. (Sessão 2026-05-12: Explore deu 9 PRONTAS/5 REVISAR; supervisor manual deu 7/6/1 -- corrigiu 30%.)
- **(gg) Cache sintético é placeholder honesto** -- quando cache OCR/extração admite em `_observacao` que foi gerado para "cobrir" um total mas com dados extrapolados, NÃO consumir como gabarito. ETL que delega a cache sem revalidar contra fonte primária amplifica placeholder a fato. (Sessão 2026-05-12: cache `cupom_fiscal_foto` da Sprint INFRA-OCR-OPUS-VISAO era sintético; ETL "concordava 100%" mas divergia 100% da realidade.)
- **(hh) Ingestão dupla OFX+XLSX escapa dedup** -- quando 2 fontes (OFX nativo + XLSX exportado) do mesmo banco/extrato têm campo `local` estruturalmente diferente (prefixo bancário OFX vs limpo XLSX), `deduplicar_por_hash_fuzzy` falha silenciosamente. Solução: normalizar prefixos antes da chave + pass 2b por `_arquivo_origem`. (Sessão 2026-05-12: 253 pares no C6 = 43% do banco.)

## Padrões 2026-05-13

- **(ii) Comandos git banidos por incidente** -- `git stash` (qualquer variante), `git reset --hard`, `git clean -fd`, `git checkout -f`, `rm -rf` em subdirs do worktree, `git config --global`. Banidos pelo Protocolo Anti-Armadilha v3.1 (`contexto/PROTOCOLO_ANTI_ARMADILHA_V3_1.md`) após incidente 2026-05-13 (executor `abdbc7a7` rodou `git stash --keep-index -u --quiet`, perdeu working tree, reconstruiu 690L da memória conversacional). Substitutos canônicos no protocolo. Verificação obrigatória antes de commit final: `git stash list` deve estar vazio.
- **(jj) Dossiê obrigatório antes de código** -- toda sprint que toca um tipo documental EXIGE que o supervisor Opus principal tenha gerado `prova_artesanal_<sha256>.json` no dossiê (`data/output/dossies/<tipo>/`) ANTES de despachar executor. Ritual canônico em `docs/CICLO_GRADUACAO_OPERACIONAL.md`. CLI: `scripts/dossie_tipo.py --prova-artesanal <tipo> <sha256>`. Sem prova, executor pode produzir código "tecnicamente correto" mas semanticamente errado (e.g. cupom NSP onde teste afirmava `soma == total` mas cupom real tem 2 colunas distintas). Padrão formalizado 2026-05-13.
- **(kk) Sprint encerra com produto final** -- sprint que toca tipo documental NÃO se encerra só com código + testes; encerra apenas quando `dossie_tipo.py --comparar` retorna `GRADUADO_OK` (ou registra DIVERGENTE com sprint-filha automática). Não existe "fechamento posterior" -- veredito sai no momento. Padrão 2026-05-13.
- **(ll) Re-trabalho em loop fechado** -- quando `--comparar` retorna `DIVERGENTE`, o relatório em `data/output/dossies/<tipo>/divergencias/<sha256>_<ts>.md` já contém brief executável para a sprint-filha de fix. Executor próximo recebe o relatório como input, não precisa re-investigar. Anti-débito automático.

---

## Padrões revogados

- **(h) Limite 800 linhas por arquivo** -- REVOGADA em 2026-05-12 (decisão do dono). Tamanho de arquivo não é mais critério de validação. Splits seguem critério de legibilidade humana, não regra fixa.

---

*"Padrão é lição empírica destilada. Quem não tem padrão repete o erro." -- princípio do validador*
