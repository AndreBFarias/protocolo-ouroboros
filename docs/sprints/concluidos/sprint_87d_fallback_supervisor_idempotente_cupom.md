## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 87d
  title: "Fallback supervisor idempotente por hash de conteúdo em cupom_termico_foto.py"
  touches:
    - path: src/extractors/cupom_termico_foto.py
      reason: "trocar uuid.uuid4().hex[:12] por cache_key(caminho) em _registrar_fallback_supervisor; atualizar docstring do módulo que cita <uuid>/"
    - path: tests/test_cupom_termico_foto.py
      reason: "teste de regressão: 2 invocações mesmo input geram 1 arquivo de proposta; inputs distintos geram 2"
  n_to_n_pairs:
    - ["identificador em dir _conferir/<hash>/", "nome de arquivo em docs/propostas/extracao_cupom/<hash>.md"]
  forbidden:
    - "Alterar outros extratores (boleto_pdf.py, danfe_pdf.py, nfce_pdf.py, cupom_garantia_estendida_pdf.py, recibo_nao_fiscal.py, receita_medica.py, garantia.py, xml_nfe.py, itau_pdf.py, santander_pdf.py, c6_xls.py, c6_csv.py, nubank_cartao_csv.py, nubank_cc_csv.py, energia_ocr.py, contracheque_pdf.py, _ocr_comum.py)"
    - "Mudar LIMIAR_CONFIDENCE_OK (70.0) ou LIMIAR_RECALL_OK (0.70)"
    - "Tocar data/cache/ocr/ ou docs/propostas/extracao_cupom/ (limpeza das 6 propostas órfãs é trabalho manual pós-sprint, fora do escopo)"
    - "Criar módulo utilitário novo ou refatorar assinatura da função além do identificador"
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/test_cupom_termico_foto.py -x -q"
      timeout: 120
    - cmd: ".venv/bin/pytest tests/ -q"
      timeout: 300
    - cmd: "make smoke"
      timeout: 120
  acceptance_criteria:
    - "Identificador do diretório _conferir/<id>/ e arquivo docs/propostas/extracao_cupom/<id>.md é determinístico por conteúdo do arquivo (derivado de cache_key(caminho), 12 chars hex)"
    - "Duas invocações sequenciais de _registrar_fallback_supervisor com mesmo caminho_foto resultam em exatamente 1 arquivo em diretorio_propostas (conteúdo sobrescrito na segunda rodada, não duplicado)"
    - "Duas invocações com caminhos de arquivos de conteúdo DIFERENTE geram 2 arquivos distintos (ids hex distintos)"
    - "Baseline de testes passa de 1139 -> 1140 passed (+1 teste novo), 10 skipped inalterado"
    - "make lint continua exit 0"
    - "make smoke continua verde (8/8 contratos aritméticos)"
    - "Zero regressão: nenhum dos 1139 testes existentes muda de status"
    - "import uuid pode permanecer no topo do módulo se ainda for usado em outro ponto; caso a linha 383 seja a única referência, remover o import"
    - "Docstring do módulo (linhas 14-15) atualizada: '<uuid>/' -> '<hash12>/' para refletir a mudança"
  proof_of_work_esperado: |
    # 1. Grep do identificador antigo deve retornar zero ocorrências em código de runtime
    grep -n "uuid.uuid4" src/extractors/cupom_termico_foto.py
    # esperado: nenhum match (ou só em comentário/docstring histórica)

    # 2. Teste de idempotência verde
    .venv/bin/pytest tests/test_cupom_termico_foto.py -x -q -k "idempotente or fallback_determin"

    # 3. Gauntlet completo
    make lint && .venv/bin/pytest tests/ -q && make smoke

    # 4. Simulação manual: criar 2 fixtures de fallback com mesmo conteúdo em tmp_path,
    # invocar _registrar_fallback_supervisor 2x, contar arquivos:
    .venv/bin/python -c "
    from pathlib import Path
    import tempfile, shutil
    from src.extractors.cupom_termico_foto import _registrar_fallback_supervisor
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        foto = base / 'cupom.jpg'
        foto.write_bytes(b'fake-jpg-bytes')
        dir_conf = base / 'conferir'
        dir_prop = base / 'propostas'
        for _ in range(3):
            _registrar_fallback_supervisor(
                caminho_foto=foto, texto_ocr='x', confidence=50.0, recall=0.3,
                documento={}, itens=[],
                diretorio_conferir=dir_conf, diretorio_propostas=dir_prop,
            )
        print('propostas geradas:', len(list(dir_prop.glob('*.md'))))
    "
    # esperado: 'propostas geradas: 1'

  tempo_estimado: "30min"
```

---

# Sprint 87d -- Fallback supervisor idempotente em `cupom_termico_foto.py`

**Status:** BACKLOG
**Prioridade:** P1 (débito técnico residual IOTA/KAPPA; sujeira visível em `docs/propostas/extracao_cupom/` a cada rodada)
**Dependências:** nenhuma -- sprint-fix independente
**Precedente:** Sprint 45 (APROVADO_COM_RESSALVAS, BRIEF §118), padrão canônico já em uso em `src/extractors/recibo_nao_fiscal.py:365-409`
**Issue:** RESSALVA-45-FALLBACK-NÃO-IDEMPOTENTE
**Tempo estimado:** 30min

## 1. Contexto

Durante a Sprint 45 (extrator de cupom fiscal térmico fotografado), a função `_registrar_fallback_supervisor` em `src/extractors/cupom_termico_foto.py:368-413` foi implementada usando `uuid.uuid4().hex[:12]` como identificador do diretório de conferência e do arquivo de proposta. A ressalva foi registrada na validação da Sprint 45 como "minúcia, sprint-prompt pronta" (BRIEF §118, item 3) e promovida a padrão recorrente canônico no BRIEF §92:

> **Fallback supervisor não-idempotente.** Rotas que criam `<uuid>/` + proposta MD quando OCR/recall abaixo do limiar devem derivar o identificador do `cache_key(caminho)` ou `sha256(conteudo)[:12]` -- nunca de `uuid.uuid4()` puro. Reprocessamento recorrente multiplica propostas se identificador for aleatório.

O padrão foi respeitado na sprint seguinte (`src/extractors/recibo_nao_fiscal.py:365-409`), que recebe `chave_hash: str` derivado de `cache_key(caminho)` como parâmetro e usa `chave_hash[:12]` como identificador. O cupom é o único extrator fora do padrão.

## 2. Evidência viva (2026-04-23)

Em `docs/propostas/extracao_cupom/` existem **6 arquivos de proposta** (`72525c89d231.md`, `7e8b49b4c07f.md`, `892feaf8ef10.md`, `c1abe00061c6.md`, `c2013c63fd82.md`, `e914ff76f33a.md`) gerados pelo reprocessamento de **2 cupons reais** em `data/raw/casal/nfs_fiscais/cupom_foto/` (`CUPOM_2e43640d.jpeg` + `CUPOM_6554d704.jpeg`). Cada cupom foi processado 3x, gerando UUID novo a cada rodada -- 2 x 3 = 6 propostas, quando o esperado seria 2 (uma por conteúdo único, sobrescrita nas rodadas seguintes).

## 3. Problema técnico

Arquivo: `src/extractors/cupom_termico_foto.py`
Linha: 383
Código atual:
```python
identificador = uuid.uuid4().hex[:12]
```

Efeito: toda invocação do fallback (confidence < 70 OU recall < 70%) gera identificador novo. Reprocessar o mesmo cupom N vezes produz N propostas em `docs/propostas/extracao_cupom/` e N diretórios em `data/raw/_conferir/`. Ingestão aprovada no grafo já é idempotente por chave sintética (`_NAO_FISCAL_<hash>`), mas a rota de fallback não foi simetrizada.

## 4. Solução

Trocar o identificador por hash determinístico derivado do conteúdo do arquivo. Duas opções:

1. **`cache_key(caminho)[:12]`** -- reuso direto da função canônica já importada no módulo (linha 42). `cache_key` é SHA-256 dos bytes do arquivo, retornando 16 hex chars (`src/extractors/_ocr_comum.py:188-196`). Usar os 12 primeiros mantém o comprimento do UUID truncado original.
2. **`sha256(conteudo_bytes)[:12]` inline** -- equivalente funcional, mas redefine hashing já encapsulado em `cache_key`.

**Decisão arquitetural recomendada: opção 1.** Razões:
- `cache_key` já é o hash canônico usado pelo cache OCR em `data/cache/ocr/`. Simetria total: arquivo -> hash -> cache OCR + diretório conferência + proposta MD (todos derivados do mesmo identificador).
- Padrão replicado exatamente do `recibo_nao_fiscal.py`, que recebe `chave_hash` via parâmetro do caller. O cupom pode derivar o mesmo hash dentro da função (já tem `caminho_foto: Path` disponível).
- Evita adicionar call-site novo em `extrair()` (linha 555) -- a mudança fica localizada em `_registrar_fallback_supervisor`.
- Zero dependência nova; `cache_key` já está importado.

## 5. Escopo permitido

### Arquivos a modificar
- `src/extractors/cupom_termico_foto.py` -- apenas 2 mudanças:
  - Linha 383: substituir `identificador = uuid.uuid4().hex[:12]` por `identificador = cache_key(caminho_foto)[:12]`.
  - Linhas 14-15 do docstring do módulo: atualizar `<uuid>/` -> `<hash12>/` (2 ocorrências: uma no path `_conferir/<uuid>/`, outra em `docs/propostas/extracao_cupom/<uuid>.md`).
  - Linha 378 do docstring interno da função: atualizar referência de "uuid" para "hash do conteúdo" (análogo à linha 378-381 de `recibo_nao_fiscal.py`).
  - Se `import uuid` (linha 34) deixar de ser usado, remover a linha. Confirmar com `grep -n "uuid" src/extractors/cupom_termico_foto.py` após a edição.

### Arquivos a criar
- Nenhum.

### Arquivos a modificar (testes)
- `tests/test_cupom_termico_foto.py` -- acrescentar 1 teste de regressão:
  - Nome sugerido: `test_fallback_supervisor_e_idempotente_por_hash_de_conteudo`
  - Comportamento: em `tmp_path`, cria arquivo `cupom.jpg` com bytes arbitrários, invoca `_registrar_fallback_supervisor` 2x com o mesmo `caminho_foto` (e quaisquer `documento`/`itens`/`confidence`/`recall` de fixture), confere que `diretorio_propostas` tem exatamente 1 arquivo após a 2a chamada; depois cria `cupom2.jpg` com bytes diferentes, invoca mais 1x, confere que agora existem 2 arquivos com nomes hex distintos.
  - Assertion adicional: o nome do arquivo de proposta bate com `cache_key(caminho_foto)[:12] + ".md"` (teste de simetria com o cache OCR).

## 6. Escopo proibido

- **Não alterar outros extratores.** Confirmado via grep que só `cupom_termico_foto.py` tem `uuid.uuid4` no pattern `_registrar_fallback_supervisor`. `recibo_nao_fiscal.py` já é canônico. Demais extratores (`boleto_pdf.py`, `danfe_pdf.py`, `nfce_pdf.py`, `cupom_garantia_estendida_pdf.py`, `receita_medica.py`, `garantia.py`, `xml_nfe.py`, `itau_pdf.py`, `santander_pdf.py`, `c6_xls.py`, `c6_csv.py`, `nubank_cartao_csv.py`, `nubank_cc_csv.py`, `energia_ocr.py`, `contracheque_pdf.py`, `_ocr_comum.py`) NÃO têm função equivalente.
- **Não mexer em `LIMIAR_CONFIDENCE_OK=70.0` ou `LIMIAR_RECALL_OK=0.70`** -- thresholds calibrados na Sprint 45 e validados em fixtures reais.
- **Não tocar em `data/cache/ocr/`** -- já idempotente por design desde Sprint 45.
- **Não remover as 6 propostas órfãs em `docs/propostas/extracao_cupom/`** -- limpeza é trabalho pós-sprint (reprocessamento completo dos 2 cupons após o fix gera 2 propostas determinísticas; operador humano deleta as 6 antigas quando conveniente). Deletar nesta sprint misturaria "fix de idempotência" com "limpeza de lixo residual" -- responsabilidades distintas.
- **Não refatorar a assinatura da função.** Manter `(caminho_foto, texto_ocr, confidence, recall, documento, itens, diretorio_conferir, diretorio_propostas)`. A mudança é interna à função (cálculo do `identificador`).
- **Não extrair utilitário compartilhado.** Recibo_nao_fiscal recebe `chave_hash` como parâmetro; cupom vai calcular internamente via `cache_key(caminho_foto)`. Assinaturas diferentes são aceitáveis -- centralizar em módulo novo é refactor INFRA separado, fora do escopo.

## 7. Invariantes a preservar

- **Chaves de dict em PT-sem-acento no grafo** (BRIEF §89, §119): não se aplica aqui, mas vale lembrar se o teste novo tocar em nodes do grafo (não deveria).
- **Fallback não ingere no grafo** (`extrair()` linha 565: `return []` após `_registrar_fallback_supervisor`) -- mudar o identificador não pode afetar esse fluxo.
- **`caminho_foto.exists()` é checado antes de copiar** (linha 387) -- idempotência em reprocessamento quando arquivo original já foi movido. Preservar.
- **`destino_foto.write_bytes(caminho_foto.read_bytes())`** (linha 389) pode falhar em `OSError` e é logado como warning, não exceção -- preservar esse contrato (linha 390-393).
- **Teste de idempotência usa `tmp_path`, nunca `docs/propostas/extracao_cupom/` real** -- convenção do projeto (BRIEF §131, padrão adapter de borda).
- **Meta-regra §7 de CLAUDE.md:** nunca remover código funcional sem autorização. Remover `import uuid` é aceitável porque a linha se torna lixo morto -- confirmar com grep que é de fato a única referência antes de deletar.
- **Acentuação correta** em docstring atualizada e nome de teste.
- **Citação filosófica final do módulo (linha 667-668) preservada intacta.**

## 8. Plano de implementação

1. **Ler `src/extractors/cupom_termico_foto.py:1-50`** para confirmar que `cache_key` já está importado de `_ocr_comum` (linha 42). Confirmado no planejamento.

2. **Editar linha 383** de `src/extractors/cupom_termico_foto.py`:
   ```python
   # Antes
   identificador = uuid.uuid4().hex[:12]
   # Depois
   identificador = cache_key(caminho_foto)[:12]
   ```

3. **Editar docstring interno da função (linhas 378-382)** para substituir referência a "uuid" por "hash do conteúdo" (espelhar `recibo_nao_fiscal.py:378-381`):
   ```
   """Move a foto para `_conferir/<hash12>/` e cria proposta em MD.

   Hash derivado de `cache_key(caminho_foto)` (SHA-256 dos bytes).
   Identificador estável: reprocessar o mesmo arquivo NÃO cria propostas
   novas, sobrescreve a mesma. Não levanta exceção se o arquivo de origem
   não existir mais (idempotência em reprocessamento).
   """
   ```

4. **Editar docstring do módulo (linhas 14-15)** para trocar `<uuid>/` -> `<hash12>/`:
   ```
     7. Calcula recall = soma(itens) / total e, se confidence < 70% ou
        recall < 70%, move a foto para `data/raw/_conferir/<hash12>/` e
        registra proposta em `docs/propostas/extracao_cupom/<hash12>.md`.
   ```

5. **Verificar se `import uuid` (linha 34) ainda é necessário:**
   ```bash
   grep -n "uuid" src/extractors/cupom_termico_foto.py
   ```
   Se só aparecer em docstring (comentários textuais) e na linha de import, remover a linha 34.

6. **Adicionar teste em `tests/test_cupom_termico_foto.py`:**
   ```python
   def test_fallback_supervisor_e_idempotente_por_hash_de_conteudo(tmp_path):
       """Duas invocações com mesmo arquivo geram 1 proposta; arquivos distintos geram 2."""
       from src.extractors.cupom_termico_foto import _registrar_fallback_supervisor

       foto_a = tmp_path / "cupom_a.jpg"
       foto_a.write_bytes(b"bytes-do-cupom-a")
       dir_conf = tmp_path / "conferir"
       dir_prop = tmp_path / "propostas"

       for _ in range(2):
           _registrar_fallback_supervisor(
               caminho_foto=foto_a,
               texto_ocr="texto ilegível",
               confidence=50.0,
               recall=0.3,
               documento={},
               itens=[],
               diretorio_conferir=dir_conf,
               diretorio_propostas=dir_prop,
           )

       propostas = list(dir_prop.glob("*.md"))
       assert len(propostas) == 1, (
           f"esperado 1 proposta após 2 invocações com mesmo conteúdo, "
           f"obtido {len(propostas)}: {[p.name for p in propostas]}"
       )

       # Simetria com cache OCR: identificador é cache_key(caminho)[:12]
       esperado = cache_key(foto_a)[:12] + ".md"
       assert propostas[0].name == esperado, (
           f"nome da proposta deveria ser {esperado}, obtido {propostas[0].name}"
       )

       # Conteúdo diferente gera proposta distinta
       foto_b = tmp_path / "cupom_b.jpg"
       foto_b.write_bytes(b"bytes-do-cupom-b-diferente")
       _registrar_fallback_supervisor(
           caminho_foto=foto_b,
           texto_ocr="outro texto",
           confidence=40.0,
           recall=0.2,
           documento={},
           itens=[],
           diretorio_conferir=dir_conf,
           diretorio_propostas=dir_prop,
       )

       propostas = list(dir_prop.glob("*.md"))
       assert len(propostas) == 2, (
           f"esperado 2 propostas após arquivos de conteúdo distinto, obtido {len(propostas)}"
       )
   ```

7. **Rodar gauntlet local:**
   ```bash
   .venv/bin/pytest tests/test_cupom_termico_foto.py -x -q
   make lint
   .venv/bin/pytest tests/ -q    # esperado: 1140 passed / 10 skipped
   make smoke
   ```

8. **Commit atômico:**
   - Mensagem: `fix: cupom termico fallback idempotente por hash de conteudo`
   - Corpo em PT-BR descrevendo ressalva Sprint 45 fechada.
   - SEM menção a ferramenta IA (hook `commit-msg` bloqueia).

9. **Mover spec** de `docs/sprints/backlog/sprint_87d_*.md` -> `docs/sprints/concluidos/sprint_87d_*_CONCLUIDA.md` após `bash scripts/finish_sprint.sh 87d` exit 0.

## 9. Aritmética

Não se aplica (sprint não tem meta de linhas).

- Linhas modificadas em `cupom_termico_foto.py`: ~5 (linha 383 + 3-4 linhas de docstring + possível remoção de `import uuid`).
- Linhas adicionadas em `tests/test_cupom_termico_foto.py`: ~40 (1 teste novo).
- Delta total: ~+35 a +45 linhas no repositório.

## 10. Testes

### Novo
- `tests/test_cupom_termico_foto.py::test_fallback_supervisor_e_idempotente_por_hash_de_conteudo` -- valida idempotência por hash de conteúdo + simetria com `cache_key`.

### Baseline
- Antes: `1139 passed / 10 skipped`
- Depois esperado: `1140 passed / 10 skipped` (+1 teste novo, zero regressão)

### Smoke
- `make smoke` deve continuar verde (8/8 contratos do XLSX -- essa sprint não toca o pipeline de transações).

## 11. Proof-of-work esperado

Gauntlet executado e documentado no commit/fechamento:

```bash
# 1. Diff final tocou apenas os 2 arquivos autorizados
git diff --name-only | sort
# esperado:
# src/extractors/cupom_termico_foto.py
# tests/test_cupom_termico_foto.py

# 2. Zero uuid.uuid4 em runtime do extrator
grep -n "uuid.uuid4" src/extractors/cupom_termico_foto.py
# esperado: nenhum match

# 3. Teste novo verde
.venv/bin/pytest tests/test_cupom_termico_foto.py::test_fallback_supervisor_e_idempotente_por_hash_de_conteudo -v

# 4. Suite completa
.venv/bin/pytest tests/ -q
# esperado: 1140 passed, 10 skipped

# 5. Lint verde (inclui scripts/check_acentuacao.py --all)
make lint

# 6. Smoke runtime-real aritmético
make smoke

# 7. Acentuação periférica nos arquivos modificados
python3 ~/.config/zsh/scripts/validar-acentuacao.py --paths \
  src/extractors/cupom_termico_foto.py \
  tests/test_cupom_termico_foto.py

# 8. Simulação manual de idempotência (opcional, reprodução empírica)
.venv/bin/python -c "
from pathlib import Path
import tempfile
from src.extractors.cupom_termico_foto import _registrar_fallback_supervisor
with tempfile.TemporaryDirectory() as tmp:
    base = Path(tmp)
    foto = base / 'cupom.jpg'; foto.write_bytes(b'fake')
    dc = base / 'c'; dp = base / 'p'
    for _ in range(3):
        _registrar_fallback_supervisor(
            caminho_foto=foto, texto_ocr='x', confidence=50.0, recall=0.3,
            documento={}, itens=[],
            diretorio_conferir=dc, diretorio_propostas=dp,
        )
    print('propostas:', len(list(dp.glob('*.md'))))
"
# esperado: propostas: 1

# 9. Gauntlet final da sprint
bash scripts/finish_sprint.sh 87d
```

### Validação visual
Não se aplica -- mudança é puramente back-end (identificador de arquivo interno).

### Hipótese verificada
- `rg "_registrar_fallback_supervisor" src/extractors/` -> apenas `cupom_termico_foto.py` e `recibo_nao_fiscal.py`. Recibo já é canônico.
- `rg "uuid.uuid4" src/extractors/` -> apenas `cupom_termico_foto.py:383`. Nenhum outro extrator afetado.
- `rg "def cache_key" src/extractors/_ocr_comum.py` -> `:188`, confirmado determinístico por conteúdo.

## 12. Riscos e não-objetivos

### Riscos
- **Testes reais do extrator que escrevem em `docs/propostas/extracao_cupom/` real.** Verificação: grep em `tests/test_cupom_termico_foto.py` por `_DIR_PROPOSTAS_PADRAO` ou `docs/propostas` -- nenhum teste existente deve usar path real (todos passam `diretorio_propostas=tmp_path`). Se algum teste existente contar "exatamente 1 arquivo" e rodava com UUID (contagem passava por sorte), pode mudar de status -- conferir no runtime.
- **`import uuid` usado em outro lugar do módulo.** Verificação via grep antes de remover (passo 5 do plano).

### Não-objetivos
- **Refatorar `_registrar_fallback_supervisor` para receber `chave_hash` via parâmetro** (como `recibo_nao_fiscal.py` faz). Seria simetria arquitetural mais forte, mas muda a assinatura pública da função e força mudança em `extrair()` -- escopo maior. Candidato a sprint INFRA futura (`INFRA-unificar-fallback-supervisor`) que extrai o padrão para módulo compartilhado.
- **Limpar as 6 propostas órfãs em `docs/propostas/extracao_cupom/`.** Trabalho manual do operador após reprocessar os 2 cupons reais. Delegar à próxima rodada do pipeline.
- **Unificar paths de propostas entre cupom e recibo.** Cada extrator tem seu próprio `diretorio_propostas` por design (domínios distintos: cupom fiscal vs recibo não-fiscal).

## 13. Referências

- BRIEF: `VALIDATOR_BRIEF.md`
  - §92 (fallback supervisor não-idempotente -- padrão recorrente de bug)
  - §118 (Sprint 45 histórico, ressalva original registrada)
  - §91 (`_parse_valor_br` redefinido localmente -- padrão análogo de helper comum não extraído, confirma que divergência de estilo entre extratores é aceitável)
- Sprint precedente: `docs/sprints/concluidos/sprint_45_extrator_cupom_termico_foto.md`
- Padrão canônico de referência: `src/extractors/recibo_nao_fiscal.py:365-409` (linhas 376-381 especificamente: "Hash derivado de `cache_key(caminho)` (SHA-256 dos bytes do arquivo). Identificador estável: reprocessar o mesmo arquivo NÃO cria propostas novas, sobrescreve a mesma.")
- Função canônica: `src/extractors/_ocr_comum.py::cache_key` (linha 188)
- Evidência viva: `ls docs/propostas/extracao_cupom/` = 6 arquivos; `ls data/raw/casal/nfs_fiscais/cupom_foto/` = 2 cupons. Razão 3:1 confirma bug.

---

*"A repetição do idêntico é obra da razão; a repetição do diferente, obra do acaso. O bom engenheiro converte acaso em razão." -- Gottfried Wilhelm Leibniz, adaptação livre dos Novos Ensaios sobre o Entendimento Humano*
