# Guia de Ingestão de Documentos no Grafo

Este documento explica como jogar PDFs, fotos de cupons, XML de NFe e outros documentos no sistema para que virem nós no grafo SQLite (`data/output/grafo.sqlite`) e apareçam na página Catalogação do dashboard.

Base empírica: auditoria 2026-04-21 descobriu que as features das Sprints 47a, 47b, 48, 49 e 50 estavam com pytest verde, mas o grafo runtime tinha apenas 2 documentos. O plumbing funciona; faltava colocar os arquivos reais nas pastas e rodar o reprocessamento.

---

## 1. Onde colocar cada tipo de arquivo

Existem dois fluxos: **inbox triada** (automático, recomendado para usuário final) e **raw direto** (quando o arquivo já está no nome/pasta correta).

### 1.1 Fluxo triado: `data/inbox/`

Jogue o arquivo em `data/inbox/` sem se preocupar com nome ou pasta. O intake (`./run.sh --inbox`) detecta o tipo por magic bytes + regex de conteúdo (via `mappings/tipos_documento.yaml`), renomeia com SHA8 + data e move para a pasta canônica.

Extensões aceitas: `.pdf`, `.xml`, `.eml`, `.zip`, `.jpg`, `.jpeg`, `.png`, `.heic`, `.heif`, `.webp`, `.csv`, `.xlsx`, `.xls`, `.ofx`, `.txt`.

### 1.2 Fluxo direto: `data/raw/<pessoa>/<tipo>/`

Para quem já conhece a convenção. As pastas canônicas são:

| Tipo de arquivo                    | Pasta destino                                      | Extrator                                       |
|------------------------------------|----------------------------------------------------|------------------------------------------------|
| DANFE NFe modelo 55 (PDF A4)       | `data/raw/<pessoa>/nfs_fiscais/`                  | `src.extractors.danfe_pdf`                     |
| NFC-e modelo 65 (mini-cupom QR)    | `data/raw/<pessoa>/nfs_fiscais/nfce/`             | `src.extractors.nfce_pdf`                      |
| XML NFe (arquivo técnico SEFAZ)    | `data/raw/<pessoa>/nfs_fiscais/`                  | `src.extractors.xml_nfe`                       |
| Cupom de garantia estendida SUSEP  | `data/raw/casal/garantias_estendidas/`            | `src.extractors.cupom_garantia_estendida_pdf`  |
| Termo de garantia de fabricante    | `data/raw/<pessoa>/garantias/`                    | `src.extractors.garantia`                      |
| Receita médica / prescrição        | `data/raw/<pessoa>/saude/receitas/`               | `src.extractors.receita_medica`                |
| Cupom fiscal térmico fotografado   | `data/raw/<pessoa>/cupons_foto/`                  | `src.extractors.cupom_termico_foto`            |
| Holerite / contracheque            | `data/raw/<pessoa>/holerites/`                    | `src.extractors.contracheque_pdf`              |
| Fatura Santander (PDF cartão)      | `data/raw/<pessoa>/santander_cartao/`             | `src.extractors.santander_pdf`                 |
| Extrato Itaú (PDF CC)              | `data/raw/<pessoa>/itau_cc/`                      | `src.extractors.itau_pdf`                      |
| Conta de luz (OCR)                 | `data/raw/<pessoa>/energia/`                      | `src.extractors.energia_ocr`                   |
| Recibo não-fiscal (catch-all)      | `data/raw/<pessoa>/recibos/`                      | `src.extractors.recibo_nao_fiscal`             |

O campo `<pessoa>` é `andre`, `vitoria` ou `casal`. Quando indeterminado, use `data/raw/_classificar/`.

---

## 2. Como rodar o pipeline manualmente

### 2.1 Triagem de inbox

```bash
./run.sh --inbox
```

Detecta, renomeia e move tudo de `data/inbox/` para `data/raw/<pessoa>/<tipo>/`. Não ingere no grafo por si só; só arruma.

### 2.2 Reprocessamento documental completo (Sprint 57)

```bash
.venv/bin/python scripts/reprocessar_documentos.py --dry-run
.venv/bin/python scripts/reprocessar_documentos.py
```

- `--dry-run` (rápido): lista o que seria ingerido, sem abrir PDF nem modificar o grafo.
- Sem flag: abre cada PDF/XML/foto, chama o extrator documental correspondente e ingere no grafo. Ao final, roda as três fases pós-ingestão:
  - **Sprint 48** — `linkar_documentos_a_transacoes` (aresta `documento_de`, ligando nó `documento` a nó `transacao` por CNPJ + data + valor).
  - **Sprint 49** — `executar_er_produtos` (aresta `mesmo_produto_que`, ligando nó `item` a nó `produto_canonico` quando a descrição casa).
  - **Sprint 50** — `categorizar_todos_items_no_grafo` (aresta `categoria_de`, ligando nó `item` a nó `categoria` via regras em `mappings/categorias_item.yaml`).

O script é **idempotente**: rodar duas vezes não duplica nós (chave_44, chave_garantia, chave_prescricao etc. são únicas).

### 2.3 Pipeline completo

```bash
./run.sh --tudo
```

Processa CSVs/XLS/OFX → XLSX consolidado → relatórios MD → sincroniza grafo (passos 12-14 do pipeline). Não abre documentos fiscais que não estejam casados com algum extrator auto-descoberto; para isso, use o script da Sprint 57.

### 2.4 Dashboard (checagem visual)

```bash
./run.sh --dashboard
```

Abre Streamlit na porta 8501. Páginas relevantes:
- **Catalogação de Documentos** (Sprint 51): tabela + filtros por tipo; contador no topo deve refletir o grafo populado.
- **Busca global** (Sprint 52): rastreia entidades (médico, fornecedor, produto) em todas as compras.
- **Grafo** (Sprint 53): visualização interativa dos nós e arestas.

---

## 3. Como verificar o resultado no grafo

```bash
.venv/bin/python - <<'EOF'
import sqlite3
con = sqlite3.connect('data/output/grafo.sqlite')
cur = con.cursor()
for tipo in ('documento', 'item', 'fornecedor', 'prescricao', 'garantia', 'apolice'):
    n = cur.execute("SELECT COUNT(*) FROM node WHERE tipo=?", (tipo,)).fetchone()[0]
    print(f"node.{tipo} = {n}")
for tipo in ('contem_item', 'fornecido_por', 'documento_de', 'mesmo_produto_que', 'categoria_de', 'cobre'):
    n = cur.execute("SELECT COUNT(*) FROM edge WHERE tipo=?", (tipo,)).fetchone()[0]
    print(f"edge.{tipo} = {n}")
EOF
```

**Baseline esperado após primeiro reprocessamento** (depende do volume real em `data/raw/`):
- `node.documento >= 2` (ao menos as 2 NFC-es de referência de Americanas)
- `node.item >= 33`
- `edge.contem_item >= 33`
- `edge.ocorre_em >= nodes.documento + nodes.transacao`
- `edge.categoria_de >= 1` por item cuja descrição casa em `categorias_item.yaml`

**Baseline pós-ingestão de volume real** (acceptance da Sprint 57):
- `node.documento >= 20`
- `node.item >= 100`
- `node.fornecedor` com >=3 entidades que têm >=2 documentos cada
- `edge.documento_de >= 5`
- `edge.mesmo_produto_que >= 3`
- `edge.categoria_de >= 50`

---

## 4. Qual sprint depende de qual tipo de arquivo

| Sprint | Feature                                      | Tipo de arquivo que ativa a feature       |
|--------|----------------------------------------------|-------------------------------------------|
| 42     | Grafo SQLite mínimo                          | XLSX do pipeline principal                |
| 44     | DANFE NFe55                                  | PDF A4 de nota fiscal eletrônica modelo 55|
| 44b    | NFC-e modelo 65                              | Mini-cupom QR SEFAZ                       |
| 45     | Cupom fiscal térmico fotografado             | Foto JPG/PNG/HEIC de cupom de loja        |
| 46     | XML NFe                                      | Arquivo XML técnico da SEFAZ              |
| 47     | Recibo não-fiscal (catch-all)                | PDF/foto de recibo sem CNPJ estruturado   |
| 47a    | Receita médica + prescrição                  | PDF/foto de receituário com CRM           |
| 47b    | Termo de garantia de fabricante              | PDF de garantia de produto                |
| 47c    | Apólice de garantia estendida SUSEP          | PDF de bilhete SUSEP                      |
| 48     | Linking documento ↔ transação                | Precisa `node.documento` + `node.transacao` não vazios |
| 49     | Entity resolution de produtos                | Precisa `node.item` com descrições repetidas |
| 50     | Categorização de itens                       | Precisa `node.item` + `mappings/categorias_item.yaml`  |
| 51     | Dashboard — página Catalogação               | Consome `node.documento`                  |
| 52     | Dashboard — busca global                     | Consome `node.fornecedor`, `node.item`, aliases |
| 53     | Dashboard — grafo visual                     | Consome arestas de todos os tipos         |

---

## 5. Armadilhas conhecidas

### 5.1 Arquivo fica em `data/raw/_classificar/`

O intake não conseguiu casar nenhuma regra do YAML. Causas comuns:
- PDF scaneado sem texto (OCR não rodou). Solução: abrir no visualizador e confirmar que há texto selecionável.
- Tipo novo que ainda não tem regra. Solução: adicionar entrada em `mappings/tipos_documento.yaml` ou mover manualmente para a pasta correta.

### 5.2 Reprocessamento lento (~3s/PDF)

Cada extrator abre o PDF com pdfplumber para `pode_processar` + `extrair`. Em 170 PDFs, são ~8 minutos. O `--dry-run` é rápido (só inspeciona path, sem abrir arquivo).

### 5.3 Arestas duplicadas se regras mudam entre rodadas

O grafo é idempotente por chave única (chave_44, chave_garantia etc.), mas arestas `categoria_de` podem acumular se `mappings/categorias_item.yaml` mudar entre rodadas (ver minúcia M50-1 no VALIDATOR_BRIEF). Correção: sprint 50b dedicada (backlog).

### 5.4 Spec da Sprint 57 cita `pago_com`, código usa `documento_de`

A aresta entre nó `documento` e nó `transacao` se chama `documento_de` (definida em `src/graph/linking.py:49`). O spec usou o termo informal `pago_com`; scripts e testes deste repo usam o nome canônico do código.

---

*"Cada documento é um nó; cada nó é uma memória." — princípio de arquivista*
