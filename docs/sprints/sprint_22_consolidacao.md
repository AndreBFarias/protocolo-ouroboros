# Sprint 22 -- Consolidação: Módulos Fantasmas, Extrator Órfão e Obsidian

## Status: Pendente

## Objetivo

Eliminar referências a módulos que não existem, integrar o extrator de energia que foi esquecido, e corrigir a sincronização Obsidian que produz metadados nulos. O projeto hoje tem código morto que crasha e funcionalidade implementada mas desconectada.

---

## Entregas

### Módulos fantasmas

- [ ] **Criar `src/utils/health_check.py`** ou remover referências
  - Menu opção 8 (`run.sh`) e flag `--check` chamam `python -m src.utils.health_check`
  - O módulo não existe -- crasha com `ModuleNotFoundError`
  - Decisão: criar health check real (verificar venv, XLSX, lint, extratores) ou apontar para o validador existente
  - Arquivos: `run.sh` (linhas do menu e flag --check), `src/utils/health_check.py` (criar)

- [ ] **Criar `src/utils/doc_generator.py`** ou remover referências
  - `make docs` chama `python -m src.utils.doc_generator`
  - O módulo não existe
  - Decisão: criar gerador de docs dos extratores (auto-documentação) ou remover target do Makefile
  - Arquivos: `Makefile` (target docs), `src/utils/doc_generator.py` (criar ou remover)

- [ ] **Corrigir mensagem desatualizada do IRPF no menu**
  - `run.sh` contém `msg_erro "Módulo IRPF ainda não implementado (Sprint 10)."` como fallback
  - O módulo IRPF está implementado e funcional
  - Fix: remover a mensagem de fallback desatualizada
  - Arquivo: `run.sh`

### Extrator de energia órfão

- [ ] **Registrar `ExtratorEnergiaOCR` em `_descobrir_extratores()`**
  - `src/extractors/energia_ocr.py` existe, exportado pelo `__init__.py`, mas não está na lista hardcoded de `pipeline.py:_descobrir_extratores()`
  - Fix: adicionar import e append na função
  - Arquivo: `src/pipeline.py`
  - Verificação: colocar screenshot de conta de energia em `data/raw/` e rodar `make tudo`

### Obsidian sync -- frontmatter quebrado

- [ ] **Corrigir regex de extração de valores**
  - `src/obsidian/sync.py:_extrair_valores_relatorio()` usa regex que procura `Receita: R$ X`
  - Formato real do relatório é tabela Markdown: `| Receita total | R$ X |`
  - Resultado: receita, despesa, saldo no frontmatter YAML ficam sempre `null`
  - Todas as queries Dataview que dependem desses valores estão quebradas
  - Fix: atualizar regex para ler o formato de tabela
  - Arquivo: `src/obsidian/sync.py`
  - Verificação: rodar `--sync`, abrir um relatório no vault e confirmar frontmatter com valores reais

---

## Armadilhas

- health_check.py precisa ser leve (não rodar pipeline completo, só checar estado)
- O extrator de energia depende de `tesseract-ocr` -- verificar se está no install.sh (já está)
- O sync Obsidian depende do vault existir em `~/Controle de Bordo/` -- graceful fail se não existir

## Critério de sucesso

- Menu opção 8 e `--check` funcionam sem erro
- `make docs` funciona ou target removido limpo
- Pipeline processa screenshots de energia quando presentes
- Frontmatter Obsidian com valores reais de receita/despesa/saldo
- Zero referências a módulos inexistentes

---

*"A perfeição não é atingida quando não há mais nada a adicionar, mas quando não há mais nada a remover." -- Antoine de Saint-Exupéry*
