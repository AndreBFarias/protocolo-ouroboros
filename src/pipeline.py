"""Orquestrador principal do pipeline ETL financeiro."""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

from src.extractors.contracheque_pdf import processar_holerites
from src.load.relatorio import gerar_relatorios
from src.load.xlsx_writer import gerar_xlsx
from src.transform.canonicalizer_casal import (
    e_transferencia_do_casal,
    variantes_curtas,
)
from src.transform.categorizer import Categorizer
from src.transform.deduplicator import deduplicar
from src.transform.irpf_tagger import aplicar_tags_irpf
from src.transform.normalizer import normalizar_transacao
from src.utils.logger import configurar_logger

logger = configurar_logger("pipeline")

RAIZ = Path(__file__).parent.parent
DIR_RAW = RAIZ / "data" / "raw"
DIR_OUTPUT = RAIZ / "data" / "output"
DIR_HISTORICO = RAIZ / "data" / "historico"
CONTROLE_ANTIGO = DIR_HISTORICO / "controle_antigo.xlsx"


def _descobrir_extratores() -> list:
    """Importa e retorna instâncias de todos os extratores disponíveis."""
    extratores = []

    try:
        from src.extractors.nubank_cartao import ExtratorNubankCartao

        extratores.append(ExtratorNubankCartao)
    except ImportError as e:
        logger.warning("Extrator nubank_cartao indisponível: %s", e)

    try:
        from src.extractors.nubank_cc import ExtratorNubankCC

        extratores.append(ExtratorNubankCC)
    except ImportError as e:
        logger.warning("Extrator nubank_cc indisponível: %s", e)

    try:
        from src.extractors.c6_cc import ExtratorC6CC

        extratores.append(ExtratorC6CC)
    except ImportError as e:
        logger.warning("Extrator c6_cc indisponível: %s", e)

    try:
        from src.extractors.c6_cartao import ExtratorC6Cartao

        extratores.append(ExtratorC6Cartao)
    except ImportError as e:
        logger.warning("Extrator c6_cartao indisponível: %s", e)

    try:
        from src.extractors.itau_pdf import ExtratorItauPDF

        extratores.append(ExtratorItauPDF)
    except ImportError as e:
        logger.warning("Extrator itau_pdf indisponível: %s", e)

    try:
        from src.extractors.santander_pdf import ExtratorSantanderPDF

        extratores.append(ExtratorSantanderPDF)
    except ImportError as e:
        logger.warning("Extrator santander_pdf indisponível: %s", e)

    try:
        from src.extractors.energia_ocr import ExtratorEnergiaOCR

        extratores.append(ExtratorEnergiaOCR)
    except ImportError as e:
        logger.warning("Extrator energia_ocr indisponível: %s", e)

    try:
        from src.extractors.ofx_parser import ExtratorOFX

        extratores.append(ExtratorOFX)
    except ImportError as e:
        logger.warning("Extrator ofx_parser indisponível: %s", e)

    try:
        from src.extractors.cupom_garantia_estendida_pdf import (
            ExtratorCupomGarantiaEstendida,
        )

        extratores.append(ExtratorCupomGarantiaEstendida)
    except ImportError as e:
        logger.warning("Extrator cupom_garantia_estendida_pdf indisponível: %s", e)

    try:
        from src.extractors.nfce_pdf import ExtratorNfcePDF

        extratores.append(ExtratorNfcePDF)
    except ImportError as e:
        logger.warning("Extrator nfce_pdf indisponível: %s", e)

    try:
        from src.extractors.danfe_pdf import ExtratorDanfePDF

        extratores.append(ExtratorDanfePDF)
    except ImportError as e:
        logger.warning("Extrator danfe_pdf indisponível: %s", e)

    try:
        from src.extractors.cupom_termico_foto import ExtratorCupomTermicoFoto

        extratores.append(ExtratorCupomTermicoFoto)
    except ImportError as e:
        logger.warning("Extrator cupom_termico_foto indisponível: %s", e)

    try:
        from src.extractors.xml_nfe import ExtratorXmlNFe

        extratores.append(ExtratorXmlNFe)
    except ImportError as e:
        logger.warning("Extrator xml_nfe indisponível: %s", e)

    # Receita médica entra ANTES do catch-all recibo_nao_fiscal e DEPOIS
    # dos extratores fiscais: receita em foto/PDF tem marcadores específicos
    # (CRM, receituário, prescrição) que não colidem com cupom/NFC-e/DANFE,
    # mas um comprovante Pix fotografado poderia cair em recibo genérico
    # caso a receita fosse avaliada por último.
    try:
        from src.extractors.receita_medica import ExtratorReceitaMedica

        extratores.append(ExtratorReceitaMedica)
    except ImportError as e:
        logger.warning("Extrator receita_medica indisponível: %s", e)

    # Garantia de fabricante (Sprint 47b). Prioridade baixa: registrada
    # ANTES do catch-all recibo_nao_fiscal e DEPOIS da receita médica.
    # Pistas específicas (`termo_garantia`, `certificado_garantia`,
    # `garantia_fabricante`) evitam colisão com apólice estendida (47c).
    try:
        from src.extractors.garantia import ExtratorGarantiaFabricante

        extratores.append(ExtratorGarantiaFabricante)
    except ImportError as e:
        logger.warning("Extrator garantia_fabricante indisponível: %s", e)

    # DAS PARCSN (P1.1 2026-04-23). Registrado antes do catch-all para
    # capturar arquivos em `casal/impostos/das_parcsn/` e `_envelopes/originais/`.
    try:
        from src.extractors.das_parcsn_pdf import ExtratorDASPARCSNPDF

        extratores.append(ExtratorDASPARCSNPDF)
    except ImportError as e:
        logger.warning("Extrator das_parcsn_pdf indisponível: %s", e)

    # DIRPF .DEC (P3.1 2026-04-23). Extensão única .DEC, não colide com outros.
    try:
        from src.extractors.dirpf_dec import ExtratorDIRPFDec

        extratores.append(ExtratorDIRPFDec)
    except ImportError as e:
        logger.warning("Extrator dirpf_dec indisponível: %s", e)

    # Boleto PDF (Sprint 87.3 / 87e 2026-04-24). Registrado antes do catch-all
    # recibo_nao_fiscal para que `./run.sh --tudo` ingira boletos no grafo sem
    # depender de reprocessar_documentos.py manual.
    try:
        from src.extractors.boleto_pdf import ExtratorBoletoPDF

        extratores.append(ExtratorBoletoPDF)
    except ImportError as e:
        logger.warning("Extrator boleto_pdf indisponível: %s", e)

    # Recibo não-fiscal é catch-all de baixa prioridade (Sprint 47):
    # registrado depois dos extratores fiscais para não capturar arquivo
    # que pertence a cupom térmico, NFC-e ou DANFE.
    try:
        from src.extractors.recibo_nao_fiscal import ExtratorReciboNaoFiscal

        extratores.append(ExtratorReciboNaoFiscal)
    except ImportError as e:
        logger.warning("Extrator recibo_nao_fiscal indisponível: %s", e)

    return extratores


def _escanear_arquivos(diretorio: Path) -> list[Path]:
    """Escaneia recursivamente todos os arquivos em data/raw/."""
    extensoes = {
        ".csv",
        ".xlsx",
        ".xls",
        ".xml",
        ".pdf",
        ".ofx",
        ".jpg",
        ".jpeg",
        ".png",
        ".heic",
        ".heif",
        ".dec",  # P3.1 2026-04-23: DIRPF .DEC (Receita Federal)
    }
    arquivos = []

    for arquivo in diretorio.rglob("*"):
        if arquivo.is_file() and arquivo.suffix.lower() in extensoes:
            # Ignorar arquivos duplicados com sufixo (1), (2)
            if " (1)" in arquivo.stem or " (2)" in arquivo.stem:
                logger.debug("Ignorando duplicata de download: %s", arquivo.name)
                continue
            arquivos.append(arquivo)

    logger.info("Encontrados %d arquivos para processar em %s", len(arquivos), diretorio)
    return sorted(arquivos)


def _extrair_tudo(arquivos: list[Path], classes_extratores: list) -> list[dict]:
    """Executa extração de todos os arquivos com os extratores disponíveis."""
    transacoes_brutas: list[dict] = []
    arquivos_processados = 0
    arquivos_ignorados = 0

    for arquivo in arquivos:
        processado = False
        for cls_extrator in classes_extratores:
            try:
                extrator = cls_extrator(arquivo)
                if extrator.pode_processar(arquivo):
                    resultado = extrator.extrair()
                    for t in resultado:
                        transacao_norm = normalizar_transacao(
                            data_transacao=t.data,
                            valor=t.valor,
                            descricao=t.descricao,
                            banco_origem=t.banco_origem,
                            tipo_extrato="cartao"
                            if "cartao" in t.banco_origem.lower() or t.forma_pagamento == "Crédito"
                            else "cc",
                            identificador=t.identificador,
                            subtipo=_inferir_subtipo(arquivo),
                            arquivo_origem=str(arquivo),
                            tipo_sugerido=t.tipo,
                            valor_original_com_sinal=t.valor,
                            virtual=getattr(t, "_virtual", False),
                        )
                        transacoes_brutas.append(transacao_norm)

                    arquivos_processados += 1
                    logger.info(
                        "Extraídas %d transações de %s (%s)",
                        len(resultado),
                        arquivo.name,
                        cls_extrator.__name__,
                    )
                    processado = True
                    break
            except Exception as e:
                logger.error(
                    "Erro ao processar %s com %s: %s", arquivo.name, cls_extrator.__name__, e
                )

        if not processado:
            arquivos_ignorados += 1
            logger.warning("Nenhum extrator compatível para: %s", arquivo.name)

    logger.info(
        "Extração concluída: %d arquivos processados, %d ignorados, %d transações brutas",
        arquivos_processados,
        arquivos_ignorados,
        len(transacoes_brutas),
    )
    return transacoes_brutas


def _inferir_subtipo(arquivo: Path) -> str | None:
    """Infere subtipo (pf/pj) pelo caminho do arquivo."""
    partes = str(arquivo).lower()
    if "pj" in partes:
        return "pj"
    if "pf" in partes:
        return "pf"
    return None


def _importar_historico() -> list[dict]:
    """Importa transações do XLSX histórico (ago/2022 - jul/2023)."""
    if not CONTROLE_ANTIGO.exists():
        logger.info("Arquivo histórico não encontrado: %s", CONTROLE_ANTIGO)
        return []

    import openpyxl

    transacoes = []
    try:
        wb = openpyxl.load_workbook(CONTROLE_ANTIGO)
        if "Extrato" not in wb.sheetnames:
            logger.warning("Aba 'Extrato' não encontrada no histórico")
            return []

        ws = wb["Extrato"]
        for row in ws.iter_rows(min_row=2, values_only=True):
            data_val = row[0] if len(row) > 0 else None
            gasto = row[1] if len(row) > 1 else None
            forma = row[2] if len(row) > 2 else ""
            local = row[3] if len(row) > 3 else ""
            quem = row[4] if len(row) > 4 else ""
            categoria = row[5] if len(row) > 5 else None
            classificacao = row[6] if len(row) > 6 else None

            if data_val is None or gasto is None:
                continue

            if isinstance(data_val, datetime):
                data_date = data_val.date()
            elif isinstance(data_val, str):
                try:
                    data_date = datetime.strptime(data_val, "%Y-%m-%d").date()
                except ValueError:
                    continue
            else:
                continue

            # Normalizar classificação corrompida do histórico
            clf_raw = str(classificacao).strip() if classificacao else "Questionável"
            clf_map = {
                "Obrigatório": "Obrigatório",
                "Obrigatórios": "Obrigatório",
                "Questionável": "Questionável",
                "Supérfluo": "Supérfluo",
            }
            clf_normalizada = clf_map.get(clf_raw, "Questionável")

            transacoes.append(
                {
                    "data": data_date,
                    "valor": abs(float(gasto)) if isinstance(gasto, (int, float)) else 0,
                    "forma_pagamento": str(forma) if forma else "Débito",
                    "local": str(local) if local else "",
                    "quem": str(quem) if quem else "Casal",
                    "categoria": str(categoria) if categoria else "Outros",
                    "classificacao": clf_normalizada,
                    "banco_origem": "Histórico",
                    "tipo": "Despesa",
                    "mes_ref": data_date.strftime("%Y-%m"),
                    "tag_irpf": None,
                    "obs": "Importado do histórico",
                    "_identificador": f"hist_{data_date.isoformat()}_{gasto}_{local}",
                    "_descricao_original": str(local),
                    "_arquivo_origem": str(CONTROLE_ANTIGO),
                }
            )

        logger.info("Histórico importado: %d transações (ago/2022 - jul/2023)", len(transacoes))
    except Exception as e:
        logger.error("Erro ao importar histórico: %s", e)

    return transacoes


def _reclassificar_ti_orfas(transacoes: list[dict]) -> list[dict]:
    """Reclassifica TIs cuja descrição NÃO bate identidade do casal.

    Sprint 68b: rede de segurança pós-deduplicação. Qualquer transação
    marcada como `Transferência Interna` cuja descrição original não
    passa pelo matcher formal `e_transferencia_do_casal` é degradada
    para `Despesa` (quando valor negativo) ou `Receita` (valor positivo).

    Exceções operacionais legítimas (pagamento de fatura do próprio
    banco, resgate/aplicação CDB/RDB, agência 6450 Itaú) são preservadas
    via heurísticas textuais simples -- essas regras ainda vivem nos
    extratores e já foram aplicadas antes deste ponto; aqui o objetivo é
    apenas caçar falsos-positivos que escaparam (ex: linhas importadas
    do `controle_antigo.xlsx` cujo `local` cita terceiro homônimo).
    """
    regex_operacional = re.compile(
        r"PAGAMENTO\s+DE\s+FATURA|PGTO\s+FAT\s+CARTAO|PGTO\s+FATURA|"
        r"Fatura\s+de\s+cart[aã]o|PAGAMENTO\s+FATURA\s+NU|PAGTO\s+NU\s*PAGAMENT|"
        r"DEBITO\s+DE\s+CARTAO|DEB\s+CART|PIX\s+QRS\s+BANCO\s+SANTA|"
        r"CDB\s+C6|LIM\.\s*GARANT|RESGATE\s+CDB|APLICA[CÇ][AÃ]O\s+CDB|"
        r"AG\s*6450|AGENCIA\s+6450|Valor\s+adicionado\s+na\s+conta|Pix\s+no\s+Cr[eé]dito",
        re.IGNORECASE,
    )

    reclassificadas = 0
    for t in transacoes:
        if t.get("tipo") != "Transferência Interna":
            continue

        # Sprint 82b: espelho virtual de cartão é TI por design (contraparte
        # de pagamento de fatura). Não depende de match textual do casal
        # nem do regex operacional -- preserva a flag e pula a degradação.
        if t.get("_virtual"):
            continue

        descricao = str(t.get("_descricao_original") or t.get("local") or "")

        if e_transferencia_do_casal(descricao):
            continue

        if regex_operacional.search(descricao):
            continue

        try:
            valor = float(t.get("valor", 0) or 0)
        except (TypeError, ValueError):
            valor = 0.0

        novo_tipo = "Receita" if valor > 0 else "Despesa"
        t["tipo"] = novo_tipo
        reclassificadas += 1

    if reclassificadas:
        logger.info(
            "Sprint 68b: %d TI órfãs reclassificadas (sem match casal + sem regra operacional)",
            reclassificadas,
        )
    return transacoes


def _promover_variantes_para_ti(transacoes: list[dict]) -> list[dict]:
    """Promove Receita/Despesa para Transferência Interna via variantes curtas.

    Sprint 82: rede de captura pós-reclassificação. Qualquer transação
    ainda marcada como Receita ou Despesa cuja descrição casa o nível 2
    do matcher (`variantes_curtas(descricao, banco_origem)`) é promovida  # noqa: accent
    a Transferência Interna. Preserva a simetria com
    `_reclassificar_ti_orfas`: a função anterior degrada falsos-positivos;
    esta captura os falsos-negativos do matcher rigoroso.

    Não toca linhas já marcadas como Transferência Interna (evita
    dupla-contagem) nem Imposto.
    """
    promovidas = 0
    for t in transacoes:
        tipo_atual = t.get("tipo")
        if tipo_atual not in {"Receita", "Despesa"}:
            continue

        descricao = str(t.get("_descricao_original") or t.get("local") or "")
        banco = str(t.get("banco_origem") or "")
        if not descricao or not banco:
            continue

        if e_transferencia_do_casal(descricao):
            # Casou no matcher rigoroso mas tipo não é TI -- aproveita
            # e reclassifica aqui (defesa em profundidade).
            t["tipo"] = "Transferência Interna"
            promovidas += 1
            continue

        if variantes_curtas(descricao, banco):
            t["tipo"] = "Transferência Interna"
            promovidas += 1

    if promovidas:
        logger.info(
            "Sprint 82: %d transações promovidas a Transferência Interna via variantes curtas",
            promovidas,
        )
    return transacoes


def _filtrar_por_mes(transacoes: list[dict], mes: str) -> list[dict]:
    """Filtra transações por mês específico."""
    return [t for t in transacoes if t.get("mes_ref") == mes]


def _executar_linking_documentos() -> None:
    """Aciona o motor de linking documento->transação quando o grafo existe.

    Importação lazy para não pagar custo quando o grafo não existe ainda
    (usuário que roda só o pipeline XLSX clássico). Falhas são logadas
    como warning e não quebram a execução.
    """
    try:
        from src.graph.db import caminho_padrao
    except ImportError as erro:
        logger.warning("Módulo src.graph indisponível: %s -- linking ignorado", erro)
        return

    caminho_grafo = caminho_padrao()
    if not caminho_grafo.exists():
        logger.info(
            "Grafo SQLite ausente em %s -- linking de documentos pulado",
            caminho_grafo,
        )
        return

    try:
        from src.graph.db import GrafoDB
        from src.graph.linking import linkar_documentos_a_transacoes

        with GrafoDB(caminho_grafo) as db:
            stats = linkar_documentos_a_transacoes(db)
        logger.info("Linking documento->transação: %s", stats)
    except Exception as erro:
        logger.warning("Linking de documentos falhou: %s", erro)


def _executar_er_produtos() -> None:
    """Aciona o entity resolution de produtos quando o grafo existe.

    Roda DEPOIS do linking de documentos (Sprint 48) para que nodes `item` já
    estejam em posição estável. Importação lazy e falhas não-fatais (mesma
    política do linking).
    """
    try:
        from src.graph.db import caminho_padrao
    except ImportError as erro:
        logger.warning("Módulo src.graph indisponível: %s -- ER produtos ignorado", erro)
        return

    caminho_grafo = caminho_padrao()
    if not caminho_grafo.exists():
        logger.info(
            "Grafo SQLite ausente em %s -- ER de produtos pulado",
            caminho_grafo,
        )
        return

    try:
        from src.graph.db import GrafoDB
        from src.graph.er_produtos import executar_er_produtos

        with GrafoDB(caminho_grafo) as db:
            stats = executar_er_produtos(db)
        logger.info("ER de produtos: %s", stats)
    except Exception as erro:
        logger.warning("ER de produtos falhou: %s", erro)


def _executar_item_categorizer() -> None:
    """Aplica categorização por regex a todos os nodes `item` do grafo.

    Sprint 50: roda DEPOIS do ER de produtos (Sprint 49) para que a agregação
    por `produto_canonico` já exista antes da atribuição de categoria. Também
    importação lazy e falhas não-fatais.
    """
    try:
        from src.graph.db import caminho_padrao
    except ImportError as erro:
        logger.warning(
            "Módulo src.graph indisponível: %s -- categorização de itens pulada",
            erro,
        )
        return

    caminho_grafo = caminho_padrao()
    if not caminho_grafo.exists():
        logger.info(
            "Grafo SQLite ausente em %s -- categorização de itens pulada",
            caminho_grafo,
        )
        return

    try:
        from src.graph.db import GrafoDB
        from src.transform.item_categorizer import categorizar_todos_items_no_grafo

        with GrafoDB(caminho_grafo) as db:
            stats = categorizar_todos_items_no_grafo(db)
        logger.info("Categorização de itens: %s", stats)
    except Exception as erro:
        logger.warning("Categorização de itens falhou: %s", erro)


def executar(mes: str | None = None, processar_tudo: bool = False) -> None:
    """Executa o pipeline completo."""
    logger.info("=== Protocolo Ouroboros -- Pipeline ===")

    # 1. Descobrir extratores
    classes_extratores = _descobrir_extratores()
    logger.info("Extratores disponíveis: %d", len(classes_extratores))

    # 2. Escanear arquivos
    arquivos = _escanear_arquivos(DIR_RAW)

    # 3. Extrair transações
    transacoes = _extrair_tudo(arquivos, classes_extratores)

    # 4. Importar histórico
    historico = _importar_historico()
    transacoes.extend(historico)

    # 5. Deduplicar
    transacoes = deduplicar(transacoes)

    # 6. Categorizar
    categorizer = Categorizer()
    transacoes = categorizer.categorizar_lote(transacoes)

    # 6b. Reclassificar TIs órfãs (Sprint 68b) -- rede de segurança
    # pós-categorização contra falsos-positivos residuais. O categorizer
    # (mappings/categorias.yaml) aplica regras regex amplas como
    # `NU.PAGAMENT|BANCO.SANTA` que marcam `tipo: Transferência Interna`
    # em qualquer PIX que passe por Nubank/Santander como intermediário
    # financeiro -- inclusive PIX para terceiros (DEIVID, JOAO, etc.).
    # Esta passagem reverte a marcação quando a descrição NÃO casa
    # identidade do casal e não bate regra operacional legítima (pagamento
    # de fatura do próprio banco, CDB, agência 6450). Rodar DEPOIS do
    # categorizer é crítico: o categorizer pode reintroduzir falsos-
    # positivos se rodarmos antes.
    transacoes = _reclassificar_ti_orfas(transacoes)

    # 6c. Promover variantes curtas para Transferência Interna (Sprint 82)
    # -- rede de captura simétrica. A Sprint 68b cobriu o rigoroso
    # (nome_aceitos completo + CPF); a 82 cobre formas abreviadas que só
    # são seguras sob contexto bancário (ex: "Vitória" no Itaú com
    # marcador PIX/TRANSF + data DD/MM, "ANDRE SILVA BATISTA FARIAS"
    # sem o "DA"). Roda DEPOIS do reclassificar para não reintroduzir
    # falsos-positivos que acabaram de ser degradados.
    transacoes = _promover_variantes_para_ti(transacoes)

    # 7. Aplicar tags IRPF
    transacoes = aplicar_tags_irpf(transacoes)

    # 8. Filtrar por mês se necessário
    if mes and not processar_tudo:
        transacoes_filtradas = _filtrar_por_mes(transacoes, mes)
        logger.info("Filtrado para %s: %d transações", mes, len(transacoes_filtradas))
    else:
        transacoes_filtradas = transacoes

    # 9. Ordenar por data
    transacoes_filtradas.sort(key=lambda t: t.get("data", ""))

    # 9b. Computar identificador canônico (mesmo hash dos nodes `transacao` do  # noqa: accent
    # grafo) para ativar `Doc?` no Extrato em runtime real (Sprint 87b).
    from src.graph.migracao_inicial import hash_transacao_do_tx

    for tx in transacoes_filtradas:
        if tx.get("identificador"):
            continue  # contrato defensivo: não sobrescrever se já existir
        ident = hash_transacao_do_tx(tx)
        if ident is not None:
            tx["identificador"] = ident

    # 10. Processar holerites (contracheques) -- fonte extra para a aba renda.
    # P3.2 (auditoria 2026-04-23): passa grafo para ingerir cada holerite como
    # node `documento` tipo `holerite` (fecha ADR-20 tracking para folha).
    from src.graph.db import GrafoDB, caminho_padrao

    caminho_grafo_hol = caminho_padrao()
    contracheques: list[dict] = []
    if caminho_grafo_hol.exists():
        with GrafoDB(caminho_grafo_hol) as grafo_hol:
            grafo_hol.criar_schema()
            contracheques = processar_holerites(DIR_RAW / "andre" / "holerites", grafo=grafo_hol)
    else:
        contracheques = processar_holerites(DIR_RAW / "andre" / "holerites")

    # 11. Gerar XLSX
    ano = mes[:4] if mes else str(datetime.now().year)
    caminho_xlsx = DIR_OUTPUT / f"ouroboros_{ano}.xlsx"
    gerar_xlsx(transacoes_filtradas, caminho_xlsx, CONTROLE_ANTIGO, contracheques)

    # 11. Gerar relatórios
    # Quando --mes é usado, passa transações completas (para projeções corretas)
    # mas filtra a geração apenas para o mês solicitado
    gerar_relatorios(
        transacoes, DIR_OUTPUT, meses_filtro=[mes] if (mes and not processar_tudo) else None
    )

    # 12. Linking de documentos fiscais às transações bancárias (Sprint 48).
    # Roda apenas se o grafo SQLite já existir (populado via
    # `python -m src.graph.migracao_inicial` e ingestão de documentos pelos
    # extratores fiscais). Ausência do grafo não é erro -- pipeline principal
    # do XLSX segue funcionando sem ele.
    _executar_linking_documentos()

    # 13. Entity resolution de produtos (Sprint 49): agrupa itens equivalentes
    # (mesma descrição, variações ortográficas) em nodes `produto_canonico`.
    # Roda depois do linking para que itens de documentos ainda por linkar
    # não fiquem pendurados sem agregado. Ausência de grafo é no-op.
    _executar_er_produtos()

    # 14. Categorização de itens (Sprint 50): aplica regras regex em
    # `mappings/categorias_item.yaml` a todos os nodes `item`, criando
    # aresta `categoria_de` -> node `categoria` (com tipo_categoria=item
    # no metadata, alinhado ao ADR-14). Roda depois do ER para que a
    # agregação por produto canônico já esteja pronta. Itens em "Outros"
    # com frequência >=3 geram proposta MD para revisão supervisor.
    _executar_item_categorizer()

    logger.info("=== Pipeline concluído ===")
    logger.info("XLSX: %s", caminho_xlsx)
    logger.info("Relatórios: %s", DIR_OUTPUT)


def _executar_backfill_metadata() -> int:
    """Rota administrativa da Sprint 87.5: backfill de arquivo_original.

    Isola-se do pipeline regular; chama apenas o módulo dedicado e sai.
    Retorna exit code (0 sempre que conclui sem exceção)."""
    from src.graph.backfill_arquivo_original import backfill_arquivo_original
    from src.graph.db import GrafoDB, caminho_padrao

    db = GrafoDB(caminho_padrao())
    try:
        stats = backfill_arquivo_original(db)
    finally:
        db.fechar()
    logger.info("backfill-metadata stats: %s", stats)
    # Saída legível no stdout do operador; pipeline não produz outros prints.
    for chave, valor in stats.items():
        sys.stdout.write(f"{chave}: {valor}\n")
    return 0


def main(argv: list[str] | None = None) -> None:
    """Entrypoint CLI."""
    parser = argparse.ArgumentParser(description="Pipeline ETL Financeiro")
    parser.add_argument("--mes", type=str, help="Mês para processar (YYYY-MM)")
    parser.add_argument("--tudo", action="store_true", help="Processar todos os dados")
    parser.add_argument(
        "--backfill-metadata",
        action="store_true",
        help="Rota administrativa: preenche arquivo_original em nodes documento (Sprint 87.5)",
    )
    args = parser.parse_args(argv)

    if args.backfill_metadata:
        sys.exit(_executar_backfill_metadata())

    if not args.mes and not args.tudo:
        parser.print_help()
        sys.exit(1)

    executar(mes=args.mes, processar_tudo=args.tudo)


if __name__ == "__main__":
    main()


# "A verdadeira sabedoria está em reconhecer a própria ignorância." -- Sócrates
