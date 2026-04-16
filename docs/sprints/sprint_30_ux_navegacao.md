# Sprint 30 -- UX Navegável: Busca, Timeline, Grafo Visual e Obsidian Rico

## Status: Pendente (proposta 2026-04-16)
Issue: #14

## Objetivo

Entregar a **camada de interface** que torna visível todo o trabalho das Sprints 27-29. Cada peça do sistema (transação, documento, entidade, evento, pessoa, assinatura) precisa ser navegável: buscável, abrível, cruzável, linkável no Obsidian. Sem essa sprint, o grafo é invisível e o usuário continua dependente de abrir CSV/XLSX.

É a ponte entre "o sistema sabe" e "o usuário vê e usa".

---

## 4 Entregáveis centrais

### 1. Busca global (campo único inteligente)
### 2. Timeline por entidade / evento / periodo
### 3. Navegador de grafo visual interativo
### 4. Obsidian rico (notas por entidade + attachments + backlinks)

Mais 2 entregáveis de suporte:

### 5. "Abrir PDF original" em qualquer lugar
### 6. Página "Vida de um Boleto"

---

## 1. Busca global

Um único campo de texto no dashboard que casa:
- **Entidade** ("neoenergia" -> nó Entidade + tudo ligado)
- **Pessoa** ("Rodrigo" -> nó Pessoa com todas as transações)
- **Valor exato ou intervalo** ("R$ 450", "450-500")
- **Período** ("março 2026", "2025", "últimos 3 meses")
- **Descrição livre** ("farmácia", "combustível PJ")
- **Tag IRPF** ("dedutível médico 2025")
- **Código** (linha digitável de boleto, chave NFe)

### Implementação
- [ ] `src/dashboard/paginas/busca.py` com `st.text_input("Buscar")` no topo do dashboard (persistente em todas as páginas via sidebar).
- [ ] `src/search/parser.py` -- parser do query: detecta tipo de input por heurística (4 dígitos no final = conta, valor = busca por valor, palavra = busca textual).
- [ ] `src/search/executor.py` -- executa no grafo SQLite + indexa entidades canônicas.
- [ ] Resultado em 3 colunas: Entidades encontradas | Transações | Documentos.
- [ ] Clique em qualquer resultado -> abre a view específica (timeline da entidade, detalhe da transação, PDF do documento).
- [ ] Keyboard shortcut `/` pra focar o campo (como GitHub).

---

## 2. Timeline por entidade / evento / periodo

Dado um nó qualquer, mostrar cronologia.

### Timeline de Entidade (ex.: Neoenergia)
- [ ] `src/dashboard/paginas/entidade.py?slug=neoenergia`
- [ ] Cabeçalho: nome, CNPJ, total gasto 12m, média mensal, último pagamento.
- [ ] Gráfico de linha: valor mensal ao longo do tempo.
- [ ] Lista cronológica: cada linha tem data, valor, conta/cartão usado, link pra transação e link pra doc (se existir).
- [ ] Alertas visíveis: "aumento de 15% em fev/2026 vs jan/2026".

### Timeline de Evento (ex.: emprestimo-rodrigo-2025)
- [ ] Mesmo padrão, mas com barra de progresso (3/10 parcelas pagas).
- [ ] Projeção: quanto falta, próximo vencimento previsto.

### Timeline de Pessoa (ex.: Rodrigo)
- [ ] Saldo relacional (quanto você deve/te deve).
- [ ] Todas as transações ordenadas.
- [ ] Lista de eventos (empréstimos, dívidas em aberto).

### Timeline de Periodo (ex.: 2026-03)
- [ ] Não é novo -- reusar `src/dashboard/paginas/mes.py` existente, mas adicionar links pra entidades e docs.

---

## 3. Navegador de grafo visual

- [ ] `src/dashboard/paginas/grafo_visual.py` usando **pyvis** (Plotly também aceitável).
- [ ] Input: nó inicial + profundidade (1 a 3 níveis).
- [ ] Filtros por tipo de nó: mostrar/esconder `Transacao`, `Documento`, `Entidade`, `Evento`, `Pessoa`.
- [ ] Cores por tipo (Transacao azul, Documento verde, Entidade laranja, Pessoa roxo).
- [ ] Hover mostra atributos principais.
- [ ] Clique em nó -> abre a timeline correspondente.
- [ ] Performance: para nós com >100 vizinhos, amostrar e permitir "ver mais".

### Layout inteligente
- [ ] Forçar layout hierárquico quando há cadeia (Evento -> Transações).
- [ ] Layout force-directed quando é hub (Entidade -> muitas Transações).

---

## 4. Obsidian rico

Expandir a integração da Sprint 06 (hoje com bugs pendentes na Sprint 23) para incluir notas por entidade, evento, pessoa, assinatura e boletos.

### Estrutura no vault (`~/Controle de Bordo/`)

```
Pessoal/Financeiro/
├── Entidades/
│   ├── Neoenergia.md             <- 1 nota por entidade
│   ├── Itau.md
│   └── ...
├── Eventos/
│   ├── Emprestimo-Rodrigo-2025.md
│   └── ...
├── Pessoas/                      <- se o usuário quiser; com alias
├── Assinaturas/
│   ├── Netflix.md
│   └── ...
├── Relatorios/                   <- já existe
├── Metas/                        <- já existe
└── Attachments/
    ├── Boletos/
    │   └── neoenergia-2026-03.pdf
    └── Contratos/
```

### Cada nota de entidade
- [ ] Frontmatter YAML com tipo, CNPJ, slug, total_gasto_12m, ultima_transacao.
- [ ] Corpo: descrição + dataview query:
  ```dataview
  TABLE data, valor, conta, doc_link
  FROM "Pessoal/Financeiro/Relatorios"
  WHERE contains(file.text, "neoenergia")
  SORT data DESC
  ```
- [ ] Seção "Documentos":
  ```
  - [[Attachments/Boletos/neoenergia-2026-03.pdf|Fatura março 2026]] -- R$ 450,23
  - [[Attachments/Boletos/neoenergia-2026-02.pdf|Fatura fevereiro 2026]] -- R$ 392,10
  ```
- [ ] Seção "Eventos" (se houver cadeia detectada).

### Attachments
- [ ] `src/obsidian/attachments.py` copia PDFs/imagens ingeridos para `Attachments/` com naming padronizado.
- [ ] Backlinks automáticos: nota do doc em `Attachments/Boletos/neoenergia-2026-03.md` (metadata) aponta pra entidade.

### Entregas específicas
- [ ] Bugs da Sprint 23 corrigidos primeiro (frontmatter nulo, nomes PF/PJ).
- [ ] `src/obsidian/sync.py` estendido para gerar notas de entidade/evento/assinatura.
- [ ] Dataview queries testadas em Obsidian real (chrome MCP se possível).

---

## 5. "Abrir PDF original" em qualquer lugar

Em toda UI que mostre uma transação ligada a um documento, exibir link/ícone:
- [ ] Streamlit: usar `st.link_button("Abrir PDF", url=f"file://{path}")` (funciona em desktop).
- [ ] Dashboard XLSX: coluna `doc_url` com hyperlink (openpyxl suporta).
- [ ] Obsidian: markdown link `[[Attachments/Boletos/...|Ver boleto]]`.
- [ ] CLI: `python -m src.graph.query --transacao <id> --abrir-pdf` abre no viewer padrão.

---

## 6. Página "Vida de um Boleto"

- [ ] `src/dashboard/paginas/vida_boleto.py?doc_id=<id>`
- [ ] Timeline vertical com eventos:
  1. **Emitido** (data emissão + fonte: email, inbox, Gmail)
  2. **Reconhecido** (OCR com confiança X, tipo Y)
  3. **Vinculado** (transação Z com confidence 0.95)
  4. **Pago** (data + conta/cartão)
  5. (se existir) **Contestado** / **Estornado** / **Duplicado**
- [ ] PDF embedded na lateral (iframe).
- [ ] Histórico de mudanças no grafo (auditoria).

---

## Entregas consolidadas

- [ ] `src/dashboard/paginas/busca.py` -- busca global
- [ ] `src/dashboard/paginas/entidade.py` -- timeline de entidade
- [ ] `src/dashboard/paginas/evento.py` -- timeline de evento
- [ ] `src/dashboard/paginas/pessoa.py` -- timeline de pessoa
- [ ] `src/dashboard/paginas/grafo_visual.py` -- navegador pyvis
- [ ] `src/dashboard/paginas/vida_boleto.py` -- vida de um boleto
- [ ] `src/search/parser.py` e `src/search/executor.py`
- [ ] `src/obsidian/sync.py` -- estendido
- [ ] `src/obsidian/attachments.py` -- novo
- [ ] Templates de nota: `src/obsidian/templates/entidade.md`, `evento.md`, `assinatura.md`, `boleto.md`
- [ ] Dashboard XLSX: nova coluna `doc_url` preenchida automaticamente
- [ ] Keyboard shortcut `/` e navegação por keyboard no dashboard

---

## Arquivos novos/modificados

| Arquivo | Tipo |
|---------|------|
| `src/dashboard/paginas/{busca,entidade,evento,pessoa,grafo_visual,vida_boleto}.py` | novos |
| `src/search/*` | novo módulo |
| `src/obsidian/sync.py` | refactor grande |
| `src/obsidian/attachments.py` | novo |
| `src/obsidian/templates/*.md` | novos |
| `src/load/xlsx_writer.py` | editar (coluna doc_url) |
| `pyproject.toml` | `pyvis` |

---

## Armadilhas

1. **`file://` em Streamlit no browser**: alguns browsers bloqueiam abrir arquivos locais. Alternativa: servir via HTTP local (Streamlit já faz isso).
2. **Dataview cache**: Obsidian demora pra indexar notas novas. Avisar usuário e documentar comando de reindex.
3. **Pyvis pesado**: HTML gerado pode passar 5MB com muitos nós. Aplicar limite de vizinhança e amostragem.
4. **Backlinks circulares no Obsidian**: entidade A referencia entidade B que referencia A. Obsidian aguenta, mas Dataview pode travar. Documentar.
5. **Attachments duplicados**: mesmo PDF pode ser referenciado em múltiplas entidades. NÃO duplicar -- usar link por caminho único.
6. **Chave primária do doc**: `Attachments/Boletos/neoenergia-2026-03.pdf` precisa ser determinístico. Naming: `{slug}-{periodo}.pdf` (colisões resolvidas por hash no sufixo).
7. **Privacidade**: ao sincronizar vault com serviço (iCloud, Syncthing), PDFs vazam. Documentar.

---

## Critério de sucesso

1. Usuário digita "neoenergia março 2026" na busca -> vê a fatura PDF + pagamento correspondente em menos de 3 segundos.
2. Página "Vida de um Boleto" mostra linha completa para pelo menos 80% dos docs ingeridos.
3. Obsidian tem 30+ notas de entidade e 5+ de evento após primeiro sync; todas com dataview queries funcionais.
4. Grafo visual carrega em menos de 5 segundos para subgrafo de 50 nós.
5. Clicar em transação no XLSX abre o PDF original.
6. Pipeline principal não regride com novas features.
7. Keyboard-only navegação funciona (acessibilidade básica).

---

## Dependências

- Sprint 27 (Ingestão) -- documentos existem pra serem abertos.
- Sprint 28 (Grafo) -- dados pra serem exibidos.
- Sprint 29 (LLM) -- opcional aqui, complementa a busca com NL query.
- Sprint 23 (Consolidação) -- bugs do sync Obsidian corrigidos PRÉVIO a essa sprint.
- Sprint 21 (Dashboard Redesign) -- layout base do dashboard novo. Combinar com esta para evitar retrabalho.

---

## Ordem sugerida internamente

1. Busca global (base de tudo).
2. Timeline de entidade (valida o grafo).
3. "Abrir PDF original" (impacto alto, esforço baixo).
4. Obsidian rico (atualizar sync existente).
5. Grafo visual (opcional, mais caro).
6. Vida de um Boleto (integra tudo).

---

*"A simplicidade é a sofisticação suprema." -- Leonardo da Vinci*
