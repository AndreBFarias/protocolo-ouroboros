"""Sprint 93f -- proof-of-work runtime que PJ da Vitória chega ao XLSX.

Até Sprint 93c, o extrator Nubank cartão emitia `Nubank` literal e colapsava
PJ da Vitória em PF do André. A 93c consertou o extrator. Sprint 93f fechou
duas lacunas runtime que faziam tx PJ desaparecerem mesmo com unit-teste verde:

1. Mismatch normalizer × contrato canônico: `inferir_pessoa` em
   `src/transform/normalizer.py` comparava contra sets sem parênteses
   (`"Nubank PF"`, `"Nubank PJ"`) enquanto os extratores emitiam com
   parênteses (`"Nubank (PF)"`, `"Nubank (PJ)"`). Bug encobria 2310 tx PF
   indo a `Casal`.

2. Colisão de identificador entre PF e PJ: `_gerar_hash` em
   `src/extractors/nubank_cartao.py` usava `(data, titulo, valor)` sem
   banco. Linha PF do André e PJ da Vitória com mesmo `(data, titulo,
   valor)` (assinaturas recorrentes) geravam mesmo hash; dedup nível 1
   descartava a PJ. Fix inclui `banco_origem` na chave.
"""

from pathlib import Path

from src.extractors.nubank_cartao import ExtratorNubankCartao
from src.extractors.nubank_cc import ExtratorNubankCC
from src.transform.normalizer import inferir_pessoa, normalizar_transacao

# ----------------------------------------------------------------------
# Unidade: inferir_pessoa alinhado ao contrato BANCOS_VALIDOS
# ----------------------------------------------------------------------


def test_inferir_pessoa_nubank_pf_com_parenteses_retorna_vitoria():
    """Rótulo canônico `Nubank (PF)` (emitido por nubank_cc.py:160) deve
    mapear para Vitória. Antes da 93f caía em `Casal`."""
    assert inferir_pessoa("Nubank (PF)", subtipo=None) == "Vitória"


def test_inferir_pessoa_nubank_pj_com_parenteses_retorna_vitoria():
    """Rótulo canônico `Nubank (PJ)` (emitido por nubank_cartao.py:134 e
    nubank_cc.py:160) deve mapear para Vitória."""
    assert inferir_pessoa("Nubank (PJ)", subtipo=None) == "Vitória"


def test_inferir_pessoa_nubank_sem_sufixo_retorna_andre():
    """Cartão PF do André (path sem nubank_pj) continua emitindo `Nubank`
    puro e deve mapear para André."""
    assert inferir_pessoa("Nubank", subtipo=None) == "André"


# ----------------------------------------------------------------------
# Integração leve: extrator PJ + normalizar_transacao -> XLSX row
# ----------------------------------------------------------------------


def _escrever_csv_cartao_pj(tmp_path: Path) -> Path:
    subdir = tmp_path / "vitoria" / "nubank_pj_cartao"
    subdir.mkdir(parents=True)
    csv_path = subdir / "Nubank_2026-04-11.csv"
    csv_path.write_text(
        "date,title,amount\n"
        "2026-04-10,Compra padaria,25.40\n"
        "2026-04-11,Pagamento recebido,-100.00\n",
        encoding="utf-8",
    )
    return csv_path


def _escrever_csv_cc_pj(tmp_path: Path) -> Path:
    subdir = tmp_path / "vitoria" / "nubank_pj_cc"
    subdir.mkdir(parents=True)
    csv_path = subdir / "cc_pj.csv"
    csv_path.write_text(
        "Data,Valor,Identificador,Descrição\n"
        "10/04/2026,150.00,abc123,Transferência Recebida - TESTE\n"
        "11/04/2026,-45.50,def456,Transferência enviada pelo Pix - FORNECEDOR\n",
        encoding="utf-8",
    )
    return csv_path


def _inferir_subtipo(arquivo: Path) -> str | None:
    partes = str(arquivo).lower()
    if "pj" in partes:
        return "pj"
    if "pf" in partes:
        return "pf"
    return None


def test_cartao_pj_produz_tx_vitoria_e_banco_canonico(tmp_path):
    """Fluxo runtime: ExtratorNubankCartao sobre CSV PJ sintético emite
    `banco_origem=Nubank (PJ)`; normalizar_transacao resolve `quem=Vitória`.
    Cobre dimensão 1 do bug 93f (rótulo PJ)."""
    csv_path = _escrever_csv_cartao_pj(tmp_path)
    ext = ExtratorNubankCartao(csv_path)
    transacoes = ext.extrair()

    assert transacoes, "extrator deve produzir tx do CSV PJ sintético"
    for t in transacoes:
        assert t.banco_origem == "Nubank (PJ)"
        norm = normalizar_transacao(
            data_transacao=t.data,
            valor=t.valor,
            descricao=t.descricao,
            banco_origem=t.banco_origem,
            tipo_extrato="cartao",
            identificador=t.identificador,
            subtipo=_inferir_subtipo(csv_path),
            arquivo_origem=str(csv_path),
            tipo_sugerido=t.tipo,
            valor_original_com_sinal=t.valor,
        )
        assert norm["banco_origem"] == "Nubank (PJ)"
        assert norm["quem"] == "Vitória"


def test_cc_pj_produz_tx_vitoria_e_banco_canonico(tmp_path):
    """Mesmo contrato da cartão mas para Nubank CC PJ."""
    csv_path = _escrever_csv_cc_pj(tmp_path)
    ext = ExtratorNubankCC(csv_path)
    transacoes = ext.extrair()

    assert transacoes, "extrator deve produzir tx do CSV CC PJ sintético"
    for t in transacoes:
        assert t.banco_origem == "Nubank (PJ)"
        norm = normalizar_transacao(
            data_transacao=t.data,
            valor=t.valor,
            descricao=t.descricao,
            banco_origem=t.banco_origem,
            tipo_extrato="cc",
            identificador=t.identificador,
            subtipo=_inferir_subtipo(csv_path),
            arquivo_origem=str(csv_path),
            tipo_sugerido=t.tipo,
            valor_original_com_sinal=t.valor,
        )
        assert norm["banco_origem"] == "Nubank (PJ)"
        assert norm["quem"] == "Vitória"


def test_cc_vitoria_default_sem_subtipo_resolve_para_vitoria(tmp_path):
    """Sprint 93f -- dimensão 2 do bug: Nubank CC default da Vitória sob path
    `vitoria/nubank_cc/` (sem sufixo _pf) não deriva subtipo. Antes da 93f
    caía em `Casal`. Fix no normalizer faz `Nubank (PF)` -> Vitória mesmo
    sem subtipo inferido. Esse é o path canônico que explicava 2310 tx como
    Casal no XLSX stale pré-fix."""
    # Nome neutro: nem "pj" nem "pf" no nome do arquivo nem no path, para
    # garantir que _inferir_subtipo retorna None (o leak com "cc_pf.csv"
    # casava `"pf" in partes` e disfarçava o bug do normalizer).
    subdir = tmp_path / "vitoria" / "nubank_cc"
    subdir.mkdir(parents=True)
    csv_path = subdir / "extrato.csv"
    csv_path.write_text(
        "Data,Valor,Identificador,Descrição\n"
        "10/04/2026,200.00,xyz789,Transferência Recebida - EMPREGADOR\n",
        encoding="utf-8",
    )
    ext = ExtratorNubankCC(csv_path)
    transacoes = ext.extrair()

    assert transacoes
    for t in transacoes:
        assert t.banco_origem == "Nubank (PF)"
        # _inferir_subtipo em "vitoria/nubank_cc" devolve None (sem "pj" nem "pf")
        norm = normalizar_transacao(
            data_transacao=t.data,
            valor=t.valor,
            descricao=t.descricao,
            banco_origem=t.banco_origem,
            tipo_extrato="cc",
            identificador=t.identificador,
            subtipo=_inferir_subtipo(csv_path),
            arquivo_origem=str(csv_path),
            tipo_sugerido=t.tipo,
            valor_original_com_sinal=t.valor,
        )
        # Dupla verificação: subtipo None E quem=Vitória (só o fix dos sets resolve)
        assert norm["quem"] == "Vitória", (
            f"PF CC com path sem sufixo deve resolver Vitoria via set canonico, "
            f"got {norm['quem']!r}"
        )


# ----------------------------------------------------------------------
# Regressão runtime: identificador PF e PJ não colidem na dedup nível 1
# ----------------------------------------------------------------------


def test_identificador_pf_pj_nao_colide_no_dedup(tmp_path):
    """Sprint 93f -- garantia anti-regressão. Mesma compra `(date, title,
    amount)` aparecendo em CSV PF do André E em CSV PJ da Vitória deve
    gerar identificadores DIFERENTES, para que dedup nível 1 preserve
    ambas. Antes do fix do hash, dedup descartava a PJ inteira."""
    from src.transform.deduplicator import deduplicar_por_identificador

    pf_dir = tmp_path / "andre" / "nubank_cartao"
    pj_dir = tmp_path / "vitoria" / "nubank_pj_cartao"
    pf_dir.mkdir(parents=True)
    pj_dir.mkdir(parents=True)

    # Mesma linha em ambos arquivos -- compra recorrente (assinatura mensal)
    linha_csv = "date,title,amount\n2026-04-10,Spotify,29.90\n"
    pf_path = pf_dir / "Nubank_2026-04-11.csv"
    pj_path = pj_dir / "Nubank_2026-04-11.csv"
    pf_path.write_text(linha_csv, encoding="utf-8")
    pj_path.write_text(linha_csv, encoding="utf-8")

    tx_pf = ExtratorNubankCartao(pf_path).extrair()
    tx_pj = ExtratorNubankCartao(pj_path).extrair()
    assert len(tx_pf) == 1 and len(tx_pj) == 1

    # Identificadores DEVEM diferir entre PF e PJ
    assert tx_pf[0].identificador != tx_pj[0].identificador, (
        "Sprint 93f: hash deve incluir banco_origem para evitar colisão "
        "entre cartão PF do André (Nubank) e PJ da Vitória (Nubank (PJ))."
    )

    # Construir dicts no formato pós-normalizar (dedup espera _identificador)
    como_dict = lambda t: {  # noqa: E731
        "_identificador": t.identificador,
        "data": t.data,
        "valor": t.valor,
        "banco_origem": t.banco_origem,
        "local": t.descricao,
    }
    transacoes = [como_dict(tx_pf[0]), como_dict(tx_pj[0])]
    resultado = deduplicar_por_identificador(transacoes)
    assert len(resultado) == 2, (
        "Dedup nível 1 deve preservar ambas as tx (PF e PJ) quando identificadores diferem."
    )
    bancos_resultado = {t["banco_origem"] for t in resultado}
    assert bancos_resultado == {"Nubank", "Nubank (PJ)"}


# "A única auditoria que vale é aquela onde se olha o arquivo com os
# próprios olhos." -- princípio do validador minucioso
