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

## 15. Duplicatas fuzzy residuais (Sprint 19)

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

*"Experiência é simplesmente o nome que damos aos nossos erros." -- Oscar Wilde*
