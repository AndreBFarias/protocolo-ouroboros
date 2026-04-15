# Sprint 25 -- Automação Bancária: Download de Extratos

## Status: Pendente (pesquisa concluída 2026-04-15)

## Objetivo

Eliminar a etapa manual de baixar extratos bancários. Hoje o gargalo do pipeline é humano: abrir cada app, exportar PDF/CSV, transferir para o computador. Esta sprint implementa automação viável baseada em pesquisa real.

---

## Resultado da Pesquisa

### pynubank (a lib que você lembra)

- **Repositório:** github.com/andreroggeri/pynubank (949 stars, 305 commits)
- **Status: MORTA.** Desde agosto/2023 o Nubank exige verificação facial para acessar dados via API. A lib não funciona mais. Último release: junho/2023. Issue #419 confirma: sem workaround.
- **Não usar.** Sem chance de voltar a funcionar -- é mudança de segurança do Nubank.

### itauscraper

- **Repositório:** github.com/henriquebastos/itauscraper
- **Status: ABANDONADO.** Poucas commits, sem manutenção. Usa requests + lxml simulando navegador mobile.
- **Risco:** URLs do Itaú mudam periodicamente. Sem manutenção ativa = quebra silenciosa.
- **Não usar** como base confiável.

### ofx-bot

- **Repositório:** github.com/maxiwell/ofx-bot
- **O que faz:** Baixa arquivos OFX de Itaú, Santander, Nubank, BB, Caixa via Selenium + Chrome.
- **Status:** Funcional mas com webdriver antigo. Nubank bot provavelmente quebrado (mesma razão da pynubank).
- **Útil como referência** para Itaú e Santander, não para Nubank.

### Pluggy (OPÇÃO MAIS VIÁVEL)

- **O que é:** API Open Finance Brasil autorizada pelo Banco Central. Agrega dados de bancos brasileiros via interface padronizada.
- **Bancos suportados:** Itaú, Santander, Nubank, C6 Bank, Bradesco, BB, Caixa, XP, BTG + centenas de outros.
- **Dados acessíveis:** Contas, saldos em tempo real, transações com categorização, faturas de cartão, investimentos, empréstimos.
- **Autenticação:** O usuário autoriza no app do banco (consentimento Open Finance, válido por 12 meses). Sem senha armazenada localmente.
- **SDK:** Tem SDKs oficiais (Node.js, Java, .NET). Python via API REST direta.
- **Preço:** A partir de $29/mês. Sandbox gratuito para testes. Free trial disponível.
- **MCP Server:** Tem servidor MCP open-source (Node.js) que integra com Claude Desktop/Cursor. Expõe `getAccounts` e `getTransactions` como tools.
- **Limitação:** Viola parcialmente o princípio Local First (dados passam pelo servidor Pluggy). Mas é regulado pelo Banco Central, com consentimento explícito.

### Belvo

- **O que é:** Plataforma Open Finance para América Latina. Concorrente do Pluggy.
- **SDK Python:** Sim, tem SDK oficial em Python (belvo-python).
- **Sandbox:** Gratuito para desenvolvimento com dados fictícios.
- **Diferença:** Foco mais enterprise. Menos documentação para uso pessoal.
- **Preço:** Não divulga publicamente. Provavelmente mais caro que Pluggy.

### Open Finance Brasil (direto)

- **O que é:** APIs padronizadas pelo Banco Central (endpoints /accounts, /balances, /transactions).
- **Complexidade:** MUITO alta para uso pessoal. Requer certificados digitais, registro como instituição no Banco Central, OAuth2 FAPI.
- **Veredicto:** Inviável para projeto pessoal. Use um agregador (Pluggy/Belvo) que abstrai essa complexidade.

### OFX (formato de arquivo)

- **O que é:** Formato padrão de exportação de extratos bancários (Open Financial Exchange).
- **Suporte:** Itaú exporta OFX pelo internet banking. Outros bancos variam.
- **Libs Python:** `ofxparse`, `ofxtools`, `bankstatementparser` -- todas parsers maduros.
- **Vantagem:** Não precisa de API. Basta baixar manualmente o .ofx e o parser extrai tudo.
- **Limitação:** Ainda requer download manual do arquivo OFX.

---

## Decisão: Abordagem em Camadas

### Camada 1: Pluggy (automação completa) -- US$ 29/mês

- Integrar Pluggy API para baixar transações de todos os 6 bancos automaticamente
- Consentimento via app dos bancos (1x por ano)
- Pipeline roda `pluggy_sync.py` que baixa transações novas e salva como CSV no `data/raw/`
- O inbox processor já sabe o que fazer com os CSVs

**Entregas:**
- [ ] Criar conta no Pluggy (meu.pluggy.ai)
- [ ] Conectar as 6 contas bancárias via consentimento Open Finance
- [ ] Criar `src/integrations/pluggy_sync.py` que:
  - Autentica com Pluggy API (client_id + client_secret)
  - Lista contas conectadas
  - Baixa transações do último mês (ou período customizável)
  - Salva em CSVs no formato que os extratores já entendem
  - Loga resultado e erros
- [ ] Integrar no `run.sh` como nova opção: `--sync-bancos`
- [ ] Agendar execução mensal (cron ou systemd timer)

### Camada 2: OFX parser (fallback manual) -- gratuito

Para quando Pluggy não estiver disponível ou para bancos não conectados:

- [ ] Adicionar extrator OFX genérico (`src/extractors/ofx_parser.py`)
  - Usa `ofxparse` para ler qualquer arquivo .ofx
  - Detecta banco pelo header OFX
  - Converte para schema padrão do Ouroboros
- [ ] Adicionar `.ofx` às extensões suportadas em `pipeline.py` e `inbox_processor.py`

### Camada 3: Pluggy MCP Server (integração com Claude) -- bônus

- [ ] Configurar o MCP server da Pluggy para que Claude Code acesse dados bancários diretamente
- [ ] Permitir consultas como: "Quanto gastei em farmácia este mês?" direto no Claude

---

## Armadilhas

- Pluggy cobra por uso. $29/mês é viável para projeto pessoal mas não é gratuito
- Consentimento Open Finance expira em 12 meses. Lembrar de renovar
- Pluggy retorna transações no formato deles, não no formato dos CSVs dos bancos. O `pluggy_sync.py` precisa converter
- Sandbox da Pluggy usa dados fictícios. Testar com sandbox, depois migrar para produção com dados reais
- Se Pluggy mudar API ou fechar, o fallback OFX garante continuidade (Local First)

## Dependências

- Conta na Pluggy ($29/mês)
- `pip install ofxparse` (para camada OFX)
- Consentimento nos apps dos 6 bancos (Open Finance)

---

## Referências da pesquisa

- pynubank (morta): github.com/andreroggeri/pynubank -- Issue #419 confirma bloqueio
- itauscraper (abandonado): github.com/henriquebastos/itauscraper
- ofx-bot (referência): github.com/maxiwell/ofx-bot
- Pluggy docs: docs.pluggy.ai
- Pluggy MCP: skywork.ai (artigo sobre integração com Claude)
- Belvo docs: developers.belvo.com
- Open Finance Brasil: openbanking-brasil.github.io
- ofxparse: pypi.org/project/ofxparse
- ofxtools: ofxtools.readthedocs.io
- bankstatementparser: github.com/sebastienrousseau/bankstatementparser

---

*"Tempo é o recurso mais escasso; a menos que seja gerenciado, nada mais pode ser gerenciado." -- Peter Drucker*
