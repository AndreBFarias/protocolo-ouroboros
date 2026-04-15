# Automação Bancária -- Pesquisa e Status

Documentação completa da pesquisa realizada em 2026-04-15 sobre automação de download de extratos bancários para o Protocolo Ouroboros.

---

## Contexto

O gargalo do pipeline é humano: baixar extratos de 6 bancos manualmente, transferir para o computador e jogar no inbox/. A pesquisa investigou todas as opções disponíveis no mercado brasileiro para automatizar esse processo.

---

## O que NÃO funciona

### pynubank (morta)

- **Repositório:** github.com/andreroggeri/pynubank (949 stars)
- **Status:** Morta desde agosto/2023. Nubank exige verificação facial para acesso via API.
- **Último release:** junho/2023. Issue #419 confirma: sem workaround.
- **Veredicto:** Não usar. Sem chance de voltar.

### Open Finance Brasil (direto)

- **O que é:** APIs padronizadas pelo Banco Central (/accounts, /balances, /transactions).
- **Por que não funciona:** Só instituições autorizadas pelo BC podem consumir as APIs. Pessoa física não tem como se registrar.
- **Veredicto:** Inviável para uso pessoal direto.

### Registrato BCB

- **O que é:** Sistema do Banco Central para consulta de dados pessoais (contas, chaves Pix, empréstimos).
- **Limitações:** Requer login gov.br prata/ouro com 2FA. Não tem API. Não exporta transações. Não é automatizável.
- **Veredicto:** Serve para consulta pontual, não para automação.

### LGPD (portabilidade de dados)

- **O que diz a lei:** Você tem direito legal aos seus dados bancários e pode solicitar portabilidade.
- **Na prática:** Processo manual via SAC de cada banco. Formato varia. Sem API padronizada.
- **Veredicto:** Direito existe mas execução é impraticável para automação.

### itauscraper

- **Repositório:** github.com/henriquebastos/itauscraper
- **Status:** Abandonado. Poucas commits, sem manutenção. URLs do Itaú mudam periodicamente.
- **Veredicto:** Referência histórica, não usar como base.

### Pluggy API

- **Preço:** R$ 2.500/mês (plano básico). 100% B2B.
- **Veredicto:** Inviável para uso pessoal.

---

## O que FUNCIONA (4 caminhos implementados)

### Caminho 1: Extrator OFX (grátis, manual, pronto)

Todos os bancos brasileiros exportam extratos em formato OFX pelo app ou internet banking.

**Status:** Implementado e registrado no pipeline.

**Como exportar por banco:**

| Banco | Como | Formato |
|-------|------|---------|
| Nubank | App > Conta > Exportar extrato (envia por email) | CSV, OFX, PDF |
| Itaú | Internet Banking > Extrato > Salvar em outros formatos | OFX |
| Santander | Internet Banking > Extrato > Exportar OFX | OFX |
| C6 Bank | App > Extrato > Exportar | CSV, XLSX |

**Como usar:**
```bash
# Baixa o .ofx, joga em inbox/
./run.sh --inbox    # detecta banco automaticamente
./run.sh --tudo     # processa tudo
```

**Arquivos:** `src/extractors/ofx_parser.py` (detecta banco pelo header OFX)

### Caminho 2: Belvo Free Tier (grátis, automático, em teste)

Belvo tem ambiente Development com 25 links reais gratuitos.

**Status:** Cadastro em andamento (aguardando confirmação de email corporativo).

**Ambientes Belvo:**

| Ambiente | Dados | Links | Custo |
|----------|-------|-------|-------|
| Sandbox | Fictícios | Ilimitados | Grátis |
| Development | REAIS | 25 conexões | Grátis |
| Production | Reais | Ilimitados | US$ 1.000/mês |

**Próximos passos:**
1. Confirmar email e criar conta developer
2. Gerar API keys do ambiente Development
3. Conectar C6 e Nubank via API
4. Testar download de transações reais
5. Configurar no .env: `BELVO_SECRET_ID` e `BELVO_SECRET_PASSWORD`

**Como usar (quando configurado):**
```bash
python -m src.integrations.belvo_sync --listar       # ver contas
python -m src.integrations.belvo_sync --dias 30      # baixar transações
```

**Arquivos:** `src/integrations/belvo_sync.py`

**Limitação conhecida:** O consentimento Open Finance dado pelo portal consumidor Belvo (belvo.com.br) é separado do acesso via API developer. Pode precisar refazer a conexão dos bancos pelo fluxo da API.

### Caminho 3: Gmail API (grátis, automático para Nubank, código pronto)

O Nubank envia faturas e extratos por email. A integração busca esses emails e baixa os anexos CSV/PDF automaticamente.

**Status:** Código implementado, precisa de setup no Google Cloud Console.

**Setup necessário:**
1. Criar projeto no console.cloud.google.com
2. Habilitar Gmail API
3. Criar credenciais OAuth2 (tipo Desktop App)
4. Baixar `credentials.json` para a raiz do projeto
5. Instalar: `pip install google-api-python-client google-auth-oauthlib`
6. Na primeira execução, autorizar no navegador

**Como usar:**
```bash
python -m src.integrations.gmail_csv --dias 60       # busca emails dos últimos 60 dias
./run.sh --inbox                                      # processa os anexos baixados
```

**Arquivos:** `src/integrations/gmail_csv.py`

**Limitação:** Funciona apenas para Nubank (que envia extratos por email). Outros bancos não enviam automaticamente.

### Caminho 4: MeuPluggy (grátis, visual, manual)

App gratuito da Pluggy para pessoa física. Conecta bancos via Open Finance e exporta para planilha.

**Status:** Disponível para teste.

**Como usar:**
1. Acessar https://meu.pluggy.ai
2. Criar conta e conectar bancos (consentimento Open Finance)
3. Exportar transações para CSV/Google Sheets
4. Salvar o CSV em `inbox/`
5. Rodar `./run.sh --inbox`

**Limitação:** Export manual (não automatizável via código). API developer requer conta paga (R$ 2.500/mês). Dados do Open Finance podem ser incompletos (parcelas, descrições faltantes -- limitação do que os bancos expõem).

---

## Comparativo final

| Caminho | Custo | Automação | Confiabilidade | Bancos | Status |
|---------|-------|-----------|----------------|--------|--------|
| OFX manual | Grátis | Manual | Alta | Todos | Pronto |
| Belvo Dev | Grátis (25 links) | Total | Média | Todos | Em teste |
| Gmail API | Grátis | Automático | Alta | Nubank | Setup pendente |
| MeuPluggy | Grátis | Manual | Média | Todos | Disponível |

**Recomendação:** Usar OFX manual como base confiável. Testar Belvo Dev para automação completa. Gmail API como complemento para Nubank.

---

## Referências

- pynubank (morta): https://github.com/andreroggeri/pynubank
- Issue #419 (bloqueio facial): https://github.com/andreroggeri/pynubank/issues/419
- itauscraper (abandonado): https://github.com/henriquebastos/itauscraper
- ofx-bot (referência Selenium): https://github.com/maxiwell/ofx-bot
- Pluggy pricing (R$ 2.500/mês): https://www.pluggy.ai/en/pricing
- MeuPluggy (gratuito): https://github.com/pluggyai/meu-pluggy
- Belvo docs: https://developers.belvo.com
- Belvo pricing: https://belvo.com/plans-and-pricing/
- Belvo ambientes: https://developers.belvo.com/docs/api-environments
- Open Finance Brasil: https://openfinancebrasil.org.br
- ofxparse (lib Python): https://pypi.org/project/ofxparse/
- ofxtools: https://ofxtools.readthedocs.io
- Registrato BCB: https://www.bcb.gov.br

---

*"A informação quer ser livre." -- Stewart Brand*
