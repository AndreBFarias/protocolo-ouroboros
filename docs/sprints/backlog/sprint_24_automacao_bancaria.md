## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 24
  title: "Automação Bancária: Open Finance e download não-manual"
  touches:
    - path: src/integrations/belvo_sync.py
      reason: "integração Belvo em produção"
    - path: src/integrations/gmail_csv.py
      reason: "watcher de anexos Gmail para CSVs e PDFs bancários"
    - path: src/extractors/ofx_parser.py
      reason: "parser OFX para exports manuais via ofxparse"
    - path: src/pipeline.py
      reason: "registrar entrypoints de automação antes dos extratores atuais"
  n_to_n_pairs:
    - [src/integrations/belvo_sync.py, mappings/senhas.yaml]
    - [src/integrations/gmail_csv.py, mappings/gmail_filtros.yaml]
  forbidden:
    - src/transform/  # sprint de integração, não toca em categorização
    - src/load/       # nem em carga final
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/test_ofx_parser.py -x -q"
      timeout: 60
  acceptance_criteria:
    - "Sincronização Belvo funcional contra sandbox (sem custo) e produção (quando orçamento autorizar)"
    - "Gmail CSV watcher identifica anexos de Itaú, Santander e Nubank e deposita em inbox"
    - "OFX parser lê exports manuais dos 4 bancos e gera DataFrame compatível com pipeline"
    - "Consentimento Open Finance documentado (validade 12 meses, renovação agendada)"
    - "Integrações externas são opcionais: sistema roda sem Belvo nem Gmail configurados"
    - "Acentuação PT-BR correta em todos os arquivos"
    - "Zero emojis e zero menções a IA"
```

> Executar antes de começar: `make lint && ./run.sh --check`

---

# Sprint 24 -- Automação Bancária: Open Finance e download não-manual

**Status:** PENDENTE
**Data:** 2026-04-18
**Prioridade:** BAIXA
**Tipo:** Feature
**Dependências:** Sprint 36 (métricas IA saudáveis antes de expandir ingestão)
**Desbloqueia:** Sprint 25 (Pacote IRPF)
**Issue:** --
**ADR:** --

---

> **Nota de contexto:** esta sprint está fora do escopo do plano 30/60/90 e só deve ser atacada após a Fase 3 estar estabilizada. Integrações externas complexas (Belvo produção, Open Finance, Gmail watcher) não são condição para o sistema virar inteligente -- o pipeline funciona hoje com ingestão manual. Esta sprint é **pós-90d** e prioridade BAIXA por escolha consciente.

---

## Como Executar

**Comandos principais:**
- `make lint`
- `python -m src.integrations.belvo_sync` -- sincroniza contas via Belvo
- `python -m src.integrations.gmail_csv` -- baixa anexos bancários do Gmail
- `.venv/bin/pytest tests/test_ofx_parser.py -x -q`
- `./run.sh --tudo` -- pipeline completo com automações habilitadas

### O que NÃO fazer

- NÃO iniciar antes da Sprint 36 (métricas IA saudáveis) estar fechada.
- NÃO depender de `pynubank` (morto desde ago/2023 por exigência de verificação facial).
- NÃO depender de `itauscraper` (abandonado, URLs mudam sem aviso).
- NÃO armazenar senhas bancárias em claro no código: usar `mappings/senhas.yaml` ou consentimento Open Finance.
- NÃO introduzir dependência paga sem revisar o orçamento mensal.

---

## Problema

O download de extratos é hoje 100% manual. Cada ciclo mensal exige: abrir 4 apps de banco (Itaú, Santander, C6, Nubank PF/PJ), exportar PDF ou CSV, transferir para o computador, mover para `data/raw/{pessoa}/{banco}/`. Multiplicado por 2 pessoas (André e Vitória), são pelo menos 6-8 fluxos manuais por mês.

Sem automação, o pipeline inteiro depende da disciplina de downloads humanos, e atrasos viram lacuna de dados visível na aba `extrato`.

---

## O que já existe (NÃO duplicar)

| Sistema | Arquivo | O que faz |
|---------|---------|-----------|
| Belvo sync | `src/integrations/belvo_sync.py` | Scaffolding inicial com SDK Belvo (em teste) |
| Gmail CSV | `src/integrations/gmail_csv.py` | Watcher de anexos CSV no Gmail (setup pendente) |
| MeuPluggy | `src/integrations/README.md` | Documentação de disponibilidade; não implementado |
| ofx-bot | referência externa | Projeto aberto com Selenium para Itaú/Santander |
| Extratores | `src/extractors/` | 8 extratores atuais processam o que já está em `data/raw/` |

---

## Implementação em camadas

### Camada 1: MeuPluggy (gratuito)

Piloto do app MeuPluggy (gratuito para uso pessoal) como fonte de dados. Usuário autoriza no app, sistema consome via webhooks ou exportação manual. Valida fluxo de consentimento sem custo.

**Limitação:** dados incompletos em alguns bancos; bom para Itaú e Santander, fraco para Nubank PF/PJ.

### Camada 2: Export OFX manual + `ofxparse`

**Arquivo:** `src/extractors/ofx_parser.py`

Para bancos sem integração direta, exportar OFX pelo app/navegador e processar com `ofxparse`:

```python
from ofxparse import OfxParser

def extrair_ofx(caminho: Path) -> pd.DataFrame:
    with open(caminho, "rb") as f:
        ofx = OfxParser.parse(f)
    linhas = []
    for account in ofx.accounts:
        for tx in account.statement.transactions:
            linhas.append({
                "data": tx.date,
                "valor": float(tx.amount),
                "descricao": tx.payee or tx.memo or "",
                "id_banco": tx.id,
                "banco_origem": _detectar_banco(account.institution),
            })
    return pd.DataFrame(linhas)
```

Cobre Itaú, Santander e Nubank quando o usuário quer/precisa exportar manualmente.

### Camada 3: Pluggy MCP Server

Experimentar um MCP server que expõe dados Pluggy como ferramentas do provedor de IA (Sprint 29a "Pergunte ao sistema"). Ainda sem commit de custo pago; avaliar se sandbox Pluggy atende.

### Camada 4: Pluggy API paga (US$ 29/mês)

Se Camadas 1-3 ficarem aquém, assinar API Pluggy / Belvo em produção. Consentimento Open Finance Brasil válido por 12 meses, renovação agendada em calendário.

---

## Armadilhas Conhecidas

| Ref | Armadilha | Como evitar |
|-----|-----------|-------------|
| A24-1 | `pynubank` morta desde ago/2023 (verificação facial exigida) | Não depender; documentar em `docs/ARMADILHAS.md` |
| A24-2 | `itauscraper` abandonado e URLs mudam | Não usar como base de produção; só referência |
| A24-3 | MeuPluggy com dados incompletos em certos bancos | Validar cobertura antes de cortar export manual |
| A24-4 | Consentimento Open Finance expira em 12 meses | Agendar renovação; alerta 30 dias antes |
| A24-5 | Senhas em YAML acabam commitadas se `.gitignore` quebra | `mappings/senhas.yaml` sempre no `.gitignore`; pre-commit hook bloqueia |
| A24-6 | Custo API paga sobe silenciosamente | Kill switch por orçamento (mesma lógica de `LLM_MONTHLY_BUDGET_USD`) |

Referência: `docs/ARMADILHAS.md`

---

## Evidências Obrigatórias

- [ ] `make lint` passa sem erros
- [ ] Sincronização Belvo funcional contra sandbox
- [ ] OFX parser lê arquivos dos 4 bancos sem erro (fixture mínima em `tests/fixtures/`)
- [ ] Gmail CSV watcher identifica >= 3 tipos de anexo bancário em teste
- [ ] Consentimento Open Finance registrado em `docs/ADR/` com data de renovação
- [ ] Sistema continua executando `./run.sh --tudo` sem Belvo/Gmail configurados

---

## Verificação end-to-end

```bash
make lint
.venv/bin/pytest tests/test_ofx_parser.py -x -q
python -m src.integrations.belvo_sync --dry-run
python -m src.integrations.gmail_csv --dry-run
./run.sh --tudo
```

---

*"Tempo é o recurso mais escasso; a menos que seja gerenciado, nada mais pode ser gerenciado." -- Peter Drucker*
---

## Papel do supervisor (Opus Claude Code)

Conforme ADR-13 e `docs/SUPERVISOR_OPUS.md`, eu (Opus principal nesta sessão interativa) sou o supervisor — não um cliente Anthropic API, não cron. Quando esta spec mencionar "LLM" ou "IA", entenda como "eu, Opus interativo nesta sessão", agindo via:

- Leitura artesanal de arquivos via `Read` tool (PDF/foto/XML).
- Edit tool sobre `mappings/`, `src/`, `docs/propostas/` — propostas viram regras YAML após aprovação humana.
- Despacho de subagent `executor-sprint` em worktree isolado via Agent tool quando o trabalho exige isolamento.
- Slash commands `/propor-extrator`, `/auditar-cobertura`, `/sprint-ciclo` quando o dono pedir.

**NÃO implementar `src/llm/`, `pip install anthropic`, `cost_tracker`, ou qualquer chamada API programática.** Regra inviolável (ADR-13).
