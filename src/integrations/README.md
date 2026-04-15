# Integrações Externas

4 caminhos para automatizar a coleta de dados bancários, do mais simples ao mais completo.

---

## 1. Extrator OFX (grátis, manual)

Todos os bancos brasileiros exportam extratos em formato OFX. Basta baixar pelo app/internet banking e jogar no `inbox/`.

**Como exportar por banco:**

| Banco | Caminho |
|-------|---------|
| Nubank | App > Conta > Exportar extrato > OFX (envia por email) |
| Itaú | Internet Banking > Extrato > Salvar em outros formatos > OFX |
| Santander | Internet Banking > Extrato > Exportar OFX |
| C6 Bank | App > Extrato > Exportar |

**Como usar:**
```bash
# 1. Baixe o .ofx do banco
# 2. Jogue em inbox/
# 3. Processe
./run.sh --inbox
./run.sh --tudo
```

O extrator OFX (`src/extractors/ofx_parser.py`) detecta o banco pelo header OFX automaticamente.

---

## 2. Belvo Open Finance (grátis para teste, 25 links)

Conecta aos bancos via Open Finance Brasil. Free tier: 25 links reais.

**Setup:**
```bash
# 1. Criar conta em https://dashboard.belvo.com
# 2. Pegar credenciais no dashboard
# 3. Configurar no .env:
echo 'BELVO_SECRET_ID=seu_id' >> .env
echo 'BELVO_SECRET_PASSWORD=sua_senha' >> .env
echo 'BELVO_AMBIENTE=sandbox' >> .env  # sandbox para testar, production para dados reais

# 4. Instalar dependência
pip install belvo-python

# 5. Listar contas conectadas
python -m src.integrations.belvo_sync --listar

# 6. Sincronizar últimos 30 dias
python -m src.integrations.belvo_sync --dias 30
```

**Limitações:**
- Free tier: 25 links reais (cada banco = 1 link)
- Dados do Open Finance podem ser incompletos (parcelas, descrições)
- Sandbox usa dados fictícios

---

## 3. Gmail API (grátis, automático para Nubank)

O Nubank envia faturas e extratos por email. Esta integração busca esses emails e baixa os anexos automaticamente.

**Setup:**
```bash
# 1. Criar projeto no Google Cloud Console (console.cloud.google.com)
# 2. Habilitar Gmail API
# 3. Criar credenciais OAuth2 (tipo Desktop App)
# 4. Baixar credentials.json para a raiz do projeto

# 5. Instalar dependências
pip install google-api-python-client google-auth-oauthlib

# 6. Primeira execução (abre navegador para autorizar)
python -m src.integrations.gmail_csv

# 7. Execuções seguintes (usa token salvo)
python -m src.integrations.gmail_csv --dias 60
```

**O que busca:**
- Emails de `todomundo@nubank.com.br`, `nu@nubank.com.br`
- Anexos com extensão .csv, .pdf, .ofx
- Salva em `inbox/` para processamento pelo pipeline

---

## 4. MeuPluggy (grátis, visual)

App gratuito da Pluggy para pessoa física. Exporta transações para planilha.

**Setup:**
1. Acesse https://meu.pluggy.ai
2. Crie conta e conecte seus bancos (consentimento Open Finance)
3. Exporte transações para CSV/Google Sheets
4. Salve o CSV em `inbox/`
5. Rode `./run.sh --inbox`

**Limitações:**
- Sem API programática garantida (depende do tier dev)
- Export manual (não automatizável)
- Dados do Open Finance podem ser incompletos

---

## Comparativo

| Caminho | Custo | Automação | Confiabilidade | Setup |
|---------|-------|-----------|----------------|-------|
| OFX manual | Grátis | Manual | Alta | Zero |
| Belvo | Grátis (25 links) | Total | Média | Médio |
| Gmail API | Grátis | Parcial (só Nubank) | Alta | Médio |
| MeuPluggy | Grátis | Manual | Média | Fácil |

**Recomendação:** Comece pelo OFX manual (funciona hoje). Teste Belvo free tier para automação. Gmail API como bônus para Nubank.
