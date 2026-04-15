# Sprint 25 -- Automação Bancária: Download de Extratos

## Status: Pendente (pesquisa necessária)

## Objetivo

Eliminar a etapa manual de baixar extratos bancários e jogar no inbox. Hoje o gargalo do pipeline é humano: abrir cada app, exportar PDF/CSV, transferir para o computador. Esta sprint pesquisa e implementa as opções viáveis de automação.

---

## Opções de automação (pesquisar)

### Opção A: Open Finance Brasil

- API regulada pelo Banco Central para compartilhamento de dados bancários
- Requer consentimento via app do banco (válido por 12 meses)
- Endpoints padronizados para extratos, cartões, investimentos
- Limitação: nem todos os bancos implementam totalmente
- Bancos do casal: Itaú, Nubank, C6, Santander -- todos participam do Open Finance
- Complexidade: alta (autenticação OAuth2, certificados, renovação de consentimento)

### Opção B: Web scraping com Playwright/Selenium

- Automação de navegador para acessar internet banking
- Risco: violação de termos de uso dos bancos
- Fragilidade: qualquer mudança no site quebra o scraper
- Requer credenciais de acesso armazenadas localmente
- Complexidade: média (mas manutenção alta)

### Opção C: Email/notificação parsing

- Nubank envia faturas por email (PDF)
- Itaú envia extratos mensais
- Integrar com Gmail API para baixar automaticamente
- Limitação: nem todos os bancos enviam, formato varia
- Complexidade: média (Gmail API é bem documentada)

### Opção D: Pluggy / Belvo (agregadores)

- APIs brasileiras que conectam com bancos via Open Finance
- Pluggy: startup brasileira, plano gratuito limitado
- Belvo: similar, foco em LatAm
- Vantagem: abstrai complexidade do Open Finance
- Limitação: dependência de terceiro, dados passam por servidor externo
- Viola princípio Local First do projeto

---

## Entregas (após pesquisa)

- [ ] Avaliar qual opção é viável (custo, complexidade, princípios do projeto)
- [ ] Implementar integração para pelo menos Nubank (maior volume de dados)
- [ ] Automatizar download mensal (cron ou trigger manual)
- [ ] Integrar com inbox processor (arquivos baixados vão para inbox/)

## Decisão pendente

Local First vs conveniência. Open Finance e agregadores envolvem servidores externos. Web scraping é local mas frágil. Email parsing é local e estável mas limitado.

---

*"Automatize as coisas tediosas." -- Al Sweigart*
