"""Heurísticas puras de detecção de marcos (Sprint MOB-bridge-3).

Cada heurística é função pura ``(eventos: list[dict]) -> list[dict]``
que devolve a lista de marcos detectados a partir dos eventos do
Vault. Função pura significa: sem efeito colateral, sem I/O, sem
dependência de relógio. Determinística: mesma entrada → mesma saída.

A escrita do marco em disco fica a cargo do orquestrador
(``marcos_auto.gerar_marcos_auto``); aqui só detectamos.

Cinco heurísticas iniciais (lista expansível por PR):

    tres_treinos_em_sete_dias(eventos)
        Detecta a primeira janela rolling de 7 dias com 3+
        ``treino_sessao`` por pessoa. Marco gerado uma vez por
        pessoa por janela inicial; janelas posteriores são
        cobertas por idempotência via hash.

    retorno_apos_hiato(eventos)
        Gap de 5 ou mais dias entre dois ``treino_sessao``
        consecutivos da mesma pessoa. Marco data = data do treino
        que rompeu o hiato.

    sete_dias_humor(eventos)
        7 dias consecutivos com registro ``humor`` da mesma
        pessoa. Marco data = data do sétimo dia.

    trinta_dias_sem_trigger(eventos)
        30 dias consecutivos sem nenhum ``diario_emocional`` com
        ``modo == 'trigger'`` da mesma pessoa, partindo da
        primeira ocorrência ou do início da série de eventos.

    primeira_vitoria_da_semana(eventos)
        Primeira ocorrência por semana ISO de ``evento.modo ==
        'positivo'`` ou ``diario_emocional.modo == 'vitoria'``,
        para cada pessoa.

Cada marco devolvido é um dict com schema:

    {
        "tipo": "marco",
        "data": "<ISO 8601>",
        "autor": "<pessoa_a|pessoa_b|casal>",
        "descricao": "<texto seco>",
        "tags": [list],
        "auto": True,
        "origem": "backend",
    }

O campo ``hash`` é calculado pelo orquestrador via
``marcos_auto.dedup.hash_marco`` antes da escrita; aqui é omitido
de propósito (separação de responsabilidades).

Restrições ADR-0005: descrições secas, sem palavras motivacionais,
sem comparativos negativos, sem nomes reais (autor sempre genérico
``pessoa_a``/``pessoa_b``/``casal``).
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Iterable

# Conjunto de autores aceitos. Outros valores caem em "casal" como fallback
# defensivo (Vault malformado não deve travar o gerador).
_AUTORES_VALIDOS = {"pessoa_a", "pessoa_b", "casal"}


def _normalizar_autor(valor: Any) -> str:
    """Devolve autor canônico, com fallback ``casal`` quando ausente/invalido."""
    if isinstance(valor, str) and valor in _AUTORES_VALIDOS:
        return valor
    return "casal"


def _data_de(evento: dict[str, Any]) -> date | None:
    """Extrai a data (apenas dia) do campo ``data`` do evento.

    Aceita ``date``, ``datetime`` ou string ISO 8601 (``YYYY-MM-DD``
    ou ``YYYY-MM-DDTHH:MM:SS[+TZ]``). Retorna ``None`` se inválido.
    """
    valor = evento.get("data")
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if isinstance(valor, str):
        # PyYAML ja parseia ISO date para date; ISO datetime para datetime.
        # Se chegar string, tentamos parse manual.
        try:
            return datetime.fromisoformat(valor.replace("Z", "+00:00")).date()
        except ValueError:
            try:
                return date.fromisoformat(valor[:10])
            except ValueError:
                return None
    return None


def _filtrar_por_tipo(eventos: Iterable[dict[str, Any]], tipo: str) -> list[dict[str, Any]]:
    """Filtra eventos por ``tipo``, descartando os sem data parseável."""
    selecionados: list[dict[str, Any]] = []
    for ev in eventos:
        if ev.get("tipo") != tipo:
            continue
        if _data_de(ev) is None:
            continue
        selecionados.append(ev)
    return selecionados


def _agrupar_por_autor(
    eventos: Iterable[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Agrupa eventos por autor canônico."""
    grupos: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for ev in eventos:
        grupos[_normalizar_autor(ev.get("autor"))].append(ev)
    return grupos


def _marco(
    data_iso: str,
    autor: str,
    descricao: str,
    tags: list[str],
) -> dict[str, Any]:
    """Constrói dict de marco no schema canônico."""
    return {
        "tipo": "marco",
        "data": data_iso,
        "autor": autor,
        "descricao": descricao,
        "tags": tags,
        "auto": True,
        "origem": "backend",
    }


def tres_treinos_em_sete_dias(
    eventos: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Detecta janelas de 7 dias com 3+ treinos por autor.

    Algoritmo: para cada autor, ordena os ``treino_sessao`` por data
    crescente. Para cada treino, conta quantos treinos do mesmo autor
    cabem em ``[treino.data - 6 dias, treino.data]``. Se o total
    atinge 3 pela primeira vez naquela janela, emite marco com
    ``data = treino.data``. Janelas posteriores que mantenham 3+
    treinos não emitem marco novo (a primeira ocorrência é o fato
    digno de registro; idempotência via hash cuida de re-execução).
    """
    treinos = _filtrar_por_tipo(eventos, "treino_sessao")
    grupos = _agrupar_por_autor(treinos)
    marcos: list[dict[str, Any]] = []
    for autor, lista in grupos.items():
        lista_ordenada = sorted(lista, key=lambda ev: _data_de(ev))
        ja_emitiu = False
        for treino in lista_ordenada:
            d_fim = _data_de(treino)
            if d_fim is None:
                continue
            d_inicio = d_fim - timedelta(days=6)
            count = sum(
                1
                for outro in lista_ordenada
                if (
                    (do := _data_de(outro)) is not None
                    and d_inicio <= do <= d_fim
                )
            )
            if count >= 3 and not ja_emitiu:
                marcos.append(
                    _marco(
                        data_iso=d_fim.isoformat(),
                        autor=autor,
                        descricao="Tres treinos nesta semana.",
                        tags=["auto", "treino"],
                    )
                )
                ja_emitiu = True
                break
    return marcos


def retorno_apos_hiato(
    eventos: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Detecta gaps de 5+ dias entre treinos consecutivos do mesmo autor.

    Para cada par de treinos consecutivos (mesma pessoa, ordenados),
    se ``data_atual - data_anterior >= 5 dias``, emite marco com
    data do treino atual e descrição contendo o número de dias
    parados.
    """
    treinos = _filtrar_por_tipo(eventos, "treino_sessao")
    grupos = _agrupar_por_autor(treinos)
    marcos: list[dict[str, Any]] = []
    for autor, lista in grupos.items():
        lista_ordenada = sorted(lista, key=lambda ev: _data_de(ev))
        anterior: date | None = None
        for treino in lista_ordenada:
            atual = _data_de(treino)
            if atual is None:
                continue
            if anterior is not None:
                gap = (atual - anterior).days
                if gap >= 5:
                    marcos.append(
                        _marco(
                            data_iso=atual.isoformat(),
                            autor=autor,
                            descricao=f"Voltou apos {gap} dias parados.",
                            tags=["auto", "treino"],
                        )
                    )
            anterior = atual
    return marcos


def sete_dias_humor(
    eventos: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Detecta 7 dias consecutivos com registro ``humor`` por autor.

    Algoritmo: para cada autor, coleta as datas únicas com
    ``tipo == 'humor'``, ordena, e procura sequências de 7 dias
    consecutivos. Emite marco no sétimo dia da primeira sequência
    encontrada por autor. Sequências subsequentes (ex.: 14, 21
    dias) não emitem novos marcos -- o fato "primeira semana
    completa" é o digno de registro; sequências mais longas podem
    ser cobertas por heurísticas adicionais em sprints futuras.
    """
    humores = _filtrar_por_tipo(eventos, "humor")
    grupos = _agrupar_por_autor(humores)
    marcos: list[dict[str, Any]] = []
    for autor, lista in grupos.items():
        datas_unicas = sorted({_data_de(ev) for ev in lista if _data_de(ev) is not None})
        if len(datas_unicas) < 7:
            continue
        # Procura primeira janela de 7 dias consecutivos.
        for i in range(len(datas_unicas) - 6):
            janela = datas_unicas[i : i + 7]
            consecutivos = all(
                (janela[j + 1] - janela[j]).days == 1 for j in range(6)
            )
            if consecutivos:
                marcos.append(
                    _marco(
                        data_iso=janela[-1].isoformat(),
                        autor=autor,
                        descricao="Sete dias acompanhando.",
                        tags=["auto", "humor"],
                    )
                )
                break
    return marcos


def trinta_dias_sem_trigger(
    eventos: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Detecta 30 dias consecutivos sem ``diario_emocional.modo == 'trigger'``.

    Algoritmo: para cada autor, coleta as datas dos eventos
    ``diario_emocional`` (qualquer modo). Se a primeira data
    diario menos a data do primeiro trigger é >= 30 dias, ou se
    há um gap >= 30 dias entre dois triggers consecutivos, emite
    marco. Para suportar o caso "começou a registrar e nunca teve
    trigger", também consideramos: data_atual - primeira_data_diario
    >= 30 sem nenhum trigger no meio.
    """
    diarios = _filtrar_por_tipo(eventos, "diario_emocional")
    grupos = _agrupar_por_autor(diarios)
    marcos: list[dict[str, Any]] = []
    for autor, lista in grupos.items():
        ordenados = sorted(lista, key=lambda ev: _data_de(ev))
        if not ordenados:
            continue
        primeira = _data_de(ordenados[0])
        triggers = [
            _data_de(ev) for ev in ordenados if ev.get("modo") == "trigger"
        ]
        triggers = [t for t in triggers if t is not None]
        ja_emitiu = False
        if not triggers:
            ultimo_diario = _data_de(ordenados[-1])
            if (
                primeira is not None
                and ultimo_diario is not None
                and (ultimo_diario - primeira).days >= 30
            ):
                marcos.append(
                    _marco(
                        data_iso=ultimo_diario.isoformat(),
                        autor=autor,
                        descricao="Trinta dias sem registrar trigger.",
                        tags=["auto", "emocional"],
                    )
                )
                ja_emitiu = True
        else:
            # Antes do primeiro trigger.
            if (
                primeira is not None
                and (triggers[0] - primeira).days >= 30
                and not ja_emitiu
            ):
                marcos.append(
                    _marco(
                        data_iso=(triggers[0] - timedelta(days=1)).isoformat(),
                        autor=autor,
                        descricao="Trinta dias sem registrar trigger.",
                        tags=["auto", "emocional"],
                    )
                )
                ja_emitiu = True
            # Entre triggers consecutivos.
            for i in range(len(triggers) - 1):
                gap = (triggers[i + 1] - triggers[i]).days
                if gap >= 30 and not ja_emitiu:
                    marcos.append(
                        _marco(
                            data_iso=(triggers[i + 1] - timedelta(days=1)).isoformat(),
                            autor=autor,
                            descricao="Trinta dias sem registrar trigger.",
                            tags=["auto", "emocional"],
                        )
                    )
                    ja_emitiu = True
                    break
    return marcos


def primeira_vitoria_da_semana(
    eventos: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Detecta a primeira "vitoria" por semana ISO por autor.

    Considera "vitoria" qualquer ``evento`` com ``modo == 'positivo'``
    ou ``diario_emocional`` com ``modo == 'vitoria'``. Para cada
    semana ISO (ano + número da semana), emite marco para a primeira
    ocorrência por autor. Janelas subsequentes na mesma semana
    são suprimidas (uma vitoria por semana basta para o registro).
    """
    candidatos: list[dict[str, Any]] = []
    for ev in eventos:
        tipo = ev.get("tipo")
        modo = ev.get("modo")
        if tipo == "evento" and modo == "positivo":
            candidatos.append(ev)
        elif tipo == "diario_emocional" and modo == "vitoria":
            candidatos.append(ev)
    grupos = _agrupar_por_autor(candidatos)
    marcos: list[dict[str, Any]] = []
    for autor, lista in grupos.items():
        ordenados = sorted(lista, key=lambda ev: _data_de(ev))
        semanas_vistas: set[tuple[int, int]] = set()
        for ev in ordenados:
            d = _data_de(ev)
            if d is None:
                continue
            chave_semana = d.isocalendar()[:2]
            if chave_semana in semanas_vistas:
                continue
            semanas_vistas.add(chave_semana)
            marcos.append(
                _marco(
                    data_iso=d.isoformat(),
                    autor=autor,
                    descricao="Primeira vitoria desta semana.",
                    tags=["auto", "emocional"],
                )
            )
    return marcos


HEURISTICAS_DISPONIVEIS = (
    tres_treinos_em_sete_dias,
    retorno_apos_hiato,
    sete_dias_humor,
    trinta_dias_sem_trigger,
    primeira_vitoria_da_semana,
)


# "Quem observa o ritmo das coisas vê o que escapa ao olhar apressado." -- Heráclito
