> **superseded_by**: `IRPF-01` (`docs/sprints/backlog/sprint_irpf_01_pacote_irpf_botao.md`).
> Conteúdo conceitual desta spec foi absorvido em IRPF-01 do plan pure-swinging-mitten (2026-04-29). Mantida em backlog/ como referência histórica até IRPF-01 ser concluída.

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 25
  title: "Pacote IRPF: gerador completo de declaração anual"
  touches:
    - path: src/irpf/__main__.py
      reason: "entrypoint python -m src.irpf --ano YYYY gera pacote completo"
    - path: src/irpf/organizador.py
      reason: "cria data/output/irpf_{ano}/ com subpastas rendimentos/, deducoes_medicas/, impostos/, isentos/"
    - path: src/irpf/simulador.py
      reason: "simula regimes completo vs simplificado e imprime comparativo"
    - path: src/irpf/resumo.py
      reason: "resumo Markdown por tipo de tag IRPF"
    - path: src/transform/irpf_tagger.py
      reason: "extração CNPJ aprimorada para cobrir casos residuais da Sprint 23"
    - path: mappings/irpf_regras.yaml
      reason: "consumidor do YAML já entregue pela Sprint 35"
  n_to_n_pairs:
    - [src/irpf/organizador.py, src/irpf/resumo.py]
    - [src/irpf/simulador.py, mappings/irpf_regras.yaml]
  forbidden:
    - src/pipeline.py  # IRPF é comando separado, não entra no pipeline mensal
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: "python -m src.irpf --ano 2027 --dry-run"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/test_irpf_simulador.py -x -q"
      timeout: 60
  acceptance_criteria:
    - "./run.sh --irpf 2027 gera data/output/irpf_2027/ com subpastas organizadas"
    - "Resumo Markdown por tipo lista total e contagem de transações"
    - "Simulador imprime regime completo vs simplificado com números reais"
    - "Extração CNPJ cobre >= 90% das transações com tag dedutível"
    - "IRPF 2026 já declarado manualmente não é impactado"
    - "Acentuação PT-BR correta em todos os arquivos"
    - "Zero emojis e zero menções a IA"
```

> Executar antes de começar: `make lint && ./run.sh --check`

---

# Sprint 25 -- Pacote IRPF: gerador completo de declaração anual

**Status:** PENDENTE
**Data:** 2026-04-18
**Prioridade:** BAIXA
**Tipo:** Feature
**Dependências:** Sprint 24 (Automação Bancária), Sprint 35 (IRPF Regras YAML)
**Desbloqueia:** Nenhuma
**Issue:** --
**ADR:** --

---

> **Nota de contexto:** sprint pós-plano 30/60/90. Requer Sprint 35 (regras IRPF em YAML) e Sprint 24 (contracheques via automação bancária) maduras. IRPF 2026 já foi declarado manualmente em 14/04/2026 -- esta sprint cobre 2027+ com pacote completo gerado automaticamente.

---

## Como Executar

**Comandos principais:**
- `make lint`
- `./run.sh --irpf 2027` -- gera pacote completo em `data/output/irpf_2027/`
- `python -m src.irpf --ano 2027 --dry-run` -- simula sem escrever
- `.venv/bin/pytest tests/test_irpf_simulador.py -x -q`

### O que NÃO fazer

- NÃO gerar dados para 2026 (já declarado manualmente).
- NÃO substituir `src/transform/irpf_tagger.py` (Sprint 35 já o refatorou em YAML).
- NÃO adivinhar CNPJ: só aceita via regex determinística (Sprint 23).
- NÃO integrar ao pipeline mensal: IRPF é comando anual separado.

---

## Problema

Preparar a papelada anual do IR é trabalhoso: extrair CNPJs, organizar informes de rendimento, consolidar deduções médicas, simular regimes (completo vs simplificado) e montar pastas separadas para cada tipo de dedução. Hoje tudo é manual; a aba `irpf` do XLSX tem os dados, mas o pacote para declaração não é gerado.

Com Sprints 23 e 35 concluídas (CNPJ via regex + regras IRPF em YAML), esta sprint fecha o ciclo: automatiza a montagem da papelada anual.

---

## O que já existe (NÃO duplicar)

| Sistema | Arquivo | O que faz |
|---------|---------|-----------|
| IRPF tagger | `src/transform/irpf_tagger.py` | 21 regras em 5 tipos, CNPJ via regex (Sprint 23) |
| Regras IRPF YAML | `mappings/irpf_regras.yaml` | Fonte editável de regras (Sprint 35) |
| Aba IRPF | `src/load/xlsx_writer.py` | 79 registros em 5 tipos, 14 com CNPJ |
| Entrypoint IRPF | `src/irpf/__main__.py` | Criado na Sprint 22; imprime CSV por ano |

---

## Implementação

### Fase 1: organizador de pastas

**Arquivo:** `src/irpf/organizador.py`

Cria `data/output/irpf_{ano}/` com subpastas:

- `rendimentos/` -- informes de rendimento (tributáveis, isentos, RRA)
- `deducoes_medicas/` -- notas fiscais médicas, exames, planos
- `impostos/` -- DARF, carnê-leão, IRRF retido
- `isentos/` -- poupança, FGTS, indenizações

Cada subpasta recebe CSV do ano com linhas correspondentes do XLSX e cópias dos PDFs originais em `data/raw/` referenciados por hash.

### Fase 2: extração CNPJ aprimorada

**Arquivo:** `src/transform/irpf_tagger.py`

Expandir regex para casos residuais deixados pela Sprint 23:

- CNPJ sem pontuação em descrições truncadas.
- CNPJ em segunda linha de descrição (Nubank PDF).
- CPF em cupons fiscais isentos.

Meta: cobrir >= 90% das transações com tag dedutível.

### Fase 3: resumo Markdown por tipo

**Arquivo:** `src/irpf/resumo.py`

Gera `data/output/irpf_{ano}/resumo.md` com seções:

```markdown
## Resumo IRPF {ano}

### Rendimentos tributáveis
- Total: R$ 120.000,00
- Fontes: 3 (G4F, Sicoob, BCB)
- Informes coletados: 3/3

### Deduções médicas
- Total: R$ 4.500,00
- 12 transações, 8 com CNPJ, 4 para revisão
- Prestadores: Unimed (R$ 3.200), Hapvida (R$ 800), ...
```

### Fase 4: integração com programa IRPF da Receita

**Arquivo:** `src/irpf/exportador.py`

Gera exports compatíveis:
- CSV nos formatos aceitos pelo programa IRPF.
- Estrutura DBK/DEC quando o layout for estável e documentado.

Prioridade: começar pelo CSV por seção, deixar DBK como feature opcional.

### Fase 5: simulador completo vs simplificado

**Arquivo:** `src/irpf/simulador.py`

Calcula:

- **Simplificado:** desconto de 20% sobre rendimentos tributáveis (limite anual atualizado).
- **Completo:** deduções médicas + educação + dependentes + previdência + INSS.

Imprime comparativo:

```
Regime simplificado: IR devido R$ 18.234,00
Regime completo:     IR devido R$ 15.987,00
Economia completo:   R$ 2.247,00 (12,3%)
```

---

## Armadilhas Conhecidas

| Ref | Armadilha | Como evitar |
|-----|-----------|-------------|
| A25-1 | Informe de rendimentos vem do empregador e não tem extrator | Entrada manual via `mappings/contracheques/{ano}.yaml` enquanto Sprint 24 não cobre |
| A25-2 | CNPJ ilegível em cupom térmico | Marcar como `revisao_humana`; não inventar |
| A25-3 | DAS MEI da Vitória requer CNPJ da MEI como contribuinte | Regra específica no YAML para isolar DAS da Vitória |
| A25-4 | Tabelas IRPF mudam a cada ano | Valores hardcoded proibidos; carregar de `mappings/irpf_tabelas/{ano}.yaml` |
| A25-5 | CSV de exportação pode ter encoding latin-1 | Testar com programa oficial antes de considerar pronto |
| A25-6 | Regime simplificado tem teto anual | Respeitar teto do ano em `mappings/irpf_tabelas/{ano}.yaml` |

Referência: `docs/ARMADILHAS.md`

---

## Evidências Obrigatórias

- [ ] `make lint` passa sem erros
- [ ] `./run.sh --irpf 2027` conclui sem crash
- [ ] `data/output/irpf_2027/` existe com 4 subpastas preenchidas
- [ ] Resumo Markdown gerado com totais e contagens
- [ ] Simulador imprime comparativo completo vs simplificado
- [ ] Extração CNPJ cobre >= 90% das transações dedutíveis
- [ ] Teste unitário de simulador passa para entradas conhecidas
- [ ] 2026 não é impactado (já declarado manualmente)

---

## Verificação end-to-end

```bash
make lint
./run.sh --irpf 2027
ls data/output/irpf_2027/
cat data/output/irpf_2027/resumo.md
.venv/bin/pytest tests/test_irpf_simulador.py -v
```

---

*"Na vida, nada deve ser temido, somente compreendido." -- Marie Curie*
---

## Papel do supervisor (Opus Claude Code)

Conforme ADR-13 e `docs/SUPERVISOR_OPUS.md`, eu (Opus principal nesta sessão interativa) sou o supervisor — não um cliente Anthropic API, não cron. Quando esta spec mencionar "LLM" ou "IA", entenda como "eu, Opus interativo nesta sessão", agindo via:

- Leitura artesanal de arquivos via `Read` tool (PDF/foto/XML).
- Edit tool sobre `mappings/`, `src/`, `docs/propostas/` — propostas viram regras YAML após aprovação humana.
- Despacho de subagent `executor-sprint` em worktree isolado via Agent tool quando o trabalho exige isolamento.
- Slash commands `/propor-extrator`, `/auditar-cobertura`, `/sprint-ciclo` quando o dono pedir.

**NÃO implementar `src/llm/`, `pip install anthropic`, `cost_tracker`, ou qualquer chamada API programática.** Regra inviolável (ADR-13).
