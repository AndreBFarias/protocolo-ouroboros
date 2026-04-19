"""Sincronização de transações bancárias via Belvo Open Finance.

Usa o free tier da Belvo (25 links reais) para baixar transações
dos bancos conectados e salvar como CSV compatível com o pipeline.

Configuração:
    BELVO_SECRET_ID=xxx       (variável de ambiente ou .env)
    BELVO_SECRET_PASSWORD=xxx
    BELVO_AMBIENTE=sandbox    (sandbox ou production)

Uso:
    python -m src.integrations.belvo_sync
    python -m src.integrations.belvo_sync --dias 60
"""

import argparse
import csv
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from src.utils.logger import configurar_logger

logger = configurar_logger("belvo_sync")

try:
    from belvo.client import Client as BelvoClient

    BELVO_DISPONIVEL = True
except ImportError:
    BELVO_DISPONIVEL = False
    logger.warning("belvo-python não instalado. Rode: pip install belvo-python")

RAIZ = Path(__file__).resolve().parents[2]
DIR_RAW = RAIZ / "data" / "raw"

AMBIENTES_BELVO = {
    "sandbox": "https://sandbox.belvo.com",
    "production": "https://api.belvo.com",
}


class BelvoSync:
    """Sincronizador de dados bancários via Belvo API."""

    def __init__(self) -> None:
        import os

        self.secret_id: str = os.environ.get("BELVO_SECRET_ID", "")
        self.secret_password: str = os.environ.get("BELVO_SECRET_PASSWORD", "")
        self.ambiente: str = os.environ.get("BELVO_AMBIENTE", "sandbox")
        self.client: Any = None

    def conectar(self) -> bool:
        """Autentica com a API Belvo."""
        if not BELVO_DISPONIVEL:
            logger.error("belvo-python não disponível")
            return False

        if not self.secret_id or not self.secret_password:
            logger.error(
                "Credenciais Belvo não configuradas. "
                "Defina BELVO_SECRET_ID e BELVO_SECRET_PASSWORD no .env"
            )
            return False

        url = AMBIENTES_BELVO.get(self.ambiente, AMBIENTES_BELVO["sandbox"])
        try:
            self.client = BelvoClient(self.secret_id, self.secret_password, url)
            logger.info("Conectado à Belvo (%s)", self.ambiente)
            return True
        except Exception as e:
            logger.error("Erro ao conectar com Belvo: %s", e)
            return False

    def listar_contas(self) -> list[dict[str, Any]]:
        """Lista todas as contas (links) conectadas."""
        if not self.client:
            return []

        try:
            links = self.client.Links.list()
            contas: list[dict[str, Any]] = []
            for link in links:
                contas.append(
                    {
                        "id": link.get("id"),
                        "instituição": link.get("institution"),
                        "status": link.get("status"),
                        "criado_em": link.get("created_at"),
                    }
                )
            logger.info("Encontradas %d contas conectadas", len(contas))
            return contas
        except Exception as e:
            logger.error("Erro ao listar contas: %s", e)
            return []

    def baixar_transacoes(
        self,
        link_id: str,
        data_inicio: date,
        data_fim: date,
    ) -> list[dict[str, Any]]:
        """Baixa transações de uma conta para o período especificado."""
        if not self.client:
            return []

        try:
            transacoes = self.client.Transactions.create(
                link_id,
                data_inicio.isoformat(),
                data_fim.isoformat(),
            )
            logger.info(
                "Baixadas %d transações (link %s, %s a %s)",
                len(transacoes),
                link_id[:8],
                data_inicio,
                data_fim,
            )
            return transacoes
        except Exception as e:
            logger.error("Erro ao baixar transações: %s", e)
            return []

    def salvar_como_csv(
        self,
        transacoes: list[dict[str, Any]],
        destino: Path,
        instituicao: str = "belvo",
    ) -> Path:
        """Salva transações como CSV compatível com ExtratorNubankCC."""
        destino.parent.mkdir(parents=True, exist_ok=True)

        with open(destino, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Data", "Valor", "Identificador", "Descrição"])

            for t in transacoes:
                data_str = t.get("value_date", t.get("accounting_date", ""))
                valor = t.get("amount", 0)
                descricao = t.get("description", "")
                identificador = t.get("internal_identification", "")

                writer.writerow([data_str, valor, identificador, descricao])

        logger.info("CSV salvo: %s (%d transações)", destino, len(transacoes))
        return destino

    def sincronizar(self, destino_dir: Path, dias: int = 30) -> list[Path]:
        """Fluxo completo: conectar, listar contas, baixar e salvar."""
        if not self.conectar():
            return []

        contas = self.listar_contas()
        if not contas:
            logger.warning("Nenhuma conta conectada na Belvo")
            return []

        data_fim = date.today()
        data_inicio = data_fim - timedelta(days=dias)
        arquivos: list[Path] = []

        for conta in contas:
            link_id = conta["id"]
            inst = conta.get("instituição", "desconhecido")
            transacoes = self.baixar_transacoes(link_id, data_inicio, data_fim)

            if transacoes:
                nome = f"belvo_{inst}_{data_fim.isoformat()}.csv"
                destino = destino_dir / nome
                self.salvar_como_csv(transacoes, destino, inst)
                arquivos.append(destino)

        logger.info("Sincronização concluída: %d arquivos gerados", len(arquivos))
        return arquivos


def main() -> None:
    """Entrypoint CLI."""
    parser = argparse.ArgumentParser(description="Sincronizar dados via Belvo")
    parser.add_argument("--dias", type=int, default=30, help="Dias para buscar")
    parser.add_argument(
        "--destino",
        type=str,
        default=str(DIR_RAW),
        help="Diretório de destino dos CSVs",
    )
    parser.add_argument("--listar", action="store_true", help="Apenas listar contas")
    args = parser.parse_args()

    sync = BelvoSync()

    if args.listar:
        if sync.conectar():
            contas = sync.listar_contas()
            for c in contas:
                print(f"  {c['instituição']}: {c['status']} (id: {c['id'][:8]}...)")
        return

    arquivos = sync.sincronizar(Path(args.destino), args.dias)
    if arquivos:
        for a in arquivos:
            print(f"  Salvo: {a}")
    else:
        print("  Nenhuma transação baixada. Verifique credenciais e contas conectadas.")


if __name__ == "__main__":
    main()

# "O conhecimento é o olho do desejo e pode tornar-se o piloto da alma." -- Will Durant
