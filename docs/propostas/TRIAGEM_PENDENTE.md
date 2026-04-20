---
id: triagem-2026-04-20
status: BLOQUEIA_PROXIMA_SPRINT
data: 2026-04-20
sprint_origem: 43
---

# Triagem Pendente -- 5 propostas da Fase BETA

> **Esta lista é gate obrigatório.** Nenhuma sprint nova (44 DANFE, 45 OCR scan,
> etc.) começa antes de todas as 5 propostas abaixo terem decisão humana
> (`aprovada` ou `rejeitada`). Decisão vai no campo `## Decisão humana` ao final
> de cada arquivo; o script `supervisor_aprovar.sh`/`supervisor_rejeitar.sh`
> grava no diário e move para `_arquivadas/`.

## Ordem sugerida de triagem

A ordem respeita dependência: decisões de upstream mudam o que faz sentido
aprovar downstream. Ex.: se item-nome-canonico mudar de formato,
apolice-item-heuristica-threshold pode precisar ser reajustado.

### 1. regra/enrich-yaml-sobrescreve-glyph

**O que decide:** quando CNPJ casa com YAML, o YAML vence o parser
(`setdefault` -> atribuição direta). Consequência: razão social "MAPFRE 5.À."
vira "MAPFRE S.A." no grafo.

**Como validar rápido (30s):**
```bash
# 1. Lê a proposta inteira (70 linhas)
cat docs/propostas/regra/2026-04-20_enrich-yaml-sobrescreve-glyph.md

# 2. Confirma o estado atual quebrado
sqlite3 data/output/grafo.sqlite \
  "SELECT json_extract(metadata,'\$.razao_social') FROM node WHERE tipo='seguradora';"
# Esperado HOJE: "MAPFRE Seguros Gerais 5.À."

# 3. Confirma que mappings/seguradoras.yaml tem razão canônica
grep -A2 "61.074.175" mappings/seguradoras.yaml
```

**Pergunta chave:** YAML é fonte de verdade quando CNPJ bate? Se sim -> aprova.

---

### 2. regra/item-nome-canonico-legivel

**O que decide:** trocar `nome_canonico` de `item` de `CNPJ|data|numero` para
algo legível (ex: descrição normalizada). Afeta queries ad-hoc e é pré-requisito
limpo pra proposta #3 (linking threshold).

**Como validar rápido (30s):**
```bash
# 1. Lê a proposta
cat docs/propostas/regra/2026-04-20_item-nome-canonico-legivel.md

# 2. Vê o problema no grafo
sqlite3 data/output/grafo.sqlite \
  "SELECT nome_canonico FROM node WHERE tipo='item' LIMIT 5;"
# Esperado HOJE: "00.776.574/0160-79|2026-04-19|000004300823" (ilegível)
```

**Pergunta chave:** prioriza legibilidade (query humana) ou unicidade
determinística (ID composto)? A proposta deve defender um dos dois.

---

### 3. linking/apolice-item-heuristica-threshold

**O que decide:** quão confiante o match fuzzy precisa ser (similaridade,
janela de data, peso do CNPJ) pra criar aresta `assegura` automática.

**Como validar rápido (1min):**
```bash
# 1. Lê a proposta
cat docs/propostas/linking/2026-04-20_apolice-item-heuristica-threshold.md

# 2. Vê as 2 arestas assegura que já foram criadas (caso-de-ouro da 44b)
sqlite3 data/output/grafo.sqlite "
SELECT a.nome_canonico, substr(i.metadata,1,80)
FROM edge e
JOIN node a ON a.id=e.src_id AND a.tipo='apolice'
JOIN node i ON i.id=e.dst_id AND i.tipo='item'
WHERE e.tipo='assegura';
"
```

**Pergunta chave:** threshold conservador (poucos falsos positivos, recall
menor) ou agressivo (mais arestas, risco de linking errado)? Proposta deve
mostrar os dois extremos com exemplos.

---

### 4. resolver/cardif-sem-bilhete-mapeado

**O que decide:** adicionar Cardif ao `mappings/seguradoras.yaml` com CNPJ +
SUSEP. Trivial — só dado novo.

**Como validar rápido (30s):**
```bash
# 1. Lê a proposta
cat docs/propostas/resolver/2026-04-20_cardif-sem-bilhete-mapeado.md

# 2. Confirma que Cardif não está no YAML hoje
grep -i cardif mappings/seguradoras.yaml || echo "ausente"

# 3. Confere se o CNPJ que a proposta sugere bate com fonte oficial
# (busca rápida no seu navegador: "Cardif do Brasil CNPJ SUSEP")
```

**Pergunta chave:** CNPJ e código SUSEP conferem com fonte oficial?
Se sim -> aprova. É cadastro, não decisão de design.

---

### 5. classificacao/notas-garantia-scan-nfce

**O que decide:** como o intake classifica o PDF escaneado
`notas de garantia e compras.pdf` (hoje vai para `_classificar/` porque
Sprint 41d não aciona OCR em scan puro). Gancho natural para Sprint 45.

**Como validar rápido (1min):**
```bash
# 1. Lê a proposta
cat docs/propostas/classificacao/2026-04-20_notas-garantia-scan-nfce.md

# 2. Confirma o arquivo parado
ls -la data/raw/_classificar/ | grep -i garantia

# 3. Olha 1 página de preview pra decidir se é NFC-e ou misto
```

**Pergunta chave:** aceitar "scan NFC-e" como subtipo agora (e deixar OCR
para Sprint 45), ou bloqueia até a 45 estar pronta?

---

## Comando de decisão

Para cada proposta, depois de ler:

**Aprovar:**
```bash
bash scripts/supervisor_aprovar.sh docs/propostas/<tipo>/<arquivo>.md
```

**Rejeitar (com motivo):**
```bash
bash scripts/supervisor_rejeitar.sh docs/propostas/<tipo>/<arquivo>.md "motivo curto"
```

Ambos gravam entrada em `docs/DIARIO_MELHORIAS.md` e movem o arquivo para
`docs/propostas/_arquivadas/`. Idempotente: rodar 2x não duplica.

## Gate para próxima sprint

Antes de começar Sprint 44 (DANFE) ou 45 (OCR scan):

```bash
# Deve retornar 0 arquivos
ls docs/propostas/{regra,classificacao,linking,resolver,categoria_item}/*.md 2>/dev/null | wc -l
```

Se retornar > 0, ainda há proposta pendente -- não abrir sprint nova.

---

*"A fila honesta de decisões vale mais que dez features sem triagem." -- princípio de artesão.*
