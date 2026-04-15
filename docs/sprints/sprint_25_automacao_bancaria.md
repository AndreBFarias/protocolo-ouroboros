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

## Por que não dá pra acessar de graça via API direta?

**Open Finance Brasil:** Só instituições autorizadas pelo Banco Central podem consumir as APIs. Pessoa física não pode. Precisa de um intermediário (Pluggy, Belvo, etc.) ou ser banco.

**Registrato BCB:** Consulta pelo gov.br (prata/ouro). Mostra histórico de contas, chaves Pix, empréstimos. Mas NÃO tem API pública, NÃO exporta transações, e NÃO é automatizável (requer login gov.br com 2FA).

**LGPD (portabilidade):** Você tem direito legal aos seus dados. Pode solicitar via SAC de cada banco. Mas o processo é manual (formulário, esperar resposta) e o formato varia (PDF, CSV, planilha). Não há API padronizada para exercer esse direito automaticamente.

**Resumo:** Os dados são seus, mas os bancos não oferecem API pessoal para baixá-los. O Open Finance existe justamente pra resolver isso, mas o Banco Central exige que o acesso seja via instituição autorizada (como Pluggy).

---

## Decisão: Abordagem em Camadas (da gratuita para a paga)

### Camada 1: MeuPluggy (GRATUITO para uso pessoal)

- **MeuPluggy** (meu.pluggy.ai) é um app gratuito da Pluggy para pessoas físicas
- Conecta suas contas bancárias via Open Finance (consentimento no app do banco)
- Exporta transações para planilha/Google Sheets
- Tem API de desenvolvedor com `client_id` + `client_secret` (trial de 15 dias, mas dados continuam acessíveis depois)
- **Limitação real:** Usuários da pynubank reportam dados incompletos via Open Finance (transações parciais, parcelas inconsistentes, descrições faltantes). Isso é limitação do Open Finance do Nubank, não da Pluggy.

**Entregas:**
- [ ] Criar conta gratuita no meu.pluggy.ai
- [ ] Conectar as 6 contas bancárias via consentimento Open Finance
- [ ] Testar export de transações (verificar se dados estão completos)
- [ ] Se API dev disponível: criar `src/integrations/pluggy_sync.py`
  - Autentica com client_id + client_secret
  - Baixa transações do último mês
  - Converte para CSV no formato dos extratores
  - Salva em `data/raw/` para o pipeline processar
- [ ] Integrar no `run.sh` como `--sync-bancos`

### Camada 2: Export manual dos bancos (GRATUITO, mais confiável)

Todos os bancos do casal exportam extratos manualmente:

| Banco | Como exportar | Formato | Nota |
|-------|--------------|---------|------|
| Nubank | App > Conta > Exportar extrato | CSV, OFX, PDF | Envia por email |
| Itaú | Internet Banking > Extrato > Salvar em outros formatos | OFX | Precisa desktop |
| Santander | Internet Banking > Extrato > Exportar OFX | OFX | Precisa desktop |
| C6 Bank | App > Extrato > Exportar | CSV, XLSX | Direto no app |

**Entregas:**
- [ ] Adicionar extrator OFX genérico (`src/extractors/ofx_parser.py`)
  - Usa `ofxparse` para ler qualquer arquivo .ofx
  - Detecta banco pelo header OFX
  - Converte para schema Ouroboros
- [ ] Adicionar `.ofx` às extensões suportadas em `pipeline.py` e `inbox_processor.py`
- [ ] Documentar procedimento de export por banco em `docs/EXPORT_BANCOS.md`

### Camada 3: Pluggy MCP Server + Claude (GRATUITO se tier dev funcionar)

- [ ] Configurar MCP server da Pluggy para Claude Code acessar dados bancários
- [ ] Consultas diretas: "Quanto gastei em farmácia este mês?"

### Camada 4: Pluggy API paga (US$ 29/mês -- só se necessário)

Se MeuPluggy gratuito não atender (dados incompletos, trial expirar sem acesso):
- Assinar plano pago da Pluggy
- API completa sem limitações
- Agendar sync mensal via cron

---

## Armadilhas

- MeuPluggy é gratuito mas dados do Open Finance podem ser incompletos (Nubank especialmente)
- Export manual do OFX é mais confiável mas não é automático
- Consentimento Open Finance expira em 12 meses -- lembrar de renovar
- API dev do MeuPluggy tem trial de 15 dias -- testar rápido e avaliar
- OFX do Itaú requer internet banking desktop (não funciona no app)
- CSV do Nubank vem por email -- pode automatizar com Gmail API no futuro

## Dependências

- Conta gratuita no meu.pluggy.ai
- `pip install ofxparse` (para extrator OFX)
- Consentimento nos apps dos bancos (Open Finance)

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
