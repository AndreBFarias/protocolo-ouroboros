"""Módulos de extração de dados financeiros de múltiplos bancos e formatos."""

from src.extractors.base import ExtratorBase, Transacao
from src.extractors.c6_cartao import ExtratorC6Cartao
from src.extractors.c6_cc import ExtratorC6CC
from src.extractors.itau_pdf import ExtratorItauPDF
from src.extractors.nubank_cartao import ExtratorNubankCartao
from src.extractors.nubank_cc import ExtratorNubankCC
from src.extractors.santander_pdf import ExtratorSantanderPDF

__all__: list[str] = [
    "ExtratorBase",
    "Transacao",
    "ExtratorC6Cartao",
    "ExtratorC6CC",
    "ExtratorItauPDF",
    "ExtratorNubankCartao",
    "ExtratorNubankCC",
    "ExtratorSantanderPDF",
]
