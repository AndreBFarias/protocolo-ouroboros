## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 22
  title: "Consolidação: encerrar lacunas de base e sincronizar docs"
  touches:
    - path: CLAUDE.md
      reason: "remover afirmações falsas sobre energia_ocr não registrado e frontmatter Obsidian nulo"
    - path: src/utils/health_check.py
      reason: "módulo referenciado em run.sh --check e menu opção 8; criar verificações leves de ambiente"
    - path: src/utils/doc_generator.py
      reason: "módulo referenciado em make docs; gerar docs/extractors/_INDEX.md a partir dos extratores"
    - path: src/dashboard/dados.py
      reason: "trocar 2 except: pass por logger.warning (linhas 174 e 188)"
    - path: src/dashboard/paginas/metas.py
      reason: "trocar except: pass por logger.warning (linha 167)"
    - path: src/extractors/santander_pdf.py
      reason: "trocar except: pass por logger.warning (linha 165)"
    - path: src/utils/file_detector.py
      reason: "trocar except: pass por logger.warning (linha 445)"
    - path: src/irpf/__main__.py
      reason: "criar entrypoint para python -m src.irpf --ano, evitando crash de ./run.sh --irpf"
    - path: run.sh
      reason: "remover mensagem desatualizada 'Módulo IRPF ainda não implementado'"
  n_to_n_pairs:
    - [CLAUDE.md, docs/ROADMAP.md]
    - [run.sh, Makefile]
  forbidden:
    - src/extractors/energia_ocr.py  # já registrado, não mexer
    - src/obsidian/sync.py  # já corrigido em trabalho anterior
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: "./run.sh --check"
      timeout: 30
    - cmd: "make docs"
      timeout: 60
    - cmd: "python -m src.irpf --ano 2026"
      timeout: 30
  acceptance_criteria:
    - "make lint passa sem erros"
    - "./run.sh --check executa sem ModuleNotFoundError"
    - "make docs gera docs/extractors/_INDEX.md"
    - "python -m src.irpf --ano 2026 imprime mensagem clara (não crasha)"
    - "grep -R 'except:\\s*pass' src/ retorna zero linhas"
    - "CLAUDE.md seção 'Lacunas conhecidas' não menciona energia_ocr nem frontmatter como abertos"
    - "Acentuação PT-BR correta em todos os arquivos"
    - "Zero emojis e zero menções a provedor de IA"
```

> Executar antes de começar: `make lint && ./run.sh --check`

---

# Sprint 22 -- Consolidação: encerrar lacunas de base e sincronizar docs

**Status:** CONCLUÍDA
**Data:** 2026-04-18
**Prioridade:** CRÍTICA
**Tipo:** Infra
**Dependências:** Nenhuma
**Desbloqueia:** Sprint 30 (Base Honesta)
**Issue:** --
**ADR:** --

---

## Como Executar

**Comandos principais:**
- `make lint` -- ruff check + format + acentuação
- `./run.sh --check` -- health check do ambiente
- `make docs` -- gerador de documentação dos extratores
- `python -m src.irpf --ano 2026` -- entrypoint IRPF
- `python -m src.utils.validator` -- 6 checagens de integridade do XLSX

### O que NÃO fazer

- NÃO mexer em `src/extractors/energia_ocr.py` nem em `src/obsidian/sync.py`; ambos já estão corretos.
- NÃO remover código funcional sem autorização.
- NÃO inventar checagens pesadas em `health_check.py`: o módulo precisa ser leve.
- NÃO expandir escopo para tarefas da Sprint 23 (dados fantasmas) ou Sprint 30 (testes).

---

## Problema

Parte do trabalho desta sprint já foi feita (§1.1 do plano 30/60/90):

- `CLAUDE.md` foi ajustado para refletir que `energia_ocr` está registrado e o frontmatter Obsidian grava valores reais.
- `src/utils/health_check.py` e `src/utils/doc_generator.py` foram criados.
- 4 `except: pass` foram trocados por `logger.warning` em `src/dashboard/dados.py:174,188`, `src/dashboard/paginas/metas.py:167`, `src/extractors/santander_pdf.py:165`.

Ainda faltam resíduos que bloqueiam usuários e a Sprint 30:

1. `src/utils/file_detector.py:445` ainda tem `except: pass` silencioso.
2. `./run.sh --irpf` crasha com `ModuleNotFoundError` porque não há `src/irpf/__main__.py`.
3. `run.sh` contém o fallback desatualizado `msg_erro "Módulo IRPF ainda não implementado (Sprint 10)."`.
4. A seção "Lacunas conhecidas" do `CLAUDE.md` historicamente mentia sobre `energia_ocr` "não registrado" e frontmatter "nulo"; a sincronização final (docs/ROADMAP.md + CLAUDE.md) precisa ser revalidada para que a mentira não volte.

---

## O que já existe (NÃO duplicar)

| Sistema | Arquivo | O que faz |
|---------|---------|-----------|
| Pipeline | `src/pipeline.py:71-76` | Já registra `ExtratorEnergiaOCR` em `_descobrir_extratores()` |
| Obsidian | `src/obsidian/sync.py:114-156` | Já extrai receita/despesa/saldo do formato de tabela markdown |
| IRPF tagger | `src/transform/irpf_tagger.py` | 21 regras em 5 tipos, funcional (falta apenas CLI) |
| Health check parcial | `src/utils/health_check.py` | Criado em §1.1; confirmar cobertura antes de fechar |
| Doc generator parcial | `src/utils/doc_generator.py` | Criado em §1.1; confirmar que gera `docs/extractors/_INDEX.md` |
| Logger | `src/utils/logger.py` | `obter_logger("<nome>")` disponível, rotacionado 5MB x 3 |

---

## Implementação

### Fase 1: fechar o último `except: pass`

**Arquivo:** `src/utils/file_detector.py`

Trocar o `except: pass` em torno da linha 445 por:

```python
except (UnicodeDecodeError, OSError) as exc:
    logger.warning("file_detector: falha ao inspecionar %s (%s)", caminho, exc)
```

Usar o logger já instanciado no topo do módulo. Não engolir `KeyboardInterrupt`.

### Fase 2: criar `src/irpf/__main__.py`

**Arquivo:** `src/irpf/__main__.py` (novo)

CLI mínima que:

1. Aceita `--ano YYYY` (default: ano corrente).
2. Lê o XLSX consolidado via `src/utils/paths.py`.
3. Chama o tagger IRPF existente.
4. Escreve `data/output/irpf_{ano}.csv` e imprime sumário.
5. Se o XLSX não existir, loga `logger.error` e sai com código 2 (nunca `raise` cru).

Remover do `run.sh` o bloco `msg_erro "Módulo IRPF ainda não implementado (Sprint 10)."`.

### Fase 3: revalidar health_check e doc_generator

**Arquivo:** `src/utils/health_check.py`

Confirmar que verifica, em ordem:

1. Python >= 3.11 e venv ativo.
2. Dependências críticas importáveis (`pandas`, `openpyxl`, `pdfplumber`, `msoffcrypto`, `rich`, `streamlit`).
3. Existência de `mappings/categorias.yaml` e `mappings/senhas.yaml` (só alerta se não achar senhas).
4. `data/output/extrato_consolidado.xlsx` presente (warning se não existe, não fail).
5. `tesseract --version` disponível (warning, não fail).

Retorna código 0 se tudo OK ou warnings; 1 se faltar dependência crítica.

**Arquivo:** `src/utils/doc_generator.py`

Confirmar que varre `src/extractors/` e gera `docs/extractors/_INDEX.md` com nome do extrator, banco alvo, formato de entrada e regex de detecção. Executa via `python -m src.utils.doc_generator`.

### Fase 4: sincronizar docs

**Arquivo:** `CLAUDE.md`

Na tabela "Lacunas conhecidas":

- Remover linhas de `health_check.py não existe`, `doc_generator.py não existe`, `energia_ocr.py não registrado`, `Obsidian sync com frontmatter nulo`.
- Atualizar o cabeçalho de contexto ativo: Sprint 22 passa para "Concluída" apenas após todos os critérios serem satisfeitos.

**Arquivo:** `docs/ROADMAP.md`

Refletir o mesmo estado da Sprint 22 (mover para bloco Concluídas quando fechada).

---

## Armadilhas Conhecidas

| Ref | Armadilha | Como evitar |
|-----|-----------|-------------|
| A22-1 | `CLAUDE.md` mentia sobre `energia_ocr.py não registrado` (na verdade está em `src/pipeline.py:71-76`) | Verificar código antes de reescrever docs; usar `grep` contra `_descobrir_extratores` |
| A22-2 | `CLAUDE.md` mentia sobre frontmatter Obsidian nulo (na verdade `src/obsidian/sync.py:114-156` extrai valores reais) | Rodar `./run.sh --sync` e abrir um relatório no vault antes de fechar |
| A22-3 | `except: pass` oculta erros reais em parsing de nome de arquivo | Sempre logar com contexto (`exc`, `caminho`) |
| A22-4 | `python -m src.irpf` sem `__main__` quebra `run.sh --irpf` | Criar `src/irpf/__main__.py` antes de tocar no `run.sh` |
| A22-5 | `health_check.py` rodando pipeline completo causa timeout | Manter leve: só imports e existência de arquivos |
| A22-6 | `tesseract` ausente em ambientes sem OCR causa `FileNotFoundError` no health check | Tratar como warning, nunca como fail |

Referência: `docs/ARMADILHAS.md`

---

## Evidências Obrigatórias

- [ ] `make lint` passa sem erros
- [ ] `./run.sh --check` executa sem `ModuleNotFoundError` e retorna 0
- [ ] `make docs` gera `docs/extractors/_INDEX.md` (confirmar `git status`)
- [ ] `python -m src.irpf --ano 2026` imprime sumário e gera `data/output/irpf_2026.csv`
- [ ] `grep -R "except:\s*pass" src/` retorna zero resultados
- [ ] `CLAUDE.md` "Lacunas conhecidas" sem entradas para energia_ocr, frontmatter, health_check, doc_generator
- [ ] `python -m src.utils.validator` com 6/6 checagens OK
- [ ] Commit message PT-BR no formato `chore: consolida base, encerra lacunas de infra`

---

## Verificação end-to-end

```bash
make lint
./run.sh --check
make docs
python -m src.irpf --ano 2026
python -m src.utils.validator
grep -R "except:\s*pass" src/ || echo "ok: nenhum except silencioso"
```

---

*"A verdade não se conquista pela sofística, mas pela honestidade com os próprios dados." -- Epicteto*
