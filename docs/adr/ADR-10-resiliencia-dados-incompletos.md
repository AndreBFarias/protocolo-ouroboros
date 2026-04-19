# ADR-10: Resiliência a Dados Incompletos

## Status: Aceita

## Contexto

O fluxo de dados do projeto depende de download manual de extratos, boletos e contracheques por parte do usuário. Na prática, isso significa que em qualquer momento pode faltar: meses inteiros de um banco, boletos de concessionárias não inseridos, holerites ausentes, PDFs de fatura atrasados.

Abordagens possíveis:
- **Pipeline estrito**: cada módulo exige dados completos. Se falta algo, falha. Forçaria o usuário a manter a inbox sempre em dia — inviável na prática.
- **Pipeline silencioso**: ignora ausências sem avisar. Gera relatórios que parecem completos mas mentem sobre a realidade.
- **Pipeline resiliente com honestidade**: sistema brilha com o que existe, sinaliza o que falta, nunca bloqueia o cérebro por causa do relatório final.

A diretriz explícita do projeto é a terceira: *"dados faltantes não deveriam bloquear nada, o projeto tem que ser super inteligente independente disso"*.

## Decisão

Cada camada do pipeline é projetada para operar com dados parciais:

1. **Separação clara entre "cérebro" e "relatório":** dashboard, grafos, análises diagnósticas, IRPF e busca devem funcionar plenamente com os dados disponíveis. Apenas o relatório mensal final pode declarar "cobertura parcial".
2. **Declaração explícita de requisitos por módulo:** cada extrator, transformer e loader declara em docstring o que é `obrigatório` e o que é `opcional`. Nada de `assert` em campos opcionais.
3. **Avisos de cobertura, não crashes:** `src/load/relatorio.py` emite bloco "Cobertura do mês: X% (faltando: fatura Santander, contracheque Vitória)" em vez de abortar. Dashboard mostra banner discreto por mês incompleto.
4. **Agregações tolerantes a nulo:** médias, comparações temporais e ranking descartam meses incompletos com aviso nos metadados do relatório — não com `NaN` silencioso.
5. **Contrato com o usuário:** download é responsabilidade dele. Projeto **não** tenta inferir dados ausentes nem usa LLM para "completar" buracos (violaria ADR-08 e ADR-11).

## Consequências

**Positivas:**
- Usuário pode rodar o pipeline a qualquer momento sem medo de travar tudo
- Dashboard e análises ficam utilizáveis mesmo em mês com 1 único extrato
- Honestidade sobre gaps cria pressão visual para preencher (sem forçar bloqueio)
- Reduz acoplamento entre módulos: cada camada sobrevive sem todas as dependências

**Negativas:**
- Cada agregação precisa lidar explicitamente com mês parcial (mais código de guarda)
- Relatórios mensais precisam de seção "cobertura" que o usuário pode ignorar
- Comparações YoY/MoM podem ficar enganosas em meses incompletos se o aviso for ignorado

---

*"Melhor aproximadamente certo que exatamente errado." -- Carveth Read*
