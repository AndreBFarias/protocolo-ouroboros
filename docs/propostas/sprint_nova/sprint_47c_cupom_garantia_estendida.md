---
id: 2026-04-19_sprint_47c_cupom_garantia_estendida
tipo: sprint_nova
data: 2026-04-19
status: aprovada
aprovada_em: 2026-04-19
autor_proposta: supervisor-artesanal-claude-code
sprint_contexto: 41
---

## Contexto

Durante a Conferência Artesanal Opus da Sprint 41 (intake universal), a leitura visual dos 2 PDFs reais da inbox revelou um tipo de documento **não previsto** em nenhuma sprint do backlog atual:

- `inbox/notas de garantia e compras.pdf` -- 2 das 4 páginas (pg2 e pg3) são "Cupom Bilhete de Seguro" da MAPFRE Seguros Gerais (CNPJ 61.074.175/0001-38) emitido na Americanas SA loja 0337.
- `inbox/pdf_notas.pdf` -- todas as 3 páginas são desse mesmo tipo (3 bilhetes, sendo 1 duplicata).

Total: **5 documentos lógicos** desse tipo nos 2 PDFs da inbox -- volume relevante para um único dia de coleta.

**O que é:** Bilhete de Seguro de Garantia Estendida -- uma APÓLICE DE SEGURO emitida no momento da compra, regulada pela SUSEP (Superintendência de Seguros Privados). O varejista (Americanas) atua como representante; a seguradora (MAPFRE, Cardif, etc) é quem assume o risco. O bilhete contém:

- Número do bilhete individual (15 dígitos, ex: 781000129322124)
- Processo SUSEP (ex: 15414.900147/2014-11)
- CPF do segurado
- Bem segurado (descrição de modelo/marca)
- Limite máximo de indenização (preço do produto)
- Prêmio líquido + IOF + prêmio total
- Forma de pagamento (parcela única, parcelado)
- Vigência: data início + data fim do contrato
- Cobertura: data início + data fim de cobertura de risco (geralmente começa no fim da garantia legal)
- Razão social da seguradora + CNPJ + código SUSEP
- Remuneração do representante

**Por que NÃO entra na Sprint 47b (Termo de Garantia):**

A Sprint 47b cobre `Termo de Garantia` do fabricante -- um documento de **cobertura de defeito de fabricação**, não comercializado, sem CNPJ de seguradora, sem prêmio, sem processo SUSEP. Os campos canônicos são fundamentalmente diferentes:

| Campo | Termo de Garantia (47b) | Bilhete de Seguro Garantia Estendida (47c) |
|-------|-------------------------|--------------------------------------------|
| Documento legal | Manual + termo do fabricante | Apólice de seguro regulada pela SUSEP |
| Quem emite | Fabricante do produto | Seguradora via varejo (MAPFRE, Cardif) |
| Quem paga | Embutido no preço do produto | Compra adicional explícita no PDV |
| Identificador único | Número de série + nota fiscal de origem | Número do bilhete individual (15 dígitos) |
| Valor | Não tem (cobertura grátis) | Prêmio líquido + IOF + prêmio total |
| Vigência | Data da compra + N meses (CDC: 90 dias para não-duráveis, fabricante define para duráveis) | Datas explícitas de início/fim de contrato e de cobertura |
| Tag IRPF | Nenhuma | Pode ser dedutível em alguns casos (a verificar com 47c) |
| Aresta no grafo | `garante` (Documento → Item) | `assegura` (Apólice → Item) + `emitida_por` (Apólice → Seguradora) |

Forçar os dois num extrator único geraria regex e schema-de-saída esquizofrênicos. Sprint dedicada é a opção limpa.

## Diff proposto

**1. Adicionar tipo ao YAML do intake (já incluído no ajuste da Sprint 41):**

```diff
+  - id: cupom_garantia_estendida
+    descricao: "Bilhete de Seguro de Garantia Estendida (apólice MAPFRE/Cardif via PDV)"
+    prioridade: 35
+    mimes: ["application/pdf", "image/jpeg", "image/png"]
+    regex_conteudo:
+      - "CUPOM\\s+BILHETE\\s+DE\\s+SEGURO"
+      - "GARANTIA\\s+ESTENDIDA"
+      - "Processo\\s+SUSEP"
+    extrator_sprint: 47c
+    pasta_destino_template: "data/raw/{pessoa}/garantias_estendidas/"
+    renomear_template: "GARANTIA_EST_{data:%Y%m%d}_{seguradora}_{bilhete}.{ext}"
```

**2. Criar arquivo de sprint no backlog:** `docs/sprints/backlog/sprint_47c_extrator_cupom_garantia_estendida.md` (escopo, campos canônicos, fixtures, ingestor de grafo, testes, conferência -- esqueleto criado junto desta proposta).

**3. Atualizar `docs/ROADMAP.md`** -- adicionar 47c na fase GAMA, atualizar contadores.

**4. Atualizar `CLAUDE.md` cabeçalho** -- contagem de sprints sobe de 51 para 53 (44b + 47c), backlog ativo de 18 para 20.

## Justificativa

- 5 documentos lógicos desse tipo numa única amostra (2 PDFs) já justifica volume.
- Modelagem distinta da Sprint 47b -- forçar unificação polui o schema.
- Fixtures REAIS já disponíveis (5 bilhetes reais nos 2 PDFs da inbox), o que é raro para sprints novas.
- Habilita um caso de teste de ouro para Sprint 48 (linking documento↔transação): a NFC-e Americanas R$ 629,98 (pg1 do PDF scan) tem 2 itens; os 2 cupons de garantia da pg2/pg3 (e os 3 do pdf_notas) cobrem **exatamente** esses 2 itens (mesma data, mesmo CPF segurado, mesma loja, mesmo bem). Se 48 conseguir formar o grafo NFC-e ⟶ Item ← Apólice ⟶ Seguradora corretamente nesse caso, a infra de linking está provada.

## Dependências e ordem

- **Bloqueada por:** Sprint 41 (intake roteia o tipo) + Sprint 42 (grafo recebe nó `Apolice`)
- **Desbloqueia:** Sprint 48 (linking) -- esta sprint provê os primeiros nós `Apolice`/`Seguradora` e a relação `assegura`. Sem 47c, o grafo de 48 nasce só com NFCe + transação, sem o lado seguro.
- **Paralelizável com:** 44b, 45, 46, 47, 47a, 47b -- todos os extratores GAMA são independentes entre si.

## Risco de falso-positivo da regra de roteamento

Risco baixo. As três frases combinadas (`CUPOM BILHETE DE SEGURO` + `GARANTIA ESTENDIDA` + `Processo SUSEP`) só ocorrem juntas em apólices SUSEP de garantia estendida. Documentos de seguro de outras modalidades (auto, vida, residencial) usam fraseologia diferente -- ainda assim, vale validar com fixture sintética em outro ramo de seguro durante implementação da 47c.

## Teste de regressão (placeholder, vira parte da 47c)

```bash
.venv/bin/pytest tests/test_intake_classifier.py::test_cupom_garantia_estendida_roteia_para_pasta_correta
.venv/bin/pytest tests/test_cupom_garantia_estendida_pdf.py -v   # criado pela 47c
```

## Decisão humana

**Aprovada em:** 2026-04-19
**Notas do humano:** Aprovada na Conferência Artesanal Opus da Sprint 41 -- volume real (5 bilhetes em 1 dia de inbox) e modelagem distinta da 47b justificam sprint dedicada. Implementação só inicia depois de Sprint 41 e 42 concluídas (dependência declarada na sprint).
