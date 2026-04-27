# Auditoria estrutural READ-ONLY -- `~/Controle de Bordo/`

Para alimentar o ADR-21 (`docs/adr/ADR-21-fusao-ouroboros-controle-bordo.md`) e o relatório `docs/AUDITORIA_2026-04-26.md`. Coletado em 2026-04-26 sem qualquer escrita no vault.

**Origem:** subagente Opus (general-purpose) executou auditoria. Modelo: `opus`. Duração: ~6.5 min. Tool calls: 54.

**Validação dos claims-chave (eu, supervisor):**
1. OK `git log --oneline` confirma 1 único commit (`40b8afe`); `git remote -v` vazio.
2. OK 3 duplicatas SHA-idênticas raiz vault vs `protocolo-ouroboros/docs/` (`QUESTIONARIO_VIDA_COMPLETO.md` `854c11673475`, `PLANO_FINANCEIRO_2026.md` `81239de4ff07`, `PLANO_FINANCEIRO_ANDRE_VITORIA.md` `a76658b4bf67`).
3. OK 76/76 .tsx/.ts estão em `.sistema/backups/`.
4. OK `Pessoal/Casal/Financeiro/{Documentos,Fornecedores,Meses,_Attachments}/` populado, mtime 2026-04-23 18:24.
5. OK `ocr_detector.py:39` referencia path obsoleto `~/Desenvolvimento/Financas/`.

---

## 1. Sumário executivo

| Métrica | Valor |
|---|---|
| Tamanho total | 325 MB |
| Notas Markdown (.md) | 1.439 |
| Scripts Python total | 175 |
| Scripts Python **vivos** (fora de `Arquivo/` e `backups/`) | **34** (19 ativos `.sistema/scripts/` + lib, 6 desativados, 9 espalhados) |
| TS / TSX | 76 -- **100% backups inertes** de `Nyx-Code/openclaud` em `.sistema/backups/2026-04-08/` |
| Anexos `_Attachments/` (raiz) | 36 imagens |
| Anexos `Pessoal/Casal/Financeiro/_Attachments/` | 4 PDFs (boletos + NFC-e produzidos pelo Ouroboros) |
| Notas geradas pelo `sync_rico.py` (Sprint 71) | 11 (Mês 2026-04 + 4 Documentos + 2 Fornecedores + 7 Metas + Relatórios pré-existentes) |
| Repositório git | Sim, 1 único commit (`40b8afe`) sem remoto |
| Obsidian Sync | NÃO -- `.obsidian/sync.json` ausente |
| `.syncignore` | Sim |

**Conclusão de uma frase:** o vault tem ~30 scripts Python vivos no `.sistema/`, todos AUXILIARES-DO-VAULT ou MOTOR-PARALELO ao intake do Ouroboros. Os 76 .tsx/.ts são lixo de backup. O alvo da Sprint 71 (`Pessoal/Casal/Financeiro/`) está vivo, foi populado no último ciclo (2026-04-23) e funciona. Não existe nenhum código de fluxo financeiro no vault que o Ouroboros já não cubra. A fusão é viável e relativamente barata.

## 2. Árvore estrutural top-3-níveis

```
Controle de Bordo/                                              325M
├── Agents.md                          .md raiz (regras, 194L)
├── Estrutura.md                       .md raiz (127L)
├── home.md                            .md raiz (dashboard root, 197L)
├── LAYOUT_PAGINAS.md                  .md raiz (231L)
├── Painel de Controle - Backlog ...md .md raiz (110L)
├── PLANO_FINANCEIRO_2026.md           DUPLICATA SHA-IDÊNTICA do ouroboros/docs/
├── PLANO_FINANCEIRO_ANDRE_VITORIA.md  DUPLICATA SHA-IDÊNTICA
├── QUESTIONARIO_VIDA_COMPLETO.md      DUPLICATA SHA-IDÊNTICA
├── _Attachments/                      6.9M     [ANEXOS, raiz Obsidian]
├── Inbox/                              16K     [4 notas .md trazidas pelo casal]
├── Diario/                            352K     [~50 daily notes 12/2025-04/2026]
├── Conceitos/                         448K     [+ 1 .py + 11 .sh utilitários]
├── Pessoal/                            20M
│   └── Casal/Financeiro/              <- ALVO DO sync_rico.py (Sprint 71) -- 63 arquivos
├── Trabalho/                           24M     [Energisa + G4F + MEC]
├── Projetos/                           12M
│   └── Protocolo Ouroboros/            <- CLONE PARCIAL DESATUALIZADO (CLAUDE.md SHA divergente)
├── Arquivo/                           159M     [DEPÓSITO PESADO -- gitignored, syncignored]
└── .sistema/                           27M     [CÓDIGO + DOCS + BACKUPS]
    ├── backups/                         76 .tsx + dezenas de .py de OUTROS projetos
    ├── scripts/                         14 vivos + gauntlet/ + _desativados/
    ├── lib/                             5 módulos compartilhados
    └── templates/, hooks/, config/, devices/, health/, inbox_processor/
```

## 3. Inventário de código no vault

### 3.1. Scripts vivos (`.sistema/scripts/` + `.sistema/lib/`)

| Arquivo | Linhas | Categoria | Descrição |
|---|---:|---|---|
| `inbox_processor.py` | 492 | MOTOR-PARALELO | Pipeline orchestrate: vê notas .md em `Inbox/`, chama detect+similar+OCR+create. Equivalente alto-nível ao `src/intake/orchestrator.py` do Ouroboros |
| `content_detector.py` | 386 | MOTOR-PARALELO | Classifica destino de NOTA por keywords + frontmatter; usa `regras.yaml`. Análogo ao `classifier.py` do Ouroboros mas opera em texto livre |
| `ocr_detector.py` | 410 | MOTOR-PARALELO | OCR pytesseract para 5 tipos (nota-fiscal, recibo, conta-energia, boleto, outros) -- subset minúsculo dos 25 do Ouroboros. **Path hardcoded `~/Desenvolvimento/Financas/`** -- bug |
| `document_creator.py` | 277 | MOTOR-PARALELO | Cria nota .md com frontmatter a partir de `DetecçãoDocumento`. Concorrente parcial do `sync_rico.py` |
| `similarity_grouper.py` | 230 | **COMPLEMENTAR** | Jaccard sobre bag-of-words. **Funcionalidade que o Ouroboros NÃO tem.** Útil para deduplicar notas livres |
| `health_check.py` | 451 | AUXILIAR | Diagnóstico de saúde do vault: tamanho, tags, emojis, links quebrados |
| `emoji_guardian.py` | 376 | AUXILIAR | Detector + removedor de emojis. Útil cross-projeto (Ouroboros tem regra inviolável) |
| `vault_backup.py` | 254 | AUXILIAR | Backups incrementais |
| `verificar_consistencia.py` | 275 | AUXILIAR | Links quebrados, órfãos, duplicatas, tags |
| `verificar_obsidian.py` | 224 | AUXILIAR | `.obsidian/*.json` contra config esperado |
| `verificar_conflitos.py` | 239 | AUXILIAR | Sufixos de conflito de sync |
| `export_to_other_devices.py` | 346 | AUXILIAR | Gera `.syncignore` por dispositivo |
| `vault_logger.py` | 68 | AUXILIAR | Logger Dracula compartilhado |
| `gauntlet/gauntlet.py` | 1.300+ | AUXILIAR | Validador 8-fases do vault. Mesmo nome do `make gauntlet` do Ouroboros mas valida coisa diferente |
| `lib/config_loader.py` | 135 | AUXILIAR | Singleton de carga de YAMLs |
| `lib/safe_io.py` | 252 | AUXILIAR | I/O seguro com backup automático |
| `lib/wikilinks.py` | 188 | **COMPLEMENTAR** | Busca/atualiza `[[wikilinks]]`. **Ausente no Ouroboros.** Útil para `sync_rico.py` |
| `lib/protecao.py` | 100 | AUXILIAR | Decorator `@verificar_antes_de_modificar` |

### 3.2. Scripts desativados (`.sistema/scripts/_desativados/`)

6 protótipos abandonados: `automatizar_vault.py`, `inbox_processor.py` (versão antiga), `padronizar_documentos.py`, `renomear_arquivos.py`, `renomear_imagens.py`, `sanitizar_ia.py`.

### 3.3. Outros .py espalhados

- `Conceitos/Claude/Claude-templates/hooks/check_acentuacao.py` -- AUXILIAR (hook reutilizável)
- `Conceitos/Claude/Claude-templates/hooks/fix_acentuacao.py` -- AUXILIAR (hook reutilizável)
- `Conceitos/Programacao/Pop-OS-Nitro-5-Linux-Utilitarios/src/font_config.py` -- OFF-TOPIC
- `Trabalho/Vitoria/MEC/Documentacao/Scripts/plataforma-freire.py` -- OFF-TOPIC
- `Trabalho/Vitoria/MEC/Documentacao/Para-Documentar/Docs-Para-Contexto-Não-Mexer/run.py` -- OFF-TOPIC

### 3.4. .ts/.tsx (76)

**Todos os 76 estão em `.sistema/backups/2026-04-08/18-45-33__home_andrefarias_Desenvolvimento_Nyx-Code_openclaud_*`** -- snapshots de outro projeto (Nyx-Code/openclaud). PROTÓTIPO/MORTO. Lixo de backup, não código vivo.

## 4. Comparação detalhada: motor de inbox do vault x intake do Ouroboros

| Capacidade | Vault | Ouroboros | Vencedor |
|---|---|---|---|
| Detecção tipo por regex em conteúdo | `content_detector.py` -- texto livre | `classifier.py` + `tipos_documento.yaml` -- 25 tipos | **Ouroboros** |
| Detecção por OCR | `ocr_detector.py` -- 5 tipos doc | `preview.py` + envelope + cupom_termico_foto | **Ouroboros** (cobre 25 tipos) |
| Detecção de pessoa | `content_detector.py` via hostname | `pessoa_detector.py` -- 3 camadas (CPF + pasta + fallback) | **Ouroboros** |
| Agrupamento por similaridade (Jaccard) | `similarity_grouper.py` -- 230L | -- | **Vault** (única feature exclusiva útil) |
| Movimentação atômica cross-mount | `lib/safe_io.safe_move` | `router.py` + envelope `_originais/` | Empate |
| Page-split de PDF heterogêneo | -- | `extractors_envelope.expandir_pdf_multipage` | **Ouroboros** |
| ZIP/EML expand | -- | `extractors_envelope` | **Ouroboros** |
| Geração de nota Markdown | `document_creator.py` -- por arquivo | `sync_rico.py` -- por node do grafo | Complementares |
| Idempotência | -- | Hash do conteúdo + `sincronizado: true` | **Ouroboros** |
| Soberania humana | -- | `sync_rico.py` pula se tag/frontmatter ausente | **Ouroboros** |

**Vault faz melhor / único:**
1. `similarity_grouper.py` (Jaccard) -- migrar.
2. `emoji_guardian.py` (scanner emoji) -- migrar como hook.
3. `lib/wikilinks.py` -- migrar.
4. `gauntlet/gauntlet.py` (vault-specific) -- mantém.
5. `Conceitos/Claude/Claude-templates/hooks/{check,fix}_acentuacao.py` -- já alinha com Ouroboros.

**Ouroboros faz melhor / único:**
1. Tudo financeiro (25 tipos vs 5).
2. Page-split, ZIP/EML, rotação EXIF, glyph-tolerant.
3. Detecção pessoa em 3 camadas.
4. Idempotência por hash + envelope auditoria.
5. Sync rico do grafo para o vault.

## 5. Inventário de notas .md por bucket PARA

| Bucket | Total | Frescos (mtime >= 2026-04) |
|---|---:|---|
| `Inbox/` | 4 | sim |
| `Diario/` (2026/, Retrospectivas/) | ~50 | sim |
| `Conceitos/` (Claude/, Programacao/, Prompts/) | ~30 + 11 .sh + 1 .py | parcial |
| `Pessoal/` | 69 | sim (Casal/Financeiro/ é o alvo do sync_rico) |
| `Trabalho/` | 19 | sim (Energisa, G4F, MEC) |
| `Projetos/` | 140 | parcial (incl. clone Ouroboros desatualizado) |
| `Arquivo/` (gitignored) | subset gigante | NÃO |
| Raiz `./X.md` | 8 | NÃO (todos 2026-04-14) |

### 5.1. Duplicatas SHA-256 (validadas)

| Vault | SHA-256 | Match no Ouroboros? |
|---|---|---|
| `QUESTIONARIO_VIDA_COMPLETO.md` | `854c116734...` | IDÊNTICO a `protocolo-ouroboros/docs/` E a `contexto/` |
| `PLANO_FINANCEIRO_2026.md` | `81239de4ff...` | IDÊNTICO a `protocolo-ouroboros/docs/` |
| `PLANO_FINANCEIRO_ANDRE_VITORIA.md` | `a76658b4bf...` | IDÊNTICO a `protocolo-ouroboros/docs/` E a `contexto/` |
| `Projetos/Protocolo Ouroboros/CLAUDE.md` | `457e08a340...` | DIVERGE (`7a3f53fc4b...` no monorepo) -- clone desatualizado |
| `Projetos/Protocolo Ouroboros/GSD.md` | `a43ab02cfc...` | DIVERGE |
| `Projetos/Protocolo Ouroboros/README.md` | `605a555bf0...` | DIVERGE |

`contexto/QUESTIONARIO_VIDA_2_COMPLETO.md` (`19c4a600cd...`) é evolução SÓ do monorepo, não existe no vault.

## 6. Estado de sincronização

| Item | Status | Detalhe |
|---|---|---|
| `.git/` | Existe (62M) | 1 commit `40b8afe feat: commit inicial -- 15 sprints` |
| Remote | NENHUM | `git remote -v` vazio |
| Status atual | 14 modificados + 7 untracked | `.obsidian/*.json`, `emoji_guardian.py` movido, `Pessoal/Casal/Financeiro/{...}/` untracked (saída sync_rico) |
| `.syncignore` | Sim | Ignora `Arquivo/`, `_reorganizacao_backup/`, `Trabalho/Vitoria/MEC/Credenciais/`, `*.csv/xlsx/pdf/...`, `.sistema/{logs,backups,scripts/_desativados}/` |
| `.gitignore` | Sim | Subset complementar |
| Obsidian Sync | NÃO existe | Nem proprietário nem Syncthing -- vault local-only |
| Plugins Obsidian em uso | ~36 | dataview, templater, calendar, periodic-notes, obsidian-tasks-plugin, omnisearch, living-graph, smart-templates |

**Frescor `Pessoal/Casal/Financeiro/Meses/2026-04.md`** modificada em 2026-04-23 18:24 -- está vivo, em produção.

## 7. Achados ad-hoc

1. **76 .tsx/.ts são lixo de backup** Nyx-Code. Zero código React legítimo no vault.
2. **`.sistema/devices/`, `.sistema/health/`, `.sistema/inbox_processor/` vazios** -- placeholders de spec não-finalizada.
3. **Backup automático cross-projeto**: o `vault_backup.py` está capturando mudanças de outros projetos do dev (Hefesto, Nyx-Code, ouroboros worktrees). 4 cópias de `grafo_obsidian.py` de worktrees Ouroboros já estão em backups de 26/04. Política de retenção necessária.
4. **`EMOJI_GUARDIAN.md` e `INTEGRACAO_EMOJI.md` são features ativas** documentadas. `emoji_guardian.py` está sendo movido de `_desativados/` na working copy atual.
5. **`ocr_detector.py:39` path obsoleto** `~/Desenvolvimento/Financas/` (renomeado para `protocolo-ouroboros`). Bug latente -- detector falha silenciosamente lendo categorias.
6. **Clone parcial do Ouroboros em `Projetos/Protocolo Ouroboros/`**: CLAUDE.md, GSD, README divergentes (mtime 2026-04-14, há 12 dias). Doc fossilizada -- candidato à exclusão pós-fusão.
7. **`.sistema/CLAUDE.md` tem missão clara e separada** -- "constituição" do vault, 10 regras alinhadas (acentuação, zero emojis, soberania humana). Não conflita com CLAUDE.md do Ouroboros.
8. **44 relatórios mensais em `Pessoal/Casal/Financeiro/Relatorios/`** (2022-08 a 2026-07) -- gerados pelo `src/obsidian/sync.py` legado (não-rico). Pré-existem ao `sync_rico`. Convivem como camadas distintas.
9. **`Pessoal/Casal/Financeiro/Metas/`** tem variante com acento: `Reserva de Emergencia.md` (gerado, sem acento) E `Reserva de Emergência.md` (escrito à mão, com acento). Possível dup semântica.
10. **`Conceitos/Claude/Claude-templates/hooks/{check,fix}_acentuacao.py`** -- praticamente os mesmos hooks que o Ouroboros precisa.

## 8. Recomendação final (10 bullets)

1. **Manter `~/Controle de Bordo/` como camada de VIEW/CAPTURA do casal** -- não migrar pra dentro do monorepo. Fica responsável por: notas livres, templates Obsidian, dashboards Dataview, anexos visuais, GUI Obsidian.
2. **Migrar 3 módulos** Python do vault para `src/`:
   - `similarity_grouper.py` -> `src/intake/similarity.py`
   - `lib/wikilinks.py` -> `src/utils/wikilinks.py`
   - `emoji_guardian.py` -> `scripts/hooks/emoji_guardian.py`
3. **Deletar do vault** (após confirmar fusão e congelar):
   - `Projetos/Protocolo Ouroboros/` (clone)
   - `.sistema/scripts/_desativados/` (6 protótipos)
   - `.sistema/scripts/ocr_detector.py` (substituído + bug path)
   - `.sistema/scripts/document_creator.py` (substituído pelo `sync_rico.py`)
   - `.sistema/backups/2026-04-08/` (76 .tsx Nyx-Code)
4. **Manter no vault sem migrar**: `gauntlet/`, `health_check.py`, `verificar_*`, `vault_backup.py`, `safe_io.py`, `protecao.py`, `config_loader.py`, `vault_logger.py`, `inbox_processor.py` (vault), `content_detector.py`.
5. **Resolver as 3 duplicatas SHA-idênticas raiz vault**: manter no monorepo `docs/` como fonte canônica e deixar no vault wikilink ou symlink.
6. **Configurar remote git no vault** -- hoje é `init` sem origem. Criar repo PRIVADO no GitHub do casal.
7. **Limpar `.sistema/backups/` periodicamente** -- política: backups > 30 dias movem para `Arquivo/` (já gitignored).
8. **Bug bloqueador `ocr_detector.py`** se resolve com a deleção (item 3).
9. **`Pessoal/Casal/Financeiro/{Documentos,Fornecedores,Meses,_Attachments}/` é o "API contract" entre Ouroboros e vault**. Ouroboros escreve, vault lê. Sem escrita do lado vault sem antes humano remover tag `#sincronizado-automaticamente`.
10. **Criar Sprint pós-fusão** para validar separação de responsabilidades:
    - Auditar que nenhum módulo do vault escreve em `data/` do Ouroboros.
    - Auditar que Ouroboros só escreve em zona declarada do vault.
    - Validar via grep que `BORDO_DIR` é a única env var compartilhada.

## 9. Material para o ADR-21

**Decisão proposta:** "Monorepo `protocolo-ouroboros` é a raiz canônica de execução; vault `Controle de Bordo` é a camada de view/captura humana, com contrato de I/O restrito a `Pessoal/Casal/Financeiro/{Documentos,Fornecedores,Meses,_Attachments}/`."

**Trade-offs aceitos:**
- Duplicação intencional de logger e config-loader (cada lado tem o seu, simples; não vale fundir).
- Vault não vai pro GitHub do Ouroboros (privacidade pessoal); precisa de remote próprio.
- Backups cross-projeto do `vault_backup.py` ficam, sob política de limpeza.

**Alternativa rejeitada:** "Fundir tudo no monorepo, vault vira só `data/raw/notes/`." Rejeitada porque (a) Obsidian precisa ser raiz própria pra plugins funcionarem, (b) PII pessoal do casal não pode misturar com repo de código, (c) o vault tem 1.439 notas + 159M de Arquivo/ que não pertencem a um repo de código.

---

**Achados-chave em uma frase cada:**
- 76 .tsx/.ts são lixo de backup (Nyx-Code), zero código vivo.
- 175 .py reais -> ~30 vivos, dos quais 3 valem migrar (similarity, wikilinks, emoji_guardian).
- 3 duplicatas SHA-idênticas na raiz do vault devem ser resolvidas.
- 1 clone parcial divergente em `Projetos/Protocolo Ouroboros/` deve ser deletado.
- Pasta `Pessoal/Casal/Financeiro/{Documentos,Fornecedores,Meses,_Attachments}/` é o contrato vivo da Sprint 71 -- preservar.
- Vault local-only sem Obsidian Sync; `.git` único commit, sem remoto.
- Backup automático do vault está capturando código de OUTROS projetos -- precisa de política de retenção.
