"""Download automático de CSVs do Nubank via Gmail API.

O Nubank envia faturas e extratos por email para todomundo@nubank.com.br.
Esta integração busca esses emails e baixa os anexos CSV/PDF para o inbox/.

Configuração:
    1. Criar projeto no Google Cloud Console
    2. Habilitar Gmail API
    3. Criar credenciais OAuth2 (tipo Desktop)
    4. Salvar credentials.json na raiz do projeto
    5. Na primeira execução, autorizar no navegador

Uso:
    python -m src.integrations.gmail_csv
    python -m src.integrations.gmail_csv --dias 60
"""

import argparse
import base64
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from src.utils.logger import configurar_logger

logger = configurar_logger("gmail_csv")

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    GMAIL_DISPONIVEL = True
except ImportError:
    GMAIL_DISPONIVEL = False
    logger.info(
        "Bibliotecas do Gmail não instaladas. "
        "Rode: pip install google-api-python-client google-auth-oauthlib"
    )

RAIZ = Path(__file__).resolve().parents[2]
DIR_INBOX = RAIZ / "inbox"
CREDENTIALS_PATH = RAIZ / "credentials.json"
TOKEN_PATH = RAIZ / ".gmail_token.json"
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

REMETENTES_NUBANK = [
    "todomundo@nubank.com.br",
    "nu@nubank.com.br",
    "noreply@nubank.com.br",
]

EXTENSOES_ANEXO = {".csv", ".pdf", ".ofx"}


class GmailCSVDownloader:
    """Baixa anexos CSV/PDF de emails do Nubank via Gmail API."""

    def __init__(self) -> None:
        self.service: Any = None

    def autenticar(self) -> bool:
        """Realiza autenticação OAuth2 com Gmail API."""
        if not GMAIL_DISPONIVEL:
            logger.error(
                "Bibliotecas do Gmail não disponíveis. "
                "Instale: pip install google-api-python-client google-auth-oauthlib"
            )
            return False

        if not CREDENTIALS_PATH.exists():
            logger.error(
                "Arquivo credentials.json não encontrado em %s. "
                "Baixe do Google Cloud Console (APIs > Credentials > OAuth2 Desktop).",
                CREDENTIALS_PATH,
            )
            return False

        creds = None
        if TOKEN_PATH.exists():
            creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(CREDENTIALS_PATH),
                    SCOPES,
                )
                creds = flow.run_local_server(port=0)

            TOKEN_PATH.write_text(creds.to_json())
            logger.info("Token Gmail salvo em %s", TOKEN_PATH)

        self.service = build("gmail", "v1", credentials=creds)
        logger.info("Autenticado com Gmail API")
        return True

    def buscar_emails_nubank(self, dias: int = 30) -> list[dict[str, Any]]:
        """Busca emails do Nubank com anexos nos últimos N dias."""
        if not self.service:
            return []

        data_limite = (datetime.now() - timedelta(days=dias)).strftime("%Y/%m/%d")
        remetentes = " OR ".join(f"from:{r}" for r in REMETENTES_NUBANK)
        query = f"({remetentes}) has:attachment after:{data_limite}"

        try:
            resultado = (
                self.service.users()
                .messages()
                .list(
                    userId="me",
                    q=query,
                    maxResults=50,
                )
                .execute()
            )

            mensagens = resultado.get("messages", [])
            logger.info(
                "Encontrados %d emails do Nubank com anexos (últimos %d dias)",
                len(mensagens),
                dias,
            )
            return mensagens
        except Exception as e:
            logger.error("Erro ao buscar emails: %s", e)
            return []

    def baixar_anexos(
        self,
        mensagens: list[dict[str, Any]],
        destino_dir: Path,
    ) -> list[Path]:
        """Baixa anexos CSV/PDF/OFX dos emails encontrados."""
        if not self.service:
            return []

        destino_dir.mkdir(parents=True, exist_ok=True)
        arquivos: list[Path] = []

        for msg_ref in mensagens:
            try:
                msg = (
                    self.service.users()
                    .messages()
                    .get(
                        userId="me",
                        id=msg_ref["id"],
                    )
                    .execute()
                )

                partes = msg.get("payload", {}).get("parts", [])
                for parte in partes:
                    nome_arquivo = parte.get("filename", "")
                    if not nome_arquivo:
                        continue

                    extensao = Path(nome_arquivo).suffix.lower()
                    if extensao not in EXTENSOES_ANEXO:
                        continue

                    corpo = parte.get("body", {})
                    attachment_id = corpo.get("attachmentId")

                    if attachment_id:
                        anexo = (
                            self.service.users()
                            .messages()
                            .attachments()
                            .get(
                                userId="me",
                                messageId=msg_ref["id"],
                                id=attachment_id,
                            )
                            .execute()
                        )

                        dados = base64.urlsafe_b64decode(anexo["data"])
                        destino = destino_dir / nome_arquivo

                        if destino.exists():
                            logger.info("Anexo já existe, pulando: %s", nome_arquivo)
                            continue

                        destino.write_bytes(dados)
                        arquivos.append(destino)
                        logger.info("Baixado: %s (%d bytes)", nome_arquivo, len(dados))

            except Exception as e:
                logger.warning("Erro ao processar email %s: %s", msg_ref.get("id"), e)

        logger.info("Total de anexos baixados: %d", len(arquivos))
        return arquivos

    def sincronizar(self, destino_dir: Path, dias: int = 30) -> list[Path]:
        """Fluxo completo: autenticar, buscar, baixar."""
        if not self.autenticar():
            return []

        mensagens = self.buscar_emails_nubank(dias)
        if not mensagens:
            logger.info("Nenhum email do Nubank encontrado")
            return []

        return self.baixar_anexos(mensagens, destino_dir)


def main() -> None:
    """Entrypoint CLI."""
    parser = argparse.ArgumentParser(
        description="Baixar CSVs do Nubank via Gmail",
    )
    parser.add_argument("--dias", type=int, default=30, help="Dias para buscar")
    parser.add_argument(
        "--destino",
        type=str,
        default=str(DIR_INBOX),
        help="Diretório de destino dos anexos",
    )
    args = parser.parse_args()

    downloader = GmailCSVDownloader()
    arquivos = downloader.sincronizar(Path(args.destino), args.dias)

    if arquivos:
        for a in arquivos:
            print(f"  Baixado: {a}")
        print("\n  Rode ./run.sh --inbox para processar os arquivos.")
    else:
        print("  Nenhum anexo baixado.")


if __name__ == "__main__":
    main()

# "A liberdade consiste em fazer tudo o que não prejudique o próximo."
# -- Declaração dos Direitos do Homem
