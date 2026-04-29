---
concluida_em: 2026-04-28
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 106
  title: "OCR ilegivel com fallback por arquivo similar do mesmo tipo (re-validacao cruzada)"
  prioridade: P1
  estimativa: ~3-4h
  origem: "achado da fase Opus Sprint 103: 2 cupons-foto em raw_conferir/ tem OCR ilegivel (qualidade da foto ruim) e ficam stale sem opcao de recuperacao automatica"
  touches:
    - path: src/intake/ocr_fallback_similar.py
      reason: "novo modulo: motor de matching por similaridade entre arquivos do mesmo tipo"
    - path: src/extractors/_ocr_comum.py
      reason: "linha ~210: quando texto extraido < limiar, chamar ocr_fallback_similar antes de jogar em _conferir"
    - path: src/intake/orchestrator.py
      reason: "registrar uso de fallback similar em metadata para auditoria (campo metadata.fallback_origem)"
    - path: mappings/ocr_fallback_config.yaml
      reason: "config: limiar de chars uteis por tipo, peso phash vs textual, janela temporal de busca"
    - path: tests/test_ocr_fallback_similar.py
      reason: "regressao: cupom ilegivel + cupom legivel mesma loja+data -> matching encontra; sem similar fica em _conferir"
  forbidden:
    - "Inventar dados que nao estao em nenhum arquivo (so reuso de campo extraido em arquivo existente)"
    - "Mudar comportamento default sem flag/config (graceful degradation)"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_ocr_fallback_similar.py -v"
    - cmd: "make smoke"
  acceptance_criteria:
    - "Quando OCR de uma foto/PDF retorna < 50 chars uteis, motor busca arquivo do mesmo tipo (cupom_fiscal_foto, recibo_nao_fiscal, etc) com OCR completo"
    - "Matching combina: phash (similaridade visual de imagem), data_proxima (+/- 7 dias do mtime), mesmo fornecedor/CNPJ se inferivel do nome do arquivo"
    - "Quando match encontrado com confidence >= 0.70, usa metadata do similar como ground-truth E grava `metadata.fallback_origem = <item_id_similar>` + `metadata.confidence_fallback = <valor>` para auditoria"
    - "Quando NAO ha match, mantem comportamento atual: vai para data/raw/_conferir/ com flag metadata.ocr_falhou=true"
    - "Helper isolado: ocr_fallback_similar.py pode ser invocado standalone para reanalise dos 2 cupons existentes em runtime real"
  proof_of_work_esperado: |
    # Antes
    ls data/raw/_conferir/ | wc -l
    # 2 (CUPOM_2e43640d.jpeg + CUPOM_6554d704.jpeg)
    
    .venv/bin/python -m src.intake.ocr_fallback_similar --reanalisar-conferir
    # Depois
    # Esperado: ate 2 arquivos saem de _conferir para pasta canonica
    # via fallback similar; nodes correspondentes ganham metadata.fallback_origem
```

---

# Sprint 106 -- OCR fallback por similar

**Status:** BACKLOG (P1, criada 2026-04-28 como achado Opus Sprint 103)

## Motivação

A fase Opus da Sprint 103 não conseguiu extrair valores confiaveis de 2 cupons-foto em `data/raw/_conferir/`:
- `CUPOM_2e43640d.jpeg` -- 2610 chars de OCR mas em sua maioria garbage; identifica apenas que e um Documento Auxiliar da NF.
- `CUPOM_6554d704.jpeg` -- compras de supermercado (sabao, fuba, atum) mas total não extraido.

Causa raiz: qualidade fotografica baixa (angulo, iluminacao, foco). Tesseract retorna texto mas com tantos erros que não e parseavel por regex.

Comportamento atual: arquivo fica em `_conferir/` aguardando humano. Mas isso assume que humano ainda tem o cupom fisico. Em volume real (760 arquivos), boa parte vai estar inutil.

**Estrategia nova:** quando OCR falha mas o arquivo e do mesmo template/loja/data de outro arquivo cujo OCR funcionou, podemos REUSAR a estrutura.

## Implementação

### 1. `src/intake/ocr_fallback_similar.py` -- motor de matching

```python
def buscar_similar(
    arquivo_falho: Path,
    grafo: GrafoDB,
    limiar_chars_uteis: int = 50,
    peso_phash: float = 0.5,
    peso_temporal: float = 0.3,
    peso_textual: float = 0.2,
    janela_dias: int = 7,
) -> dict | None:
    """Busca arquivo do mesmo tipo cujo OCR foi bem-sucedido.

    Heuristicas combinadas:
      - phash (perceptual hash) entre as imagens (imagehash lib).
      - data_proxima: |mtime(falho) - data_emissao(candidato)| <= janela_dias.
      - textual: substring do nome de fornecedor/CNPJ no nome do falho ou
        nos poucos chars uteis extraidos.

    Score combinado >= 0.70 dispara o uso do similar como template.
    Devolve dict com {item_id_similar, score, evidencia} ou None.
    """
```

### 2. Integração em `src/extractors/_ocr_comum.py`

Quando texto extraido < `limiar_chars_uteis` (default 50):
- Chama `buscar_similar`.
- Se acha: copia campos canonicos (data_emissao, total, fornecedor) do similar e grava metadata extra:
  ```python
  metadata.fallback_origem = item_id_similar
  metadata.confidence_fallback = score
  metadata.ocr_falhou = True   # auditoria
  ```
- Se não acha: comportamento atual (vai para `_conferir/`).

### 3. Config `mappings/ocr_fallback_config.yaml`

```yaml
limiar_chars_uteis_por_tipo:
  cupom_fiscal_foto: 50
  recibo_nao_fiscal: 30
  default: 50

pesos_score:
  phash: 0.5
  temporal: 0.3
  textual: 0.2

janela_temporal_dias_por_tipo:
  cupom_fiscal_foto: 7
  recibo_nao_fiscal: 30
  default: 14
```

### 4. CLI standalone para reanalise retroativa

```bash
.venv/bin/python -m src.intake.ocr_fallback_similar --reanalisar-conferir
.venv/bin/python -m src.intake.ocr_fallback_similar --reanalisar-conferir --executar
```

Roda fallback nos 2 cupons existentes em `_conferir/`.

## Armadilhas

- **phash precisa de `imagehash` (dep nova)**: adicionar em `pyproject.toml` `[project.optional-dependencies.dashboard]` (graceful degradation: se ausente, ignora componente phash mas continua com temporal+textual).
- **Risco de inferir errado**: confidence threshold de 0.70 e pesos configuraveis. Se humano discordar, override manual no Revisor.
- **Auditoria obrigatoria**: campo `metadata.fallback_origem` permite tracear cada inferencia. Sprint 103 ja exporta CSV com flag `divergencia` -- adicionar coluna `fallback_origem` no export.

## Testes regressivos

1. Cupom ilegivel (10 chars) + cupom legivel mesmo dia mesma loja -> matching encontra.
2. Cupom ilegivel sem similar -> vai para `_conferir/` (comportamento atual).
3. Cupom ilegivel com similar de outra data (>janela) -> não matcheia.
4. phash ausente (lib não instalada) -> matching funciona com peso temporal+textual zerando phash.
5. `--reanalisar-conferir` em runtime real: tenta resolver os 2 cupons.

## Dependências

- Sprint 95 (linking runtime) ja em main.
- Sprint 103 (fase Opus) entrega o estado atual para validacao.
- Adiciona dep opcional `imagehash` em pyproject.
