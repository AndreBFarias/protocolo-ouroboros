---
concluida_em: 2026-04-23
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: E-AUDITORIA-TECNICA
  title: "Auditoria técnica honesta do projeto + consolidação de toda a documentação"
  touches:
    - path: docs/auditoria_tecnica_2026-04-23.md
      reason: "relatório mestre com todos os achados (bugs, órfãos, integração, dívida técnica)"
    - path: CLAUDE.md
      reason: "versão, contagens, fases, estrutura -- atualizar para refletir estado pós rota conserta-tudo + A + B + C"
    - path: VALIDATOR_BRIEF.md
      reason: "rodapé com entradas de todas as sprints da sessão (P0.1 ... C3) e padrões canônicos novos"
    - path: docs/ROADMAP.md
      reason: "refletir fases concluídas, sprints-filhas novas (82b, 92a/b/c, 93a/b/c), fase OMEGA (94)"
    - path: README.md
      reason: "apresentação do projeto com números atuais"
    - path: docs/ARCHITECTURE.md
      reason: "diagrama de fluxo + módulos + extratores atualizado (9 extratores + DAS + DIRPF = 11)"
    - path: docs/ARMADILHAS.md
      reason: "armadilhas novas descobertas na sessão (uuid.uuid4 em fallback, razão social como CNPJ, etc.)"
    - path: docs/AUDITORIA_SPRINTS.md
      reason: "seção nova para sprints da sessão 2026-04-23 com veredicto honesto"
    - path: docs/MODELOS.md
      reason: "schemas atualizados (aba renda restritiva, tipos de documento novos no grafo)"
  forbidden:
    - "Inventar números: toda contagem no texto tem que ser verificada via grep/pytest/sqlite"
    - "Embelezar bugs conhecidos: auditoria é honesta, não é release notes"
    - "Alterar código de produção: esta sprint é só auditoria + docs (exceção: órfãos óbvios podem ser removidos com commit separado)"
    - "Declarar 'projeto 100% pronto' se houver qualquer bug P0 ou P1 em aberto"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/ -q"
    - cmd: "make smoke"
  acceptance_criteria:
    - "docs/auditoria_tecnica_2026-04-23.md existe e tem 7 seções mínimas: bugs, órfãos, integração, dívida, deps, testes, config"
    - "Cada bug listado tem: evidência (comando/linha), impacto (P0/P1/P2), sprint-filha proposta"
    - "Cada arquivo órfão listado tem: path, motivo (grep sem hits), ação (deletar/manter/documentar)"
    - "CLAUDE.md versão >= 5.3 com contagens verificadas (tests, docs no grafo, sprints)"
    - "VALIDATOR_BRIEF.md tem entrada de rodapé 2026-04-23 descrevendo as 18 sprints da sessão + 7 sprints-filhas"
    - "README.md lista extratores atuais (11: 9 bancários + DAS + DIRPF + docs) e features (13 abas + 2 secoes de relatorio)"
    - "docs/ARMADILHAS.md tem seção nova 2026-04-23 com >= 5 armadilhas descobertas"
    - "Gauntlet verde após todas as mudanças (lint + pytest + smoke)"
    - "Commit único ou máximo 3 (1 para auditoria, 1 para docs, 1 para órfãos) -- não fragmentar"
  proof_of_work_esperado: |
    # Verificação do relatório
    wc -l docs/auditoria_tecnica_2026-04-23.md  # >= 300 linhas
    grep -c "^### P0\|^### P1\|^### P2" docs/auditoria_tecnica_2026-04-23.md  # >= 10 bugs listados

    # Verificação docs
    grep "VERSÃO: 5.3" CLAUDE.md  # atualizado
    grep "TESTES: 1.261" CLAUDE.md  # bate com pytest
    grep "2026-04-23" VALIDATOR_BRIEF.md  # rodapé atualizado

    # Gauntlet
    make lint  # exit 0
    .venv/bin/pytest tests/ -q  # 1261+ passed
    make smoke  # 23/0 + 8/8
```

---

# Sprint E — Auditoria técnica completa + consolidação de documentação

**Status:** BACKLOG (penúltima da rota "conserta tudo"; precede Sprint D ARTESANAL FINAL)
**Prioridade:** P0 ao chegar nela (antes de começar Fase D, garante baseline limpo)
**Dependências:** Rota conserta-tudo + Fases A/B/C concluídas (todas do dia 2026-04-23)
**Origem:** pedido do dono 2026-04-23 -- "auditoria honesta, erros, bugs, correções, faltas de integração, arquivos órfãos e afins. Só depois a auditoria artesanal. Salva e atualiza a documentação toda do projeto. Não quero que seu conhecimento se perca."

## Motivação

A sessão 2026-04-23 executou 18 sprints em rajada + descobriu 7 sprints-filhas. O projeto mudou substancialmente:
- +22 testes totais (1139 -> 1261)
- +35 documentos no grafo (4 -> 39)
- +2 extratores novos (DAS PARCSN, DIRPF)
- Aba renda ressignificada (459 -> 99 linhas)
- pessoa_detector ampliado (CPF -> CPF+CNPJ+razão social)
- Fallback supervisor idempotente
- Dedupe de roteamento por hash
- UX v3 (6 fixes visuais)
- Relatórios diagnósticos + narrativos
- IRPF em YAML

Mas:
- Documentação mestre (CLAUDE.md, README, ADRs, BRIEF) ficou para trás em detalhes.
- Alguns arquivos podem ter ficado órfãos.
- Integração entre extratores novos e o restante do pipeline merece check rigoroso.
- Bugs conhecidos (Sprints 93a/b/c dos extratores) precisam ficar visíveis no registro mestre.

Esta sprint é a **parada obrigatória** antes de mergulhar na Sprint D (auditoria artesanal com humano): garantir que a documentação reflete a realidade e que todos os bugs conhecidos estão mapeados.

## Escopo

### Fase 1 — Coleta de evidências (sem alterar nada)

Executar uma série de comandos de auditoria e salvar o output bruto como apêndice:

1. **Contagens canônicas:**
   - `find src -name "*.py" | xargs wc -l | tail -1` (LOC produção)
   - `find tests -name "*.py" | xargs wc -l | tail -1` (LOC testes)
   - `.venv/bin/pytest tests/ -q --no-header` (baseline)
   - `.venv/bin/pytest --collect-only -q | grep -c "test session"` (N testes)
   - `ls src/extractors/*.py | grep -v __init__ | wc -l` (N extratores)
   - `ls src/dashboard/paginas/*.py | grep -v __init__ | wc -l` (N abas)
   - `ls docs/adr/*.md | wc -l` (N ADRs)
   - `ls docs/sprints/{concluidos,backlog,arquivadas}/*.md | wc -l` (N sprints)
   - `.venv/bin/python -c "import sqlite3; ..."` (nodes + edges + docs no grafo)

2. **Busca de órfãos:**
   - `find src -name "*.py" -exec grep -L "^from\|^import" {} \;` (arquivos sem imports próprios -- candidatos órfãos)
   - Para cada arquivo em src/, grep no resto do src/ por imports dele. Zero hits = órfão.
   - Verificar `src/integrations/`, `src/projections/`, `src/llm/` (se existir) -- são usados?
   - YAMLs em `mappings/` que não são lidos por nenhum módulo.

3. **Busca de dívida técnica:**
   - `grep -rn "TODO\|FIXME\|XXX\|HACK" src/ scripts/ | wc -l`
   - `grep -rn "# noqa" src/ tests/ | wc -l` (e quais códigos)
   - `grep -rn "skipif\|@pytest.mark.skip" tests/ | wc -l`
   - `grep -rn "raise NotImplementedError" src/`
   - Arquivos >800 linhas (violação da meta do projeto): `find src -name "*.py" -exec wc -l {} \; | awk '$1>800'`

4. **Dependências:**
   - `pip list` vs imports reais -- quais pacotes são realmente usados?
   - `grep "^import\|^from" src/ -rh | sort -u | awk -F'[ .]' '{print $2}' | sort -u` (módulos top-level usados)

5. **Integração:**
   - Cada extrator está em `_descobrir_extratores` de `src/pipeline.py`? (grep cruzado)
   - Cada extrator tem teste? (`tests/test_<extrator>.py` existe?)
   - Cada extrator tem pista no YAML `tipos_documento.yaml` ou `inbox_routing.yaml`?
   - `scripts/reprocessar_documentos.py::EXTRATORES_DOCUMENTAIS` bate com `src/pipeline.py::_descobrir_extratores`?

6. **Testes:**
   - Quais testes estão SKIP e por quê? (`pytest -v --no-header | grep SKIP`)
   - Testes marcados `@pytest.mark.slow` -- funcionam sem flags especiais?
   - Cobertura mínima: cada módulo em `src/` tem pelo menos 1 teste em `tests/`?

7. **Configuração e smoke:**
   - `./run.sh --check` retorna 0 erros?
   - `scripts/smoke_aritmetico.py --strict` retorna 8/8?
   - `.env.example` (se existir) cobre todas as variáveis esperadas?

### Fase 2 — Consolidação do relatório

Compilar tudo em `docs/auditoria_tecnica_2026-04-23.md` com estrutura:

```markdown
# Auditoria técnica 2026-04-23

## Sumário executivo
- Estado geral: saudável / atenção / crítico
- N bugs P0, P1, P2 mapeados
- N arquivos órfãos
- N armadilhas novas descobertas

## 1. Bugs conhecidos
### P0 (bloqueadores) -- lista com sprint-filha proposta
### P1 (importantes) -- lista
### P2 (minúcias) -- lista

## 2. Arquivos órfãos
| Path | Último uso | Ação sugerida |
| ... | ... | deletar / manter / documentar |

## 3. Integração e consistência
- Pipeline vs reprocessar_documentos
- YAMLs vs código
- Extratores vs testes

## 4. Dívida técnica
- TODOs, FIXMEs, noqas contados
- Arquivos >800 linhas
- Testes skipados por motivo

## 5. Dependências
- Lista de pacotes usados vs pyproject.toml
- Importações zumbis

## 6. Testes
- Baseline, skips, slows
- Cobertura por módulo (estimada)

## 7. Configuração e smoke
- Contratos aritméticos OK
- ./run.sh --check limpo

## Apêndice: outputs brutos dos comandos de auditoria
```

### Fase 3 — Atualização de documentação mestre

Atualizar ESTES arquivos para refletir estado real atual (verificado pela auditoria da Fase 1):

1. **CLAUDE.md**:
   - Versão (ex: 5.2 -> 5.3)
   - Contagem de transações, meses, bancos, extratores
   - Baseline de testes (1261)
   - Grafo: N nodes, N edges, N documentos
   - Fases: marcar rota conserta-tudo + A + B + C como concluídas
   - Sprints: totalizar
   - ADRs ativos (atualizar se algum mudou)
   - Seção "Próxima sessão — retomada canônica" aponta para HANDOFF atual + sprint E + sprint D

2. **VALIDATOR_BRIEF.md**:
   - Rodapé novo em 2026-04-23 descrevendo as 18 sprints da sessão + padrões canônicos novos (fontes_renda whitelist, pessoas.yaml CNPJ+razão, fallback idempotente por cache_key, dedupe por hash, diagnóstico comparativo, resumo narrativo heurístico, IRPF declarativo, canonicalizer variantes curtas, auditoria automática extratores, UX audit Nielsen).

3. **docs/ROADMAP.md**:
   - Fases ALFA-KAPPA: CONCLUÍDAS (histórico)
   - Fase LAMBDA (rota conserta tudo + A + B + C): CONCLUÍDA 2026-04-23
   - Fase MU (sprints-filhas 82b, 92a/b/c, 93a/b/c): BACKLOG
   - Fase OMEGA (Sprint 94 fusão total): estratégica 12-18 meses
   - Fase D (auditoria artesanal com humano): penúltima, após esta sprint E
   - Sprint E (esta): marcar como em execução

4. **README.md**:
   - Números atuais (6086 tx, 82 meses, 6 bancos, 11 extratores, 1261 testes, 39 docs no grafo, 13 abas)
   - Principais features (rota conserta-tudo trouxe 9 novas)
   - Como rodar, instalar, contribuir (checar se está correto)

5. **docs/ARCHITECTURE.md**:
   - Diagrama de fluxo ETL atualizado com DAS + DIRPF + NFCe OCR fallback
   - Diagrama de componentes com `canonicalizer_casal.variantes_curtas`
   - Seção sobre `pessoa_detector` ampliado (4 níveis)
   - Seção sobre aba renda restritiva + YAML whitelist

6. **docs/ARMADILHAS.md**:
   - Armadilhas novas (mínimo 5 descobertas nesta sessão):
     1. `uuid.uuid4()` em fallback supervisor gera duplicatas a cada rodada (Sprint 87d)
     2. `pessoa_detector` só com CPF literal falha em DAS/certidões (Sprint 90)
     3. Roteador duplica arquivos literal sem dedupe por hash (Sprint P2.3)
     4. Aba renda sem whitelist vira dump de qualquer crédito (Sprint P0.1)
     5. Contrato aritmético #1 mascarado por dado sujo (auditoria 2026-04-23)
     6. `ExtratorNfcePDF` sem OCR falhava em PDF-imagem silenciosamente (Sprint A2)
     7. Hash canônico do grafo precisa `.upper()` para simetria XLSX (BRIEF §2026-04-24)

7. **docs/AUDITORIA_SPRINTS.md**:
   - Seção nova para sessão 2026-04-23 com 18 sprints + 7 sprints-filhas
   - Veredicto honesto por sprint (SUCESSO / APROVADO_COM_RESSALVAS / PARCIAL)

8. **docs/MODELOS.md**:
   - Schema atualizado de `aba renda` (agora restritiva, 99 linhas vs 459)
   - Novos `tipo_documento`: `das_parcsn`, `das_parcsn_andre`, `dirpf`, `dirpf_retif`, `holerite`, `cpf_comprovante`
   - Schema de `mappings/pessoas.yaml` (novo)
   - Schema de `mappings/fontes_renda.yaml` (novo)
   - Schema de `mappings/irpf_regras.yaml` (novo)

### Fase 4 — Limpeza de órfãos óbvios (OPCIONAL)

SÓ se a Fase 1 encontrou órfãos confirmados (grep em todo src/ + scripts/ sem nenhum hit):
- Deletar com commit separado e explicação.
- NÃO apagar coisa duvidosa -- manter com `# NOTE: órfão sob revisão 2026-04-23` como anotação.

### Fase 5 — Gauntlet + commit + push

- `make lint` (exit 0)
- `.venv/bin/pytest tests/ -q` (>= 1261 passed)
- `make smoke` (23/0 + 8/8)
- Commit único ou máximo 3 atômicos. Mensagem em PT-BR imperativa, sem IA.
- Push para `origin/main`.
- Atualizar HANDOFF_2026-04-23_conserta_tudo.md marcando Fase E concluída.

### Fase 6 — Habilitar Sprint D

Após Sprint E, o projeto está em estado documentalmente honesto. Sprint D (artesanal com humano) fica habilitada com confiança no que vai ser revisado.

## Armadilhas

- **Auditoria honesta é chata.** Não ceder à tentação de minimizar bugs. Se achar algo feio, escrever feio.
- **Documentação em drift.** CLAUDE.md tinha 5.2 no começo desta sessão e ficou 5.2 o tempo todo. Contagens ficam desatualizadas rapidamente -- esta sprint repara UMA VEZ e deixa checklist para próxima sessão.
- **Órfãos falsos-positivos.** Arquivo sem import pode ser script CLI, template, fixture. Sempre verificar: `grep -r "nome_arquivo" scripts/ tests/ src/` antes de declarar órfão.
- **Atualização massiva de docs gera conflito.** Fazer commits atômicos por arquivo quando o diff ficar grande.

## Não-objetivos

- **Não é para implementar fixes.** Bugs P0/P1 mapeados viram sprint-filha, não são corrigidos aqui.
- **Não é release notes.** Relatório é técnico, para o time (humano + IA futura), não marketing.
- **Não é sprint D.** A auditoria aqui é documental + automática; a artesanal (D) é humana + interativa.

## Valor

Ao fim desta sprint, qualquer IA ou humano que abrir o projeto tem:
- Mapa completo do que funciona e do que não funciona.
- Documentação reflete código.
- Base honesta para a Sprint D.
- Zero conhecimento perdido da sessão 2026-04-23.

---

*"Saber o que não se sabe é o começo da sabedoria." -- adaptação socrática*
