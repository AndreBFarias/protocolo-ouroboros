"""CLI -- auditoria estrutural do vault Ouroboros (read-only).

Sprint MOB-audit-estrutura-vault-md.

Percorre ``~/Protocolo-Ouroboros/inbox/`` (Syncthing compartilhado entre
backend Python e app mobile Protocolo-Mob-Ouroboros) e fiscaliza:

1. **Estrutura canônica**: cada arquivo em ``inbox/<area>/<subtipo>/``,
   com área e subtipo do mapping ``mappings/areas_subtipos.yaml``.
2. **Filename regex**: ``YYYY-MM-DD-HHmmss[-slug].<ext>``.
3. **Frontmatter YAML** do ``.md`` companion: campos obrigatórios
   ``_schema_version=1``, ``tipo=inbox_arquivo``, ``area``, ``subtipo``,
   ``arquivo``, ``revisar``.
4. **Companion presente**: cada binário (jpg/png/pdf/m4a/...) tem um
   ``.md`` ao lado com mesmo basename. ``.md`` órfão (sem binário) também
   é violação.

Read-only por design (ADR Syncthing): não modifica arquivos do vault. Só
relata. Correção é manual (ou sprint-filha de remediação).

Saídas:

* Relatório markdown em ``docs/auditorias/AUDITORIA_VAULT_MD_<data>.md``
  (path customizável via ``--relatorio``).
* Exit code: 0 vault limpo / 1 vault com violações.

Uso:

.. code-block:: bash

    .venv/bin/python scripts/audit_vault_md.py
    .venv/bin/python scripts/audit_vault_md.py --vault-path /tmp/vault_teste
    .venv/bin/python scripts/audit_vault_md.py --exit-zero-mesmo-com-violacao

PII: paths reais do vault podem conter nomes próprios. Este script imprime
basenames e paths relativos no relatório; o caller decide se compartilha.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import yaml

_RAIZ_REPO: Path = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_RAIZ_REPO))

# Regex canônico de filename: YYYY-MM-DD-HHmmss[-slug].<ext>
FILENAME_REGEX: re.Pattern[str] = re.compile(
    r"^\d{4}-\d{2}-\d{2}-\d{6}(-[a-z0-9-]+)?\.[a-z0-9]+$"
)

# Extensões consideradas binários elegíveis a companion .md.
EXTENSOES_BINARIAS: frozenset[str] = frozenset(
    {".jpg", ".jpeg", ".png", ".pdf", ".m4a", ".mp3", ".webp", ".heic"}
)

# Campos obrigatórios do frontmatter do .md companion. Sincronizado com
# src/lib/schemas/inbox_arquivo.ts do app mobile.
FRONTMATTER_OBRIGATORIOS: tuple[str, ...] = (
    "_schema_version",
    "tipo",
    "area",
    "subtipo",
    "arquivo",
    "revisar",
)

# Valor canônico do tipo no app mobile (constante de frontmatter.ts).
TIPO_INBOX_ARQUIVO: str = "inbox_arquivo"


@dataclass
class Violacao:
    """Uma violação detectada na auditoria.

    Categorias: ``estrutura``, ``filename``, ``frontmatter``, ``companion``.
    """

    categoria: str
    path: str
    detalhe: str


@dataclass
class Relatorio:
    """Resultado agregado de uma execução do auditor."""

    vault: Path
    total_arquivos: int = 0
    total_companions: int = 0
    total_binarios: int = 0
    violacoes: list[Violacao] = field(default_factory=list)

    @property
    def conformes(self) -> int:
        """Número de arquivos sem nenhuma violação registrada."""
        paths_violados: set[str] = {v.path for v in self.violacoes}
        return self.total_arquivos - len(paths_violados)

    def adicionar(self, categoria: str, path: str, detalhe: str) -> None:
        self.violacoes.append(Violacao(categoria, path, detalhe))


def carregar_mapping(path_mapping: Path) -> dict[str, list[str]]:
    """Carrega ``mappings/areas_subtipos.yaml`` canônico."""
    with path_mapping.open("r", encoding="utf-8") as fh:
        dados = yaml.safe_load(fh)
    if not isinstance(dados, dict):
        raise ValueError(
            f"mapping inválido em {path_mapping}: raiz precisa ser dict de áreas"
        )
    return {area: list(subtipos) for area, subtipos in dados.items()}


def extrair_frontmatter(texto: str) -> dict[str, object] | None:
    """Extrai bloco YAML entre ``---`` no topo do arquivo .md.

    Retorna ``None`` se não houver frontmatter ou se ele estiver malformado.
    """
    linhas = texto.splitlines()
    if not linhas or linhas[0].strip() != "---":
        return None
    fim: int | None = None
    for indice in range(1, len(linhas)):
        if linhas[indice].strip() == "---":
            fim = indice
            break
    if fim is None:
        return None
    bloco = "\n".join(linhas[1:fim])
    try:
        dados = yaml.safe_load(bloco)
    except yaml.YAMLError:
        return None
    return dados if isinstance(dados, dict) else None


class AuditorVault:
    """Percorre o vault e produz um relatório agregado."""

    def __init__(
        self,
        vault: Path,
        mapping_areas_subtipos: dict[str, list[str]],
    ) -> None:
        self.vault = vault
        self.mapping = mapping_areas_subtipos
        self.relatorio = Relatorio(vault=vault)

    def executar(self) -> Relatorio:
        """Roda todas as 4 categorias de check sobre ``vault/inbox/``."""
        inbox = self.vault / "inbox"
        if not inbox.exists():
            self.relatorio.adicionar(
                "estrutura",
                str(inbox),
                "pasta inbox/ inexistente no vault",
            )
            return self.relatorio

        # Coleta todos os arquivos sob inbox/ (recursivo).
        arquivos: list[Path] = [p for p in inbox.rglob("*") if p.is_file()]
        self.relatorio.total_arquivos = len(arquivos)

        for arquivo in arquivos:
            self._verificar_estrutura(arquivo, inbox)
            self._verificar_filename(arquivo)

        self._verificar_frontmatters(arquivos)
        self._verificar_companions(arquivos)

        return self.relatorio

    def _path_relativo(self, arquivo: Path) -> str:
        try:
            return str(arquivo.relative_to(self.vault))
        except ValueError:
            return str(arquivo)

    def _verificar_estrutura(self, arquivo: Path, inbox: Path) -> None:
        """Valida que o arquivo está em ``inbox/<area>/<subtipo>/`` canônica.

        Exceção da regra: área ``outros`` aceita tanto ``inbox/outros/`` quanto
        ``inbox/outros/outro/`` (espelha o folder declarado pelo app, que
        omite o subtipo quando ele é único).
        """
        try:
            rel = arquivo.relative_to(inbox)
        except ValueError:
            self.relatorio.adicionar(
                "estrutura",
                self._path_relativo(arquivo),
                "arquivo fora de inbox/",
            )
            return

        partes = rel.parts
        # Esperado: <area>/<subtipo>/<filename> (3 partes) OU para outros,
        # <area>/<filename> (2 partes) também aceito.
        if len(partes) < 2:
            self.relatorio.adicionar(
                "estrutura",
                self._path_relativo(arquivo),
                "arquivo solto na raiz de inbox/ (esperado inbox/<area>/<subtipo>/)",
            )
            return

        area = partes[0]
        if area not in self.mapping:
            self.relatorio.adicionar(
                "estrutura",
                self._path_relativo(arquivo),
                f"área '{area}' fora do mapping canônico {sorted(self.mapping)}",
            )
            return

        # outros aceita 2 ou 3 partes; demais áreas exigem 3 (com subtipo).
        if area == "outros" and len(partes) == 2:
            return
        if len(partes) < 3:
            self.relatorio.adicionar(
                "estrutura",
                self._path_relativo(arquivo),
                f"arquivo em inbox/{area}/ sem subpasta de subtipo",
            )
            return

        subtipo = partes[1]
        subtipos_validos = self.mapping[area]
        if subtipo not in subtipos_validos:
            self.relatorio.adicionar(
                "estrutura",
                self._path_relativo(arquivo),
                (
                    f"subtipo '{subtipo}' fora do mapping para área '{area}' "
                    f"(válidos: {subtipos_validos})"
                ),
            )

    def _verificar_filename(self, arquivo: Path) -> None:
        """Valida que o basename casa com ``FILENAME_REGEX``."""
        nome = arquivo.name
        if not FILENAME_REGEX.match(nome):
            self.relatorio.adicionar(
                "filename",
                self._path_relativo(arquivo),
                f"filename '{nome}' fora do regex YYYY-MM-DD-HHmmss[-slug].<ext>",
            )

    def _verificar_frontmatters(self, arquivos: list[Path]) -> None:
        """Para cada .md companion, valida frontmatter obrigatório."""
        for arquivo in arquivos:
            if arquivo.suffix.lower() != ".md":
                continue
            self.relatorio.total_companions += 1
            try:
                texto = arquivo.read_text(encoding="utf-8")
            except OSError as exc:
                self.relatorio.adicionar(
                    "frontmatter",
                    self._path_relativo(arquivo),
                    f"erro lendo arquivo: {exc}",
                )
                continue

            frontmatter = extrair_frontmatter(texto)
            if frontmatter is None:
                self.relatorio.adicionar(
                    "frontmatter",
                    self._path_relativo(arquivo),
                    "frontmatter YAML ausente ou malformado",
                )
                continue

            ausentes = [
                campo
                for campo in FRONTMATTER_OBRIGATORIOS
                if campo not in frontmatter
            ]
            if ausentes:
                self.relatorio.adicionar(
                    "frontmatter",
                    self._path_relativo(arquivo),
                    f"campos obrigatórios ausentes: {ausentes}",
                )
                continue

            schema_version = frontmatter.get("_schema_version")
            if schema_version != 1:
                self.relatorio.adicionar(
                    "frontmatter",
                    self._path_relativo(arquivo),
                    f"_schema_version={schema_version!r} (esperado 1)",
                )

            tipo = frontmatter.get("tipo")
            if tipo != TIPO_INBOX_ARQUIVO:
                self.relatorio.adicionar(
                    "frontmatter",
                    self._path_relativo(arquivo),
                    f"tipo={tipo!r} (esperado {TIPO_INBOX_ARQUIVO!r})",
                )

    def _verificar_companions(self, arquivos: list[Path]) -> None:
        """Garante pareamento binário <-> .md companion."""
        binarios: dict[Path, Path] = {}
        markdowns: dict[Path, Path] = {}
        for arquivo in arquivos:
            ext = arquivo.suffix.lower()
            if ext in EXTENSOES_BINARIAS:
                chave = arquivo.with_suffix("")
                binarios[chave] = arquivo
            elif ext == ".md":
                chave = arquivo.with_suffix("")
                markdowns[chave] = arquivo

        self.relatorio.total_binarios = len(binarios)

        # Binários sem .md companion.
        for chave, bin_path in binarios.items():
            if chave not in markdowns:
                self.relatorio.adicionar(
                    "companion",
                    self._path_relativo(bin_path),
                    "binário sem .md companion ao lado",
                )

        # .md órfãos (sem binário correspondente). Exceção: arquivos .md que
        # são notas independentes (ex.: diario/) e não se referem a binário
        # externo. O critério aqui é checar se o frontmatter declara um campo
        # 'arquivo' que aponta para binário inexistente.
        for _chave, md_path in markdowns.items():
            try:
                texto = md_path.read_text(encoding="utf-8")
            except OSError:
                continue
            frontmatter = extrair_frontmatter(texto)
            if frontmatter is None:
                continue
            campo_arquivo = frontmatter.get("arquivo")
            if not isinstance(campo_arquivo, str):
                continue
            # Frontmatter referencia binário -> ele precisa existir.
            esperado = md_path.parent / campo_arquivo
            if not esperado.exists():
                self.relatorio.adicionar(
                    "companion",
                    self._path_relativo(md_path),
                    (
                        f".md referencia 'arquivo: {campo_arquivo}' mas binário "
                        f"não existe ao lado"
                    ),
                )


def gerar_relatorio_md(relatorio: Relatorio, path_saida: Path) -> None:
    """Serializa o relatório em markdown canônico."""
    hoje = datetime.now().strftime("%Y-%m-%d")
    linhas: list[str] = [
        "---",
        "titulo: Auditoria estrutural do vault Ouroboros",
        f"data: {hoje}",
        "auditor: scripts/audit_vault_md.py",
        f"escopo: {relatorio.vault}/inbox/",
        "---",
        "",
        "# Auditoria estrutural",
        "",
        "## Resumo",
        f"- Total auditado: {relatorio.total_arquivos}",
        f"- Conformes: {relatorio.conformes}",
        f"- Violações: {len(relatorio.violacoes)}",
        f"- Companions (.md): {relatorio.total_companions}",
        f"- Binários: {relatorio.total_binarios}",
        "",
    ]

    categorias_ordem = ("estrutura", "filename", "frontmatter", "companion")
    titulos = {
        "estrutura": "Categoria 1 -- Estrutura",
        "filename": "Categoria 2 -- Filename",
        "frontmatter": "Categoria 3 -- Frontmatter",
        "companion": "Categoria 4 -- Companion",
    }
    for categoria in categorias_ordem:
        itens = [v for v in relatorio.violacoes if v.categoria == categoria]
        linhas.append(f"## {titulos[categoria]}")
        if not itens:
            linhas.append("- nenhuma violação")
        else:
            for violacao in itens:
                linhas.append(f"- `{violacao.path}` -- {violacao.detalhe}")
        linhas.append("")

    linhas.append("## Recomendações")
    if not relatorio.violacoes:
        linhas.append("- vault limpo, nenhuma ação necessária")
    else:
        linhas.extend(_recomendacoes(relatorio))
    linhas.append("")

    path_saida.parent.mkdir(parents=True, exist_ok=True)
    path_saida.write_text("\n".join(linhas), encoding="utf-8")


def _recomendacoes(relatorio: Relatorio) -> list[str]:
    """Heurística simples: 5 bullets priorizando categorias com mais casos."""
    contagem: dict[str, int] = {}
    for violacao in relatorio.violacoes:
        contagem[violacao.categoria] = contagem.get(violacao.categoria, 0) + 1
    prioridade = sorted(contagem.items(), key=lambda x: -x[1])
    mapa = {
        "estrutura": (
            "Mover arquivos para `inbox/<area>/<subtipo>/` conforme mapping "
            "canônico."
        ),
        "filename": (
            "Renomear binários para o regex `YYYY-MM-DD-HHmmss[-slug].<ext>`."
        ),
        "frontmatter": (
            "Reescrever frontmatter dos .md companions com `_schema_version=1` "
            "+ campos obrigatórios."
        ),
        "companion": (
            "Gerar .md companion para cada binário (ou remover binário solto)."
        ),
    }
    bullets: list[str] = []
    for categoria, total in prioridade[:5]:
        sufixo = "caso" if total == 1 else "casos"
        bullets.append(
            f"- ({total} {sufixo}) {mapa.get(categoria, categoria)}"
        )
    while len(bullets) < 5:
        bullets.append("- (sem mais categorias com violação)")
    return bullets[:5]


def _path_relatorio_padrao() -> Path:
    hoje = datetime.now().strftime("%Y-%m-%d")
    return _RAIZ_REPO / "docs" / "auditorias" / f"AUDITORIA_VAULT_MD_{hoje}.md"


def _path_mapping_padrao() -> Path:
    return _RAIZ_REPO / "mappings" / "areas_subtipos.yaml"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Auditoria estrutural do vault Ouroboros (read-only)"
    )
    parser.add_argument(
        "--vault-path",
        default=str(Path.home() / "Protocolo-Ouroboros"),
        help="Raiz do vault (default: ~/Protocolo-Ouroboros)",
    )
    parser.add_argument(
        "--mapping",
        default=str(_path_mapping_padrao()),
        help="Path do YAML areas_subtipos canônico",
    )
    parser.add_argument(
        "--relatorio",
        default=None,
        help="Path do .md de saída (default: docs/auditorias/AUDITORIA_VAULT_MD_<data>.md)",
    )
    parser.add_argument(
        "--exit-zero-mesmo-com-violacao",
        action="store_true",
        help="Força exit code 0 mesmo se houver violações (uso em CI não-bloqueante)",
    )
    args = parser.parse_args(argv)

    vault = Path(args.vault_path).expanduser()
    if not vault.exists():
        print(f"[AUDIT] Vault não encontrado: {vault}")
        return 1

    mapping = carregar_mapping(Path(args.mapping))

    auditor = AuditorVault(vault, mapping)
    relatorio = auditor.executar()

    path_saida = (
        Path(args.relatorio).expanduser()
        if args.relatorio
        else _path_relatorio_padrao()
    )
    gerar_relatorio_md(relatorio, path_saida)

    print(
        f"[AUDIT] {relatorio.total_arquivos} arquivos auditados, "
        f"{len(relatorio.violacoes)} violações -> {path_saida}"
    )

    if relatorio.violacoes and not args.exit_zero_mesmo_com_violacao:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

# "Auditoria estrutural é a vacina contra drift: rodar uma vez por
# semana evita reescrever um trimestre depois." -- princípio da sprint
# MOB-audit-estrutura-vault-md.
#
# "O preço da liberdade é a vigilância eterna." -- Thomas Jefferson.
