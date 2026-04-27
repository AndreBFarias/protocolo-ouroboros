"""Sprint 63 -- garante que títulos de páginas do dashboard não vazem ID de sprint.

Regra: nenhum título visível começa com dígitos. Cobre dois padrões de título
usados no projeto:

- ``st.header(...)`` / ``st.title(...)`` / ``st.subheader(...)`` -- API direta
  do Streamlit.
- ``hero_titulo_html(numero, texto, descricao=None)`` -- helper custom do tema  # noqa: accent
  (``src/dashboard/tema.py``) cujo primeiro argumento é o rótulo numérico
  exibido em destaque.

Implementação: AST parsing das páginas em ``src/dashboard/paginas/*.py``,
inspecionando os call sites relevantes e extraindo literais de string.

Referências:
- Spec: ``docs/sprints/backlog/sprint_63_remover_prefixo_sprint_titulos.md``
- Helper: ``src/dashboard/tema.py::hero_titulo_html``
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

RAIZ_PAGINAS = Path(__file__).resolve().parents[1] / "src" / "dashboard" / "paginas"

TITULOS_STREAMLIT: frozenset[str] = frozenset({"header", "title", "subheader"})

PADRAO_PREFIXO_DIGITO = re.compile(r"^\s*\d")


def _listar_paginas() -> list[Path]:
    """Retorna todas as páginas Python do dashboard (exclui ``__init__``)."""
    return sorted(arquivo for arquivo in RAIZ_PAGINAS.glob("*.py") if arquivo.name != "__init__.py")


def _primeiro_arg_literal(chamada: ast.Call) -> str | None:
    """Extrai o primeiro argumento posicional como literal string, se houver."""
    if not chamada.args:
        return None
    primeiro = chamada.args[0]
    if isinstance(primeiro, ast.Constant) and isinstance(primeiro.value, str):
        return primeiro.value
    return None


def _eh_chamada_streamlit_titulo(chamada: ast.Call) -> bool:
    """Detecta ``st.header(...)``, ``st.title(...)``, ``st.subheader(...)``."""
    func = chamada.func
    if not isinstance(func, ast.Attribute):
        return False
    if func.attr not in TITULOS_STREAMLIT:
        return False
    raiz = func.value
    return isinstance(raiz, ast.Name) and raiz.id == "st"


def _eh_chamada_hero(chamada: ast.Call) -> bool:
    """Detecta ``hero_titulo_html(...)`` (importado do ``src.dashboard.tema``)."""
    func = chamada.func
    if isinstance(func, ast.Name) and func.id == "hero_titulo_html":
        return True
    if isinstance(func, ast.Attribute) and func.attr == "hero_titulo_html":
        return True
    return False


def _coletar_titulos_streamlit(arvore: ast.AST) -> list[tuple[int, str]]:
    """Lista ``(linha, texto)`` para cada ``st.header/title/subheader`` com literal."""
    resultado: list[tuple[int, str]] = []
    for node in ast.walk(arvore):
        if not isinstance(node, ast.Call):
            continue
        if not _eh_chamada_streamlit_titulo(node):
            continue
        texto = _primeiro_arg_literal(node)
        if texto is not None:
            resultado.append((node.lineno, texto))
    return resultado


def _coletar_numeros_hero(arvore: ast.AST) -> list[tuple[int, str]]:
    """Lista ``(linha, numero)`` para cada ``hero_titulo_html`` com primeiro arg literal."""
    resultado: list[tuple[int, str]] = []
    for node in ast.walk(arvore):
        if not isinstance(node, ast.Call):
            continue
        if not _eh_chamada_hero(node):
            continue
        numero = _primeiro_arg_literal(node)
        if numero is not None:
            resultado.append((node.lineno, numero))
    return resultado


@pytest.mark.parametrize("caminho", _listar_paginas(), ids=lambda p: p.name)
def test_titulos_streamlit_nao_comecam_com_digito(caminho: Path) -> None:
    """Nenhum ``st.header/title/subheader`` começa com dígito."""
    arvore = ast.parse(caminho.read_text(encoding="utf-8"))
    titulos = _coletar_titulos_streamlit(arvore)
    violacoes = [(linha, texto) for linha, texto in titulos if PADRAO_PREFIXO_DIGITO.match(texto)]
    assert not violacoes, f"{caminho.name} tem título(s) começando com dígito: {violacoes}"


@pytest.mark.parametrize("caminho", _listar_paginas(), ids=lambda p: p.name)
def test_hero_titulo_numero_nao_vaza_sprint_id(caminho: Path) -> None:
    """Primeiro arg de ``hero_titulo_html`` não pode vazar ID de sprint.

    O helper aceita string vazia (omite o badge). Sprint 92a instituiu
    numeração canônica 01-13 para as 13 abas do dashboard (ordem em
    ``src/dashboard/app.py::main``). Valores aceitos para o badge numérico:

    - string vazia ``""`` — nenhum badge exibido (ex: aba Busca);
    - dois dígitos ``"01"`` até ``"13"`` — índice de aba.

    Qualquer outro valor puramente numérico (ex: ``"51"``, ``"52"``) indica
    vazamento de ID de sprint e é rejeitado.
    """
    arvore = ast.parse(caminho.read_text(encoding="utf-8"))
    numeros = _coletar_numeros_hero(arvore)
    violacoes = []
    for linha, numero in numeros:
        texto = numero.strip()
        if texto == "":
            continue
        if not texto.isdigit():
            continue
        # Sprint 92a: 01-13 são índices canônicos de aba; o restante vaza ID.
        try:
            valor = int(texto)
        except ValueError:  # pragma: no cover -- isdigit implica conversível
            violacoes.append((linha, numero))
            continue
        if not (1 <= valor <= 13):
            violacoes.append((linha, numero))
    assert not violacoes, f"{caminho.name} passa prefixo numérico ao hero_titulo_html: {violacoes}"


def test_listagem_de_paginas_nao_vazia() -> None:
    """Sanity: varredura encontra pelo menos uma página."""
    paginas = _listar_paginas()
    assert paginas, f"Nenhuma página encontrada em {RAIZ_PAGINAS}"


# Sprint 92a.6 instituiu badge numérico ('01' a '13') em 10 páginas.
# Sprint UX-122 (2026-04-27) removeu os prefixos numéricos por serem
# ruído visual arbitrário; o helper continua obrigatório, mas com badge
# vazio. Lista mantida para garantir que todas as páginas seguem chamando
# o helper canônico.
PAGINAS_COM_HERO: frozenset[str] = frozenset(
    {
        "visao_geral.py",
        "categorias.py",
        "extrato.py",
        "contas.py",
        "pagamentos.py",
        "projecoes.py",
        "metas.py",
        "analise_avancada.py",
        "irpf.py",
        "completude.py",
    }
)


@pytest.mark.parametrize("nome_pagina", sorted(PAGINAS_COM_HERO), ids=lambda s: s)
def test_pagina_chama_hero_titulo_sem_numero(nome_pagina: str) -> None:
    """Sprint UX-122: cada página chama ``hero_titulo_html`` com badge vazio.

    Garante que todas as páginas do escopo histórico da Sprint 92a.6 seguem
    invocando o helper, porém com primeiro arg ``""`` (sem prefixo numérico).
    Substitui ``test_pagina_tem_hero_titulo_numerado`` antigo.
    """
    caminho = RAIZ_PAGINAS / nome_pagina
    arvore = ast.parse(caminho.read_text(encoding="utf-8"))
    numeros = _coletar_numeros_hero(arvore)
    assert numeros, f"{nome_pagina} não chama hero_titulo_html"
    badges_vazios = [numero for _, numero in numeros if numero == ""]
    assert badges_vazios, (
        f"{nome_pagina} não chama hero_titulo_html com badge vazio "
        f"(Sprint UX-122). Chamadas encontradas: {numeros}"
    )


# "Produção não é changelog." -- princípio de release
