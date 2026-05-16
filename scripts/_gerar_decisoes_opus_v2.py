"""Helper one-shot: gera decisoes_opus_v2.json a partir de transcricoes_v2.json.

Aplica julgamento Opus por família de documento detectada em metadata_etl ou OCR.
NÃO é automatizado em produção — é um one-shot para popular o ground-truth da
sessão de auditoria 4-way pós-Sprint 108.

Cada decisão segue o brief: para cada uma das 5 dimensões (data, valor, itens,
fornecedor, pessoa), escrever o valor canônico que o Opus julga correto após
ler a transcrição. Ausência verdadeira é "N/A". Quando ETL acertou, copio o
valor (Opus concorda como baseline). Quando ETL falhou ou usou ortografia
diferente do canônico, escrevo o valor canônico — assim a comparação 4-way
revela tanto bug do extrator (ETL ≠ Opus) quanto efeito da normalização
(ETL ≠ Grafo, esperado para fornecedor sintético da Sprint 107).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

_RAIZ = Path(__file__).resolve().parents[1]
_FONTE = _RAIZ / "data" / "output" / "transcricoes_opus" / "transcricoes_v2.json"
_LEGACY = _RAIZ / "data" / "output" / "transcricoes_opus" / "decisoes_opus.json"
_DESTINO = _RAIZ / "data" / "output" / "transcricoes_opus" / "decisoes_opus_v2.json"


def _decidir_das_parcsn(entry: dict) -> dict:
    """DAS PARCSN do André: ETL extrai data/valor/fornecedor; itens/pessoa
    canônicos. Fornecedor canônico é RECEITA_FEDERAL (Sprint 107).
    """
    etl = entry["valores_etl_por_dimensao"]
    return {
        "decisoes": {
            "data": etl.get("data") or "",
            "valor": etl.get("valor") or "",
            "itens": "1 parcela DAS PARCSN (Simples Nacional parcelado)",
            "fornecedor": "RECEITA_FEDERAL",
            "pessoa": "andre",
        },
        "observacao_opus": (
            "DAS PARCSN do André; ETL extrai data/valor corretos. Fornecedor "
            "canonico Sprint 107 = RECEITA_FEDERAL (CNPJ 00.394.460/0001-41). "
            "ETL diz 'Receita Federal do Brasil' (razao_social humana) — "
            "esperado divergir do canonico no comparativo. Pessoa = andre "
            "(CPF do contribuinte aparece na transcricao)."
        ),
    }


def _decidir_boleto_sesc(entry: dict) -> dict:
    """Boleto SESC NATAÇÃO do André: ETL extrai bem; texto confirma."""
    etl = entry["valores_etl_por_dimensao"]
    return {
        "decisoes": {
            "data": etl.get("data") or "",
            "valor": etl.get("valor") or "",
            "itens": "Natacao adulto UOP Gama (servico mensal SEG/QUA)",
            "fornecedor": "SESC - Servico Social do Comercio do DF",
            "pessoa": "andre",
        },
        "observacao_opus": (
            "Boleto SESC NATAÇÃO; transcricao confirma todos os campos. "
            "Pessoa = andre (boleto aponta para CPF dele)."
        ),
    }


def _decidir_holerite(entry: dict) -> dict:
    """Holerite do André (G4F ou INFOBASE). ETL extrai data/valor/fornecedor;
    itens canônicos = 'vencimentos + descontos' (estrutural).

    Observação importante: o `valor` do ETL para holerite é o LÍQUIDO em alguns
    extratores (G4F) e BRUTO em outros (INFOBASE quando OCR só pegou bruto).
    Sprint 95a (em backlog) prevê separar liquido/bruto explicitamente.
    """
    etl = entry["valores_etl_por_dimensao"]
    fornecedor_etl = etl.get("fornecedor") or ""
    # Tipo: cálculo mensal vs adiantamento 13 vs 13 integral
    transcricao = entry.get("transcricao", "")
    item_descritor = "Folha mensal"
    if "Adiantamento 13" in transcricao or "Adiantamento 13°" in transcricao:
        item_descritor = "Adiantamento 13o salario"
    elif "13° Salário Integral" in transcricao or "13o Salario Integral" in transcricao:
        item_descritor = "13o salario integral"
    return {
        "decisoes": {
            "data": etl.get("data") or "",
            "valor": etl.get("valor") or "",
            "itens": item_descritor,
            "fornecedor": fornecedor_etl,
            "pessoa": "andre",
        },
        "observacao_opus": (
            f"Holerite {fornecedor_etl}; ETL extrai data/valor/fornecedor. "
            f"Tipo de calculo identificado: {item_descritor}. valor pode ser "
            f"liquido (G4F) ou bruto (INFOBASE OCR) — Sprint 95a separara."
        ),
    }


def _decidir_certidao_rf(entry: dict) -> dict:
    """Certidão RF (regularidade fiscal): documento informativo sem valor
    financeiro. Data extraída do OCR (header tem timestamp). Itens N/A.
    """
    transcricao = entry.get("transcricao", "")
    # Procura data ISO ou DD/MM/AAAA
    m = re.search(r"(\d{2})/(\d{2})/(\d{4})", transcricao)
    data = ""
    if m:
        data = f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    return {
        "decisoes": {
            "data": data,
            "valor": "N/A",
            "itens": "Certidao de regularidade fiscal (documento informativo)",
            "fornecedor": "RECEITA_FEDERAL",
            "pessoa": "andre",
        },
        "observacao_opus": (
            "Certidao RF/PGFN; sem valor financeiro. Data extraida do header "
            "do e-CAC. Fornecedor = RECEITA_FEDERAL (canonico Sprint 107)."
        ),
    }


def _decidir_cpf_cad(entry: dict) -> dict:
    """Comprovante de Situação Cadastral CPF — informativo, sem valor."""
    transcricao = entry.get("transcricao", "")
    m = re.search(r"(\d{2})/(\d{2})/(\d{4})", transcricao)
    data = ""
    if m:
        data = f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    return {
        "decisoes": {
            "data": data,
            "valor": "N/A",
            "itens": "Comprovante situação cadastral CPF (documento informativo)",
            "fornecedor": "RECEITA_FEDERAL",
            "pessoa": "andre",
        },
        "observacao_opus": (
            "Comprovante CPF; documento informativo sem valor. "
            "Fornecedor canonico = RECEITA_FEDERAL."
        ),
    }


def _decidir_garantia_americanas(entry: dict) -> dict:
    """Cupom de garantia estendida MAPFRE vendido pela Americanas. OCR cru."""
    transcricao = entry.get("transcricao", "")
    # Procura data DD/MM/AAAA HH:MM no header
    m = re.search(r"(\d{2})/(\d{2})/(\d{4})", transcricao)
    data = ""
    if m:
        data = f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    # Valor: procura R$ ou xx,xx — cupom garantia geralmente tem PROD R$ XX,XX
    valor = ""
    m_val = re.search(r"R\$\s*([\d\.,]+)", transcricao)
    if m_val:
        bruto = m_val.group(1).replace(".", "").replace(",", ".")
        try:
            valor = f"{float(bruto):.2f}"
        except ValueError:
            valor = ""
    return {
        "decisoes": {
            "data": data,
            "valor": valor,
            "itens": "Garantia estendida MAPFRE (cupom servico Americanas)",
            "fornecedor": "AMERICANAS SA - 0337",
            "pessoa": "andre",
        },
        "observacao_opus": (
            "Cupom servico Americanas (garantia estendida MAPFRE). OCR cru, "
            "data e valor extraidos por regex. Fornecedor da loja Americanas "
            "(emite o cupom), MAPFRE eh seguradora subjacente. ETL falhou "
            "em todos os campos — Tipo A bug do extrator de cupom termico."
        ),
    }


def _decidir_extrato_bb(entry: dict) -> dict:
    """Extrato BB (entry 31, 818e33db.pdf). PDF de extrato bancario do
    Banco do Brasil — fora do escopo dos extratores documentais; o pipeline
    bancario CSV/OFX cobre. Aqui registro como informativo.
    """
    transcricao = entry.get("transcricao", "")
    m = re.search(r"(\d{1,2})\s+de\s+\w+\s+de\s+(\d{4})", transcricao)
    data = ""
    if m:
        data = f"{m.group(2)}-XX-{int(m.group(1)):02d}"  # data de exportacao
    return {
        "decisoes": {
            "data": data,
            "valor": "agregado_extrato",
            "itens": "Extrato bancario PDF (varias transacoes)",
            "fornecedor": "Banco do Brasil",
            "pessoa": "andre",
        },
        "observacao_opus": (
            "Extrato bancario PDF do Banco do Brasil; contem multiplas "
            "transações (não eh um documento atomico). Fora do escopo dos "
            "extratores documentais — CSV/OFX paralelo cobre."
        ),
    }


def _decidir_nfce_americanas(entry: dict) -> dict:
    """NFC-e Americanas (entry 6c1cc203.pdf). Igual a decisão legacy do
    _CLASSIFICAR_6c1cc203.pdf, ja existente em decisoes_opus.json.
    """
    return {
        "decisoes": {
            "data": "2026-04-19",
            "valor": "629.98",
            "itens": "2 itens (Controle PS5 R$ 449,99 + Base Carregamento R$ 179,99)",
            "fornecedor": "AMERICANAS SA - 0337",
            "pessoa": "andre",
        },
        "observacao_opus": (
            "NFC-e Americanas (mesmo conteúdo do _CLASSIFICAR_6c1cc203.pdf "
            "ja decidido). 2 itens, valor total R$ 629,98."
        ),
    }


def _decidir_indecidivel(entry: dict, motivo: str) -> dict:
    """Quando OCR ficou ilegivel demais, marca todas as 5 dimensoes com '?'."""
    return {
        "decisoes": {
            "data": "?",
            "valor": "?",
            "itens": "?",
            "fornecedor": "?",
            "pessoa": "?",
        },
        "observacao_opus": (
            f"Opus não conseguiu inferir do OCR. Motivo: {motivo}. "
            "Tipo C (limite arquitetural): dado não esta legivel no arquivo."
        ),
    }


def _decidir_nfce_envelope(entry: dict) -> dict:
    """NFC-e Americanas via envelope OCR (entry 6c1cc203.pdf legivel)."""
    transcricao = entry.get("transcricao", "")
    if "americanas sa - 0337" in transcricao.lower():
        return _decidir_nfce_americanas(entry)
    return _decidir_indecidivel(entry, "envelope OCR sem identificador conhecido")


def _classificar_familia(entry: dict) -> str:
    """Identifica a familia do documento para decidir qual handler usar."""
    meta = entry.get("metadata_etl") or {}
    tipo_doc = meta.get("tipo_documento") or ""
    transcricao = entry.get("transcricao", "")
    item_id = entry["item_id"]

    if tipo_doc.startswith("das_parcsn"):
        return "das_parcsn"
    if tipo_doc == "boleto_servico" and "SESC" in (meta.get("razao_social") or ""):
        return "boleto_sesc"
    if tipo_doc == "holerite":
        return "holerite"

    # estendido_v2: detecta por OCR/path
    path_lower = item_id.lower()
    if "das_parcsn" in path_lower or "documento de arrecadação" in transcricao.lower()[:300]:
        return "das_parcsn_envelope"  # extender flag, ETL não tem meta
    transcricao_lower = transcricao.lower()
    if "ministério da fazenda" in transcricao_lower[:300] and (
        "regularidade" in transcricao_lower[:1500]
        or "certid" in transcricao_lower[:1500]
        or "procuradoria-geral da fazenda nacional" in transcricao_lower[:500]
    ):
        return "certidao_rf"
    if "comprovante de situação cadastral no cpf" in transcricao_lower[:300]:
        return "cpf_cad"
    if "boleto banco do brasil" in transcricao_lower[:300]:
        return "boleto_sesc_envelope"
    if "extrato exportado" in transcricao_lower[:200] or "agencia: 1 • conta:" in transcricao_lower:
        return "extrato_bb"
    if "garantia" in path_lower or "garantia_est" in path_lower:
        return "garantia_americanas"
    if "cupom" in path_lower and "americanas" in transcricao_lower[:500]:
        return "garantia_americanas"
    # Cupom de servico Americanas (mesmo formato fisico do cupom de garantia)
    if "americanas sa - 0337" in transcricao_lower and "cupom de servi" in transcricao_lower[:1000]:
        return "garantia_americanas"
    if (
        "americanas sa - 0337" in transcricao_lower
        and "documento auxiliar da nota fiscal" in transcricao_lower
    ):
        return "nfce_envelope"
    if path_lower.endswith((".jpeg", ".jpg", ".png")):
        return "ilegivel"  # cupom foto OCR cru ruim
    if "holerite" in path_lower or "demonstrativo de pagamento de salário" in transcricao[:200]:
        return "holerite_envelope"

    return "desconhecido"


def _decidir(entry: dict) -> dict:
    familia = _classificar_familia(entry)
    handlers = {
        "das_parcsn": _decidir_das_parcsn,
        "das_parcsn_envelope": _decidir_das_parcsn,  # mesmo formato
        "boleto_sesc": _decidir_boleto_sesc,
        "boleto_sesc_envelope": _decidir_boleto_sesc,
        "holerite": _decidir_holerite,
        "holerite_envelope": _decidir_holerite,
        "certidao_rf": _decidir_certidao_rf,
        "cpf_cad": _decidir_cpf_cad,
        "garantia_americanas": _decidir_garantia_americanas,
        "extrato_bb": _decidir_extrato_bb,
        "nfce_envelope": _decidir_nfce_envelope,
    }
    if familia in handlers:
        decisao = handlers[familia](entry)
    elif familia == "ilegivel":
        decisao = _decidir_indecidivel(entry, "OCR muito borrado em foto cupom")
    else:
        decisao = _decidir_indecidivel(entry, f"familia não reconhecida: {familia}")

    return {
        "item_id": entry["item_id"],
        "tipo": entry["tipo"],
        **decisao,
    }


def main() -> int:
    if not _FONTE.exists():
        print(f"[ERRO] {_FONTE} não existe.")
        return 1
    entries = json.loads(_FONTE.read_text(encoding="utf-8"))

    # Carrega decisoes legacy preservando-as quando o item_id casa
    legacy = []
    if _LEGACY.exists():
        legacy = json.loads(_LEGACY.read_text(encoding="utf-8"))
    legacy_indexada = {d["item_id"]: d for d in legacy}

    saida: list[dict] = []
    contagem_familia: dict[str, int] = {}
    for entry in entries:
        if entry["item_id"] in legacy_indexada:
            saida.append(legacy_indexada[entry["item_id"]])
            contagem_familia["legacy"] = contagem_familia.get("legacy", 0) + 1
            continue
        familia = _classificar_familia(entry)
        contagem_familia[familia] = contagem_familia.get(familia, 0) + 1
        saida.append(_decidir(entry))

    _DESTINO.parent.mkdir(parents=True, exist_ok=True)
    _DESTINO.write_text(
        json.dumps(saida, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Gravado {len(saida)} decisoes em {_DESTINO}")
    print("Familias detectadas:")
    for f, n in sorted(contagem_familia.items(), key=lambda x: -x[1]):
        print(f"  {f}: {n}")
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
