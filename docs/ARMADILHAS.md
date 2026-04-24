# Armadilhas Críticas -- Lições das Sprints 1-4 e 19

15 problemas reais encontrados durante o desenvolvimento. Cada um custou tempo de debug e gerou correção específica.

---

## 1. C6 XLS encriptado

**O que aconteceu:** O extrator C6 falhava ao tentar ler o arquivo XLS com xlrd. O erro era genérico (`CompDocError` ou `XLRDError`), sem indicar que o arquivo estava encriptado. Horas perdidas achando que era corrupção de arquivo.

**Solução aplicada:** Adicionada dependência `msoffcrypto-tool` ao pipeline. O extrator C6 agora decripta o arquivo com a senha conhecida antes de passar para xlrd. Fluxo: msoffcrypto decripta -> BytesIO -> xlrd lê.

**Como evitar no futuro:** Sempre tentar decriptar arquivos XLS/XLSX antes de assumir corrupção. Bancos brasileiros frequentemente encriptam exports mesmo quando não há senha visível ao usuário.

---

## 2. Itaú PDF protegido

**O que aconteceu:** PyPDF2 não conseguia abrir os PDFs do Itaú mesmo com senha correta. O erro era inconsistente entre versões da biblioteca. Tentativas com diferentes modos de decriptação falhavam.

**Solução aplicada:** Substituído PyPDF2 por pdfplumber, que usa pdfminer internamente e aceita senha via parâmetro `password="[SENHA]"`. Funciona de forma consistente.

**Como evitar no futuro:** Para PDFs bancários brasileiros, pdfplumber é a escolha padrão. PyPDF2 tem problemas conhecidos com certos tipos de encriptação PDF.

---

## 3. Nubank 2 formatos CSV

**O que aconteceu:** O extrator Nubank falhava em metade dos arquivos. Descobrimos que Nubank tem 2 formatos CSV completamente diferentes: cartão de crédito (colunas: date, title, amount) e conta corrente (colunas: Data, Valor, Identificador, Descricao).

**Solução aplicada:** Criados 2 extratores separados: `nubank_cartao.py` e `nubank_cc.py`. O inbox_processor detecta qual formato pelo header do CSV.

**Como evitar no futuro:** Nunca assumir que o mesmo banco usa o mesmo formato em todos os produtos. Sempre inspecionar o header do arquivo antes de rotear para extrator.

---

## 4. Ki-Sabor valor duplo

**O que aconteceu:** O estabelecimento "Ki-Sabor" aparecia tanto como padaria (gastos pequenos, < R$100) quanto como aluguel (R$800+). O regex categorizava tudo como "Padaria" porque matchava pelo nome.

**Solução aplicada:** Regra condicional no categorizer: se descrição contém "KI.SABOR" e valor >= R$800, categoria = "Aluguel" (Obrigatório). Caso contrário, categoria = "Padaria" (Questionável).

**Como evitar no futuro:** Quando o mesmo estabelecimento tem transações com ordens de grandeza diferentes, sempre considerar regra por valor além do regex de descrição.

---

## 5. Categorizer return vs break

**O que aconteceu:** O categorizer usava `return` após encontrar match de categoria. Isso impedia que a classificação (Obrigatório/Questionável/Supérfluo) fosse atribuída quando vinha de uma regra diferente da categoria. Transações ficavam com classificação "N/A".

**Solução aplicada:** Substituído `return` por lógica que continua avaliando regras de classificação mesmo após match de categoria. O fluxo agora é: overrides -> categoria regex -> classificação regex -> defaults.

**Como evitar no futuro:** Em pipelines de regras com múltiplos atributos, nunca interromper avaliação após match parcial. Cada atributo deve ter sua própria cadeia de avaliação.

---

## 6. Histórico classificações corrompidas

**O que aconteceu:** Ao importar o XLSX antigo (1.254 lançamentos), várias classificações estavam corrompidas: "Obrigatorios" (com 's' extra), "Rou" (truncado), "questionavel" (minúsculo), "Supérfulo" (typo). O pipeline não validava e propagava os erros.

**Solução aplicada:** Adicionada etapa de normalização de classificações na importação de histórico. Mapa de correção: {"Obrigatorios": "Obrigatório", "Rou": "Obrigatório", "questionavel": "Questionável", "Supérfulo": "Supérfluo", ...}.

**Como evitar no futuro:** Sempre validar e normalizar dados importados de fontes externas. Nunca confiar que dados manuais seguem o schema esperado.

---

## 7. Prazos XLSX antigo colunas erradas

**O que aconteceu:** O importador da aba "prazos" do XLSX antigo usava índices de coluna 0 e 1 (assumindo que as primeiras colunas eram as relevantes). Na verdade, os dados estavam nas colunas 2 e 3. Resultado: dados de prazos completamente errados.

**Solução aplicada:** Corrigidos os índices para 2 e 3. Adicionada validação que verifica se os headers das colunas correspondem ao esperado antes de extrair dados.

**Como evitar no futuro:** Nunca acessar colunas por índice numérico sem validar headers. Preferir acesso por nome de coluna quando possível.

---

## 8. Git push SSH alias

**O que aconteceu:** `git push` falhava com erro de autenticação. O repositório usava SSH, mas a máquina tem múltiplas chaves SSH (pessoal e trabalho). O alias padrão `github.com` apontava para a chave errada.

**Solução aplicada:** Configurado alias `github.com-personal` no `~/.ssh/config` com a chave correta. Remote do repositório atualizado para usar o alias.

**Como evitar no futuro:** Em máquinas com múltiplas contas GitHub, sempre usar alias SSH específicos no config e nos remotes.

---

## 9. Pre-commit core.hooksPath global

**O que aconteceu:** O git tinha `core.hooksPath` configurado globalmente (provavelmente por outra ferramenta). Isso impedia que o hook pre-commit local do projeto fosse executado. O hook simplesmente não rodava sem erro visível.

**Solução aplicada:** Em vez de lutar contra o `core.hooksPath` global, criado script de pre-commit local que é invocado explicitamente via Makefile target `make check`.

**Como evitar no futuro:** Verificar `git config --global core.hooksPath` ao configurar hooks em novo projeto. Se estiver setado, considerar abordagem alternativa.

---

## 10. OCR energia -- valores parciais

**O que aconteceu:** O OCR via tesseract conseguia extrair valores em R$ das contas de energia com boa precisão, mas o consumo em kWh era extraído corretamente em apenas 67% dos casos. Números com fontes menores ou em áreas com baixo contraste falhavam.

**Solução aplicada:** Implementado gabarito de validação: valores extraídos são comparados com range esperado (100-500 kWh para residencial). Valores fora do range são marcados com flag de baixa confiança para revisão manual.

**Como evitar no futuro:** OCR local (tesseract) tem limitações reais. Para campos críticos, sempre validar contra ranges esperados. Considerar pré-processamento de imagem (binarização, aumento de contraste) antes do OCR.

---

## 11. Streamlit tabs JavaScript

**O que aconteceu:** Ao tentar trocar de aba programaticamente no Streamlit (ex: clicar em botão que leva para aba "Categorias"), o click no elemento Python não funcionava. A aba só mudava visualmente.

**Solução aplicada:** Troca de aba requer injeção de JavaScript via `st.components.v1.html()`. O JS simula click no elemento DOM correto da tab bar.

**Como evitar no futuro:** Streamlit não foi projetado para navegação programática entre tabs. Usar `st.sidebar` com radio buttons como alternativa mais estável.

---

## 12. Santander Black Way

**O que aconteceu:** O extrator Santander não reconhecia o cartão "Black Way" como sendo o cartão Elite Visa final 7342. O nome "Black Way" não aparecia na documentação do banco e não era óbvio que se tratava do mesmo produto.

**Solução aplicada:** Mapeamento explícito no extrator: "Black Way" = cartão Elite Visa final 7342. Regex atualizado para incluir ambas as denominações.

**Como evitar no futuro:** Bancos mudam nomes comerciais de produtos sem aviso. Ao encontrar nome desconhecido, verificar se os últimos 4 dígitos do cartão correspondem a um produto já conhecido.

---

## 13. Nubank CC duplicatas por arquivos

**O que aconteceu:** O usuário baixou o mesmo extrato CSV do Nubank CC várias vezes, gerando arquivos com sufixo "(1)", "(2)", "(3)". Cada arquivo era processado como se fosse novo, triplicando as transações.

**Solução aplicada:** O deduplicator usa a coluna `Identificador` (UUID) do Nubank CC como chave primária. Transações com mesmo UUID são mantidas apenas uma vez, independente de quantos arquivos contenham a mesma transação.

**Como evitar no futuro:** Sempre implementar deduplicação baseada em identificador único quando a fonte fornece um. Para fontes sem UUID, hash é a segunda melhor opção.

---

## 14. msoffcrypto-tool dependência oculta

**O que aconteceu:** O pipeline falhava em máquina limpa ao processar arquivos C6 XLS. O erro era de importação (`ModuleNotFoundError: msoffcrypto`), mas a dependência não estava listada no `pyproject.toml` nem no `install.sh` original.

**Solução aplicada:** Adicionada `msoffcrypto-tool` ao `pyproject.toml` e ao `install.sh`. Documentada como dependência crítica no extrator C6.

**Como evitar no futuro:** Ao adicionar `import` novo em qualquer módulo, imediatamente verificar se a dependência está no `pyproject.toml`. Rodar `pip install` em venv limpo periodicamente para detectar dependências ocultas.

---

## 15. Duplicatas fuzzy residuais (Sprint 18)

**O que aconteceu:** O validador reporta 16 duplicatas residuais (mesmo data+valor+local). Análise manual revela 4 categorias distintas:

**Categoria A -- Pares de transferência entre contas (legítimos):**
Ambos os lados de uma transferência são visíveis porque o casal tem contas em bancos diferentes. Exemplos: C6->Nubank (Pix enviado/recebido), Nubank PF->Nubank PJ (Vitória), Itaú->Santander (pagamento de fatura). Corretamente marcados como Transferência Interna. Manter ambos.

**Categoria B -- Duplicatas reais de CSVs sobrepostos:**
Mesmo banco, mesma descrição, mesmo valor, mesma data. Exemplos: 99 TECNOLOGIA LTDA (múltiplas corridas 99), Recarga de celular, DAS-SIMPLES NACIONAL. Causa: CSVs baixados com períodos que se sobrepõem. Nível 1 (UUID) não removeu porque os identificadores são diferentes.

**Categoria C -- Reembolsos no mesmo dia:**
Despesa original + receita de reembolso com mesmo valor. Exemplos: iFood (despesa + Pix de reembolso), 99 TECNOLOGIA (corrida + cancelamento). São transações distintas -- uma é Despesa, outra é Receita.

**Categoria D -- Coincidências históricas:**
Dados manuais do XLSX antigo (2022-2023) com mesmo valor+data mas locais completamente diferentes. Exemplos: R$ 20,00 em Barbearia e Vivendas no mesmo dia. Coincidência, não duplicata.

**Decisão:** Categorias A, C e D são legítimas e não devem ser removidas. Categoria B requer melhoria no deduplicator (nível 2 deveria remover quando banco+local+data+valor são idênticos, não apenas marcar).

**Como evitar no futuro:** Ao baixar CSVs bancários, anotar o período exato para evitar sobreposição. Considerar melhorar dedup nível 2 para remoção quando todos os campos coincidem (não apenas data+valor).

---

## 16. OFX com espaços no header ENCODING (Sprint 37)

**O que aconteceu:** O OFX do C6 (`c6_cc_andre_2022-06_2026-04.ofx`) falhava no parser `ofxparse` com erro obscuro `cannot access local variable 'encoding' where it is not associated with a value`. O cabeçalho do arquivo tinha `ENCODING: UTF - 8` com espaços ao redor do hífen, e a lib não tolera essa variação. 1.784 transações do C6 ficavam fora do XLSX consolidado.

**Solução aplicada:** Pré-processar o arquivo em memória via regex `REGEX_ENCODING_HEADER` que remove espaços internos do valor do header ENCODING antes de passar bytes para `OfxParser.parse` via `io.BytesIO`. Código em `src/extractors/ofx_parser.py:37,88-94`.

**Como evitar no futuro:** Bancos brasileiros exportam OFX com variações livres no cabeçalho. Quando adicionar extrator para novo banco, rodar `head -c 400 arquivo.ofx` e comparar com formato canônico antes de assumir compatibilidade com ofxparse.

---

## 17. Deduplicator fuzzy só marcava, não removia (Sprint 38)

**O que aconteceu:** Validator reportava 88 duplicatas residuais após destravar o OFX do C6. Causa: `deduplicar_por_hash_fuzzy` usava chave frouxa `(data, valor)` e apenas setava `_duplicata_fuzzy=True` sem remover, com comentário "pode ser coincidência legítima". Histórico vs OFX novo, e OFX vs CSV do mesmo banco, inflavam o XLSX.

**Solução aplicada:** Chave passou a `(data+valor+local)` alinhada ao validator; remove ao invés de marcar; quando múltiplos registros casam, prefere `banco_origem != "Histórico"` (metadados mais ricos); inclui Transferências Internas (pares legítimos entre bancos diferentes não colidem pois `local` é distinto em cada ponta). 88 → 43 → 5 → 0 duplicatas.

**Como evitar no futuro:** Regras de dedup sem ação concreta (marcar sem remover) contaminam downstream silenciosamente. Sempre remover OU justificar por escrito no código que a ambiguidade foi intencional.

---

## 18. `bool(NaN) == True` passa NaN como tag válida (Sprint 39)

**O que aconteceu:** `python -m src.irpf --ano 2026` crashava com `TypeError: '<' not supported between instances of 'str' and 'float'` em `sorted(por_tipo.items())`. Causa: transações sem `tag_irpf` vinham do `pd.read_excel` como `NaN` (float), e `if tag:` aceita NaN como truthy, fazendo NaN entrar como chave junto com tags-string.

**Solução aplicada:** Substituir `if tag:` por `if isinstance(tag, str) and tag:` em `gerar_csvs_por_tipo` (src/irpf/gerador_pacote.py:17-19) e `gerar_resumo` (linhas 61-65). Condição dupla filtra NaN/None/numéricos e strings vazias.

**Como evitar no futuro:** Ao consumir coluna opcional vinda de XLSX via pandas, assumir que o valor pode ser `pd.NA`, `math.nan` ou `None`. Truthy-checks ingênuos passam NaN. Usar `isinstance(x, str)` explicitamente antes de agregação ou sort.

---

## 19. Fallback do categorizer forçava Questionável para Receita/TI (Sprint 40)

**O que aconteceu:** Testes da Sprint 30 revelaram que transações `Receita` e `Transferência Interna` sem match de regex eram classificadas como `"Questionável"`. Causa: `categorizar()` setava `classificacao="Questionável"` no fallback (`categorizer.py:197`) antes de `_garantir_classificacao` rodar, e este último só atua quando a classificação é None. Impactava `resumo_mensal.total_questionavel` silenciosamente.

**Solução aplicada:** Fallback agora só marca Questionável se `tipo in ("Despesa", None)`. Outros tipos ficam com `classificacao=None` e `_garantir_classificacao` atribui N/A (Receita, TI) ou Obrigatório (Imposto). Testes de regressão em `tests/test_categorizer.py::test_receita_sem_match_cai_em_na` e `test_transferencia_interna_sem_match_cai_em_na`.

**Como evitar no futuro:** Uma classificação é um rótulo de despesa -- Questionável/Supérfluo/Obrigatório não fazem sentido para Receita ou TI. Fallbacks que "chutam valor padrão" devem respeitar a semântica do domínio, não só o fluxo de controle.

---

## 20. Glyphs corrompidos em PDF nativo confundem regex (descoberta 2026-04-19, Sprint 41)

**O que aconteceu:** Cupom de garantia da Americanas (`inbox/pdf_notas.pdf`) é PDF de texto nativo, mas a fonte embarcada tem mapeamento ToUnicode incompleto. `pdfplumber.extract_text()` devolve texto legível para humanos, mas com caracteres únicos trocados de forma sistemática: `CNPJ` aparece como `CNP)`, `S.A.` como `5.A.`, `O BILHETE` como `Q BILHETE`, `Modelo` como `Modela`, `DÚVIDAS` sem til. Regex ingênua tipo `r"CNPJ:\s*([\d./-]+)"` deixa passar 100% dos casos -- o detector de tipo ignora um arquivo válido.

**Solução aplicada:** Toda regex de detecção de tipo de documento e de campos canônicos (CNPJ, CPF, razão social, palavras-chave de cabeçalho como `BILHETE`, `NOTA FISCAL`, `CUPOM`) deve usar **classes de caractere tolerantes** para os pares conhecidos de troca. Padrões reusáveis (centralizar em `src/intake/glyph_tolerant.py` quando passar de dois usos):

| Original | Padrão tolerante | Por que |
|----------|------------------|---------|
| `CNPJ` | `CNP[J\)]` | `J` vira `)` |
| `S.A.` ou `SA` | `[S5]\.?[AÁ]\.?` | `S` vira `5` |
| `O BILHETE` | `[OQ]\s+BILHETE` | `O` maiúsculo vira `Q` |
| qualquer dígito | `[\d.\s,]` | espaços/pontos colados de OCR-like |
| acentos opcionais | `[ÚU]VIDAS`, `Modela?` | acento omitido pela fonte |

**Como evitar no futuro:** Antes de escrever regex contra texto extraído de PDF nativo, **sempre** rodar `pdfplumber.extract_text()` num arquivo real e inspecionar visualmente -- não confiar em renderização. Se aparecer ASCII estranho (`)` no lugar de `J`, `5` no lugar de `S`), assumir fonte com ToUnicode quebrado e adotar classes de char. Esta armadilha é cross-cutting: vale para Sprint 41 (detector de tipo), 44/44b (DANFE/NFC-e), 46 (XML quando vier inline em PDF), 47b (termo de garantia), 47c (cupom garantia estendida) e qualquer extrator futuro de PDF nativo de cupom térmico.

---

## 21. Diagnóstico scan/nativo: texto-primeiro, NUNCA imagem-primeiro (descoberta 2026-04-19, Sprint 41)

**O que aconteceu:** A pg1 do `inbox/pdf_notas.pdf` é PDF nativo (1.584 chars de texto extraível) MAS tem QR code embutido como imagem que cobre > 80% da área da página. Implementação inicial de `diagnosticar_pagina` em `src/intake/extractors_envelope.py` checava se havia "imagem grande" antes de avaliar o texto -- resultado: a página seria classificada como `scan` e enviada para o pipeline de OCR pesado, perdendo o texto nativo já disponível.

**Solução aplicada:** A heurística sempre verifica TEXTO primeiro:
1. Se `len(texto_util) >= LIMITE_CHARS_NATIVO` (50 chars por padrão) -> `nativo` (DECIDIDO, ignora imagens).
2. Caso contrário, se há imagem cobrindo > 80% da área -> `scan`.
3. Caso contrário -> `misto` (vai para `_classificar/_aguardando_ocr/`).

**Como evitar no futuro:** Em qualquer extrator que tenha que decidir entre texto-nativo e OCR (Sprint 45 cupom térmico, 47b termo de garantia, etc.), aplicar a mesma ordem: texto-primeiro. PDFs reais frequentemente carregam logos, QR codes, marcas d'água e anúncios -- presença de imagem grande NÃO implica ausência de texto extraível. Inverter a ordem manda PDF perfeitamente parseável para o pipeline OCR (mais lento, mais ruidoso, mais caro). Comentário explícito em `src/intake/extractors_envelope.py:diagnosticar_pagina` para a próxima pessoa não inverter.

---

## 22. `setdefault` no enrich por YAML preserva glyph no metadata (descoberta 2026-04-19, Sprint 47c end-to-end)

**O que aconteceu:** Após rodar `./run.sh --tudo` contra `pdf_notas.pdf`, o nó `seguradora` foi persistido com `razao_social = "MAPFRE Seguros Gerais 5.À."` (glyph quebrado: `S` virou `5`, `A` virou `À`). O `mappings/seguradoras.yaml` tem a versão canônica `"MAPFRE Seguros Gerais S.A."`, mas o enrich (`_enriquecer_seguradora` em `src/extractors/cupom_garantia_estendida_pdf.py`) usa `bilhete.setdefault("seguradora_razao_social", cfg["razao_social"])` -- `setdefault` só preenche quando ausente, e o parser já preencheu com a versão com glyph. CNPJ e código SUSEP têm lógica de sobrescrita quando detectam glyph (`D` no lugar de `0`), mas a razão social não.

**Solução aplicada:** nenhuma nesta sprint (scope atômico). Registrada como observação na conferência artesanal da 47c (`docs/propostas/sprint_47c_conferencia.md §12.3`) para ser endereçada em sprint dedicada de melhoria do enrich. Workaround para quem precisa da razão canônica AGORA: query cruzada, buscando via CNPJ diretamente no `mappings/seguradoras.yaml`.

**Como evitar no futuro:** enrich por YAML deve SOBRESCREVER campos canônicos (razão social, código SUSEP, nome fantasia) quando o CNPJ bate -- o YAML É a fonte de verdade, por definição. `setdefault` preserva glyph e anula o propósito do registro. Aplicar essa regra também nas Sprints 44 (DANFE), 44b (NFC-e) e 46 (XML NFe) quando forem introduzidas, pois vão usar o mesmo padrão enrich-via-mapping.

---

## Sessão 2026-04-23 (rota "conserta tudo" + Fases A/B/C/E) -- 7 armadilhas novas

### A-202304-01. `uuid.uuid4()` em fallback supervisor gera duplicatas a cada rodada

**Sintoma:** 2 cupons fotografados geraram 6 arquivos distintos em `docs/propostas/extracao_cupom/<uuid>.md` + 6 pastas `data/raw/_conferir/<uuid>/` após 3 rodadas do `cupom_termico_foto`. Cada reprocessamento gerava UUID novo.

**Causa raiz:** `_registrar_fallback_supervisor` usava `uuid.uuid4().hex[:12]` como identificador. Não-determinístico.

**Fix (Sprint 87d):** trocado por `cache_key(caminho)[:12]` (SHA-256 por conteúdo, já padrão do cache OCR). Mesma foto → mesmo hash → sobrescrita idempotente.

**Princípio canônico:** qualquer rota que crie arquivos em `docs/propostas/` ou `data/raw/_conferir/` DEVE derivar identificador de `cache_key(caminho)` ou `sha256(conteudo)[:12]`. NUNCA `uuid.uuid4()`.

### A-202304-02. `pessoa_detector` só com CPF literal falha em DAS/certidões

**Sintoma:** 19 DAS PARCSN + 3 certidões Receita Federal do André (CNPJ 45.850.636 + razão social explícita) todos roteados para `data/raw/casal/` em vez de `andre/`.

**Causa raiz:** `pessoa_detector.py` só buscava CPF literal no preview. Documentos legais do MEI mostram CNPJ + razão social, não o CPF do titular.

**Fix (Sprint 90):** camada nova `_casar_via_pessoas_yaml` usando `mappings/pessoas.yaml` (no .gitignore) com schema cpfs/cnpjs/razao_social/aliases. Ordem: CPF > CNPJ > razão > alias > pasta > fallback.

**Princípio canônico:** identificação de pessoa precisa de várias camadas semânticas, cada uma mais específica que a anterior.

### A-202304-03. Roteador duplica arquivos sem dedupe por hash

**Sintoma:** Itaú com 5 extratos únicos virou 29 arquivos físicos (`extrato.pdf`, `extrato_1.pdf`, ..., `_6.pdf`). Santander 18 únicos virou 102. Dedupe de transações salvou, mas storage inflou ~5.8x.

**Causa raiz:** `_resolver_destino_sem_colisao` em `extractors_envelope.py` desambiguava com `_1`/`_N` quando o destino existia, SEM verificar se o conteúdo era idêntico ao da origem.

**Fix (Sprint P2.3):** função ganha `arquivo_origem` opcional. Hash SHA-256 bate → retorna destino (sem criar cópia). Diverge → desambigua canonicamente.

**Princípio canônico:** toda função de roteamento que pode colidir destino DEVE comparar hash antes de desambiguar. "Mesmo conteúdo = mesmo arquivo" é invariante.

### A-202304-04. Aba `renda` sem whitelist vira dump de qualquer crédito

**Sintoma:** Aba `renda` do XLSX com 459 linhas quando a realidade era 24 holerites + 75 MEI. Reembolsos PIX (iFood, Amazon, 99, RAIA), cashback, PIX entre amigos, transferências recebidas -- tudo virou "renda".

**Causa raiz:** `_criar_aba_renda` aceitava qualquer `tipo=="Receita"` sem filtro. O classificador de tipo tem default `valor > 0 = Receita`.

**Fix (Sprint P0.1):** `mappings/fontes_renda.yaml` declara whitelist (salário CLT, MEI por empresa conhecida, bolsa, rendimento) + blacklist (reembolso, estorno, cashback, devolução, PIX genérico, aplicação/resgate RDB, Brasil Bitcoin). Whitelist prioritária quando ambas casam.

**Princípio canônico:** filtros semânticos (renda, IRPF dedutível, despesa essencial) precisam de whitelist declarativa em YAML. Default liberal contamina agregados silenciosamente.

### A-202304-05. Contrato aritmético mascarado por dado sujo

**Sintoma:** Contrato smoke #1 (`receita não exagera salário × limiar`) passava verde há meses. Após a Sprint P0.1 limpar a aba renda, o contrato virou vermelho em 5 meses de 2022-2023.

**Causa raiz:** contrato comparava `receita_mes_extrato` com `salario_mes_aba_renda`. Ambos estavam inflados por falsos-positivos, então a razão passava. Limpando só o denominador, o numerador (que ainda carregava reembolsos como Receita) ficou relativamente maior.

**Fix:** o contrato agora aplica a blacklist de `fontes_renda.yaml` antes de somar `receita_mes`. Compara "renda operacional real" em ambos os lados.

**Princípio canônico:** quando se limpa um lado de um contrato, limpar o outro lado também. Verde em dado sujo é cego, não honesto.

### A-202304-06. `ExtratorNfcePDF` sem OCR falhava em PDF-imagem silenciosamente

**Sintoma:** PDF de NFCe com 0 chars extraíveis (4 páginas, 100% imagem) era **roteado corretamente** para `nfs_fiscais/nfce/` (via Sprint 89 que adicionou OCR no preview do intake), mas **não era extraído** -- o extrator retornava lista vazia de NFCe.

**Causa raiz:** cada extrator tem seu próprio `_ler_paginas_pdf`. O fallback OCR do intake cobria só a classificação. Extração detalhada não herdava.

**Fix (Sprint A2):** `_ler_paginas_pdf` em `nfce_pdf.py` ganhou `_ler_paginas_pdf_via_ocr` próprio (pypdfium2 + tesseract). "notas de garantia e compras.pdf" passou a extrair 2 NFCe + 16 itens da Americanas.

**Princípio canônico:** OCR fallback do intake NÃO se propaga automaticamente para extratores downstream. `ExtratorDanfePDF` e `ExtratorBoletoPDF` ainda não têm -- sprint-filha pendente.

### A-202304-07. Hash canônico precisa `.upper()` para simetria XLSX ↔ grafo

Originalmente descoberta na Sprint 87b. Reforçando aqui: `GrafoDB.upsert_node` aplica `normalizar_nome_canonico` (`strip().upper()`). Helpers que geram hash canônico para consumo externo (XLSX, APIs) DEVEM retornar `.upper()` direto para manter simetria bit-a-bit com o que está gravado. Esquecer causa join XLSX↔grafo silenciosamente vazio.

---

*"Experiência é simplesmente o nome que damos aos nossos erros." -- Oscar Wilde*
