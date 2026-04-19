> **ARQUIVADA em 2026-04-19** -- absorvida em 53 (Grafo Visual + Obsidian Rico). Conteúdo preservado abaixo para referência histórica.

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 29b
  title: "UX Rica -- grafo visual e Obsidian enriquecido"
  touches:
    - path: src/dashboard/paginas/grafo_visual.py
      reason: "visualização pyvis interativa"
    - path: src/dashboard/paginas/vida_boleto.py
      reason: "timeline visual da jornada do documento"
    - path: src/obsidian/sync.py
      reason: "frontmatter ampliado + links de entidade"
    - path: src/obsidian/templates/entidade.md
      reason: "template de nota por entidade com Dataview"
    - path: src/obsidian/moc.py
      reason: "gerador de Map of Content por mês/categoria/entidade"
  n_to_n_pairs:
    - [src/dashboard/paginas/grafo_visual.py, src/graph/visual.py]
    - [src/obsidian/sync.py, src/obsidian/templates/entidade.md]
  forbidden:
    - src/graph/models.py  # só consome
    - src/search/*         # não mexe na busca
  tests:
    - cmd: "make lint"
      timeout: 60
  acceptance_criteria:
    - "MOC gerado para 3 meses representativos"
    - "queries Dataview funcionais no vault"
    - "zero frontmatter nulo no sync Obsidian"
    - "grafo visual carrega em < 5s para subgrafo de 50 nós"
    - "Acentuação PT-BR correta"
    - "Zero emojis e zero menções a IA"
```

---

# Sprint 29b -- UX Rica: grafo visual e Obsidian enriquecido

**Status:** OBSOLETA
**Data:** 2026-04-18
**Prioridade:** BAIXA
**Tipo:** Feature
**Dependências:** Sprint 27b (motores avançados do grafo), Sprint 29a (busca e timeline)
**Desbloqueia:** --
**Issue:** (a criar quando a sprint for ativada)
**ADR:** --

---

## Como Executar

Sprint de visão pós-90 dias. Só abrir quando:
- Sprint 27b em produção (Motor 1 e Motor 3 funcionando)
- Sprint 29a em produção há pelo menos 30 dias
- Vault Obsidian do André estável, sem bugs residuais de sync

### O que NÃO fazer

- NÃO ultrapassar 30 campos por frontmatter (Obsidian renderiza lento)
- NÃO renderizar `pyvis` com >500 nodes sem amostragem
- NÃO substituir a busca da Sprint 29a pelo grafo visual -- é complementar

---

## Problema

Após 29a, o usuário já tem busca, consulta natural e timeline -- mas falta:
1. **Visualização exploratória**: entender relações não-óbvias ("quais entidades pagam de cartões diferentes?").
2. **Jornada do documento**: boleto chega -> é reconhecido -> é categorizado -> é pago -> entra no IRPF. Hoje isso é invisível.
3. **Obsidian pobre**: o sync atual gera relatórios básicos. O usuário quer explorar finanças no próprio vault com Dataview, MOC e backlinks.

Esta sprint complementa 29a com a camada visual rica e Obsidian enriquecido.

---

## O que já existe (NÃO duplicar)

| Sistema | Arquivo | O que faz |
|---------|---------|-----------|
| Busca global | `src/dashboard/paginas/busca.py` | Sprint 29a |
| Timeline entidade | `src/dashboard/paginas/entidade.py` | Sprint 29a |
| Motor 1 | `src/graph/linker.py` | Sprint 27b |
| Motor 3 | `src/graph/event_detector.py` | Sprint 27b |
| Sync Obsidian | `src/obsidian/sync.py` | frontmatter básico (Sprint 06 + bugs da 22) |

---

## Implementação

### Fase 1: Grafo visual

**Arquivo:** `src/dashboard/paginas/grafo_visual.py` + reusa `src/graph/visual.py` (Sprint 27b)

- Input: nó inicial + profundidade (1 a 3).
- Filtros por tipo de nó.
- Cores por tipo; hover mostra atributos.
- Clique em nó -> abre timeline correspondente (usa Sprint 29a).
- Amostragem obrigatória para hubs com >100 vizinhos.

### Fase 2: "Vida de um Boleto"

**Arquivo:** `src/dashboard/paginas/vida_boleto.py`

Timeline vertical com etapas:
1. Emitido (fonte: email, inbox, Gmail)
2. Reconhecido (OCR -- Sprint 32 via visão)
3. Vinculado (transação via Motor 1 da Sprint 27b)
4. Pago (data + conta)
5. IRPF (se dedutível)

PDF embedded na lateral; histórico de mudanças no grafo exibido como auditoria.

### Fase 3: Obsidian enriquecido

**Arquivos:** `src/obsidian/sync.py` (refactor) + `src/obsidian/templates/entidade.md` + `src/obsidian/moc.py`

- Frontmatter ampliado (máx. 30 campos): slug, CNPJ, total_12m, média_mensal, última_transação, tags, backlinks.
- Notas por entidade em `Entidades/`, com Dataview:
  ```
  TABLE data, valor, conta, doc_link
  FROM "Pessoal/Financeiro/Relatorios"
  WHERE contains(file.text, "{slug}")
  SORT data DESC
  ```
- MOC por mês: `MOC/2026-03.md` lista categorias -> entidades -> transações top.
- MOC por categoria: `MOC/Categorias/Saude.md` agrega entidades e meses.
- Attachments em `Attachments/Boletos/{slug}-{periodo}.pdf`, naming determinístico.

---

## Armadilhas Conhecidas

| Ref | Armadilha | Como evitar |
|-----|-----------|-------------|
| A29b-1 | Obsidian lento com frontmatter muito grande | Limite 30 campos; resto vai para corpo |
| A29b-2 | `pyvis` travando navegador | Amostragem + limite 500 nodes visíveis |
| A29b-3 | Dataview cache desatualizado | Documentar comando de reindex; aviso ao usuário |
| A29b-4 | Backlinks circulares travando Dataview | Limitar profundidade nas queries |
| A29b-5 | Attachments duplicados | Chave única determinística `{slug}-{periodo}.pdf` |
| A29b-6 | PDFs sincronizados para iCloud vazando | Documentar privacidade; `.gitignore` + opt-in |

Referência: `docs/ARMADILHAS.md`

---

## Evidências Obrigatórias

- [ ] `make lint` passa
- [ ] MOC gerado para 3 meses representativos (ex.: 2026-01, 2026-02, 2026-03)
- [ ] Queries Dataview funcionais no vault real do André
- [ ] Zero frontmatter nulo -- validador `src/obsidian/validator.py` confirma
- [ ] Grafo visual carrega em < 5s para subgrafo de 50 nós
- [ ] "Vida de um Boleto" renderiza para pelo menos 10 documentos
- [ ] `make process` sem regressão no XLSX

---

## Verificação end-to-end

```bash
make lint
python -m src.obsidian.sync --dry-run
python -m src.obsidian.moc --mes 2026-03
make dashboard  # validar grafo_visual e vida_boleto
```

---

*"A simplicidade é a sofisticação suprema." -- Leonardo da Vinci*
