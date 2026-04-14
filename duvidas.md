# Duvidas, Inconsistencias e Pontos de Atencao

> Gerado apos leitura completa de todos os arquivos do projeto.
> Data: 2026-04-14

---

## 1. ESTRUTURA DE ARQUIVOS vs PROMPT

### 1.1 Organizacao atual nao bate com a proposta

O prompt-1 propoe a estrutura `data/raw/YYYY-MM/`, onde o usuario joga arquivos brutos organizados por mes. Mas os arquivos reais estao organizados por **pessoa -> banco -> arquivos soltos**, sem nenhuma separacao por mes:

```
Estrutura real:
andre/nubank/*.csv
andre/itau/*.pdf
andre/c6_senha 051273/*.xlsx
vitoria/pf_nubank/*.csv
vitoria/pj_nubank/*.csv
...

Estrutura proposta no prompt:
data/raw/2026-04/itau_extrato.pdf
data/raw/2026-04/nubank_andre.csv
...
```

**Decisao necessaria:** O pipeline precisa aceitar a estrutura real OU reorganizar os arquivos automaticamente? O usuario mencionou que quer renomeacao automatica.
Propõe uma nova estrutura real. E a renomeação e movimentação automática faz o resto.
### 1.2 Nomes de arquivo sao caoticos

O usuario confirmou: "nomes de arquivos precisam ser padronizados sempre, tipo vou jogar um arquivo x com o nome direto do app bugado, ele precisa ser renomeado pela automacao".

Exemplos do caos atual:
- `fatura-1776093934172.pdf` (numero aleatorio, nao identifica mes nem banco)
- `NU_977370681_01ABR2025_30ABR2025.csv` (numero de conta + periodo em portugues abreviado)
- `Nubank_2026-04-11.csv` (data ISO no nome)
- `Fatura-CPF-fevereiro-andre.xls` (mes por extenso)
- `WhatsApp Image 2026-04-13 at 22.45.26.jpeg` (nome padrao do WhatsApp)
- `extrato_conta_corrente_c6.xlsx` (sem periodo)
- `cc_pj_vitoria.csv` (sem periodo, sem banco explicito)

**O pipeline precisa:** Ler o conteudo do arquivo, identificar banco/periodo/tipo, e renomear automaticamente para um padrao como `{banco}_{tipo}_{YYYY-MM}_{pessoa}.{ext}`.
Isso, diferenciar se é pra ficar na pasta pj também.
---

## 2. ARQUIVOS DUPLICADOS

### 2.1 Pastas `pf_nubank` e `pf_cc_nubank` da Vitoria

Sao quase identicas. `pf_cc_nubank` e um superset que contem:
- Todos os 17 CSVs de `pf_nubank`
- MAIS 3 meses adicionais: Out/2024, Nov/2024, Dez/2024
- MAIS Marco 2026
- MAIS copias duplicadas com sufixo "(1)" e "(2)"

Total: 37 arquivos em `pf_cc_nubank` vs 17 em `pf_nubank`.

**Decisao:** Usar `pf_cc_nubank` como fonte canonica (tem mais dados) e ignorar `pf_nubank`? Ou unificar e deduplicar?
Leia cada um dos arquivos, mas o certo seria unificar deduplicar.
### 2.2 Copias com sufixo "(1)", "(2)"

Varios arquivos aparecem duplicados:
- `NU_977370681_01JAN2026_31JAN2026.csv`
- `NU_977370681_01JAN2026_31JAN2026 (1).csv`
- `NU_977370681_01JAN2026_31JAN2026 (2).csv`

Isso e padrao de download duplicado do navegador. O pipeline precisa detectar e ignorar.

### 2.3 CSVs de PJ Nubank da Vitoria

Na pasta `pj_nubank`:
- `Nubank_2025-06-11.csv` e `Nubank_2025-06-11 (1).csv` -- identicos
Veja hash ou tamanho dos arquivos.
---

## 3. FORMATOS DE CSV INCONSISTENTES

### 3.1 Dois formatos distintos do Nubank

**Formato 1 - Cartao de credito (fatura):**
```csv
date,title,amount
2026-04-02,Juros por fatura atrasada,29.44
```
- Headers em ingles
- Data ISO (YYYY-MM-DD)
- Valor sempre positivo
- Sem identificador unico
- Usado em: `andre/nubank/`, `vitoria/pj_nubank/`
Quero que vc proponha da forma mais coerente possível. só fui colocando esses termos pra irmos separando inicialmente.
**Formato 2 - Conta corrente (extrato):**
```csv
Data,Valor,Identificador,Descricao
01/04/2026,80.00,69cdbd59-...,Transferencia Recebida - ...
01/04/2026,-54.93,69cdbd92-...,Transferencia enviada pelo Pix - ...
```
- Headers em portugues
- Data BR (DD/MM/YYYY)
- Valor positivo = entrada, negativo = saida
- UUID como identificador unico (excelente para dedup)
- Usado em: `vitoria/pf_nubank/`, `vitoria/pf_cc_nubank/`, `vitoria/pj_cc_nubank/`

**O prompt-1 assume um unico formato Nubank CSV.** Na realidade sao dois formatos completamente diferentes. Precisa de dois parsers distintos.
Dois parsers
### 3.2 Formato C6

Arquivos `.xls` (Excel 97-2003), NAO `.xlsx`. Requer biblioteca `xlrd`, que nao esta no `install.sh`. Alem disso, tem um `.xlsx` de extrato CC que e formato diferente.

**Descoberta:** As faturas do C6 tem extensao `.xls`, nao o CSV que o prompt menciona. O extrato CC do C6 e `.xlsx`.
ok
### 3.3 Formato Black Way / Santander

O prompt-1 NAO menciona "Black Way" em lugar nenhum. Mas existe a pasta `andre/cartao_black_way/` com 4 PDFs de faturas.

**Descoberta:** "Black Way" e o nome comercial do cartao Santander de Andre. As faturas mostram:
- Banco Santander (Brasil) S.A.
- Cartao SANTANDER ELITE VISA
- Final 7342
- Limite total: R$ 4.010,00
é exatamente isso, tem que incluir sim, é o outro cartão q tenho
Faturas encontradas:
| Mes       | Valor     | Vencimento  |
|-----------|-----------|-------------|
| Janeiro   | R$ 109,38 | 10/01/2026  |
| Fevereiro | R$ 1.184,60 | 10/02/2026 |
| Marco     | R$ 2.155,72 | 10/03/2026 |
| Abril     | R$ 707,77 | 10/04/2026  |

**O prompt precisa incluir um extrator pra Santander PDF (fatura cartao).** Esta nos planos da Sprint 2, mas os dados ja existem agora.

---

## 4. DADOS FINANCEIROS - INCONSISTENCIAS COM OS PROMPTS

### 4.1 Divida da Vitoria - Valores divergem

O prompt/planos mencionam "~R$ 22k de divida Nubank".

**Realidade encontrada nos PDFs do Serasa:**
- Divida PF (CPF Vitoria): R$ 13.049,65 (valor negociacao) / original R$ 12.715,69
- Divida PJ (CNPJ 52.488.753): R$ 10.783,72 (valor negociacao) / original R$ 12.392,83
- **Total real para quitar: R$ 23.833,37**
- Ambas datadas de 11/09/2025, cartao de credito, Nu Financeira S.A.

**SCR (Banco Central) mostra evolucao:**
- 02/2026: Divida vencida R$ 18.253,12 (PF)
- 01/2026: Divida vencida R$ 17.904,71 (PF)
- Isso cresce todo mes com juros

**Questao:** Sao DUAS dividas separadas (PF e PJ) ou uma unica que foi dividida? Isso muda a estrategia de negociacao.
Uhum, são duas dívidas uma pra PF e outra pra PJ. Por isso separei elas.

### 4.2 Renda da Vitoria - Descoberta nova

O prompt diz "Vitoria PJ R$ 4.000/mes". Mas o contrato da Bolsa MEC (NEES/UFAL) mostra:
- Cargo: Analista de BI
- Valor: R$ 3.700,00/mes
- Carga: 20h semanais
- Aceito em 27/03/2026

**Perguntas:**
- Essa bolsa e ADICIONAL aos R$ 4k PJ ou SUBSTITUIU?
- Se e adicional, a renda dela subiu pra ~R$ 7.700/mes?
- A bolsa e isenta de IR? (bolsas de pesquisa geralmente sao)
- O cc_pj_vitoria.csv mostra recebimentos da "PAIM" (CNPJ 94.425.154) de R$ 3.700 -- isso e o NEES/UFAL via a empresa PAIM?
Então, ela é PJ, tem um mei, mas foi contratada como bolsista da UFAL pra trabalhar lá. Isenta. O que ela recebe é 3700 mesmo.
### 4.3 Renda do Andre - Confirmada

**Infobase (contracheque PDF):**
- Bruto: R$ 10.000,00
- INSS: R$ 988,07
- IRRF: R$ 1.569,55
- Liquido: R$ 7.442,38
- Admissao: 02/06/2025
- FGTS/mes: R$ 800,00

**G4F (contracheque XLSX):**
- Bruto: R$ 8.657,25
- Desc. Vale Alimentacao: R$ 96,52
- INSS: R$ 988,07
- IRRF: R$ 1.200,29
- Seguro Vida: R$ 2,75
- Pago via Santander (ag 2327, conta 71018701-1)

**Liquido total Andre: R$ 7.442,38 + ~R$ 6.370 = ~R$ 13.812/mes**
Certo.
### 4.4 Gastos reais vs estimativa dos planos

A aba "Dividas Ativas" do XLSX mostra gastos fixos que NAO aparecem nos planos:
- Marmitas Congeladas Fit Da Nutri: R$ 2.800 (!!)
- IA (Cursos + Programas): R$ 1.500
- Pos (2 da Vitoria): R$ 600
- Hobbies: R$ 150
- PIRATA IPTV: R$ 70
- Contador: R$ 70
- Gas: R$ 120
- Gatos: R$ 200
- Psicologo: R$ 200
- Psiquiatra: R$ 500
- Receita Federal (DAS + multa): R$ 440

**Gasto total fixo na planilha: ~R$ 12.380/mes** (somando tudo, incluindo "Nao Pago").

Isso e mais do que os R$ 9.400 estimados no plano financeiro.
Então kkkkk, a ideia é chegar nessa meta, pq quero sair da infobase e quero fazer o planejamento certo pra isso.

### 4.5 Contas de luz - Discrepancia

Screenshots mostram:
| Mes     | Consumo | Valor     |
|---------|---------|-----------|
| 03/2026 | 351 kWh | R$ 20,38  |
| 02/2026 | 316 kWh | R$ 360,57 |
| 01/2026 | 364 kWh | R$ 400,82 |
| 12/2025 | 222 kWh | R$ 261,33 |
| 11/2025 | 257 kWh | R$ 307,30 |
| 10/2025 | 228 kWh | R$ 250,79 |

Mas na aba Dividas Ativas: "Luz: R$ 400". E no "dividas_luz" da Vitoria tem screenshots de faturas de energia. O valor de 03/2026 caiu para R$ 20,38 (tarifa social?). **Precisa esclarecer.**

A pasta se chama "dividas_luz" -- existem contas de luz em atraso?
Isso é pq eu paguei a de janeiro duas vezes no pix e descontou no mês 3. Tá certo.
---

## 5. PLANILHA XLSX EXISTENTE (HISTORICO)

### 5.1 Schema antigo vs schema novo

A planilha existente tem 1.254 linhas de ago/2022 a jul/2023 com schema:

**Schema antigo (7 colunas uteis):**
| Data | Gasto | Forma de pagamento | Local | Quem fez | Categoria | Classificacao de despesas |

**Schema novo proposto no prompt (12 colunas):**
| data | valor | forma_pagamento | local | quem | categoria | classificacao | banco_origem | tipo | mes_ref | tag_irpf | obs |

**Mapeamento necessario:**
- `Gasto` -> `valor`
- `Forma de pagamento` -> `forma_pagamento`
- `Local` -> `local`
- `Quem fez` -> `quem`
- `Categoria` -> `categoria`
- `Classificacao de despesas` -> `classificacao`
- `banco_origem` -> NAO EXISTE no antigo (preencher null)
- `tipo` -> NAO EXISTE (inferir: tudo e "Despesa" exceto se for receita)
- `mes_ref` -> derivar da coluna `Data`
- `tag_irpf` -> null
- `obs` -> null

### 5.2 Categorias do historico vs categorias novas

O historico usa categorias como "Cafe da manha", "Alcool", "Insumos", "Skincare", "Remedios TDAH" que NAO existem no mapeamento regex do prompt-1.

**Decisao:** Preservar as categorias originais ou re-categorizar tudo?
É contigo. Muita coisa ali mudou, tipo hoje nem bebo mais e nem saio de casa ou fumo, mas era pra deixar como exemplo de como eu tinha feito no passado, mas era tão horrível que deixe pra lá e hoje to super full quebrado.

aproveitando sobre as dividas da vitoria vamos deixar caducar. Provavelmente, mas isso preciso ver com calma.

### 5.3 Aba Renda - Incompleta

A aba Renda tem colunas (PJ, C6, Nubank, Vale, Pontos, Fatura_PJ, etc.) mas esta vazia (so formulas sem dados). O schema novo e completamente diferente. Nao ha dados para importar aqui.
Temos que arrumar ela pra que ela passe a ter os dados cruzados certos.

### 5.4 Aba Inventario - Schema diferente

O inventario antigo tem campos que o schema novo nao tem (vida util, taxa depreciacao, formula de perda mensal). O schema novo e mais simples. **Migrar os dados extras ou descartar?**
A ideia é melhorarmos os bancos de dados ali não só descartar.

---

## 6. BANCOS E CONTAS - MAPA COMPLETO

### 6.1 Andre (Registrato CCS)

| Banco | Desde | Status | Dados disponiveis? |
|-------|-------|--------|-------------------|
| BRB | 07/2018 | Ativo | NAO |
| Nubank (pagamentos) | 10/2019 | Ativo | Sim (CSV cartao, poucos dados) |
| Nu Financeira | 10/2019 | Ativo | NAO (separada da Nubank pagamentos) |
| Bradesco | 11/2020 | Ativo | NAO |
| Nu Investimentos | 12/2021 | Ativo | NAO |
| C6 Bank | 05/2022 | Ativo | Sim (XLSX CC + XLS faturas) |
| C6 CTVM | 05/2022 | Ativo | NAO |
| Itau | 06/2022 | Ativo | Sim (1 PDF, jan/2026) |
| 99Pay | 07/2023 | Ativo | NAO |
| Mercado Pago | 05/2025 | Ativo | NAO |
| Swap | 05/2025 | Ativo | NAO |
| Santander | 07/2025 | Ativo | Sim (4 faturas Black Way PDF) |
| Caixa | 02/2026 | Ativo | NAO |

**13 relacionamentos bancarios ativos**, dados de apenas 4 bancos.

### 6.2 Vitoria (Registrato CCS)

| Banco | Desde | Status | Dados disponiveis? |
|-------|-------|--------|-------------------|
| BRB | 05/2018 | Ativo | NAO |
| Caixa | 09/2019 | Ativo | NAO |
| PicPay | 09/2019 | Ativo | NAO |
| Nubank (pagamentos) | 09/2019 | Ativo | Sim (CSVs CC PF + CC PJ) |
| Itau | 01/2021 | Ativo | NAO |
| Nu Financeira | 10/2023 | Ativo | Sim (CSVs cartao PJ) |

**6 relacionamentos ativos**, dados de apenas 2 (Nubank CC e cartao PJ).

### 6.3 Bancos sem dados

Sem NENHUM dado disponivel para: BRB, Bradesco, Caixa, PicPay, 99Pay, Mercado Pago, Swap. Isso significa que transacoes nesses bancos ficarao **invisiveis** para o pipeline.

**Pergunta ao usuario:** Voces usam ativamente esses bancos? Existem extratos para baixar?
Não usamos mesmo. Mas pra criar conta em tudo pede pra criar conta de banco. Aí fica nisso, deixa no rdar pra eu apagar minhas contas e deixa no radar as documentações também pra levarmos pra aí. Inclusive. dá uma estudada aqui nesses arquivos dessa pasta, lá já tem parte do que tentei automatizar e organizar.  andrefarias@nitro-5  ~/Controle de Bordo


---

## 7. PERIODO DOS DADOS

### 7.1 Cobertura temporal

| Fonte | Periodo |
|-------|---------|
| XLSX historico | Ago/2022 - Jul/2023 |
| CC PJ Vitoria (Nubank) | Jan/2024 - atual (mais completo) |
| CC PF Vitoria (Nubank) | Out/2024 - Abr/2026 |
| Cartao PJ Vitoria (Nubank) | Jun/2025 - Mai/2026 |
| Cartao Andre (Nubank) | Jul/2026 - Nov/2026 (!) |
| CC Andre (C6) | ? (nao consegui ler, falta xlrd) |
| Faturas Andre (C6) | Jan-Mar/2026 (nao consegui ler) |
| Extrato Andre (Itau) | Jan/2026 (PDF protegido) |
| Faturas Andre (Santander) | Jan-Abr/2026 |

**Gap de jul/2023 a dez/2023** -- 6 meses sem nenhum dado.
**Gap de jan/2024 a set/2024** -- so tem dados da PJ da Vitoria.

### 7.2 CSVs do Nubank do Andre - Datas futuras

Os CSVs em `andre/nubank/` mostram datas de Jul-Nov/2026, que sao **meses futuros** (estamos em abril/2026). Isso e normal para faturas de cartao de credito -- a fatura de julho fecha em julho mas contem parcelas compradas antes.

Conteudo: apenas parcelas da Amazon (R$ 52-58). Muito pouco uso desse cartao.

---

## 8. DEPENDENCIAS TECNICAS

### 8.1 Bibliotecas que faltam no install.sh

O `install.sh` do prompt inclui `pdfplumber`, `openpyxl`, `pandas`, etc. Mas faltam:
- `xlrd` -- necessario para ler os `.xls` do C6 (formato Excel 97-2003)
- Possivelmente `camelot` ou `tabula-py` como fallback para PDFs complexos

### 8.2 PDFs protegidos por senha

O Itau PDF requer senha. Senhas a tentar (conforme CLAUDE.md + usuario):
1. `051273`
2. `05127`
3. `05127373122` (CPF completo)

Nao consegui validar porque `pdfplumber` nao esta instalado no ambiente atual. **Precisa testar no ambiente do pipeline.** Faça o install.sh e o run aliás, instala eles antes só pra vc ver os conteudos.

### 8.3 OCR para screenshots

As imagens de conta de luz (`dividas_luz/`) sao screenshots do WhatsApp. O `install.sh` inclui `tesseract-ocr`, mas:
- As imagens sao de app de energia (Neoenergia?) com layout visual
- OCR em screenshot de app pode ser impreciso
- Alternativa: extrair dados manualmente e registrar no YAML
A ideia é usarmos ocr, se não der certo, usamos o moondream local dentro da pasta models pra fazer essa extração. Tipo o que eu fiz na luna.
---

## 9. DEDUPLICACAO - COMPLEXIDADES

### 9.1 Transferencias entre contas proprias

O extrato PF da Vitoria mostra transferencias recebidas do Andre:
```
Transferencia recebida pelo Pix - ANDRE SILVA BATISTA FARIAS - Itau ag 6450
```
Isso apareceria como SAIDA no extrato do Itau do Andre e ENTRADA no Nubank da Vitoria.

**Sem o extrato do Itau**, nao da para cruzar e marcar como Transferencia Interna automaticamente. So temos um lado da transacao.
eu fiz o pix pra ela pagar umas contas.
### 9.2 Transferencias PF <-> PJ da Vitoria

O extrato mostra movimentacoes entre a conta PF e PJ da Vitoria:
```
01/04/2026 - Transferencia Recebida - 52.488.753 VITORIA MARIA SILVA DOS SANTOS (PJ -> PF)
```
Isso precisa ser marcado como Transferencia Interna tambem.
sim sim.
### 9.3 Pagamento de fatura de cartao

Quando a Vitoria paga a fatura do cartao PJ, aparece como saida na CC:
```
Pagamento de boleto efetuado - NU PAGAMENTOS SA
```
E os gastos individuais aparecem no CSV do cartao. **Nao pode contar ambos.**

### 9.4 Reembolsos

Existem reembolsos nos extratos (99 Tecnologia LTDA devolvendo valor). O pipeline precisa tratar:
```
10/04/2026,-19.80,Transferencia enviada pelo Pix - 99 TECNOLOGIA
10/04/2026,19.80,Reembolso recebido pelo Pix - 99 TECNOLOGIA
```

---

## 10. CATEGORIZACAO - GAPS NO MAPEAMENTO

### 10.1 Padroes encontrados nos dados que NAO tem regex no prompt

| Padrao encontrado | Sugestao de categoria |
|-------------------|----------------------|
| SUPERLOGICA | Aluguel/Condominio |
| CLIENT CO SERVICOS DE REDE | Internet (Claro?) |
| SOCIEDADE MINEIRA DE CULTURA | Pos-graduacao Vitoria |
| PANIFICADORA KI-SABOR / KISABOR | Aluguel (!) - conforme planilha |
| AG SERVICOS NEUROLOGIC | Saude (psiquiatra?) |
| CARTAO DE TODOS | Plano de desconto |
| SESC (multiplos CNPJs) | Natacao/Lazer |
| CREPE CAFFE | Alimentacao |
| MAIS QUE OTICA | Saude/Otica |
| SHPP BRASIL (Shopee) | Compras online |
| PIX Marketplace (Mercado Pago) | Compras online |
| CLINICA LUDENS | Saude (psicologo?) |
| LOUCOMOTIVAPIZZA | Delivery |
| DOCARIA DA ROSE | Alimentacao |
| SACOLAO KIDELICIA | Mercado |
| ATACADAO RURAL | Mercado |
| Meg Farma | Farmacia |
| Gamafarma | Farmacia |

### 10.2 "Aluguel" e pago na Panificadora Ki-Sabor

A aba Dividas Ativas diz: "Aluguel (panificadora kisabor) - R$ 900". Isso significa que o aluguel e pago diretamente na panificadora (provavelmente o imovel e do mesmo dono). Uma transacao "PANIFICADORA KI-SABOR" pode ser aluguel OU compra de paes.

**Precisa de regra especial:** valor alto (>= R$ 800) para Ki-Sabor = Aluguel, valor baixo = Alimentacao.

### 10.3 "PAIM" nos extratos PJ

Transferencias recebidas de "PAIM - 94.425.154/0001-79" sao a renda PJ da Vitoria (bolsa NEES/UFAL ou contrato anterior). Valor: R$ 3.700/mes.

---

## 11. PERGUNTAS DIRETAS AO USUARIO

### Sobre os dados

1. **Pastas duplicadas:** `pf_nubank` e `pf_cc_nubank` contem dados sobrepostos. Posso considerar `pf_cc_nubank` como a fonte completa e ignorar `pf_nubank`?

2. **Bolsa NEES/UFAL:** A Vitoria aceitou a bolsa de R$ 3.700 em 27/mar/2026. Isso e ADICIONAL ao contrato PJ de R$ 4.000 ou SUBSTITUIU? A renda dela agora e R$ 3.700 ou R$ 7.700?

3. **Bancos sem extrato:** Voces usam BRB, Bradesco, Caixa, PicPay ativamente? Tem extratos pra baixar?

4. **Contas de luz:** A pasta `dividas_luz` indica dividas de energia eletrica. Existem contas de luz atrasadas? O valor de R$ 20,38 em mar/2026 (vs R$ 400 em jan) e por tarifa social ou outro motivo?

5. **Extrato Itau:** So tem um mes (jan/2026). Tem como exportar os demais? O Itau e o banco principal do Andre? A G4F deposita la? Cria uma to do list pro andre entregar pra gnt

6. **Santander Black Way:** Esse cartao e de uso ativo? As faturas estao sendo pagas (o historico mostra que a de novembro foi R$ 1.816,99 e a de janeiro caiu pra R$ 109,38)?
sium, é o principal. Mas não consigo exportar os meses seguintes dele. Em breve posto o resto. lá.
7. **C6 Bank:** O nome da pasta e `c6_senha 051273` -- a senha do extrato C6 e 051273?
creio que sim
8. **XLSX principal:** A planilha "Preencher a aba estrato financas_gerar a versao atualizada..." -- esse e o arquivo que o pipeline deve ATUALIZAR ou e um template para gerar do zero? Acho que serve como template

9. **Extrato Serasa do Andre** foi emitido em 28/06/2023 (quase 3 anos atras). O CPF dele continua limpo? Precisa de um extrato atualizado.Cara deu bug então, pq eu gerei o arquivo hoje. E sim tá limpo.

10. **Investimentos:** O arquivo `investimentos_aleatorios` menciona R$ 1.000 CDB Vitoria + R$ 200 pontos Andre + R$ 200 CDB. Esses valores sao atuais?
uhum
### Sobre o pipeline

11. **Escopo da Sprint 1:** O prompt diz "rodar com dados de abril 2026". Mas os dados disponiveis cobrem de out/2024 a abr/2026. Processar so abril ou tudo que existe?
tudo.
12. **Cartao PJ Vitoria -- divida ativa:** Os CSVs do cartao PJ mostram juros, multas e IOF de fatura atrasada acumulando todo mes (R$ 100+ em encargos). Isso faz parte da divida de R$ 10.783 no Serasa PJ, ou e uma divida separada do cartao de credito PJ?
acho q foi no feirão q ela olhou pra ver o que ofereceriam pra gnt .
13. **Dois contracheques Infobase:** O PDF do contracheque Energisa/Infobase mostra a MESMA folha duplicada duas vezes (ambas "Marco de 2026"). E uma copia ou sao dois meses iguais?
copia.
14. **Andre recebe em qual banco pela Infobase?** O contracheque nao mostra banco de deposito. O G4F deposita no Santander. E a Infobase?
itau
---

## 12. RISCOS TECNICOS IDENTIFICADOS

1. **PDFs sem pdfplumber no ambiente atual** -- nao consegui validar a leitura dos PDFs do Itau e das faturas do Santander. Precisa instalar o ambiente primeiro.

2. **XLS (Excel 97-2003)** -- as faturas do C6 usam formato antigo. `openpyxl` nao le `.xls`, precisa de `xlrd`.

3. **XLSX com formulas** -- a planilha historica tem formulas (=SUM, =SUMIF). O `openpyxl` le formulas como strings por padrao. Precisa de `data_only=True` para ler valores calculados, mas isso so funciona se o arquivo foi salvo com cache de valores.

4. **Encoding dos CSVs** -- os extratos Nubank usam caracteres especiais (acentos, &amp; como escape HTML). O parser precisa lidar com encoding e entidades HTML.

5. **Valores monetarios** -- os CSVs usam ponto como separador decimal (padrao US). Mas o XLSX antigo pode usar virgula (padrao BR). O pipeline precisa normalizar.

6. **Volume de dados** -- So a CC PJ da Vitoria (`cc_pj_vitoria.csv`) tem 82KB / ~1500+ linhas desde jan/2024. Com todos os bancos, o volume total pode ser significativo.

---

## 13. OBSERVACOES SOBRE PRIVACIDADE/SEGURANCA

1. O nome da pasta `c6_senha 051273` expoe a senha no nome do diretorio. Se esse projeto for versionado com Git, o `.gitignore` precisa cobrir a pasta `data/` inteira (ja previsto no prompt).
2. Renomeia e cria um env pra gnt.

2. Os CSVs contem CPFs parciais, CNPJs, numeros de conta e agencia. Nunca commitar no repositorio.
nem te esquenta com isso o repo é privado.
3. Os PDFs do Registrato e Serasa contem informacoes financeiras sensiveis (dividas, relacionamentos bancarios).
ok, sem problemas.
---

*"Quem nao sabe de onde parte, nao sabe pra onde vai." -- Seneca*
