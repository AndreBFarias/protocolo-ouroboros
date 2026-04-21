# VALIDATOR_BRIEF — protocolo-ouroboros

> Memória acumulada do validador. Versionada no repo. Atualizada pelo subagente `validador-sprint` quando detecta padrão novo. Não editar manualmente sem registrar no rodapé.

## [CORE] Identidade

- Nome: protocolo-ouroboros
- Linguagem principal: Python 3.11+
- Framework/stack: pdfplumber + pandas + openpyxl + SQLite (grafo) + Streamlit (dashboard) + pytest
- Propósito (1 linha): pipeline ETL financeiro pessoal (casal) com grafo de conhecimento SQLite, 6 bancos, 82 meses, supervisor Claude Code
- Tipo-de-projeto (para validação visual): cli <!-- tui | gui | web | cli | lib | docs -->

## [CORE] Como rodar

- Smoke (boot ok <5s): `./run.sh --check` (23 checagens de dependências/dirs/mappings; flag `--smoke` NÃO existe -- usar `--check`)
- Testes unitários: `.venv/bin/pytest tests/ -q`
- Integração / gauntlet (se existir): `bash scripts/finish_sprint.sh NN` (NN = número da sprint)
- Lint / format: `make lint` (roda `ruff check` + `ruff format` + `scripts/check_acentuacao.py --all`)
- TUI / GUI run (se aplicável): `./run.sh --dashboard` (Streamlit, porta 8501) -- CLI puro para pipeline

## [CORE] Arquitetura essencial

<!-- 5-10 componentes. Nome + responsabilidade em 1 linha + arquivo principal. Ex:
- AgentLoop — loop principal de inferência, `src/agent/loop.py`
- ToolRegistry — registro central de tools, `src/tools/registry.py`
-->

## [CORE] Checks universais ativados

Matriz das 14 lições empíricas dos 3 projetos (Luna, Nyx-Code, protocolo-ouroboros). Marque "sim/não" por check, conforme aplicável a este projeto. O validador usa esta tabela para decidir o que validar.

| # | Check | Origem | Aplicável aqui? | Comando de teste |
|---|---|---|---|---|
| 1 | Runtime real (não CLI/pytest puro) | Luna feedback_always_test_tui | sim | `./run.sh --smoke` |
| 2 | Screenshot UI automático | Luna Sprint 09 | sim | skill validacao-visual |
| 3 | Acentuação periférica | Luna AUD-03 FEN-11 | sim (PT-BR) | `python3 ~/.config/zsh/scripts/validar-acentuacao.py` |
| 4 | Hipótese do revisor empírica | Luna AUD-03 FEN-01d | sim | `rg` antes de aplicar fix |
| 5 | Fix inline vs pular | Luna feedback_fix_inline_never_skip | sim | protocolo explícito |
| 6 | Zero follow-up | Luna + Nyx | sim | Edit-pronto OU sprint-ID |
| 7 | Aritmética de refactor | Luna INFRA-83 ORFEU | sim | `wc -l` + projeção |
| 8 | Plano antes de código | Luna + Nyx feedback_plan_before_sprint | sim | `/planejar-sprint` sempre |
| 9 | Nenhum débito fica pra trás | Nyx feedback_nenhum_debito | sim | `SPRINT_ORDER_MASTER.md` |
| 10 | Sprints divididas e profundas | Luna feedback_split_sprints_deep | sim | rejeitar monolítica |
| 11 | Integração obrigatória (nada solto) | Nyx ADR-013/014 | sim | registry/command/service |
| 12 | Smoke boot real | Nyx BOOT-FIX-01 check #13 | sim | `./run.sh --smoke` |
| 13 | Sprint CONCLUÍDA = Gauntlet | Luna ADR-017 | sim | gauntlet por fase |
| 14 | Opus centro de inteligência | Luna feedback_opus_review_center | sim | validador-sprint é esse |

## [CORE] Contratos de runtime

Comandos canônicos (existem e foram testados neste projeto):

- Smoke: `./run.sh --check` (flag `--smoke` não existe neste projeto)
- Unit tests: `.venv/bin/pytest tests/ -q` (baseline Sprint 44: 319 passed, 8 skipped)
- Integração: `bash scripts/finish_sprint.sh NN`
- Gauntlet: `bash scripts/finish_sprint.sh NN`
- Validar acentuação (global, sensível): `python3 ~/.config/zsh/scripts/validar-acentuacao.py --paths <arq1> <arq2> ...`
- Validar acentuação (oficial do projeto, contextual): `.venv/bin/python scripts/check_acentuacao.py --all`
- Lint: `make lint`

## [CORE] Arquivos periféricos (onde acentuação escapa)

Paths onde acentuação historicamente escapa da auto-revisão. O validador (check #3) varre esses além do core funcional.

- `<path:linha>` — citação filosófica (CLAUDE.md §12)
- `<glob>` — docstrings de teste (ex: `tests/**/*.py`)
- `<glob>` — comentários ornamentais
- `<glob>` — f-strings que não são input direto

## [CORE] Heurísticas de aritmética

- Meta de linhas por arquivo: 800 (ex: 800)
- Exceções autorizadas: config/, testes/, registries/ (ex: config/, testes/, registries/)
- Comando de verificação: `find src -name '*.py' -exec wc -l {} \\; | awk '$1>800'`

## [CORE] Capacidades visuais aplicáveis

- Tipo-de-projeto: cli (TUI/GUI/Web/CLI)
- Stack visual: <a preencher> (ex: Textual, GTK, React, etc.)
- Como capturar screenshot:
  - Ferramenta primária: `<a preencher>` (ex: `bash scripts/tui_tests/capture.sh`)
  - Fallback secundário: scrot + claude-in-chrome MCP + playwright MCP (scrot / claude-in-chrome MCP / playwright MCP)
- Critérios de validação (se há): `<a preencher ou omitir>`

## [OPCIONAL] Padrões recorrentes de bug

- **Acentuação em identificadores técnicos é aceita.** O projeto usa chaves de dict (`"codigo"`, `"descricao"`, `"ncm"`, `"periodo"`, `"historico"`), named-groups de regex (`(?P<descricao>...)`), parâmetros (`diretorio: Path`) e variáveis locais (`historico = ...`) sem acento por coerência N-para-N com o schema do grafo (`src/graph/ingestor_documento.py`). O checker oficial (`scripts/check_acentuacao.py`) já trata isso contextualmente e passa; o checker global (`validar-acentuacao.py`) sinaliza falsos-positivos nesses casos. **Regra do validador: só considerar PONTO-CEGO se a violação aparece em texto PT-BR humano (docstring, comentário, string de log, citação filosófica) -- nunca em chave/parâmetro/variável que participa de contrato entre módulos.**
- **Reuso de função shared quando spec pede criar.** Sprint 44 pediu criar `ingerir_documento` em `src/graph/ingestor_documento.py`. Função `ingerir_documento_fiscal` com contrato equivalente (nodes documento/fornecedor/itens/periodo + arestas `fornecido_por`/`contem_item`/`ocorre_em`, idempotente) já existia desde sprints 44b/47c prévias. Reuso é legítimo e preferível a duplicar. Validador aceita como ressalva se: (a) ambos contratos cobrem mesmos nodes/edges, (b) dict `documento` do extrator inclui `tipo_documento` equivalente ao parâmetro separado do spec, (c) testes do grafo validam contagens precisas.
- **`_parse_valor_br` redefinido localmente é o padrão do projeto.** Sete extratores redefinem essa função em vez de importar de um módulo comum: `itau_pdf.py:207`, `santander_pdf.py:357`, `contracheque_pdf.py:55`, `cupom_garantia_estendida_pdf.py:513`, `danfe_pdf.py:572`, `nfce_pdf.py:539`, `cupom_termico_foto.py:296`. Contrato idêntico (`str | None -> float | None`, trata `1.234,56`). Validador aceita redefinição local em novos extratores como padrão — NÃO é débito. Refactor para `src/utils/parse_br.py` é candidato a sprint INFRA futura (escopo 7 arquivos, 7 × ~8L = ~55L removidos), mas nunca exigência bloqueante de sprint-feature.
- **Fallback supervisor não-idempotente.** Rotas que criam `<uuid>/` + proposta MD quando OCR/recall abaixo do limiar (cupom_termico_foto `_registrar_fallback_supervisor`, qualquer nova rota semelhante) devem derivar o identificador do `cache_key(caminho)` ou `sha256(conteudo)[:12]` — nunca de `uuid.uuid4()` puro. Reprocessamento recorrente multiplica propostas se identificador for aleatório. Ingestão aprovada no grafo já é idempotente por `chave_44` sintética; simetrizar a rota de fallback é obrigatório para não acumular lixo em `docs/propostas/*` a cada rodada do cron.
- **Aritmética de recall = Σ(item.valor_total) / cupom.total.** Fixtures texto dos cupons devem ter soma exata dos itens = total do cupom (recall 100%) para que o teste de acceptance "recall ≥80%" tenha folga e os testes do extrator validem de fato o parser, não a tolerância. Validador confere aritmética fixture por fixture (bate com `grep "R$" + soma) antes de aceitar.

## [OPCIONAL] Invariantes não-óbvios

<!-- Omitir se vazio. -->

## [OPCIONAL] Decisões arquiteturais chave

<!-- ADRs, decisões de design que não estão documentadas em ADR. -->

## [OPCIONAL] Gambiarras conhecidas / antipatterns

<!-- Com justificativa histórica do porquê estão lá. -->

## [OPCIONAL] Cheiros específicos do projeto

<!-- Sinais de alerta típicos. -->

## [OPCIONAL] Histórico de sprints relevantes

- SPRINT-44 — Extrator DANFE NFe55 (586L, 31 testes, reusou `ingerir_documento_fiscal` pré-existente em vez de criar `ingerir_documento` — contrato equivalente, aceito como ressalva). Acceptance "CNPJ emissor bate com chave" ficou PARCIAL: cross-check texto × chave não foi implementado. Introduziu warning I001 em `src/extractors/danfe_pdf.py:46-64` que bloqueia `make lint` global — fix determinístico via `ruff --fix` deixado como ressalva herdada para commit separado.
- SPRINT-44b — NFC-e modelo 65 (proxima, escopo dividido da 44 pela diferença de layout).
- SPRINT-45 — Extrator cupom fiscal térmico fotografado (678L extrator + 279L OCR util + 717L testes + 83L regex YAML, 63 testes, baseline 320 → 383 passed +63 sem regressão). 4 layouts (Americanas, Mercado genérico, Farmácia, Posto) com recall aritmético 100% em fixtures `.txt`; round-trip real em JPG 527KB cobre EXIF via `@pytest.mark.slow`. Aceito APROVADO_COM_RESSALVAS. Achados registrados: (1) I001 pré-existente em `danfe_pdf.py` da Sprint 44 (commit separado pós-45 com `ruff --fix`), (2) `test_cupom_com_rotacao_exif_reconhece` não valida dimensão-transposta com EXIF=6 (minúcia), (3) fallback supervisor não-idempotente por usar `uuid.uuid4()` em vez de `cache_key()` (minúcia, sprint-prompt pronta).
- SPRINT-42 — Grafo SQLite com 7.378 nodes, 24.506 edges. Schema define chaves de dict em PT-sem-acento (`"transacao"`, `"periodo"`, `"descricao"`) — é N-para-N obrigatório em todos os extratores/ingestores que consomem o grafo.

## [OPCIONAL] Perfis / ambientes

<!-- Ex: Ryzen 5 7535HS + RTX 3050 4GB para Luna (limites de VRAM). -->

---
*Atualizado em 2026-04-20T19:19:40 por bootstrap-rico-brief.py (modo bootstrap_rico, 0 memórias lidas)*
*Atualizado em 2026-04-20 por validador-sprint (modo VALIDATE, Sprint 44): preencheu CORE (Identidade, Como rodar, Contratos de runtime) com evidência empírica do repo; adicionou 2 padrões recorrentes de bug (acentuação em identificadores técnicos; reuso de função shared); registrou SPRINT-44/44b/42 em histórico relevante.*
*Atualizado em 2026-04-20 por validador-sprint (modo VALIDATE, Sprint 45): adicionou 3 padrões recorrentes (`_parse_valor_br` redefinido localmente é padrão do projeto em 7 extratores; fallback supervisor deve usar `cache_key`/hash-conteúdo, nunca `uuid.uuid4()` puro; aritmética de recall validada fixture-por-fixture); registrou SPRINT-45 em histórico com 3 achados (I001 herdado, EXIF test fraco, fallback não-idempotente); anotou I001 em `danfe_pdf.py` como ressalva herdada Sprint 44 para commit separado.*

## [OPCIONAL] Regras especiais deste projeto

- Claude Code é o supervisor (sem API programática)
- Fases ALFA/BETA/GAMA/DELTA/EPSILON/ZETA
- Grafo SQLite + extração granular em mappings/
- ADRs 13/14/15 em docs/adr/

## [OPCIONAL] Template de bootstrap específico

Template do projeto em `~/.claude/templates/bootstrap-ouroboros.md`.
Contém estrutura recomendada + padrões conhecidos. Leia para enriquecimento manual.
