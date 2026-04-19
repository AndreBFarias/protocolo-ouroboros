# Prompt de Execução -- Protocolo Ouroboros (Fases BETA → ZETA)

> **Este documento é o briefing completo para uma IA (Claude Code Opus, idealmente) continuar o desenvolvimento do projeto a partir do re-roadmap de 2026-04-19.**
> Cole o conteúdo deste arquivo como primeira mensagem numa nova sessão e peça "execute as sprints em ordem". O supervisor é a própria IA -- ela lê, propõe, humano aprova.

---

## 1. Contexto do projeto em 30 segundos

**Protocolo Ouroboros** é um pipeline ETL financeiro artesanal para o casal André e Vitória. Versão atual 4.0. Visão: catalogador universal -- o usuário joga QUALQUER arquivo do dia a dia (foto de cupom, DANFE PDF, XML NFe, recibo, receita médica, garantia, holerite, extrato, boleto) numa inbox. O sistema classifica, extrai conteúdo granular (itens individuais de NF com categoria), linka tudo num grafo SQLite (transação ↔ documento ↔ item ↔ fornecedor ↔ categoria) e apresenta em dashboard + Obsidian.

**Objetivo final:** quando o pipeline determinístico cobrir 100% dos casos, a IA deixa de ser necessária (autossuficiência). O loop é: IA propõe regra nova em `mappings/*.yaml`, humano aprova, pipeline cresce, IA roda menos. Isso está registrado em **ADR-09 (Autossuficiência Progressiva)** e **ADR-13 (Supervisor Artesanal via Claude Code)**.

**Restrição crítica:** o supervisor é esta sessão de Claude Code. Não existe cliente Anthropic programático no projeto. Não crie `src/llm/`. Veja ADR-13.

---

## 2. Antes de começar -- leia nesta ordem

1. `CLAUDE.md` (raiz do projeto) -- regras invioláveis (acentuação, zero emojis, zero menção a IA em commits, Local First)
2. `docs/ROADMAP.md` -- fases ALFA → ZETA; estado atual
3. `docs/ARMADILHAS.md` -- 19 armadilhas reais já catalogadas; evitar
4. `docs/adr/ADR-13*.md`, `ADR-14*.md`, `ADR-15*.md` -- decisões base do re-roadmap
5. `docs/templates/SPRINT_TEMPLATE.md` -- padrão canônico; seção "Conferência Artesanal Opus" é obrigatória em sprints de feature
6. `scripts/ci/validate_sprint_structure.py --all` -- valida que cada sprint segue o padrão (roda antes de commitar)

---

## 3. Regras invioláveis (do CLAUDE.md)

1. **Acentuação PT-BR correta em TUDO** -- código, commits, docs, comentários, variáveis. "função", "validação", "descrição". Nunca "funcao", "validacao", "descricao". Sem exceção.
2. **Zero emojis** em código, commits, docs e respostas.
3. **Zero menções a IA** em commits e código (nomes como Claude, GPT, Anthropic no subject do commit bloqueiam o pre-commit hook).
4. **Local First** -- tudo funciona offline. APIs externas são opcionais.
5. **Nunca `print()`** em produção. Logging via `rich` + `logging` com rotação.
6. **Nunca inventar dados.** Se não reconhecer, loga warning e pula.
7. **Nunca remover código funcional** sem autorização explícita.
8. **`data/` inteiro no .gitignore** -- dados financeiros nunca no repositório.
9. **Paths relativos via `Path`** -- nunca hardcoded absolutos.
10. **Citação de filósofo** como comentário final de todo arquivo .py e sprint .md (o validador `scripts/ci/validate_sprint_structure.py` exige).
11. **Limite 800 linhas por arquivo** (exceto config/testes/registries).
12. **Scope atômico** -- bug encontrado ao testar feature Y NÃO é fixado inline. Registra como sprint nova.

---

## 4. Ambiente e comandos essenciais

```bash
# Ativar venv
source .venv/bin/activate

# Rotina diária
make lint                                 # ruff + acentuação
./run.sh --tudo                           # pipeline completo (todos os meses)
./run.sh --mes 2026-04                    # mês específico
python -m src.utils.validator             # 6 checagens de integridade
./run.sh --dashboard                      # Streamlit
./run.sh --sync                           # Obsidian
./run.sh --supervisor                     # (Sprint 43) snapshot pra IA consumir
make test                                 # pytest
make test-cov                             # pytest com cobertura
scripts/ci/validate_sprint_structure.py   # valida sprints

# Git: commit hook bloqueia menção a IA e acentuação faltando
# Nunca force push, nunca --no-verify, nunca --amend sem autorização
```

---

## 5. Como trabalhar: o loop do artesão

Toda sessão segue o ciclo:

1. **Abra a sessão**, rode `./run.sh --supervisor` (quando Sprint 43 estiver feita) para pegar contexto do estado atual.
2. **Leia a sprint que vai executar** em `docs/sprints/backlog/sprint_NN_*.md`.
3. **Cheque `docs/ARMADILHAS.md`** -- veja se alguma armadilha se aplica à sprint.
4. **Implemente a sprint** respeitando SPEC YAML no topo (arquivos permitidos/proibidos, acceptance criteria).
5. **Rode os testes da sprint** após cada mudança incremental.
6. **Conferência Artesanal Opus** -- após implementar, leia arquivos originais mencionados na seção "Conferência Artesanal Opus" da sprint, compare com outputs do pipeline, escreva `docs/propostas/sprint_NN_conferencia.md` com tabela de achados.
7. **Registre propostas de regras novas** em `docs/propostas/<tipo>/<slug>.md` usando templates.
8. **Peça aprovação ao humano** antes de commitar. Se aprovar, comita. Se rejeitar, move proposta para `docs/propostas/<tipo>/_rejeitadas/`.
9. **Atualize `docs/DIARIO_MELHORIAS.md`** com o que aprendeu.
10. **Ao fechar sprint**: mude status para CONCLUÍDA, mova arquivo para `docs/sprints/concluidos/`, atualize `docs/ROADMAP.md` e `CLAUDE.md`.

---

## 6. Ordem de execução (sprints no backlog)

**Fase BETA (infra, PRÉ-REQUISITO de tudo):**

1. Sprint 41 -- Intake Universal Multiformato
2. Sprint 42 -- Grafo SQLite Mínimo
3. Sprint 43 -- Workflow Supervisor Artesanal

41 e 42 podem rodar em paralelo (sessões separadas). 43 depende da 42.

**Fase GAMA (extratores, pode-se escolher qual atacar primeiro conforme os arquivos disponíveis):**

4. Sprint 44 -- DANFE PDF
5. Sprint 45 -- Cupom Fiscal Térmico (foto)
6. Sprint 46 -- XML NFe
7. Sprint 47 -- Recibo Não-Fiscal
8. Sprint 47a -- Receita Médica
9. Sprint 47b -- Garantia

Sugestão: começar por 44 e 45 (maior impacto diário). 46 quando houver XMLs no projeto. 47a e 47b conforme chegarem receitas/garantias na inbox.

**Fase DELTA (linking + classificação):**

10. Sprint 48 -- Linking Documento ↔ Transação
11. Sprint 49 -- Entity Resolution de Produtos
12. Sprint 50 -- Categorização de Itens via YAML

Ordem sequencial (49 depende de itens extraídos por 44-47b; 50 depende de 49).

**Fase EPSILON (UX):**

13. Sprint 51 -- Dashboard de Catalogação
14. Sprint 52 -- Busca Global Doc-Cêntrica
15. Sprint 53 -- Grafo Visual + Obsidian Rico

**Fase ZETA (consumo dos dados granulares -- sprints já no backlog mas dependem de DELTA/EPSILON):**

Veja `docs/ROADMAP.md` tabela "Fase ZETA" (sprints 20, 21, 24, 25, 33, 34, 35, 36).

---

## 7. Padrões técnicos a seguir

### 7.1. Estrutura de extrator novo

```python
# src/extractors/novo_extrator.py
from pathlib import Path
from src.utils.logger import configurar_logger
from src.extractors.base import ExtratorBase, Transacao

logger = configurar_logger("NovoExtrator")

class NovoExtrator(ExtratorBase):
    def pode_processar(self, caminho: Path) -> bool: ...
    def extrair(self) -> list[Transacao]: ...

# "<Citação>" -- Autor
```

Registrar em `src/pipeline.py:_descobrir_extratores()` via `try/import/append`.

### 7.2. Tratamento de erro

- Nunca `except:` genérico. Sempre especifique exceções.
- Sempre logue com contexto: `logger.warning("falha em %s: %s", caminho, exc)`.
- Nunca `# TODO` inline -- crie issue ou sprint.

### 7.3. Testes

- Fixtures em `tests/fixtures/<tipo>/`.
- Usar `tests/conftest.py:_transacao` factory para transações.
- Um teste = um cenário; nome descritivo em PT-BR.

### 7.4. Acentuação

Arquivos em PT-BR exigem acentos corretos. O pre-commit hook bloqueia.

---

## 8. Forma do supervisor artesanal

Quando uma sprint pede "Conferência Artesanal Opus", a IA deve:

1. Ler os arquivos originais mencionados (PDFs, imagens, CSVs) usando ferramentas de leitura da sessão. Para imagens, LER visualmente (a interface suporta).
2. Para cada arquivo, comparar o conteúdo observado com o que o pipeline extraiu.
3. Se houver discrepância → abrir proposta em `docs/propostas/<tipo>/<slug>.md` com diff, justificativa, teste.
4. Registrar o relatório de conferência em `docs/propostas/sprint_NN_conferencia.md`.
5. Apresentar o relatório ao humano na conversa e aguardar aprovação antes de continuar.

**Exemplo de proposta (arquivo):**

```markdown
---
id: 2026-04-20_neoenergia-variante
tipo: regra
data: 2026-04-20
status: aberta
autor_proposta: claude-code-opus
sprint_contexto: 45
---

## Contexto

Cupom de energia do mercado "Pantry" (CNPJ 01.234.567/0001-89) traz linha
"NEOEN S/A" em vez de "NEOENERGIA" -- categoria "Outros" em 3 ocorrências
este mês.

## Diff proposto

```diff
--- a/mappings/categorias.yaml
+++ b/mappings/categorias.yaml
@@ -43,6 +43,7 @@
   neoenergia:
-    regex: "NEOENERGIA|NEOEN(?!ERGIA)"
+    regex: "NEOENERGIA|NEOEN\\s*S[./]?A|NEOEN(?!ERGIA)"
     categoria: "Energia"
     classificacao: "Obrigatório"  # noqa: accent
```

## Justificativa

3 transações do último mês e 11 do histórico casavam erroneamente como
"Outros". Risco de falso-positivo: nenhum outro fornecedor com "NEOEN S/A"
foi encontrado no XLSX.

## Teste de regressão

```bash
.venv/bin/pytest tests/test_categorizer.py::test_neoenergia_variantes
```

## Decisão humana

**Aprovada em:** (preencher)
```

---

## 9. Ciclo de uma sprint fechada

Ao fim da execução de uma sprint:

1. `make lint` passa
2. Testes relevantes passam
3. `./run.sh --tudo` conclui sem crash
4. `python -m src.utils.validator` retorna 6/6 (se sprint mexeu no ETL)
5. `scripts/ci/validate_sprint_structure.py <caminho>` retorna OK
6. Relatório de Conferência Artesanal Opus registrado e aprovado
7. Mudança do `Status` da sprint para `CONCLUÍDA`
8. Mover arquivo para `docs/sprints/concluidos/` (ou rodar `scripts/finish_sprint.sh NN`)
9. Atualizar `CLAUDE.md` cabeçalho (contagens) e `docs/ROADMAP.md` (tabela de estado)
10. Atualizar `docs/ARMADILHAS.md` se encontrar armadilha nova
11. Commit atômico: `feat: Sprint NN -- <título curto>` (sem menção a IA no subject)

---

## 10. O que NÃO fazer (erros comuns)

- NÃO criar `src/llm/` nem adicionar `anthropic` em `pyproject.toml` -- veta ADR-13.
- NÃO fazer commit com "Claude", "GPT", "Anthropic" no subject -- hook bloqueia.
- NÃO esquecer a citação de filósofo no final de sprint/arquivo .py -- validador reclama.
- NÃO misturar escopo de bug novo descoberto com a sprint atual. Abra sprint nova.
- NÃO quebrar as 8 abas do XLSX consolidado sem migrar o dashboard.
- NÃO assumir que arquivo novo na inbox é do mesmo pessoa. Confirme por conteúdo.
- NÃO fazer OCR de PDF que tem texto nativo -- perde precisão. Tente `pdfplumber.extract_text()` primeiro.
- NÃO adicionar dependência sem justificar no corpo da sprint e no pyproject.toml.

---

## 11. Primeira ação na sessão

Se este é o primeiro turno da sessão:

1. Leia este arquivo inteiro
2. Leia `CLAUDE.md`
3. Leia `docs/ROADMAP.md`
4. Liste as sprints em `docs/sprints/backlog/` (espera-se `sprint_41` até `sprint_53`)
5. Pergunte ao humano: "Quer que eu comece pela Sprint 41 (Intake Universal Multiformato), Sprint 42 (Grafo) ou outra?"
6. Se o humano pedir pra executar, siga a seção 5 (loop do artesão) da Sprint escolhida.

**Jamais "execute tudo de uma vez"** -- uma sprint por sessão mantém escopo atômico e permite revisão humana.

---

## 12. Arquivos de referência

- `CLAUDE.md` -- regras e contexto
- `docs/ROADMAP.md` -- roadmap atual
- `docs/ARMADILHAS.md` -- armadilhas históricas
- `docs/templates/SPRINT_TEMPLATE.md` -- template canônico de sprint
- `docs/templates/PROPOSTA_REGRA.md` -- template de proposta (Sprint 43 cria)
- `docs/DIARIO_MELHORIAS.md` -- log cronológico de aprendizados (Sprint 43 cria)
- `docs/adr/ADR-NN-*.md` -- decisões arquiteturais (15 ADRs)
- `/home/andrefarias/.claude/plans/sprint-fluffy-puddle.md` -- plano completo do re-roadmap

---

*"O artesão não despacha, o artesão escuta."* -- princípio do ofício
