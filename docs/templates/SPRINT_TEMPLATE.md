## 0. SPEC (machine-readable)

```yaml
sprint:
  id: NN
  title: "título descritivo"
  touches:
    - path: src/modulo/arquivo.py
      reason: "o que muda e por quê"
  n_to_n_pairs:
    - [src/arquivo_a.py, src/arquivo_b.py]
  forbidden:
    - src/path/nao_tocar.py  # motivo
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/ -x -q"
      timeout: 120
  acceptance_criteria:
    - "Critério verificável 1"
    - "Critério verificável 2"
    - "Acentuação PT-BR correta em todos os arquivos"
    - "Zero emojis e zero menções a IA"
```

> Executar antes de começar: `make lint && ./run.sh --check`

---

# Sprint NN -- Título Imperativo

**Status:** PENDENTE | PLANEJADA | EM ANDAMENTO | CONCLUÍDA | OBSOLETA | CANCELADA
**Data:** YYYY-MM-DD
**Prioridade:** CRÍTICA | ALTA | MEDIA | BAIXA
**Tipo:** Feature | Bugfix | Refactor | Validação | Infra | Documentação
**Dependências:** Sprint XX (nome) | Nenhuma
**Desbloqueia:** Sprint YY (nome) | --
**Issue:** #NNN (GitHub -- se aplicável)
**ADR:** ADR-NNN (se aplicável)

---

## Como Executar

**Comandos principais:**
- `make lint` -- ruff check + format + acentuação
- `make process` -- pipeline completo (se sprint mexe no ETL)
- `./run.sh --check` -- health check do ambiente
- `python -m src.utils.validator` -- 6 checagens de integridade do XLSX

### O que NÃO fazer

- NÃO remover código funcional sem autorização explícita
- NÃO criar abstrações ou frameworks desnecessários
- NÃO quebrar as 8 abas do XLSX
- NÃO adicionar dependências novas sem justificar no pyproject.toml
- NÃO misturar escopo: bug encontrado durante a sprint vira issue, não commit inline

---

## Problema

Descrição clara do problema que esta sprint resolve.
Incluir evidências: logs, caminhos de arquivo, comportamento observado.
Incluir fluxo de código se aplicável (citar arquivo:linha).

---

## O que já existe (NÃO duplicar)

| Sistema | Arquivo | O que faz |
|---------|---------|-----------|
| (sistema) | `src/path/arquivo.py` | (descrição curta) |

---

## Implementação

### Fase 1: (título)

**Arquivo:** `src/path/arquivo.py`

(passos concretos com snippet de código quando necessário)

### Fase 2: (título)

(mais passos)

---

## Armadilhas Conhecidas

| Ref | Armadilha | Como evitar |
|-----|-----------|-------------|
| ANN | (descrição) | (regra preventiva) |

Referência: `docs/ARMADILHAS.md`

---

## Evidências Obrigatórias

- [ ] `make lint` passa sem erros
- [ ] `make process` concluído sem crash (se a sprint mexe no ETL)
- [ ] `python -m src.utils.validator` com 6/6 checagens OK
- [ ] Dashboard inicia sem erro (se a sprint mexe na UI): `make dashboard`
- [ ] Testes relevantes: `.venv/bin/pytest tests/<arquivo>.py -x -q`
- [ ] Documentação viva: `CLAUDE.md` e/ou `ROADMAP.md` atualizados se a sprint muda contexto

---

## Conferência Artesanal Opus

Seção obrigatória para sprints de feature/infra que tocam em catalogação, extração ou linking. Sprints puramente de bugfix podem pular (teste de regressão já cobre).

Descreve o que o **supervisor artesanal (Claude Code Opus via sessão)** deve fazer antes de a sprint ser considerada fechada:

1. **Arquivos originais a ler** (lista explícita de amostras em `data/raw/` ou `data/input/`):
   - `data/raw/.../arquivo_A.pdf`
   - `data/raw/.../arquivo_B.jpg`
   - (mínimo 3 amostras por tipo de documento coberto)

2. **Outputs a comparar** (o que o pipeline determinístico produziu):
   - `data/output/ouroboros_YYYY.xlsx`, aba `<aba>`
   - `data/output/catalogo/documento_<id>.json` (quando existir)
   - `data/output/grafo.sqlite` (query específica)

3. **Checklist de conferência** (o que eu, Opus, devo validar arquivo por arquivo):
   - Nome renomeado corretamente? (ex: `NF_20260419_AMERICANAS_12345.pdf`)
   - Pasta de destino correta? (ex: `data/raw/andre/nfs_fiscais/`)
   - Trackeado no grafo? (nó `Documento` existe, arestas esperadas)
   - Conteúdo extraído bate com o que está no original? (fornecedor, data, total, itens)
   - Linking com transação bancária correto? (`documento_de` aponta para transação certa)

4. **Relatório esperado** (o que apresento ao usuário ao final):
   - Markdown em `docs/propostas/sprint_NN_conferencia.md` com:
     - Tabela: arquivo | tipo | renomeação OK? | pasta OK? | extração OK? | linking OK?
     - Lista de discrepâncias encontradas
     - Propostas de regra nova em `mappings/*.yaml` (com diff)

5. **Critério de aprovação**: usuário revisa `docs/propostas/sprint_NN_conferencia.md` e aprova/rejeita item por item. Propostas aprovadas viram commits separados.

---

## Verificação end-to-end

```bash
# Comandos de verificação específicos
make lint
make process
./run.sh --check
python -m src.utils.validator
# (testes específicos da sprint)
```

---

*"Citação de filósofo/estoico/libertário em PT-BR." -- Autor*
