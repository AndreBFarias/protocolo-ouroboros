"""Sprint 106: motor de fallback OCR por similaridade entre arquivos do mesmo
tipo.

Quando OCR de uma foto/PDF retorna texto abaixo do limiar de chars úteis,
este motor busca outro arquivo (já catalogado no grafo) do mesmo
``tipo_documento`` cujo OCR foi bem-sucedido. Se o candidato é
suficientemente similar (phash visual + janela temporal + textual), seu
metadata é copiado como template -- com flag ``metadata.fallback_origem``
para auditoria.

Estratégia:
  - phash: comparação perceptual hash (lib ``imagehash``, opcional).
  - temporal: |mtime_falho - data_emissao_candidato| <= janela_dias.
  - textual: substring do nome de fornecedor/CNPJ no nome do falho ou nos
    poucos chars úteis extraídos.

Score combinado >= ``confidence_minima`` (default 0.70) dispara o uso.

Graceful degradation:
  - ``imagehash`` ausente: ignora componente phash, prossegue com peso
    redistribuído entre temporal e textual.
"""

from __future__ import annotations

import functools
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml

from src.graph.db import GrafoDB
from src.utils.logger import configurar_logger

logger = configurar_logger("intake.ocr_fallback_similar")

_RAIZ_REPO: Path = Path(__file__).resolve().parents[2]
_PATH_CONFIG: Path = _RAIZ_REPO / "mappings" / "ocr_fallback_config.yaml"


def _config_default() -> dict[str, Any]:
    return {
        "limiar_chars_uteis_por_tipo": {"default": 50},
        "pesos_score": {"phash": 0.5, "temporal": 0.3, "textual": 0.2},
        "janela_temporal_dias_por_tipo": {"default": 14},
        "confidence_minima": 0.70,
    }


@functools.lru_cache(maxsize=1)
def _carregar_config() -> dict[str, Any]:
    """AUDIT-CACHE-THREADSAFE: usa lru_cache(maxsize=1) em vez de global mutavel."""
    if not _PATH_CONFIG.exists():
        return _config_default()
    with _PATH_CONFIG.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or _config_default()


def _resetar_cache_config() -> None:
    """Helper para testes -- delega para lru_cache.cache_clear()."""
    _carregar_config.cache_clear()


# Sprint 106a: whitelist de palavras DOMINIO-ESPECIFICAS para detectar coerência.
# Preposições curtas (de, da, do, em) foram REMOVIDAS porque aparecem por acaso
# em garbage do Tesseract -- precisamos de substantivos específicos de fiscal/financeiro.
_PALAVRAS_PT_BR_COMUNS: frozenset[str] = frozenset(
    {
        # Substantivos específicos de documentos fiscais/financeiros
        "valor",
        "total",
        "pagamento",
        "forma",
        "documento",
        "data",
        "nota",
        "fiscal",
        "consumidor",
        "cnpj",
        "cpf",
        "loja",
        "endereco",
        "produto",
        "quantidade",
        "unidade",
        "preco",
        "compra",
        "boleto",
        "vencimento",
        "beneficiario",
        "pagador",
        "banco",
        "conta",
        "agencia",
        "codigo",
        "numero",
        "serie",
        "emissao",
        "protocolo",
        "autorizacao",
        "consulta",
        "chave",
        "acesso",
        "filial",
        "subtotal",
        "desconto",
        "imposto",
        "trib",
        "tributo",
        # Variantes com acento
        "endereço",
        "código",
        "número",
        "série",
        "emissão",
        "agência",
        "preço",
        "cnpj",
        "tributário",
        "vencimento",
        # Indicadores monetários
        "r$",
        "rs",
        # Verbos comuns em recibos
        "pagar",
        "pago",
        "receber",
        "recebido",
        "emitir",
        "emitido",
        # Tipos de pagamento
        "pix",
        "credito",
        "debito",
        "dinheiro",
        "transferencia",
        "tef",
        # Loja/empresarial
        "ltda",
        "americanas",
        "filial",
        "matriz",
        "razao",
        "social",
    }
)

import re as _re_106a  # noqa: E402

_RE_PALAVRAS = _re_106a.compile(r"\b[\wÀ-ÿ$]+\b", _re_106a.UNICODE)


def _contar_palavras_conhecidas(texto: str) -> int:
    """Sprint 106a: conta tokens em PT-BR contra whitelist."""
    palavras = _RE_PALAVRAS.findall((texto or "").lower())
    return sum(1 for p in palavras if p in _PALAVRAS_PT_BR_COMUNS)


def _ocr_e_ilegivel(texto: str, tipo: str, config: dict[str, Any] | None = None) -> bool:
    """True se texto extraído está abaixo dos critérios de legibilidade.

    Sprint 106a: criterio composite (qualquer um dispara ilegível):
      1. chars úteis (alnum) < limiar_chars_uteis_por_tipo
      2. palavras conhecidas em PT-BR < min_palavras_conhecidas_por_tipo
      3. ratio non-letras > max_ratio_non_letras_por_tipo (quando total > 100)

    Garbage do Tesseract pode ter 1000+ chars mas falha (2) e (3).
    """
    cfg = config or _carregar_config()
    if not texto:
        return True

    # Critério 1 (Sprint 106 original): chars úteis
    limiares = cfg.get("limiar_chars_uteis_por_tipo", {})
    limiar_chars = limiares.get(tipo, limiares.get("default", 50))
    chars_uteis = sum(1 for c in texto if c.isalnum())
    if chars_uteis < limiar_chars:
        return True

    # Critério 2 (Sprint 106a): palavras conhecidas em PT-BR
    min_pal_cfg = cfg.get("min_palavras_conhecidas_por_tipo", {})
    min_pal = min_pal_cfg.get(tipo, min_pal_cfg.get("default", 5))
    if _contar_palavras_conhecidas(texto) < min_pal:
        return True

    # Critério 3 (Sprint 106a): ratio non-letras
    chars_total = len(texto)
    if chars_total > 100:
        non_alpha = sum(1 for c in texto if not c.isalpha() and not c.isspace())
        max_ratio_cfg = cfg.get("max_ratio_non_letras_por_tipo", {})
        max_ratio = max_ratio_cfg.get(tipo, max_ratio_cfg.get("default", 0.45))
        if non_alpha / chars_total > max_ratio:
            return True

    return False


def _phash_imagem(caminho: Path) -> Any:
    """Retorna phash da imagem ou None se imagehash/PIL indisponível."""
    try:
        import imagehash
        from PIL import Image
    except ImportError:
        return None
    try:
        return imagehash.phash(Image.open(caminho))
    except Exception as exc:  # noqa: BLE001
        logger.debug("phash falhou em %s: %s", caminho, exc)
        return None


def _score_phash(falho: Path, candidato_path: Path | None) -> float:
    """Score visual 0..1 (1 = idêntico). Devolve 0 se libs indisponíveis."""
    if candidato_path is None or not candidato_path.exists():
        return 0.0
    h1 = _phash_imagem(falho)
    h2 = _phash_imagem(candidato_path)
    if h1 is None or h2 is None:
        return 0.0
    distancia = h1 - h2  # tipo: int (Hamming)
    # phash retorna hash de 64 bits; distancia 0 = idêntico, 32 = aleatório.
    return max(0.0, 1.0 - distancia / 64.0)


def _score_temporal(falho_mtime: float, candidato_data: str | None, janela_dias: int) -> float:
    """Score 0..1 baseado em distância temporal vs janela.

    AUDIT-TIMEZONE-OCR: compara apenas date() em ambos os lados para evitar
    flutuação de +/-1 dia causada por timezone naive vs hora local.
    """
    if not candidato_data:
        return 0.0
    try:
        d_cand = date.fromisoformat(str(candidato_data)[:10])
        d_falho = datetime.fromtimestamp(falho_mtime).date()
        delta_dias = abs((d_cand - d_falho).days)
        if delta_dias > janela_dias:
            return 0.0
        return 1.0 - (delta_dias / max(1, janela_dias))
    except (ValueError, TypeError):
        return 0.0


# AUDIT-SCORE-TEXTUAL: ignorar palavras genericas que casam por acaso em
# qualquer cupom (BANCO, EMPRESA, COMERCIO, SA, LTDA, etc.).
_PALAVRAS_GENERICAS_FORNECEDOR: frozenset[str] = frozenset(
    {
        "BANCO",
        "EMPRESA",
        "COMERCIO",
        "SA",
        "S.A.",
        "S/A",
        "LTDA",
        "INDUSTRIA",
        "SERVICOS",
        "DISTRIBUIDORA",
        "CONSULTORIA",
        "DE",
        "DA",
        "DO",
        "DAS",
        "DOS",  # preposicoes
    }
)


def _palavras_especificas_fornecedor(razao: str) -> list[str]:
    """Filtra fornecedor preservando apenas palavras especificas (>=4 chars,
    nao-genericas).
    """
    return [
        p for p in razao.upper().split() if p not in _PALAVRAS_GENERICAS_FORNECEDOR and len(p) >= 4
    ]


def _score_textual(falho_nome: str, falho_texto: str, candidato_meta: dict[str, Any]) -> float:
    """Score 0..1 se fornecedor/CNPJ do candidato aparece no nome ou texto do falho.

    AUDIT-SCORE-TEXTUAL: ignora palavras genericas (BANCO, SA, LTDA) e considera
    ate 3 palavras especificas + CNPJ raiz. Score = matches / 3.0.
    """
    fornecedor = (candidato_meta.get("razao_social") or "").upper()
    cnpj_raw = candidato_meta.get("cnpj_emitente") or ""
    cnpj = cnpj_raw.replace(".", "").replace("/", "").replace("-", "")
    falho_combinado = (falho_nome.upper() + " " + (falho_texto or "").upper())[:5000]
    matches = 0
    palavras = _palavras_especificas_fornecedor(fornecedor)
    matches += sum(1 for p in palavras[:3] if p in falho_combinado)
    if cnpj and len(cnpj) >= 8 and cnpj[:8] in falho_combinado.replace(" ", ""):
        matches += 1
    return min(1.0, matches / 3.0)


def buscar_similar(
    arquivo_falho: Path,
    grafo: GrafoDB,
    tipo_falho: str,
    texto_falho: str = "",
    config: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Busca arquivo do mesmo tipo cujo OCR foi bem-sucedido.

    Retorna dict com {item_id_similar, score, evidencia, candidato_meta}
    ou None.
    """
    cfg = config or _carregar_config()
    pesos = cfg["pesos_score"]
    janelas = cfg.get("janela_temporal_dias_por_tipo", {})
    janela = int(janelas.get(tipo_falho, janelas.get("default", 14)))
    confidence_min = float(cfg.get("confidence_minima", 0.70))

    # Lista nodes do mesmo tipo no grafo
    cur = grafo._conn.execute(  # noqa: SLF001
        "SELECT id, nome_canonico, metadata FROM node WHERE tipo='documento'"
    )
    candidatos: list[dict[str, Any]] = []
    for row in cur:
        meta = json.loads(row[2] or "{}")
        if meta.get("tipo_documento") != tipo_falho:
            continue
        ao = meta.get("arquivo_origem")
        if ao and Path(ao).exists():
            candidatos.append(
                {
                    "id": row[0],
                    "nome_canonico": row[1],
                    "metadata": meta,
                    "arquivo_origem": Path(ao),
                }
            )

    if not candidatos:
        logger.info(
            "buscar_similar: nenhum candidato com OCR válido para tipo=%s",
            tipo_falho,
        )
        return None

    falho_mtime = arquivo_falho.stat().st_mtime
    falho_nome = arquivo_falho.name

    melhor: dict[str, Any] | None = None
    for cand in candidatos:
        s_phash = _score_phash(arquivo_falho, cand["arquivo_origem"])
        s_temp = _score_temporal(falho_mtime, cand["metadata"].get("data_emissao"), janela)
        s_text = _score_textual(falho_nome, texto_falho, cand["metadata"])

        # Reescala pesos quando phash é 0 (lib ausente ou conteúdo não-imagem)
        if s_phash == 0.0:
            denom = pesos["temporal"] + pesos["textual"]
            if denom <= 0:
                score = 0.0
            else:
                p_temp = pesos["temporal"] / denom
                p_text = pesos["textual"] / denom
                score = s_temp * p_temp + s_text * p_text
        else:
            score = (
                s_phash * pesos["phash"] + s_temp * pesos["temporal"] + s_text * pesos["textual"]
            )

        evidencia = {
            "phash": round(s_phash, 3),
            "temporal": round(s_temp, 3),
            "textual": round(s_text, 3),
            "score": round(score, 3),
            "janela_dias": janela,
        }
        if melhor is None or score > melhor["score"]:
            melhor = {
                "item_id_similar": cand["nome_canonico"],
                "score": score,
                "evidencia": evidencia,
                "candidato_meta": cand["metadata"],
                "candidato_id": cand["id"],
            }

    if melhor is None or melhor["score"] < confidence_min:
        logger.info(
            "buscar_similar: melhor score %.3f abaixo de %.2f -- sem fallback",
            melhor["score"] if melhor else 0.0,
            confidence_min,
        )
        return None

    logger.info(
        "buscar_similar: match encontrado (score=%.3f, similar=%s)",
        melhor["score"],
        melhor["item_id_similar"],
    )
    return melhor


def reanalisar_pasta_conferir(
    grafo: GrafoDB,
    raiz_raw: Path | None = None,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Reanalisa data/raw/_conferir/ tentando aplicar fallback similar.

    Para cada arquivo em ``_conferir/``:
      1. Faz preview OCR.
      2. Se ilegível para o tipo inferido (via path ou nome), busca similar.
      3. Se match encontrado: copia metadata e move para pasta canônica.
      4. Senão: preserva em ``_conferir/``.

    Idempotente: arquivos já movidos saem da varredura.
    """
    raiz = raiz_raw if raiz_raw is not None else _RAIZ_REPO / "data" / "raw"
    pasta = raiz / "_conferir"
    stats: dict[str, Any] = {
        "arquivos": 0,
        "ilegiveis": 0,
        "matched": 0,
        "preservados": 0,
        "movidos": 0,
        "matches": [],
    }
    if not pasta.exists():
        return stats

    arquivos = [p for p in pasta.rglob("*") if p.is_file()]
    stats["arquivos"] = len(arquivos)

    # Sprint 106 (P0-02 fix): mapeamento real por nome/extensão.
    # Cada padrão lê em ordem de especificidade: prefixos mais específicos primeiro.
    _MAPA_TIPO_POR_NOME = (
        ("recibo_", "recibo_nao_fiscal"),
        ("das_parcsn_", "das_parcsn_andre"),
        ("das_", "das_parcsn_andre"),
        ("holerite", "holerite"),
        ("nfce_", "nfce_modelo_65"),
        ("danfe_", "danfe_nfe"),
        ("garantia_", "cupom_garantia_estendida"),
        ("boleto_", "boleto_servico"),
        ("cupom_", "cupom_fiscal_foto"),
    )

    for arq in arquivos:
        nome_lower = arq.name.lower()
        tipo_inferido: str | None = None
        for prefixo, tipo_canon in _MAPA_TIPO_POR_NOME:
            if prefixo in nome_lower:
                tipo_inferido = tipo_canon
                break
        if tipo_inferido is None:
            # Fallback: imagens (jpeg/png) sem prefixo conhecido viram cupom-foto.
            if arq.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
                tipo_inferido = "cupom_fiscal_foto"
            else:
                tipo_inferido = "recibo_nao_fiscal"  # PDF generico

        # AUDIT-IMPORT-CAMADA: usa helper compartilhado em src/intake/preview.py
        from src.intake.preview import extrair_preview_completo

        texto = extrair_preview_completo(arq, max_chars=2000)
        if not _ocr_e_ilegivel(texto, tipo_inferido):
            stats["preservados"] += 1
            continue
        stats["ilegiveis"] += 1

        match = buscar_similar(arq, grafo, tipo_inferido, texto_falho=texto)
        if match is None:
            stats["preservados"] += 1
            continue
        stats["matched"] += 1
        stats["matches"].append(
            {
                "arquivo": str(arq),
                "similar_id": match["item_id_similar"],
                "score": match["score"],
                "evidencia": match["evidencia"],
            }
        )

        if not dry_run:
            # Move para pasta canônica do similar (se conhecida) e atualiza grafo.
            # (P0-03 fix Sprint 108): atualizar arquivo_origem no node correspondente
            # para que backfill futuro não detecte como path quebrado.
            cand_origem = match["candidato_meta"].get("arquivo_origem")
            if cand_origem and Path(cand_origem).parent.exists():
                destino_pasta = Path(cand_origem).parent
                destino = destino_pasta / arq.name
                if destino.exists():
                    logger.warning("destino existe, pulando: %s", destino)
                    continue
                import shutil

                shutil.move(str(arq), str(destino))
                stats["movidos"] += 1

                # Atualiza node correspondente do match no grafo.
                cur_upd = grafo._conn.execute(  # noqa: SLF001
                    "SELECT id, tipo, nome_canonico, metadata, aliases FROM node WHERE id=?",
                    (match["candidato_id"],),
                )
                row = cur_upd.fetchone()
                if row is not None:
                    meta_upd = json.loads(row[3] or "{}")
                    meta_upd["fallback_origem"] = match["item_id_similar"]
                    meta_upd["confidence_fallback"] = match["score"]
                    meta_upd["arquivo_origem_aplicado"] = str(destino.resolve())
                    grafo.upsert_node(
                        tipo="documento",
                        nome_canonico=row[2],
                        metadata=meta_upd,
                        aliases=json.loads(row[4] or "[]"),
                    )

    return stats


def main(argv: list[str] | None = None) -> int:
    """CLI standalone: reanalisa data/raw/_conferir/ aplicando fallback similar."""
    import argparse

    from src.graph.db import caminho_padrao

    parser = argparse.ArgumentParser(
        description="Sprint 106 -- reanalisa _conferir/ via fallback de similar.",
    )
    parser.add_argument(
        "--reanalisar-conferir",
        action="store_true",
        help="Roda reanalise (default: requer essa flag).",
    )
    parser.add_argument(
        "--executar",
        action="store_true",
        help="Aplica moves (default: dry-run).",
    )
    parser.add_argument("--grafo", type=Path, default=None)
    args = parser.parse_args(argv)

    if not args.reanalisar_conferir:
        parser.print_help()
        return 0

    cam = args.grafo or caminho_padrao()
    if not cam.exists():
        print(f"Grafo não encontrado: {cam}")
        return 1
    grafo = GrafoDB(cam)
    rel = reanalisar_pasta_conferir(grafo, dry_run=not args.executar)
    modo = "EXECUTAR" if args.executar else "DRY-RUN"
    print(f"\n[OCR fallback similar -- {modo}]")
    print(f"  Arquivos:    {rel['arquivos']}")
    print(f"  Ilegiveis:   {rel['ilegiveis']}")
    print(f"  Matched:     {rel['matched']}")
    print(f"  Movidos:     {rel['movidos']}")
    print(f"  Preservados: {rel['preservados']}")
    if rel["matches"]:
        print("  Matches (5 primeiros):")
        for m in rel["matches"][:5]:
            print(f"    - {Path(m['arquivo']).name} -> {m['similar_id']} (score={m['score']:.3f})")
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())


# "Quando a foto falha, peça o template ao gêmeo." -- princípio do fallback inteligente
