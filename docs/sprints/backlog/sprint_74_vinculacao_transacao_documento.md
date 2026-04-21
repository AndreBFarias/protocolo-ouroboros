## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 74
  title: "Vinculação transação<->documento: matching heurístico + modal com preview real do PDF/imagem"
  touches:
    - path: src/graph/linking.py
      reason: "motor de matching (data+valor+fornecedor) -> edges pago_com/confirma/comprovante/origem"
    - path: src/graph/queries.py
      reason: "nova função documentos_de_transacao(tx_id) -> list[dict]"
    - path: src/dashboard/componentes/preview_documento.py
      reason: "novo: componente que embeda PDF ou imagem via data URL base64"
    - path: src/dashboard/componentes/modal_transacao.py
      reason: "novo: st.dialog reutilizável que junta detalhes + preview"
    - path: src/dashboard/paginas/extrato.py
      reason: "coluna nova 'Ações' com botão que abre modal"
    - path: mappings/categorias_tracking.yaml
      reason: "declara categorias obrigatórias ADR-20"
    - path: tests/test_linking_heuristico.py
      reason: "testes de score, matching e GTC-01"
    - path: tests/test_preview_documento.py
      reason: "testes do componente (PDF e imagem)"
  n_to_n_pairs:
    - ["tipos de edge em src/graph/linking.py", "ADR-20 §Regras.1"]
    - ["categorias obrigatória_tracking", "badge amarelo no Extrato"]
  forbidden:
    - "Criar vínculo auto com score < 0.8"
    - "Depender de servidor externo para servir arquivos (usar data URL base64)"
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/test_linking_heuristico.py tests/test_preview_documento.py -v"
      timeout: 60
  acceptance_criteria:
    - "4 tipos de edge em src/graph/linking.py: pago_com, confirma, comprovante, origem"
    - "score_matching retorna 0..1 usando pesos: data 0.3, valor 0.4, fornecedor 0.3"
    - "Score >= 0.8: vínculo automático (edge criada com peso=score)"
    - "Score 0.5-0.8: proposta em docs/propostas/linking/{data}-{slug}.md"
    - "Score < 0.5: ignorado"
    - "GTC-01 passa: natacao_andre.pdf casa com SESC C6 R$ 103,93 2026-03-19 OU vira proposta"
    - "Componente preview_documento.py aceita PDF (iframe data URL) e imagem (st.image) e retorna st.markdown/st.image"
    - "Modal da transação abre via botão em linha do Extrato; mostra preview inline do primeiro documento vinculado"
    - "mappings/categorias_tracking.yaml declara categorias obrigatórias"
    - "Transação sem comprovante + categoria obrigatória mostra badge amarelo na tabela"
    - "Estado da transação (aberta/confirmada/totalmente_documentada/irrecuperavel) calculado e exibido no modal"
  proof_of_work_esperado: |
    # 1. Rodar matcher em grafo atual
    .venv/bin/python -c "
    from src.graph.linking import linkar_documentos
    stats = linkar_documentos()
    print(stats)
    assert stats['auto'] + stats['propostas'] >= 1
    "
    # 2. Testes
    .venv/bin/pytest tests/test_linking_heuristico.py tests/test_preview_documento.py -v
    # 3. Playwright: abrir aba Extrato, clicar em linha de Sesc, confirmar modal com PDF
```

---

# Sprint 74 — Vinculação transação <-> documento

**Status:** BACKLOG
**Prioridade:** P0 (coração da visão ADR-20)
**Dependências:** Sprints 48 (base linking), 49 (entity resolution), 57 (volume real), 70 (inbox unificada)
**Desbloqueia:** 75 (gap analysis), 79 (aba pagamentos)
**ADR:** ADR-20

## Problema

Andre quer: clicar em "Natação André" e ver o boleto E o recibo. Hoje: 99% das transações sem comprovante; grafo tem apenas 2 documentos (Sprint 57 expôs).

Golden Test Case (GTC-01 em `docs/GOLDEN_TEST_CASES.md`): `inbox/natacao_andre.pdf` + `natacao_andre2.pdf` já estão preparados pelo Andre. Devem casar com linhas 5948/5954 (C6 R$ 103,93 2026-03-19) e 6056 (Itaú R$ 101,60 2026-04-10).

## Contexto técnico (LEITURA OBRIGATÓRIA)

### Como embedar PDF no Streamlit

Streamlit não serve arquivos locais por `file://` path (bloqueio CORS do browser). Soluções:

**Opção A — Data URL base64 via iframe** (preferida, self-contained)

```python
import base64
from pathlib import Path
import streamlit as st

def embed_pdf(caminho_pdf: Path, altura: int = 600):
    """Embeda PDF inline via data URL base64. Funciona 100% offline."""
    if not caminho_pdf.exists():
        st.error(f"Arquivo não encontrado: {caminho_pdf}")
        return
    data = caminho_pdf.read_bytes()
    b64 = base64.b64encode(data).decode("utf-8")
    html = f'''
    <iframe src="data:application/pdf;base64,{b64}"
            width="100%" height="{altura}"
            style="border:1px solid #44475a; border-radius:6px;">
    </iframe>
    '''
    st.markdown(html, unsafe_allow_html=True)
```

Limite: PDFs >5MB ficam lentos (base64 infla 33%). Para esses, cair para link de download.

**Opção B — Servir via endpoint Flask lateral** (descartada — requer processo extra).

### Como embedar imagem

Simples: `st.image(str(caminho_imagem))`. Aceita PNG, JPG, WEBP.

### Componente canônico

```python
# src/dashboard/componentes/preview_documento.py
import base64
from pathlib import Path
from typing import Literal
import streamlit as st

TipoArquivo = Literal["pdf", "imagem", "outro"]

LIMITE_BYTES_EMBED = 5 * 1024 * 1024  # 5 MB

def _tipo_arquivo(caminho: Path) -> TipoArquivo:
    suf = caminho.suffix.lower()
    if suf == ".pdf":
        return "pdf"
    if suf in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
        return "imagem"
    return "outro"

def preview_documento(caminho_original: Path, altura: int = 600):
    """Renderiza preview inline de PDF ou imagem. Fallback para link se tipo não suportado."""
    if not caminho_original.exists():
        st.error(f"Arquivo não encontrado: {caminho_original.name}")
        return

    tipo = _tipo_arquivo(caminho_original)
    tamanho = caminho_original.stat().st_size

    if tipo == "pdf":
        if tamanho > LIMITE_BYTES_EMBED:
            st.warning(f"PDF grande ({tamanho / 1024 / 1024:.1f} MB). Baixe para visualizar.")
            st.download_button(
                "Baixar PDF",
                data=caminho_original.read_bytes(),
                file_name=caminho_original.name,
                mime="application/pdf",
            )
        else:
            b64 = base64.b64encode(caminho_original.read_bytes()).decode("utf-8")
            html = (
                f'<iframe src="data:application/pdf;base64,{b64}" '
                f'width="100%" height="{altura}" '
                f'style="border:1px solid #44475a; border-radius:6px;"></iframe>'
            )
            st.markdown(html, unsafe_allow_html=True)
    elif tipo == "imagem":
        st.image(str(caminho_original), use_column_width=True)
    else:
        st.info(f"Tipo não suportado para preview: {caminho_original.suffix}")
        st.download_button(
            "Baixar arquivo",
            data=caminho_original.read_bytes(),
            file_name=caminho_original.name,
        )
```

### Modal da transação — padrão canônico

Streamlit 1.31+ tem `st.dialog` (decorator que transforma função em modal). Padrão:

```python
# src/dashboard/componentes/modal_transacao.py
import streamlit as st
from pathlib import Path
from src.dashboard.componentes.preview_documento import preview_documento

@st.dialog("Detalhes da transação", width="large")
def mostrar_modal(tx: dict, docs_vinculados: list[dict]):
    # Cabeçalho
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Data", tx["data"].strftime("%d/%m/%Y"))
    col2.metric("Valor", f"R$ {tx['valor']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    col3.metric("Categoria", tx.get("categoria", "-"))
    col4.metric("Banco", tx.get("banco_origem", "-"))

    st.divider()

    # Estado documental
    estado = _inferir_estado(docs_vinculados)
    cor_estado = {
        "aberta": "red", "confirmada": "orange",
        "totalmente_documentada": "green", "irrecuperavel": "gray",
    }[estado]
    st.markdown(
        f"**Estado:** :{cor_estado}[{estado.upper().replace('_', ' ')}]"
    )

    # Documentos vinculados
    if docs_vinculados:
        for i, doc in enumerate(docs_vinculados):
            with st.expander(
                f"{doc['tipo_documento']} — {doc['tipo_edge']} — R$ {doc.get('valor', 0):,.2f}",
                expanded=(i == 0),  # primeiro expandido
            ):
                caminho = Path(doc["arquivo_original"])
                preview_documento(caminho, altura=500)
    else:
        st.warning("Nenhum comprovante vinculado.")
        _oferecer_associacao_manual(tx)


def _oferecer_associacao_manual(tx: dict):
    """Lista arquivos na inbox não vinculados + botão Vincular."""
    from src.graph.queries import listar_docs_inbox_nao_vinculados
    candidatos = listar_docs_inbox_nao_vinculados(pessoa=tx.get("quem"))
    if not candidatos:
        st.info("Nenhum documento não-vinculado na inbox. Jogue um PDF/JPG em ~/Controle de Bordo/Inbox/ e rode ./run.sh --inbox.")
        return
    sel = st.selectbox("Documentos disponíveis", candidatos, format_func=lambda d: d["nome"])
    if st.button("Vincular", type="primary"):
        from src.graph.linking import criar_edge_manual
        criar_edge_manual(doc_id=sel["id"], tx_id=tx["id"], tipo="comprovante")
        st.success("Vinculado!")
        st.rerun()


def _inferir_estado(docs: list[dict]) -> str:
    tipos = {d["tipo_edge"] for d in docs}
    if not tipos:
        return "aberta"
    if "origem" in tipos and ("confirma" in tipos or "comprovante" in tipos):
        return "totalmente_documentada"
    if "confirma" in tipos or "comprovante" in tipos:
        return "confirmada"
    return "confirmada"  # fallback conservador
```

### Motor de matching — detalhado

```python
# src/graph/linking.py
from datetime import timedelta
import unicodedata

TIPOS_EDGE = {"pago_com", "confirma", "comprovante", "origem"}

def _normalizar(s: str) -> str:
    return unicodedata.normalize("NFD", s.upper()).encode("ascii", "ignore").decode("ascii")

def _score_data(doc_data, tx_data) -> float:
    dias = abs((doc_data - tx_data).days)
    if dias <= 3:
        return 1.0
    if dias <= 7:
        return 0.5
    return 0.0

def _score_valor(doc_valor: float, tx_valor: float) -> float:
    if doc_valor <= 0 or tx_valor <= 0:
        return 0.0
    diff_pct = abs(doc_valor - tx_valor) / max(tx_valor, 0.01)
    if diff_pct < 0.001:  # match exato até 1 centavo
        return 1.0
    if diff_pct < 0.01:   # tolerância 1%
        return 0.7
    if diff_pct < 0.05:   # tolerância 5% (juros/multa em boleto)
        return 0.4
    return 0.0

def _score_fornecedor(doc_fornecedor: str, tx_local: str) -> float:
    if not doc_fornecedor or not tx_local:
        return 0.0
    dn = _normalizar(doc_fornecedor)
    tn = _normalizar(tx_local)
    if dn == tn:
        return 1.0
    if dn in tn or tn in dn:
        return 0.8
    # fuzzy via rapidfuzz (já no pyproject.toml desde Sprint 49)
    from rapidfuzz import fuzz
    ratio = fuzz.token_set_ratio(dn, tn) / 100
    return ratio if ratio > 0.6 else 0.0

def score_matching(doc: dict, tx: dict) -> float:
    return (
        0.3 * _score_data(doc["data"], tx["data"])
        + 0.4 * _score_valor(doc["valor"], tx["valor"])
        + 0.3 * _score_fornecedor(doc.get("fornecedor", ""), tx.get("local", ""))
    )

def classificar_edge(doc: dict, score: float) -> str:
    tipo_doc = doc.get("tipo_documento", "")
    if tipo_doc == "boleto":
        return "confirma"
    if tipo_doc in {"recibo", "cupom_termico", "cupom_nao_fiscal", "voucher", "nfce", "cupom_termico_foto"}:
        return "comprovante"
    if tipo_doc in {"contrato", "apolice", "cupom_garantia"}:
        return "origem"
    return "pago_com"

def linkar_documentos() -> dict:
    stats = {"auto": 0, "propostas": 0, "zero": 0, "pulados": 0}
    from src.graph.queries import documentos_sem_edge_transacao, tx_candidatas_para_doc
    for doc in documentos_sem_edge_transacao():
        candidatas = tx_candidatas_para_doc(doc, janela_dias=10, mesmo_pessoa=True)
        if not candidatas:
            stats["pulados"] += 1
            continue
        melhor = max(candidatas, key=lambda tx: score_matching(doc, tx))
        s = score_matching(doc, melhor)
        tipo_edge = classificar_edge(doc, s)
        if s >= 0.8:
            _criar_edge(doc_id=doc["id"], tx_id=melhor["id"], tipo=tipo_edge, peso=s)
            stats["auto"] += 1
        elif s >= 0.5:
            _criar_proposta(doc=doc, tx=melhor, score=s, tipo_edge=tipo_edge)
            stats["propostas"] += 1
        else:
            stats["zero"] += 1
    return stats
```

### Proposta (score 0.5-0.8) em arquivo .md

```python
def _criar_proposta(doc, tx, score, tipo_edge):
    from pathlib import Path
    pasta = Path("docs/propostas/linking")
    pasta.mkdir(parents=True, exist_ok=True)
    arq = pasta / f"{doc['data'].isoformat()}-doc{doc['id']}-tx{tx['id']}.md"
    arq.write_text(f"""---
tipo: proposta_linking
doc_id: {doc['id']}
tx_id: {tx['id']}
score: {score:.3f}
tipo_edge_sugerido: {tipo_edge}
criada_em: {datetime.now().isoformat()}
---

# Proposta de vínculo documento <-> transação (score {score:.2f})

**Documento:** {doc.get('tipo_documento')} de {doc.get('fornecedor')} em {doc['data']} por R$ {doc['valor']:.2f}
**Transação:** {tx['local']} ({tx['banco_origem']}) em {tx['data']} por R$ {tx['valor']:.2f}

## Para aprovar

```bash
.venv/bin/python -m src.graph.linking aprovar --doc {doc['id']} --tx {tx['id']} --tipo {tipo_edge}
```

## Para rejeitar

Apagar este arquivo. Na próxima rodada de matcher, score ficará registrado como "rejeitado pelo supervisor" via flag.
""")
```

### Categorias de tracking obrigatório

```yaml
# mappings/categorias_tracking.yaml
# Categorias onde AUSÊNCIA de comprovante é ANOMALIA destacada no dashboard.
obrigatoria_tracking:
  - Farmácia         # IRPF
  - Saúde            # IRPF
  - Aluguel          # comprovação moradia
  - Educação         # IRPF
  - Impostos         # legal
  - Seguros          # apólice
  - Plano de saúde   # IRPF
  - Natação          # recorrente, Andre pediu
```

### Badge na aba Extrato

```python
# src/dashboard/paginas/extrato.py trecho
def _badge_sem_doc(row, categorias_obrigatorias: set[str]) -> str:
    if row["categoria"] not in categorias_obrigatorias:
        return ""
    if row.get("_tem_documento"):
        return ""
    return "sem comprovante"
```

## Armadilhas com solução

| Ref | Armadilha | Solução concreta |
|---|---|---|
| A74-1 | `st.dialog` exige Streamlit 1.31+ | Mesmo requisito da Sprint 73; já coberto em pyproject.toml |
| A74-2 | PDF embed via data URL lento em >5MB | Fallback para download_button no limiar (implementado em `preview_documento`) |
| A74-3 | iframe bloqueado por CSP em data URL | Streamlit por padrão permite; se usuário tem config custom, documentar |
| A74-4 | Matching via fuzzy pode dar falso positivo em fornecedores genéricos ("Pix Recebido") | Exigir match exato ou score_fornecedor >= 0.6; transações sem fornecedor claro pulam |
| A74-5 | GTC-01 pode falhar se PDF tem conteúdo ilegível (OCR necessário) | Extrator de boleto precisa OCR fallback; se falhar, registrar GTC como "pendente extrator OCR melhor" sem bloquear sprint |
| A74-6 | Propostas em docs/propostas/linking/ acumulam indefinidamente | Sprint futura: script de revisão em lote. Aqui apenas criar pasta + arquivo .md + comando inline para aprovar |
| A74-7 | Categoria "Natação" do Andre + Sesc tem Obrigatório mas formas variam | Matcher usa `_normalizar` (NFD + ASCII) + fuzzy token_set |

## Testes concretos

```python
# tests/test_linking_heuristico.py
from datetime import date
from src.graph.linking import score_matching, classificar_edge, _score_data, _score_valor, _score_fornecedor

def test_score_data_exata():
    assert _score_data(date(2026, 3, 19), date(2026, 3, 19)) == 1.0

def test_score_data_3_dias():
    assert _score_data(date(2026, 3, 19), date(2026, 3, 22)) == 1.0  # <= 3 dias

def test_score_data_7_dias():
    assert _score_data(date(2026, 3, 19), date(2026, 3, 26)) == 0.5

def test_score_valor_exato():
    assert _score_valor(103.93, 103.93) == 1.0

def test_score_valor_juros_5pct():
    # boleto R$ 100 pago com juros R$ 104 (4%) deve dar 0.4 (5% tolerância)
    assert _score_valor(104.0, 100.0) == 0.4

def test_score_fornecedor_sesc_variantes():
    assert _score_fornecedor("Sesc", "SESC - Serviço SOCIAL DO Comércio ADMINI") > 0.7
    assert _score_fornecedor("SESC", "SESC") == 1.0

def test_classificar_edge_boleto():
    assert classificar_edge({"tipo_documento": "boleto"}, 0.95) == "confirma"

def test_classificar_edge_cupom():
    assert classificar_edge({"tipo_documento": "cupom_termico"}, 0.85) == "comprovante"

def test_gtc01_natacao_sesc():
    """Golden test case: boleto natação casa com transação Sesc C6."""
    doc = {"data": date(2026, 3, 17), "valor": 103.93, "fornecedor": "Sesc",
           "tipo_documento": "boleto", "id": 1}
    tx = {"data": date(2026, 3, 19), "valor": 103.93,
          "local": "SESC - Serviço SOCIAL DO Comércio ADMINI", "id": 5948}
    s = score_matching(doc, tx)
    assert s >= 0.8, f"score {s} deveria ser >= 0.8 para GTC-01"
```

```python
# tests/test_preview_documento.py
from pathlib import Path
from src.dashboard.componentes.preview_documento import _tipo_arquivo

def test_tipo_pdf():
    assert _tipo_arquivo(Path("foo.pdf")) == "pdf"

def test_tipo_imagem():
    assert _tipo_arquivo(Path("foo.jpg")) == "imagem"

def test_tipo_outro():
    assert _tipo_arquivo(Path("foo.csv")) == "outro"
```

## Evidências obrigatórias

- [ ] Testes de score: 8+ casos passando
- [ ] GTC-01 passa (`natacao_andre.pdf` + linha 5948 = score ≥ 0.8)
- [ ] Matching rodado em grafo atual: auto + propostas >= 1
- [ ] Screenshot do modal com PDF embedado (tela real)
- [ ] `mappings/categorias_tracking.yaml` existe com >=6 categorias
- [ ] Badge amarelo visível em transação Farmácia sem comprovante

## Referência cruzada

- `docs/GOLDEN_TEST_CASES.md` — GTC-01 (natação) + GTC-02 + GTC-03
- `docs/adr/ADR-20-tracking-documental-completo.md`
- `docs/CONTEXT.md` §2 (gastos recorrentes conhecidos)

---

*"Clicar em gasto e ver comprovante é o jogo inteiro." — Andre*
