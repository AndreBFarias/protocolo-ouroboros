"""Deduplicação de transações em múltiplos níveis."""

from src.transform.canonicalizer_casal import e_transferencia_do_casal
from src.utils.logger import configurar_logger

logger = configurar_logger("deduplicator")


def deduplicar_por_identificador(transacoes: list[dict]) -> list[dict]:
    """Nível 1: Remove duplicatas exatas por _identificador (UUID ou hash).

    Mantém a primeira ocorrência, descarta as demais.
    """
    vistos: dict[str, int] = {}
    resultado: list[dict] = []
    duplicatas = 0

    for t in transacoes:
        ident = t.get("_identificador")
        if ident is None:
            resultado.append(t)
            continue

        if ident in vistos:
            duplicatas += 1
            continue

        vistos[ident] = len(resultado)
        resultado.append(t)

    if duplicatas > 0:
        logger.info("Dedup nível 1 (identificador): %d duplicatas removidas", duplicatas)

    return resultado


def _normalizar_local_para_chave(local: str) -> str:
    """Sprint INFRA-DEDUP-C6-OFX-XLSX-AMPLO: normaliza `local` para dedup nível-2.

    Remove prefixo bancário até o primeiro ` - `, lowercase e strip. Cobre
    ingestão paralela C6 OFX + XLSX onde OFX traz `"RECEBIMENTO SALARIO - X"`
    e XLSX traz só `"X"`. Após normalização ambos casam pela mesma chave.

    Cuidado: a regra `split(" - ", 1)[-1]` é segura para pares legítimos
    porque, quando NÃO existe ` - ` no `local`, devolve a string inteira
    inalterada (mesma chave antiga). Pares legítimos como `"Pix enviado
    para X"` vs `"Pix recebido de Y"` continuam com locais distintos
    (apenas o lado da TI muda o nome do destinatário).
    """
    return str(local).split(" - ", 1)[-1].strip().lower()


def _riqueza_descricao(t: dict) -> int:
    """Heurística de qualidade: comprimento de `_descricao_original` ou `local`.

    Quando dois registros colidem, preserva o de descrição mais rica. Em
    C6, OFX traz prefixo `"RECEBIMENTO SALARIO - <conta>"` (mais informativo)
    e XLSX traz apenas `"<conta>"`. Manter a versão mais longa preserva
    informação para auditoria e relatórios.
    """
    desc = str(t.get("_descricao_original") or t.get("local") or "")
    return len(desc)


def _eh_arquivo_ofx(t: dict) -> bool:
    """Detecta se a transação veio de arquivo OFX pelo `_arquivo_origem`."""
    arq = str(t.get("_arquivo_origem") or "").lower()
    return arq.endswith(".ofx")


def _eh_arquivo_xlsx_csv(t: dict) -> bool:
    """Detecta se a transação veio de XLSX/CSV/XLS pelo `_arquivo_origem`."""
    arq = str(t.get("_arquivo_origem") or "").lower()
    return arq.endswith((".xlsx", ".xls", ".csv"))


def _consolidar_historico_com_real(transacoes: list[dict]) -> list[dict]:
    """Sprint INFRA-DEDUP-NIVEL-2-INCLUI-BANCO: pass nível-2a-pre.

    Quando a chave de dedup nível-2 passa a incluir `banco_origem`,
    transações com `banco_origem in (None, "", "Histórico")` deixam de
    consolidar com a versão re-extraída do banco real (que tem
    `banco_origem` definido). Esse pareamento é o caso de uso original do
    XLSX histórico do casal: cada linha sem fonte primária deve ser
    descartada quando o ETL atual reextrai o mesmo evento bancário.

    Esta pré-fase preserva o contrato antigo (padrão (o) retrocompat):
    para cada transação "histórica" (`banco_origem` ausente ou
    `"Histórico"`), se existir outra com mesmo `(data, valor,
    local_normalizado)` e `banco_origem` real (não-histórico), marca a
    histórica para remoção. Preferência: banco real ganha (metadados
    melhores, padrão já estabelecido pelo critério de `_riqueza_descricao`
    + `nao_historicos` em `deduplicar_por_hash_fuzzy`).

    Sem este pré-pass, testes regressivos
    `test_nivel2_prefere_nao_historico` e
    `test_deduplicar_orquestra_tres_niveis` quebrariam porque "Histórico"
    e "Nubank (PF)" caem em buckets distintos na chave 4-tuple.
    """
    def _chave_3tuple(t: dict) -> tuple:
        d = t["data"]
        data_str = d.isoformat() if hasattr(d, "isoformat") else str(d)
        local_norm = _normalizar_local_para_chave(t.get("local", ""))
        return (data_str, f"{abs(t['valor']):.2f}", local_norm)

    reais_por_chave: dict[tuple, int] = {}
    for idx, t in enumerate(transacoes):
        banco = t.get("banco_origem")
        if not banco or banco == "Histórico":
            continue
        if t.get("_virtual"):
            continue
        # Em colisão de bancos reais distintos (cross-bank), mantém o primeiro
        # como representante -- não importa qual, pois o pass principal vai
        # tratá-los em buckets separados depois desta pré-fase.
        reais_por_chave.setdefault(_chave_3tuple(t), idx)

    indices_remover: set[int] = set()
    for idx, t in enumerate(transacoes):
        banco = t.get("banco_origem")
        if banco and banco != "Histórico":
            continue
        if t.get("_virtual"):
            continue
        if _chave_3tuple(t) in reais_por_chave:
            indices_remover.add(idx)

    if not indices_remover:
        return transacoes

    logger.info(
        "Dedup nível 2a-pre (histórico com real): %d duplicatas removidas",
        len(indices_remover),
    )
    return [t for idx, t in enumerate(transacoes) if idx not in indices_remover]


def _consolidar_pares_ofx_xlsx_mesmo_banco(transacoes: list[dict]) -> list[dict]:
    """Sprint INFRA-DEDUP-C6-OFX-XLSX-AMPLO: pass nível-2b.

    Consolida pares onde mesma transação foi ingerida por OFX e XLSX/CSV
    do MESMO banco, mesmo `quem`, mesmo `(data, valor)` -- casos que o
    nível-2 com normalização de sufixo não pega porque o `local` é
    materialmente distinto (ex.: XLSX C6 truncado em `"TRANSF ENVIADA PIX"`
    vs OFX detalhado `"Pix enviado para X - TRANSF E"`).

    Critério de detecção (TODOS obrigatórios):
        - mesmo `(data, valor_abs, banco_origem, quem)`,
        - ambos `banco_origem` declarado (sem `None`/`""`/`Histórico`),
        - um veio de `.ofx` e outro veio de `.xlsx/.csv/.xls`,
        - nenhum é `_virtual`.

    Preserva a transação OFX (descrição mais rica). Risco controlado:
    pares legítimos entre bancos diferentes têm `banco_origem` distinto e
    NÃO entram aqui. Pares legítimos no MESMO banco/conta com mesmo valor
    e data são raros e quase sempre erro de duplicidade (cliente humano
    não envia 2 PIX idênticos no mesmo segundo).
    """
    grupos: dict[tuple, list[int]] = {}
    for idx, t in enumerate(transacoes):
        banco = t.get("banco_origem")
        if not banco or banco == "Histórico":
            continue
        if t.get("_virtual"):
            continue
        data_str = t["data"].isoformat() if hasattr(t["data"], "isoformat") else str(t["data"])
        chave = (data_str, f"{abs(t['valor']):.2f}", banco, t.get("quem"))
        grupos.setdefault(chave, []).append(idx)

    indices_remover: set[int] = set()
    for ids in grupos.values():
        if len(ids) < 2:
            continue
        ofx_ids = [i for i in ids if _eh_arquivo_ofx(transacoes[i])]
        xlsx_ids = [i for i in ids if _eh_arquivo_xlsx_csv(transacoes[i])]
        if not ofx_ids or not xlsx_ids:
            continue
        # Preserva OFX (descrição mais informativa); descarta XLSX/CSV
        # correspondente. Se houver múltiplos de cada, descarta todos os
        # XLSX (cenário raro: mesmo arquivo XLSX importado 2x já foi
        # consolidado pelo nível-2 normal).
        for i in xlsx_ids:
            indices_remover.add(i)

    if not indices_remover:
        return transacoes

    logger.info(
        "Dedup nível 2b (par OFX/XLSX mesmo banco): %d duplicatas removidas",
        len(indices_remover),
    )
    return [t for idx, t in enumerate(transacoes) if idx not in indices_remover]


def deduplicar_por_hash_fuzzy(transacoes: list[dict]) -> list[dict]:
    """Nível 2: Remove duplicatas por combinação data + valor + local_normalizado.

    Cobre três cenários reais:
    - Mesma transação em OFX e XLSX/CSV legacy do mesmo banco
    - Mesma transação no XLSX histórico (banco_origem="Histórico") e na
      re-extração atual do banco de origem
    - Transferência interna listada pelo OFX e pelo CSV do mesmo banco

    Sprint INFRA-DEDUP-C6-OFX-XLSX-AMPLO: o `local` usado na chave passa
    pela normalização `_normalizar_local_para_chave` que remove prefixo
    bancário antes do primeiro ` - ` (padrão OFX). Sem isso, 253 pares C6
    de pessoa_a (~510 linhas, ~43% do total) escapavam dedup por divergência
    de prefixo entre extratores `ofx_parser.py` (OFX) e `c6_cc.py` (XLSX).

    Após o pass principal, executa `_consolidar_pares_ofx_xlsx_mesmo_banco`
    para limpar pares residuais que não casam pelo `local` mas vêm
    inequivocamente do mesmo evento bancário (mesmo banco, mesma data,
    mesmo valor, mesmo `quem`, um arquivo OFX e outro XLSX/CSV).

    Quando múltiplas transações casam pela chave, preservação em ordem:
        1. NÃO `_virtual` (espelhos de cartão preservados sempre, ver 82b).
        2. `banco_origem != "Histórico"` (fonte com metadados melhores).
        3. Descrição mais rica (`_descricao_original` mais longa) -- preserva
           informação semântica do OFX (`"PIX ENVIADO - <NOME>"`) sobre
           sufixo truncado do XLSX (`"<NOME>"`). Critério introduzido por
           esta sprint.

    Pares LEGÍTIMOS de transferência interna (entre bancos diferentes) não
    colidem na chave, pois têm `local` materialmente distinto (nome do
    destinatário) -- a normalização preserva o conteúdo após ` - `, não
    apaga.

    Sprint INFRA-DEDUP-NIVEL-2-INCLUI-BANCO: a chave inclui `banco_origem`
    como quarta componente para impedir colisão cross-bank. Cenário real:
    PIX R$5000 no mesmo dia, Nubank "Recebimento Pix - X" vs C6 "X" -- após
    `_normalizar_local_para_chave` ambos viram `"x"` e, com chave 3-tuple,
    consolidavam erroneamente como mesma transação. Com `banco_origem` na
    chave, cross-bank fica em buckets distintos e pares legítimos cross-bank
    são preservados. Padrão (n): defesa em camadas (pré-fase 2a-pre +
    chave 4-tuple + pass 2b por banco_origem). Padrão (o): retrocompat --
    a pré-fase `_consolidar_historico_com_real` casa transações
    "Histórico"/`None` com a versão real ANTES desta fase, preservando o
    contrato antigo de consolidação histórico-com-reextração; em seguida
    a chave 4-tuple atua sobre o restante onde todos têm `banco_origem`
    definido (ou todos são histórico residual sem correspondente real,
    bucket `_sem_banco`).
    """
    transacoes = _consolidar_historico_com_real(transacoes)

    grupos: dict[str, list[int]] = {}

    for idx, t in enumerate(transacoes):
        data_str = t["data"].isoformat() if hasattr(t["data"], "isoformat") else str(t["data"])
        valor_str = f"{abs(t['valor']):.2f}"
        local_normalizado = _normalizar_local_para_chave(t.get("local", ""))
        banco_raw = t.get("banco_origem")
        banco_bucket = banco_raw if banco_raw and banco_raw != "Histórico" else "_sem_banco"
        chave = f"{data_str}|{valor_str}|{local_normalizado}|{banco_bucket}"
        grupos.setdefault(chave, []).append(idx)

    indices_remover: set[int] = set()
    for ids in grupos.values():
        if len(ids) <= 1:
            continue
        # Sprint 82b: espelho virtual de cartão tem razão de existir como
        # contraparte; se colide com saída real, PRESERVA AMBOS (dedup
        # clássico não se aplica a pares conta-espelho).
        tem_virtual = any(transacoes[i].get("_virtual") for i in ids)
        if tem_virtual:
            continue
        nao_historicos = [i for i in ids if transacoes[i].get("banco_origem") != "Histórico"]
        candidatos = nao_historicos if nao_historicos else ids
        # Entre candidatos elegíveis, preserva o de descrição mais rica
        # (Sprint INFRA-DEDUP-C6-OFX-XLSX-AMPLO). Em empate, o primeiro
        # (ordem de inserção) -- comportamento determinístico.
        preservar = max(candidatos, key=lambda i: (_riqueza_descricao(transacoes[i]), -i))
        for i in ids:
            if i != preservar:
                indices_remover.add(i)

    resultado: list[dict] = []
    for idx, t in enumerate(transacoes):
        if idx in indices_remover:
            continue
        resultado.append(t)

    if indices_remover:
        logger.info(
            "Dedup nível 2 (fuzzy por data+valor+local): %d duplicatas removidas",
            len(indices_remover),
        )

    # Pass 2b: consolidar pares OFX/XLSX mesmo banco que escapam ao 2a por
    # `local` materialmente distinto (descrição genérica XLSX vs detalhada OFX).
    resultado = _consolidar_pares_ofx_xlsx_mesmo_banco(resultado)

    return resultado


def _descricao_para_match(transacao: dict) -> str:
    """Extrai o melhor texto da transação para matching de identidade do casal.

    Prioriza `_descricao_original` (string crua do extrator) e cai para `local`
    quando a original não existe (histórico importado).
    """
    return str(transacao.get("_descricao_original") or transacao.get("local") or "")


def _parear_espelhos_virtuais(transacoes: list[dict]) -> int:
    """Sprint 82b: pareia espelho virtual (cartão) com saída real (CC).

    Extratores de cartão (c6_cartao, santander_pdf) emitem linha virtual
    com `_virtual=True` quando detectam pagamento de fatura recebido. A
    contraparte real é a saída no CC (mesma data, mesmo valor, outra
    conta) que já chega ao deduplicator com tipo="Transferência Interna"
    via regex operacional do extrator ou do pipeline. O pareamento clássico
    de `marcar_transferencias_internas` não cobre esse caso porque ambos
    os lados já são TI (nenhum é Despesa/None) e ambos têm pessoa="pessoa_a".

    Esta função apenas GARANTE que ambos os lados permanecem como TI e
    conta os pares encontrados (pelo menos um dos dois com `_virtual=True`
    + mesma data + mesmo valor absoluto, ignorando a identidade). Idempotente:
    não remove nem duplica linhas; só acumula estatística para log.
    """
    virtuais_por_chave: dict[str, list[int]] = {}
    reais_por_chave: dict[str, list[int]] = {}

    for idx, t in enumerate(transacoes):
        if t.get("tipo") != "Transferência Interna":
            continue
        data_str = t["data"].isoformat() if hasattr(t["data"], "isoformat") else str(t["data"])
        chave = f"{data_str}|{abs(t.get('valor', 0)):.2f}"
        if t.get("_virtual"):
            virtuais_por_chave.setdefault(chave, []).append(idx)
        else:
            reais_por_chave.setdefault(chave, []).append(idx)

    pares = 0
    for chave, idx_virtuais in virtuais_por_chave.items():
        idx_reais = reais_por_chave.get(chave)
        if not idx_reais:
            continue
        # Confirma que ambos os lados continuam TI -- ja deveriam estar.
        for i in idx_virtuais:
            transacoes[i]["tipo"] = "Transferência Interna"
        for i in idx_reais:
            transacoes[i]["tipo"] = "Transferência Interna"
        pares += min(len(idx_virtuais), len(idx_reais))

    return pares


def marcar_transferencias_internas(transacoes: list[dict]) -> list[dict]:
    """Nível 3: Identifica pares de transferência interna.

    Procura pares onde:
    - Saída de uma conta = Entrada em outra
    - Mesmo valor, mesma data
    - Entre contas da pessoa_a e da pessoa_b

    Para evitar falso-positivo (Sprint 68), exige que PELO MENOS UM lado
    do par contenha identidade do casal na descrição -- via
    `canonicalizer_casal.e_transferencia_do_casal`. Se nenhum dos dois
    lados bate com a whitelist, o par é ignorado (não vira TI).

    Marca ambos como Transferência Interna sem remover.

    Sprint 82b: pareia também espelhos virtuais de cartão (_virtual=True)
    com saídas reais no CC do mesmo valor/data -- via `_parear_espelhos_virtuais`.
    """
    pares_encontrados = 0

    entradas: dict[str, list[int]] = {}
    for i, t in enumerate(transacoes):
        if t.get("tipo") == "Receita" or (
            t.get("tipo") == "Transferência Interna" and t.get("valor", 0) > 0
        ):
            data_str = t["data"].isoformat() if hasattr(t["data"], "isoformat") else str(t["data"])
            chave = f"{data_str}|{abs(t['valor']):.2f}"
            entradas.setdefault(chave, []).append(i)

    for t in transacoes:
        if t.get("tipo") not in ("Despesa", None):
            continue

        data_str = t["data"].isoformat() if hasattr(t["data"], "isoformat") else str(t["data"])
        chave = f"{data_str}|{abs(t['valor']):.2f}"

        if chave not in entradas:
            continue

        for idx in entradas[chave]:
            entrada = transacoes[idx]
            if entrada.get("quem") == t.get("quem"):
                continue

            desc_saida = _descricao_para_match(t)
            desc_entrada = _descricao_para_match(entrada)
            if not (e_transferencia_do_casal(desc_saida) or e_transferencia_do_casal(desc_entrada)):
                continue

            t["tipo"] = "Transferência Interna"
            entrada["tipo"] = "Transferência Interna"
            pares_encontrados += 1
            break

    if pares_encontrados > 0:
        logger.info(
            "Dedup nível 3: %d pares de transferência interna identificados",
            pares_encontrados,
        )

    pares_virtuais = _parear_espelhos_virtuais(transacoes)
    if pares_virtuais > 0:
        logger.info(
            "Dedup nível 3 (Sprint 82b): %d pares espelho-virtual + saída-real confirmados",
            pares_virtuais,
        )

    return transacoes


def deduplicar(transacoes: list[dict]) -> list[dict]:
    """Executa todos os níveis de deduplicação em sequência."""
    logger.info("Iniciando deduplicação de %d transações", len(transacoes))

    resultado = deduplicar_por_identificador(transacoes)
    resultado = marcar_transferencias_internas(resultado)
    resultado = deduplicar_por_hash_fuzzy(resultado)

    logger.info("Deduplicação concluída: %d transações restantes", len(resultado))
    return resultado


# "A repetição é a mãe do aprendizado." -- Plutarco
