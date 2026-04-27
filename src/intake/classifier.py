"""Classificador do intake universal: avalia `mappings/tipos_documento.yaml` e
decide tipo + pasta + nome canônico para um arquivo de entrada (Sprint 41).

Contrato:

    decisao = classificar(caminho_arquivo, mime, preview_texto, pessoa="andre")

    decisao.tipo                 -> str (id do tipo) ou None
    decisao.prioridade           -> "especifico" | "normal" | "fallback" | None
    decisao.match_mode           -> "all" | "any" | None
    decisao.extrator_modulo      -> str (caminho de import) ou None
    decisao.origem_sprint        -> int/str ou None
    decisao.pasta_destino        -> Path absoluto computado
    decisao.nome_canonico        -> str (<TIPO>[_<YYYY-MM-DD>]_<sha8>.<ext>)
    decisao.data_detectada_iso   -> str "YYYY-MM-DD" ou None
    decisao.regras_avaliadas     -> int (auditoria/debug)

Política:

- Avalia tipos em ordem: prioridade `especifico` -> `normal` -> `fallback`.
- Dentro do mesmo nível, primeiro que casa (segundo `match_mode`) ganha;
  empate resolve por ordem de declaração no YAML.
- Se nada casa: tipo=None, pasta_destino aponta para `data/raw/_classificar/`,
  nome_canonico usa `_CLASSIFICAR_<sha8>.<ext>`. NÃO levanta exceção --
  "não classifiquei" é estado legítimo do sistema (decisão arquitetural
  alinhada com Sprint 41 Fase 5: fallback supervisor).
- Carrega o YAML uma vez no import. Para testes ou recarga após edição,
  usar `recarregar_tipos()`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml

from src.intake import sha8_arquivo
from src.intake.glyph_tolerant import casa_padroes, extrair_data_br
from src.utils.logger import configurar_logger

logger = configurar_logger("intake.classifier")

# Caminhos canônicos (relativos à raiz do repo)
_RAIZ_REPO: Path = Path(__file__).resolve().parents[2]
_PATH_YAML: Path = _RAIZ_REPO / "mappings" / "tipos_documento.yaml"
_PATH_DATA_RAW: Path = _RAIZ_REPO / "data" / "raw"

# Ordem de prioridade -- níveis baixos avaliados antes
_ORDEM_PRIORIDADE: dict[str, int] = {
    "especifico": 0,
    "normal": 1,
    "fallback": 2,
}


# ============================================================================
# Estruturas
# ============================================================================


@dataclass(frozen=True)
class Decisao:
    """Resultado da classificação. tipo=None significa 'não classificado'.

    `match_submodo` é populado quando uma subregra composta (Sprint 96)
    decide o match -- ex.: `cupom_fiscal_foto` casado pela subregra
    `ocr_curto`. Para regras tradicionais (`regex_conteudo` plano),
    permanece None e `match_mode` carrega `all`/`any`.
    """

    tipo: str | None
    prioridade: Literal["especifico", "normal", "fallback"] | None
    match_mode: Literal["all", "any"] | None
    extrator_modulo: str | None
    origem_sprint: Any | None
    pasta_destino: Path
    nome_canonico: str
    data_detectada_iso: str | None
    regras_avaliadas: int = 0
    motivo_fallback: str | None = field(default=None)
    match_submodo: str | None = field(default=None)


# ============================================================================
# Cache de tipos (carregado uma vez no import)
# ============================================================================

_TIPOS_CACHE: list[dict[str, Any]] | None = None


def recarregar_tipos(path: Path | None = None) -> list[dict[str, Any]]:
    """Recarrega o YAML de tipos (use em testes ou após editar o YAML).

    Falha NO IMPORT (não em produção) se o YAML estiver mal formado --
    melhor pegar `KeyError` ou regra órfã na inicialização do que no
    meio de um batch de 50 arquivos.
    """
    global _TIPOS_CACHE
    arquivo = path or _PATH_YAML
    with arquivo.open(encoding="utf-8") as f:
        dados = yaml.safe_load(f)
    if not isinstance(dados, dict) or "tipos" not in dados:
        raise ValueError(f"YAML em {arquivo} sem chave raiz 'tipos' -- formato inválido")
    tipos = dados["tipos"]
    if not isinstance(tipos, list) or not tipos:
        raise ValueError(f"YAML em {arquivo} com lista 'tipos' vazia ou inválida")
    _validar_tipos(tipos, origem=arquivo)
    _TIPOS_CACHE = sorted(tipos, key=_chave_ordenacao)
    logger.info("tipos_documento.yaml carregado: %d entradas", len(_TIPOS_CACHE))
    return _TIPOS_CACHE


_CAMPOS_OBRIGATORIOS: tuple[str, ...] = (
    "id",
    "prioridade",
    "match_mode",
    "mimes",
    "regex_conteudo",
    "pasta_destino_template",
    "renomear_template",
)
_PRIORIDADES_VALIDAS: frozenset[str] = frozenset(_ORDEM_PRIORIDADE)
_MATCH_MODES_VALIDOS: frozenset[str] = frozenset({"all", "any"})
_TEMPLATES_OBRIGATORIOS: tuple[str, ...] = ("com_data", "sem_data")


def _validar_tipos(tipos: list[Any], origem: Path) -> None:
    """Valida cada entrada do YAML; levanta ValueError com lista de erros.

    Confere por entrada:
      - campos obrigatórios presentes
      - prioridade in {especifico, normal, fallback}
      - match_mode in {all, any}
      - mimes é lista não vazia
      - regex_conteudo é lista não vazia
      - renomear_template tem chaves com_data e sem_data
      - id único entre todas as entradas
    """
    erros: list[str] = []
    ids_vistos: dict[str, int] = {}
    for indice, tipo in enumerate(tipos):
        rotulo = f"entrada #{indice}"
        if not isinstance(tipo, dict):
            erros.append(f"{rotulo}: esperado dict, veio {type(tipo).__name__}")
            continue
        rotulo = f"tipo {tipo.get('id', f'#{indice}')!r}"
        for campo in _CAMPOS_OBRIGATORIOS:
            if campo not in tipo:
                erros.append(f"{rotulo}: faltando campo obrigatório {campo!r}")
        if tipo.get("prioridade") not in _PRIORIDADES_VALIDAS:
            erros.append(
                f"{rotulo}: prioridade {tipo.get('prioridade')!r} inválida "
                f"(esperado {sorted(_PRIORIDADES_VALIDAS)})"
            )
        if tipo.get("match_mode") not in _MATCH_MODES_VALIDOS:
            erros.append(
                f"{rotulo}: match_mode {tipo.get('match_mode')!r} inválido "
                f"(esperado {sorted(_MATCH_MODES_VALIDOS)})"
            )
        for campo in ("mimes", "regex_conteudo"):
            valor = tipo.get(campo)
            if not isinstance(valor, list) or not valor:
                erros.append(f"{rotulo}: {campo} deve ser lista não vazia")
        # Sprint 96: subregras compostas opcionais. Quando presentes, cada
        # subregra precisa ter rótulo `tipo` + `requer_todos` lista não vazia
        # + `requer_qualquer` lista não vazia (ou ausente). `ocr_minimo` e
        # `ocr_maximo` são opcionais e devem ser inteiros não negativos.
        regras_compostas = tipo.get("regras")
        if regras_compostas is not None:
            if not isinstance(regras_compostas, list) or not regras_compostas:
                erros.append(
                    f"{rotulo}: regras (opcional) deve ser lista não vazia quando declarada"
                )
            else:
                for sub_idx, sub in enumerate(regras_compostas):
                    sub_rotulo = f"{rotulo} regras[{sub_idx}]"
                    if not isinstance(sub, dict):
                        erros.append(f"{sub_rotulo}: esperado dict, veio {type(sub).__name__}")
                        continue
                    if not isinstance(sub.get("tipo"), str) or not sub["tipo"]:
                        erros.append(f"{sub_rotulo}: campo 'tipo' (rótulo) obrigatório como string")
                    requer_todos = sub.get("requer_todos")
                    if not isinstance(requer_todos, list) or not requer_todos:
                        erros.append(f"{sub_rotulo}: requer_todos deve ser lista não vazia")
                    requer_qualquer = sub.get("requer_qualquer")
                    if requer_qualquer is not None and (
                        not isinstance(requer_qualquer, list) or not requer_qualquer
                    ):
                        erros.append(
                            f"{sub_rotulo}: requer_qualquer (opcional) deve ser lista não vazia"
                        )
                    for chave_int in ("ocr_minimo", "ocr_maximo"):
                        valor_int = sub.get(chave_int)
                        if valor_int is not None and (
                            not isinstance(valor_int, int) or valor_int < 0
                        ):
                            erros.append(
                                f"{sub_rotulo}: {chave_int} deve ser inteiro >= 0 quando declarado"
                            )
        renomear = tipo.get("renomear_template")
        if not isinstance(renomear, dict) or not all(
            k in renomear for k in _TEMPLATES_OBRIGATORIOS
        ):
            erros.append(f"{rotulo}: renomear_template deve ter chaves {_TEMPLATES_OBRIGATORIOS}")
        identificador = tipo.get("id")
        if identificador in ids_vistos:
            erros.append(
                f"{rotulo}: id duplicado (já visto na entrada #{ids_vistos[identificador]})"
            )
        elif isinstance(identificador, str):
            ids_vistos[identificador] = indice
    if erros:
        msg = f"YAML em {origem} com {len(erros)} erro(s) de schema:\n  - " + "\n  - ".join(erros)
        raise ValueError(msg)


def _chave_ordenacao(tipo: dict[str, Any]) -> tuple[int, int]:
    """Ordena por (nível de prioridade, índice de declaração).

    Como o `sorted` é estável e não temos índice original aqui, devolvemos
    índice fixo 0 para empate -- a estabilidade do `sorted` preserva a
    ordem original do YAML dentro do mesmo nível.
    """
    nivel = _ORDEM_PRIORIDADE.get(tipo.get("prioridade", "normal"), 1)
    return (nivel, 0)


def _carregar_se_preciso() -> list[dict[str, Any]]:
    if _TIPOS_CACHE is None:
        recarregar_tipos()
    assert _TIPOS_CACHE is not None
    return _TIPOS_CACHE


# ============================================================================
# API pública
# ============================================================================


def classificar(
    caminho_arquivo: Path,
    mime: str,
    preview_texto: str,
    pessoa: str = "_indefinida",
) -> Decisao:
    """Devolve `Decisao` -- não levanta para "não classificado".

    Parâmetros:
        caminho_arquivo: Path do arquivo (usado para extensão e SHA8 de bytes).
        mime: MIME detectado por `src.utils.file_detector` ou similar.
        preview_texto: texto extraído do arquivo (PDF nativo) ou OCR rápido.
        pessoa: "andre" | "vitoria" | "casal" | "_indefinida" -- expandido em
                `pasta_destino_template`.

    Levanta:
        FileNotFoundError se `caminho_arquivo` não existir (precisamos do SHA8).
    """
    if not caminho_arquivo.exists():
        raise FileNotFoundError(f"arquivo não existe: {caminho_arquivo}")

    sha8 = sha8_arquivo(caminho_arquivo)
    extensao = _extensao(caminho_arquivo)
    data_iso = extrair_data_br(preview_texto)
    tipos = _carregar_se_preciso()

    avaliadas = 0
    for tipo in tipos:
        avaliadas += 1
        if not _mime_compativel(mime, tipo.get("mimes", [])):
            continue
        casou_regex_plano = casa_padroes(
            tipo["regex_conteudo"], preview_texto, modo=tipo.get("match_mode", "any")
        )
        submodo: str | None = None
        if not casou_regex_plano:
            submodo = _avaliar_subregras(tipo.get("regras"), preview_texto)
            if submodo is None:
                continue
        return _montar_decisao(
            tipo=tipo,
            sha8=sha8,
            extensao=extensao,
            data_iso=data_iso,
            pessoa=pessoa,
            avaliadas=avaliadas,
            match_submodo=submodo,
        )

    return _decisao_nao_classificado(sha8=sha8, extensao=extensao, avaliadas=avaliadas, mime=mime)


# ============================================================================
# Internals
# ============================================================================


def _mime_compativel(mime: str, mimes_aceitos: list[str]) -> bool:
    if not mimes_aceitos:
        return True  # tipo sem mimes declarados aceita qualquer MIME
    return mime in mimes_aceitos


def _montar_decisao(
    tipo: dict[str, Any],
    sha8: str,
    extensao: str,
    data_iso: str | None,
    pessoa: str,
    avaliadas: int,
    match_submodo: str | None = None,
) -> Decisao:
    pasta = _resolver_pasta(tipo["pasta_destino_template"], pessoa)
    nome = _resolver_nome(
        templates=tipo["renomear_template"],
        sha8=sha8,
        extensao=extensao,
        data_iso=data_iso,
    )
    return Decisao(
        tipo=tipo["id"],
        prioridade=tipo["prioridade"],
        match_mode=tipo.get("match_mode", "any"),
        extrator_modulo=tipo.get("extrator_modulo"),
        origem_sprint=tipo.get("origem_sprint"),
        pasta_destino=pasta,
        nome_canonico=nome,
        data_detectada_iso=data_iso,
        regras_avaliadas=avaliadas,
        match_submodo=match_submodo,
    )


def _avaliar_subregras(regras: list[dict[str, Any]] | None, texto: str) -> str | None:
    """Avalia subregras compostas (Sprint 96).

    Cada subregra casa quando TODAS as condições são verdadeiras:
      - len(texto) está em [ocr_minimo, ocr_maximo] (se declarados);
      - todos os padrões de `requer_todos` casam no texto;
      - pelo menos um padrão de `requer_qualquer` casa (se declarado).

    Devolve o rótulo `tipo` da primeira subregra que casa, ou None
    se nenhuma casa.
    """
    if not regras:
        return None
    tamanho = len(texto)
    for sub in regras:
        ocr_min = sub.get("ocr_minimo")
        if ocr_min is not None and tamanho < ocr_min:
            continue
        ocr_max = sub.get("ocr_maximo")
        if ocr_max is not None and tamanho > ocr_max:
            continue
        if not casa_padroes(sub["requer_todos"], texto, modo="all"):
            continue
        requer_qualquer = sub.get("requer_qualquer")
        if requer_qualquer and not casa_padroes(requer_qualquer, texto, modo="any"):
            continue
        rotulo = sub.get("tipo")
        if isinstance(rotulo, str):
            return rotulo
    return None


def _decisao_nao_classificado(sha8: str, extensao: str, avaliadas: int, mime: str) -> Decisao:
    pasta = _PATH_DATA_RAW / "_classificar"
    nome = f"_CLASSIFICAR_{sha8}.{extensao}"
    return Decisao(
        tipo=None,
        prioridade=None,
        match_mode=None,
        extrator_modulo=None,
        origem_sprint=None,
        pasta_destino=pasta,
        nome_canonico=nome,
        data_detectada_iso=None,
        regras_avaliadas=avaliadas,
        motivo_fallback=f"nenhum tipo casou (mime={mime!r})",
    )


def _resolver_pasta(template: str, pessoa: str) -> Path:
    sub = template.format(pessoa=pessoa)
    if sub.startswith("data/"):
        sub = sub[len("data/") :]
    return (_RAIZ_REPO / "data" / sub).resolve()


def _resolver_nome(
    templates: dict[str, str], sha8: str, extensao: str, data_iso: str | None
) -> str:
    if data_iso:
        template = templates["com_data"]
        # Convertemos 'YYYY-MM-DD' em datetime só para alimentar o {data:%Y-%m-%d}
        # do template. Manter a conversão local evita propagar datetime à API.
        from datetime import date

        ano, mes, dia = data_iso.split("-")
        valor = date(int(ano), int(mes), int(dia))
        return template.format(data=valor, sha8=sha8, ext=extensao)
    return templates["sem_data"].format(sha8=sha8, ext=extensao)


def _extensao(caminho: Path) -> str:
    """Devolve extensão sem ponto, em minúsculas. PDF -> 'pdf'."""
    suf = caminho.suffix.lstrip(".").lower()
    return suf or "bin"


# "Quem não conhece o porto para o qual navega não terá vento favorável." -- Sêneca
