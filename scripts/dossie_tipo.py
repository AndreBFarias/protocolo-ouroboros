"""CLI canonica de auditoria por tipo documental -- ciclo de graduacao Opus -> ETL.

Implementa o ritual canonico descrito em `docs/CICLO_GRADUACAO_OPERACIONAL.md`.
Cada tipo documental tem um dossie persistente em `data/output/dossies/<tipo>/`
que acumula amostras, provas artesanais (Opus multimodal), comparacoes ETL e
divergencias. O dashboard `src/dashboard/paginas/graduacao_tipos.py` consome
`data/output/graduacao_tipos.json` que este script mantem atualizado.

Subcomandos
-----------

- `--abrir TIPO`: imprime estado atual do dossie.
- `--listar-candidatos TIPO`: lista arquivos em inbox/ ou data/raw que parecem do tipo.
- `--prova-artesanal TIPO SHA256`: cria stub JSON para o supervisor preencher.
- `--comparar TIPO SHA256`: confronta prova artesanal com output do ETL.
- `--graduar-se-pronto TIPO`: avalia se tipo deve passar a GRADUADO.
- `--snapshot`: regenera `data/output/graduacao_tipos.json` global.
- `--listar-tipos`: lista todos os tipos canonicos do projeto.

Veredito de `--comparar`
------------------------

- `GRADUADO_OK`: prova bate ETL dentro da tolerancia por campo.
- `DIVERGENTE`: ao menos 1 campo critico diverge; gera relatorio MD.  # noqa: accent
- `INSUFICIENTE`: amostra inadequada (OCR ruim, tipo errado, dados ausentes).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constantes canonicas
# ---------------------------------------------------------------------------

_RAIZ_REPO: Path = Path(__file__).resolve().parents[1]
DIR_DOSSIES: Path = _RAIZ_REPO / "data" / "output" / "dossies"
DIR_OPUS_CACHE: Path = _RAIZ_REPO / "data" / "output" / "opus_ocr_cache"
PATH_GRAFO: Path = _RAIZ_REPO / "data" / "output" / "grafo.sqlite"
PATH_GRADUACAO: Path = _RAIZ_REPO / "data" / "output" / "graduacao_tipos.json"
PATH_TIPOS_YAML: Path = _RAIZ_REPO / "mappings" / "tipos_documento.yaml"

# Tolerancias por tipo de campo
TOLERANCIA_NUMERICA: float = 0.01  # 1 centavo
TOLERANCIA_DATA_DIAS: int = 0  # data deve bater exato

STATUS_PENDENTE: str = "PENDENTE"
STATUS_CALIBRANDO: str = "CALIBRANDO"
STATUS_GRADUADO: str = "GRADUADO"
STATUS_REGREDINDO: str = "REGREDINDO"

# Amostras minimas para graduar
MINIMO_AMOSTRAS_GRADUACAO: int = 2


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dir_tipo(tipo: str) -> Path:
    return DIR_DOSSIES / tipo


def _garantir_estrutura_dossie(tipo: str) -> Path:
    """Cria estrutura inicial do dossie se não existe. Idempotente."""  # noqa: accent
    d = _dir_tipo(tipo)
    for sub in ("amostras", "provas_artesanais", "comparacoes", "divergencias"):
        (d / sub).mkdir(parents=True, exist_ok=True)
    readme = d / "README.md"
    if not readme.exists():
        readme.write_text(
            f"# Dossie do tipo `{tipo}`\n\n"
            f"Criado em {_agora_iso()} pelo `scripts/dossie_tipo.py`.\n\n"
            f"Estrutura canonica (ver `docs/CICLO_GRADUACAO_OPERACIONAL.md`):\n\n"
            "- `estado.json`: status do tipo + historico de eventos\n"
            "- `amostras/<sha256>.json`: metadata de cada amostra\n"
            "- `provas_artesanais/<sha256>.json`: gabarito Opus multimodal\n"
            "- `comparacoes/<sha256>_<ts>.json`: resultado de cada rodada\n"
            "- `divergencias/<sha256>_<ts>.md`: rel. quando ETL diverge\n"  # noqa: accent
            "- `sprint_filhas.md`: log de sprints geradas a partir deste tipo\n",
            encoding="utf-8",
        )
    estado = d / "estado.json"
    if not estado.exists():
        estado.write_text(
            json.dumps(
                {
                    "tipo": tipo,
                    "status": STATUS_PENDENTE,
                    "amostras_ok": [],
                    "divergencias_ativas": [],
                    "_historico_divergencias": [],
                    "criado_em": _agora_iso(),
                    "atualizado_em": _agora_iso(),
                    "historico": [],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    return d


def _migrar_estado_schema(estado: dict) -> dict:
    """Migra estado legado (`amostras_divergentes` acumulativo) para schema novo.

    Idempotente: roda multiplas vezes sem mudanca apos primeira migracao.

    Semantica nova (Sprint FIX-REGREDINDO-SEMANTICA):

    - `amostras_ok`: hashes que estao verdes AGORA.
    - `divergencias_ativas`: hashes que divergem AGORA (esvazia ao revalidar OK).
    - `_historico_divergencias`: hashes que ja divergiram em algum momento (acumula sempre).

    Migração do legado: `amostras_divergentes` (acumulava) vira `_historico_divergencias`;
    `divergencias_ativas` recebe apenas os hashes que NÃO foram revalidados OK depois
    (interseção `amostras_divergentes - amostras_ok`).
    """  # noqa: accent
    if "divergencias_ativas" in estado and "_historico_divergencias" in estado:
        return estado
    legado = estado.pop("amostras_divergentes", [])
    estado["_historico_divergencias"] = list(legado)
    set_ok = set(estado.get("amostras_ok", []))
    estado["divergencias_ativas"] = [h for h in legado if h not in set_ok]
    return estado


def _ler_estado(tipo: str) -> dict:
    estado = json.loads((_dir_tipo(tipo) / "estado.json").read_text(encoding="utf-8"))
    return _migrar_estado_schema(estado)


def _gravar_estado(tipo: str, estado: dict) -> None:
    estado["atualizado_em"] = _agora_iso()
    (_dir_tipo(tipo) / "estado.json").write_text(
        json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _registrar_evento(estado: dict, mensagem: str) -> None:
    estado.setdefault("historico", []).append(
        {"ts": _agora_iso(), "mensagem": mensagem}
    )


def _calcular_sha256(caminho: Path) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


def _tipos_canonicos() -> list[str]:
    """Lista tipos canonicos a partir de mappings/tipos_documento.yaml."""
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        return []
    if not PATH_TIPOS_YAML.exists():
        return []
    dados = yaml.safe_load(PATH_TIPOS_YAML.read_text(encoding="utf-8")) or {}
    tipos = dados.get("tipos") or []
    return [t["id"] for t in tipos if t.get("id")]


# ---------------------------------------------------------------------------
# Subcomando: abrir
# ---------------------------------------------------------------------------


def cmd_abrir(tipo: str) -> int:
    _garantir_estrutura_dossie(tipo)
    estado = _ler_estado(tipo)
    _gravar_estado(tipo, estado)  # persiste migracao se legado  # noqa: accent
    ativas = estado.get("divergencias_ativas", [])
    historico = estado.get("_historico_divergencias", [])
    print(f"=== Dossie {tipo} ===")
    print(f"Status:               {estado['status']}")
    print(f"Amostras OK:          {len(estado['amostras_ok'])} {estado['amostras_ok']}")
    print(f"Divergencias ativas:  {len(ativas)} {ativas}")
    print(f"Historico divergencias (acumulado): {len(historico)}")
    print(f"Criado em:            {estado.get('criado_em', '?')}")
    print(f"Atualizado em:        {estado.get('atualizado_em', '?')}")
    print(f"Localizacao:          {_dir_tipo(tipo)}")
    print("\nHistorico (ultimos 5 eventos):")
    for ev in (estado.get("historico") or [])[-5:]:
        print(f"  [{ev['ts']}] {ev['mensagem']}")
    return 0


# ---------------------------------------------------------------------------
# Subcomando: listar-candidatos
# ---------------------------------------------------------------------------


# Mapa explicito de palavras-chave por tipo. Tipos nao listados caem no default  # noqa: accent
# (split("_")[0]) por retrocompatibilidade. Quando criar tipo novo, adicione  # noqa: accent
# entrada aqui (padrao (n) -- defesa em camadas).
CHAVES_BUSCA: dict[str, list[str]] = {
    "comprovante_pix_foto": ["pix", "comprovante_pix", "whatsapp image"],
    "cupom_fiscal_foto": ["cupom", "nfce_n", "ncfe"],
    "holerite": ["holerite", "contracheque", "pagamento"],
    "das_parcsn": ["das_parcsn", "das ", "parcsn"],
    "das_mei": ["das_mei", "darf_mei", "mei_das"],
    "nfce_modelo_65": ["nfce", "nf_consumidor"],
    "boleto_servico": ["boleto", "bol_"],
    "fatura_cartao": ["fatura", "_cartao", "cartao_"],
    "extrato_bancario": ["extrato", "_cc_", "bancario"],
    "cupom_garantia_estendida": ["garantia_est", "garantia est"],
    "certidao_receita_cnpj": ["certidao", "cert_rf", "cnpj"],
    "comprovante_cpf": ["comprovante_cpf", "cpf_cad"],
    "irpf_parcela": ["darf", "irpf_parcela", "irpf-parcela"],
    "conta_luz": ["conta_luz", "neoenergia", "ceb_", "energia_"],
    "conta_agua": ["conta_agua", "caesb", "agua_"],
    "receita_medica": ["receita_med", "receita medica", "prescricao"],
    "garantia_fabricante": ["garantia_fab", "manual"],
    "contrato": ["contrato"],
    "danfe_nfe55": ["danfe", "nfe55", "nf55"],
    "xml_nfe": ["xmlnfe", "xml_nfe"],
    "extrato_c6_pdf": ["extrato_c6", "c6_cc"],
    "recibo_nao_fiscal": ["recibo"],
    "dirpf_retif": ["dirpf", "irpf-a", "irpf_a", "-irpf-"],
}


def cmd_listar_candidatos(tipo: str) -> int:
    """Heuristica: nome ou pasta contem alguma chave do mapa CHAVES_BUSCA do tipo."""
    inbox = _RAIZ_REPO / "inbox"
    raw = _RAIZ_REPO / "data" / "raw"
    encontrados: list[Path] = []
    chaves = CHAVES_BUSCA.get(tipo, [tipo.lower().split("_")[0]])
    for base in (inbox, raw):
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if not p.is_file():
                continue
            if p.suffix.lower() not in (".jpg", ".jpeg", ".png", ".pdf", ".heic"):
                continue
            caminho_lower = str(p).lower()
            nome_lower = p.name.lower()
            if any(c in caminho_lower or c in nome_lower for c in chaves):
                encontrados.append(p)
    print(f"Candidatos para tipo `{tipo}` (chaves={chaves}): {len(encontrados)}")
    for p in encontrados[:20]:
        sha = _calcular_sha256(p)[:12]
        print(f"  {sha}  {p.relative_to(_RAIZ_REPO)}")
    return 0


# ---------------------------------------------------------------------------
# Subcomando: prova-artesanal (stub interativo)
# ---------------------------------------------------------------------------


def cmd_prova_artesanal(tipo: str, sha256: str) -> int:
    """Cria template JSON da prova artesanal para o supervisor preencher.

    Nao chama o modelo automaticamente -- o ritual exige que o supervisor  # noqa: accent
    leia a imagem via Read multimodal e edite o JSON manualmente.
    """
    _garantir_estrutura_dossie(tipo)
    destino = _dir_tipo(tipo) / "provas_artesanais" / f"{sha256}.json"
    if destino.exists():
        print(f"Prova ja existe em {destino} -- não sobrescrevo.")  # noqa: accent
        print("Para refazer, delete o arquivo e re-rode o comando.")
        return 1

    template = {
        "sha256": sha256,
        "tipo": tipo,
        "lido_por": "opus_4_7_multimodal",
        "lido_em": _agora_iso(),
        "_instrucao": (
            "Supervisor: leia a imagem/PDF original via Read multimodal e "
            "preencha campos_canonicos conforme o schema do tipo. Salve este "
            "arquivo. Depois rode `--comparar` para confrontar com ETL."
        ),
        "campos_canonicos": {
            "PREENCHER": "valores que voce leu da imagem com seus olhos"
        },
        "_notas_supervisor": "",
    }
    destino.write_text(
        json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Stub criado em {destino}")
    print("Edite o arquivo preenchendo `campos_canonicos`, depois rode --comparar.")
    return 0


# ---------------------------------------------------------------------------
# Subcomando: comparar
# ---------------------------------------------------------------------------


def _carregar_etl_output(sha256: str) -> dict | None:
    """Tenta carregar o output do ETL para a amostra: prefere grafo, fallback cache."""
    # 1) Tentar cache Opus OCR (mais rico em campos)
    cache = DIR_OPUS_CACHE / f"{sha256}.json"
    if cache.exists():
        try:
            return json.loads(cache.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    # 2) Tentar grafo SQLite (no documento com chave contendo sha256). Schema  # noqa: accent
    # real da tabela `node`: id, tipo, nome_canonico, aliases, metadata,  # noqa: accent
    # created_at, updated_at. Defesa em camadas (padrao (n)): busca em  # noqa: accent
    # nome_canonico E metadata.  # noqa: accent
    if PATH_GRAFO.exists():
        con = sqlite3.connect(PATH_GRAFO)
        try:
            cur = con.execute(
                "SELECT metadata FROM node WHERE tipo='documento' "
                "AND (nome_canonico LIKE ? OR metadata LIKE ?)",
                (f"%{sha256}%", f"%{sha256}%"),
            )
            row = cur.fetchone()
            if row and row[0]:
                meta = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                return {"_fonte": "grafo", **meta}
        finally:
            con.close()
    return None


def _comparar_dicts(
    prova: dict, etl: dict, prefixo: str = ""
) -> list[dict[str, Any]]:
    """Diff campo-a-campo entre prova artesanal e output do ETL.

    Retorna lista de divergencias com {campo, esperado, obtido, tipo_divergencia}.
    """
    divergencias: list[dict[str, Any]] = []
    for chave, esperado in prova.items():
        if chave.startswith("_"):
            continue
        caminho = f"{prefixo}{chave}" if not prefixo else f"{prefixo}.{chave}"
        if chave not in etl:
            divergencias.append(
                {
                    "campo": caminho,
                    "esperado": esperado,
                    "obtido": None,
                    "tipo": "ausente_no_etl",
                }
            )
            continue
        obtido = etl[chave]
        # Numeros: tolerancia  # noqa: accent
        if isinstance(esperado, (int, float)) and isinstance(obtido, (int, float)):
            if abs(float(esperado) - float(obtido)) > TOLERANCIA_NUMERICA:
                divergencias.append(
                    {
                        "campo": caminho,
                        "esperado": esperado,
                        "obtido": obtido,
                        "tipo": "valor_diverge",
                    }
                )
        # Strings: case-insensitive + strip
        elif isinstance(esperado, str) and isinstance(obtido, str):
            if esperado.strip().lower() != obtido.strip().lower():
                divergencias.append(
                    {
                        "campo": caminho,
                        "esperado": esperado,
                        "obtido": obtido,
                        "tipo": "string_diverge",
                    }
                )
        # Dicts recursivos
        elif isinstance(esperado, dict) and isinstance(obtido, dict):
            divergencias.extend(_comparar_dicts(esperado, obtido, prefixo=caminho))
        # Listas: comparar tamanho (detalhe item-a-item ficaria pesado)
        elif isinstance(esperado, list) and isinstance(obtido, list):
            if len(esperado) != len(obtido):
                divergencias.append(
                    {
                        "campo": caminho,
                        "esperado": f"len={len(esperado)}",
                        "obtido": f"len={len(obtido)}",
                        "tipo": "lista_tamanho_diverge",
                    }
                )
        # Tipos diferentes
        elif esperado != obtido:
            divergencias.append(
                {
                    "campo": caminho,
                    "esperado": esperado,
                    "obtido": obtido,
                    "tipo": "valor_diverge",
                }
            )
    return divergencias


def cmd_comparar(tipo: str, sha256: str) -> int:
    """Veredito: GRADUADO_OK / DIVERGENTE / INSUFICIENTE."""
    _garantir_estrutura_dossie(tipo)
    prova_path = _dir_tipo(tipo) / "provas_artesanais" / f"{sha256}.json"
    if not prova_path.exists():
        print(f"ERRO: prova artesanal ausente em {prova_path}")
        print(f"Rode: dossie_tipo.py --prova-artesanal {tipo} {sha256}")
        return 2

    prova = json.loads(prova_path.read_text(encoding="utf-8"))
    if prova.get("campos_canonicos", {}).get("PREENCHER"):
        print("ERRO: prova ainda contem placeholder PREENCHER. Edite antes.")
        return 2

    etl = _carregar_etl_output(sha256)
    if etl is None:
        veredito = "INSUFICIENTE"
        divergencias: list = []
        print(f"INSUFICIENTE: ETL ainda não processou sha {sha256[:12]}.")  # noqa: accent
        print("Rode `./run.sh --tudo` e tente de novo.")
    else:
        # Compara apenas o sub-dict campos_canonicos contra o root do ETL
        prova_dados = prova.get("campos_canonicos", {})
        divergencias = _comparar_dicts(prova_dados, etl)
        if not divergencias:
            veredito = "GRADUADO_OK"
            print(f"GRADUADO_OK: prova e ETL concordam para {sha256[:12]}.")
        else:
            veredito = "DIVERGENTE"
            print(f"DIVERGENTE: {len(divergencias)} campo(s) divergem.")
            for d in divergencias[:10]:
                print(f"  - {d['campo']}: esperado={d['esperado']!r} obtido={d['obtido']!r}")

    # Persistir resultado
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rel = _dir_tipo(tipo) / "comparacoes" / f"{sha256}_{ts}.json"
    rel.write_text(
        json.dumps(
            {
                "sha256": sha256,
                "tipo": tipo,
                "veredito": veredito,
                "comparado_em": _agora_iso(),
                "divergencias": divergencias,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    if veredito == "DIVERGENTE":
        # Gera relatorio MD humanizado  # noqa: accent
        md = _dir_tipo(tipo) / "divergencias" / f"{sha256}_{ts}.md"
        linhas = [
            f"# Divergencia {tipo} -- {sha256[:12]}",
            "",
            f"Comparado em: {_agora_iso()}",
            f"Total de divergencias: {len(divergencias)}",
            "",
            "## Campos divergentes",
            "",
            "| Campo | Esperado (Opus) | Obtido (ETL) | Tipo |",
            "|---|---|---|---|",
        ]
        for d in divergencias:
            linhas.append(
                f"| `{d['campo']}` | `{d['esperado']!r}` | `{d['obtido']!r}` | "
                f"{d['tipo']} |"
            )
        linhas.append("")
        linhas.append("## Acao sugerida")
        linhas.append("")
        linhas.append(
            "Registrar sprint-filha no Epico 1 do ROADMAP com brief de correcao "
            "do extrator. Executor recebe link para este arquivo + diff acima."
        )
        md.write_text("\n".join(linhas), encoding="utf-8")
        print(f"\nRelatorio detalhado em {md}")

    # Atualizar estado com semantica nova (FIX-REGREDINDO-SEMANTICA).  # noqa: accent
    estado = _ler_estado(tipo)
    if veredito == "GRADUADO_OK":
        if sha256 not in estado["amostras_ok"]:
            estado["amostras_ok"].append(sha256)
            _registrar_evento(estado, f"amostra {sha256[:12]} validada OK")
        # Revalidar OK retira de divergencias_ativas mas preserva historico.  # noqa: accent
        if sha256 in estado.get("divergencias_ativas", []):
            estado["divergencias_ativas"].remove(sha256)
            _registrar_evento(estado, f"amostra {sha256[:12]} saiu de divergencias_ativas")
    elif veredito == "DIVERGENTE":
        if sha256 not in estado.get("divergencias_ativas", []):
            estado.setdefault("divergencias_ativas", []).append(sha256)
            _registrar_evento(estado, f"amostra {sha256[:12]} divergiu")
        if sha256 not in estado.get("_historico_divergencias", []):
            estado.setdefault("_historico_divergencias", []).append(sha256)
        # Amostra que diverge agora nao pode estar em amostras_ok.  # noqa: accent
        if sha256 in estado.get("amostras_ok", []):
            estado["amostras_ok"].remove(sha256)
            _registrar_evento(estado, f"amostra {sha256[:12]} saiu de amostras_ok")
    _gravar_estado(tipo, estado)

    return 0 if veredito == "GRADUADO_OK" else 1


# ---------------------------------------------------------------------------
# Subcomando: graduar-se-pronto
# ---------------------------------------------------------------------------


def cmd_graduar_se_pronto(tipo: str) -> int:
    _garantir_estrutura_dossie(tipo)
    estado = _ler_estado(tipo)
    n_ok = len(estado["amostras_ok"])
    status_antes = estado["status"]
    if n_ok >= MINIMO_AMOSTRAS_GRADUACAO:
        novo = STATUS_GRADUADO
    elif n_ok == 1:
        novo = STATUS_CALIBRANDO
    else:
        novo = STATUS_PENDENTE
    # REGREDINDO: graduacao tecnica satisfeita (n_ok >= 2) MAS ha divergencias  # noqa: accent
    # ativas nao-revalidadas. Detecta inclusive na primeira transicao para  # noqa: accent
    # GRADUADO. Histórico (`_historico_divergencias`) não influencia.
    if novo == STATUS_GRADUADO and estado.get("divergencias_ativas"):
        novo = STATUS_REGREDINDO

    estado["status"] = novo
    if novo != status_antes:
        _registrar_evento(estado, f"transicao {status_antes} -> {novo}")
    _gravar_estado(tipo, estado)
    print(f"Tipo {tipo}: {status_antes} -> {novo} (amostras OK: {n_ok})")
    cmd_snapshot()
    return 0


# ---------------------------------------------------------------------------
# Subcomando: snapshot
# ---------------------------------------------------------------------------


def cmd_snapshot() -> int:
    """Regenera data/output/graduacao_tipos.json agregando todos os dossies."""
    if not DIR_DOSSIES.exists():
        DIR_DOSSIES.mkdir(parents=True, exist_ok=True)
    agregado: dict[str, Any] = {
        "gerado_em": _agora_iso(),
        "tipos": {},
        "totais": {
            STATUS_PENDENTE: 0,
            STATUS_CALIBRANDO: 0,
            STATUS_GRADUADO: 0,
            STATUS_REGREDINDO: 0,
        },
    }
    for d in sorted(DIR_DOSSIES.glob("*")):
        if not d.is_dir():
            continue
        estado_path = d / "estado.json"
        if not estado_path.exists():
            continue
        # Migrador idempotente persiste schema novo nos dossies legados.  # noqa: accent
        estado = _migrar_estado_schema(
            json.loads(estado_path.read_text(encoding="utf-8"))
        )
        estado_path.write_text(
            json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        status = estado.get("status", STATUS_PENDENTE)
        agregado["tipos"][d.name] = {
            "status": status,
            "amostras_ok": len(estado.get("amostras_ok", [])),
            "divergencias_ativas": len(estado.get("divergencias_ativas", [])),
            "historico_divergencias_count": len(estado.get("_historico_divergencias", [])),
            "atualizado_em": estado.get("atualizado_em"),
        }
        agregado["totais"][status] = agregado["totais"].get(status, 0) + 1

    PATH_GRADUACAO.write_text(
        json.dumps(agregado, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f"Snapshot: {PATH_GRADUACAO} (GRADUADOS: {agregado['totais'][STATUS_GRADUADO]}, "
        f"CALIBRANDO: {agregado['totais'][STATUS_CALIBRANDO]}, "
        f"PENDENTE: {agregado['totais'][STATUS_PENDENTE]})"
    )
    return 0


# ---------------------------------------------------------------------------
# Subcomando: listar-tipos
# ---------------------------------------------------------------------------


def cmd_listar_tipos() -> int:
    tipos = _tipos_canonicos()
    print(f"Tipos canonicos em mappings/tipos_documento.yaml: {len(tipos)}")
    for t in tipos:
        d = _dir_tipo(t)
        marca = "+" if d.exists() else " "
        print(f"  {marca} {t}")
    print("\n+ = dossie existe; vazio = pendente de criar via --abrir")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Auditoria por tipo documental -- ciclo Opus/ETL graduacao"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_abrir = sub.add_parser("abrir", help="estado do dossie do tipo")
    p_abrir.add_argument("tipo")

    p_lc = sub.add_parser("listar-candidatos", help="arquivos candidatos do tipo")
    p_lc.add_argument("tipo")

    p_pa = sub.add_parser("prova-artesanal", help="stub para supervisor preencher")
    p_pa.add_argument("tipo")
    p_pa.add_argument("sha256")

    p_cmp = sub.add_parser("comparar", help="confronto prova × ETL")
    p_cmp.add_argument("tipo")
    p_cmp.add_argument("sha256")

    p_gr = sub.add_parser(
        "graduar-se-pronto", help="avalia transicao de status do tipo"
    )
    p_gr.add_argument("tipo")

    sub.add_parser("snapshot", help="regenera graduacao_tipos.json global")
    sub.add_parser("listar-tipos", help="lista tipos canonicos")

    # Tambem aceita flags --xxx (sintaxe alternativa) para retrocompat com o doc  # noqa: accent
    parser.add_argument("--abrir", dest="flag_abrir", help=argparse.SUPPRESS)
    parser.add_argument(
        "--listar-candidatos", dest="flag_listar_cand", help=argparse.SUPPRESS
    )
    parser.add_argument(
        "--listar-tipos",
        dest="flag_listar_tipos",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--snapshot",
        dest="flag_snapshot",
        action="store_true",
        help=argparse.SUPPRESS,
    )

    if argv is None:
        argv = sys.argv[1:]

    # Suporte alternativo a flags estilo --abrir TIPO
    if argv and argv[0].startswith("--"):
        flag = argv[0][2:]
        if flag == "abrir" and len(argv) >= 2:
            return cmd_abrir(argv[1])
        if flag == "listar-candidatos" and len(argv) >= 2:
            return cmd_listar_candidatos(argv[1])
        if flag == "prova-artesanal" and len(argv) >= 3:
            return cmd_prova_artesanal(argv[1], argv[2])
        if flag == "comparar" and len(argv) >= 3:
            return cmd_comparar(argv[1], argv[2])
        if flag == "graduar-se-pronto" and len(argv) >= 2:
            return cmd_graduar_se_pronto(argv[1])
        if flag == "snapshot":
            return cmd_snapshot()
        if flag == "listar-tipos":
            return cmd_listar_tipos()

    args = parser.parse_args(argv)

    if args.cmd == "abrir":
        return cmd_abrir(args.tipo)
    if args.cmd == "listar-candidatos":
        return cmd_listar_candidatos(args.tipo)
    if args.cmd == "prova-artesanal":
        return cmd_prova_artesanal(args.tipo, args.sha256)
    if args.cmd == "comparar":
        return cmd_comparar(args.tipo, args.sha256)
    if args.cmd == "graduar-se-pronto":
        return cmd_graduar_se_pronto(args.tipo)
    if args.cmd == "snapshot":
        return cmd_snapshot()
    if args.cmd == "listar-tipos":
        return cmd_listar_tipos()
    return 1


if __name__ == "__main__":
    sys.exit(main())


# "Dossie e memoria longa do artesao; sem ele, trabalho vira gambiarra." -- dossie vivo
