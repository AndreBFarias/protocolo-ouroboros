"""Checklist de documentos para declaração do IRPF."""

from typing import Any

from src.utils.logger import configurar_logger

logger = configurar_logger("irpf_checklist")

DOCUMENTOS_NECESSARIOS: list[dict[str, Any]] = [
    {
        "tipo": "rendimento_tributavel",
        "documento": "Informe de rendimentos do empregador",
        "obrigatorio": True,
    },
    {
        "tipo": "rendimento_tributavel",
        "documento": "Comprovante de renda PJ (pró-labore/distribuição)",
        "obrigatorio": True,
    },
    {
        "tipo": "rendimento_isento",
        "documento": "Comprovante de bolsa de estudos",
        "obrigatorio": False,
    },
    {
        "tipo": "rendimento_isento",
        "documento": "Informe de rendimentos de poupança",
        "obrigatorio": False,
    },
    {
        "tipo": "dedutivel_medico",
        "documento": "Recibos médicos com CNPJ do prestador",
        "obrigatorio": True,
    },
    {
        "tipo": "dedutivel_medico",
        "documento": "Informe do plano de saúde",
        "obrigatorio": True,
    },
    {
        "tipo": "inss_retido",
        "documento": "Comprovante de INSS retido na fonte",
        "obrigatorio": True,
    },
    {
        "tipo": "imposto_pago",
        "documento": "DARFs pagos (carnê-leão/DARF avulso)",
        "obrigatorio": True,
    },
    {
        "tipo": "imposto_pago",
        "documento": "DAS MEI/Simples Nacional",
        "obrigatorio": False,
    },
    {
        "tipo": "geral",
        "documento": "CPF de todos os dependentes",
        "obrigatorio": False,
    },
    {
        "tipo": "geral",
        "documento": "Informe de rendimentos bancários (aplicações)",
        "obrigatorio": True,
    },
    {
        "tipo": "geral",
        "documento": "Comprovante de endereço atualizado",
        "obrigatorio": True,
    },
]


def gerar_checklist(transacoes: list[dict]) -> list[dict[str, Any]]:
    """Gera checklist comparando documentos necessários vs dados disponíveis."""
    tipos_encontrados: set[str] = set()
    for t in transacoes:
        tag = t.get("tag_irpf")
        if tag:
            tipos_encontrados.add(tag)

    checklist: list[dict[str, Any]] = []
    for doc in DOCUMENTOS_NECESSARIOS:
        tipo = doc["tipo"]
        status = (
            "Dados no sistema"
            if (tipo in tipos_encontrados and tipo != "geral")
            else "Verificar manualmente"
        )

        checklist.append(
            {
                "documento": doc["documento"],
                "tipo": tipo,
                "obrigatorio": doc["obrigatorio"],
                "status": status,
            }
        )

    coletados = sum(1 for c in checklist if c["status"] == "Dados no sistema")
    total = len(checklist)
    logger.info("Checklist IRPF: %d/%d documentos com dados no sistema", coletados, total)

    return checklist


# "A preparação é a chave do sucesso." -- Alexander Graham Bell
