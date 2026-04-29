#!/usr/bin/env python3
"""Verificação de acentuação em textos PT-BR.

Verifica se palavras comuns em português estão escritas com acentuação
correta em textos livres (docstrings, strings, logs, comentários, docs).
Ignora identificadores Python e paths de arquivo.

Uso:
    python scripts/check_acentuacao.py [arquivo1] [arquivo2] ...
    python scripts/check_acentuacao.py --all
    python scripts/check_acentuacao.py          (verifica staged no git)
"""

import re
import subprocess
import sys
from pathlib import Path

DICIONARIO: dict[str, str] = {
    # Palavras com ç (ão/ões)
    "funcao": "função",
    "funcoes": "funções",
    "validacao": "validação",
    "validacoes": "validações",
    "descricao": "descrição",
    "descricoes": "descrições",
    "configuracao": "configuração",
    "comunicacao": "comunicação",
    "transacao": "transação",
    "transacoes": "transações",
    "opcao": "opção",
    "opcoes": "opções",
    "operacao": "operação",
    "operacoes": "operações",
    "informacao": "informação",
    "informacoes": "informações",
    "classificacao": "classificação",
    "autorizacao": "autorização",
    "atualizacao": "atualização",
    "sincronizacao": "sincronização",
    "integracao": "integração",
    "execucao": "execução",
    "solucao": "solução",
    "situacao": "situação",
    "excecao": "exceção",
    "excecoes": "exceções",
    "verificacao": "verificação",
    "producao": "produção",
    "conexao": "conexão",
    "protecao": "proteção",
    "aplicacao": "aplicação",
    "organizacao": "organização",
    "resolucao": "resolução",
    "migracao": "migração",
    "documentacao": "documentação",
    "implementacao": "implementação",
    "depreciacao": "depreciação",
    "manutencao": "manutenção",
    # Palavras com acento agudo/grave
    "obrigatorio": "obrigatório",
    "obrigatorios": "obrigatórios",
    "necessario": "necessário",
    "relatorio": "relatório",
    "relatorios": "relatórios",
    "horario": "horário",
    "unico": "único",
    "indice": "índice",
    "codigo": "código",
    "valido": "válido",
    "invalido": "inválido",
    "binario": "binário",
    "binaria": "binária",
    "diretorio": "diretório",
    "numero": "número",
    "numeros": "números",
    "minimo": "mínimo",
    "maximo": "máximo",
    "metodo": "método",
    "ultimo": "último",
    "ultima": "última",
    "inicio": "início",
    "analise": "análise",
    "deposito": "depósito",
    "aleatorio": "aleatório",
    # Palavras com til
    "nao": "não",
    "sao": "são",
    "tambem": "também",
    # Palavras com circunflexo
    "concluido": "concluído",
    "concluida": "concluída",
    "concluidos": "concluídos",
    "conteudo": "conteúdo",
    # Palavras com acento em vogal
    "dificeis": "difíceis",
    # NOTA: "esta" (pronome demonstrativo) é válido sem acento.
    # "está" (verbo) vs "esta" (pronome) requer análise semântica
    # que está fora do escopo deste hook.
}

_PADRAO = re.compile(
    r"\b(" + "|".join(re.escape(w) for w in sorted(DICIONARIO, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)

# YAML excluído: chaves como 'classificacao' são identificadores técnicos do schema
EXTENSOES_VALIDAS = {".py", ".md", ".sh"}

# Padrão para detectar se a palavra está dentro de backticks ou é referência a código
_PADRAO_BACKTICK = re.compile(r"`[^`]*`")
_PADRAO_PATH = re.compile(r"[\w/\\]+\.\w{1,4}")


def _esta_em_codigo_md(linha: str, pos_inicio: int, pos_fim: int) -> bool:
    """Verifica se a posição está dentro de backticks ou referência a código em .md."""
    # Dentro de bloco de código (``` ... ```)
    # Isso é tratado por linha, então checamos se a linha começa com espaços (indentação de código)
    stripped = linha.lstrip()
    if stripped.startswith("```"):
        return True

    # Dentro de backticks inline
    for match in _PADRAO_BACKTICK.finditer(linha):
        if match.start() <= pos_inicio and match.end() >= pos_fim:
            return True

    # Adjacente a extensão de arquivo (.py, .md, .yaml, etc.)
    contexto = linha[max(0, pos_inicio - 5) : min(len(linha), pos_fim + 5)]
    if re.search(r"\.\w{1,4}", contexto):
        return True

    # Identificador genérico (adjacente a caracteres de código)
    if _e_identificador(linha, pos_inicio, pos_fim):
        return True

    # Em tabelas Markdown: célula sem espaço é nome de coluna/identificador
    if "|" in linha:
        antes_pipe = linha[:pos_inicio].rfind("|")
        depois_pipe = linha.find("|", pos_fim)
        if antes_pipe >= 0 and depois_pipe >= 0:
            celula = linha[antes_pipe + 1 : depois_pipe].strip()
            if celula and " " not in celula:
                return True

    return False


_PADRAO_STRING = re.compile(
    r'"""(.*?)"""|\'\'\'(.*?)\'\'\'|"([^"\\]*(?:\\.[^"\\]*)*)"|\'([^\'\\]*(?:\\.[^\'\\]*)*)\'',
    re.DOTALL,
)
_PADRAO_COMENTARIO = re.compile(r"#(.+)$", re.MULTILINE)
_PADRAO_FSTRING_VAR = re.compile(r"\{[^}]*?\}")


def _e_identificador(texto: str, pos_inicio: int, pos_fim: int) -> bool:
    """Verifica se a palavra está em contexto de identificador/código."""
    if pos_inicio > 0 and texto[pos_inicio - 1] in "_/.${\"'":
        return True
    if pos_fim < len(texto) and texto[pos_fim] in "_/.(){}=\"'":
        return True
    if pos_inicio >= 2 and texto[pos_inicio - 2 : pos_inicio] == "--":
        return True
    return False


def _e_linha_codigo_shell(linha: str) -> bool:
    """Detecta se a linha de .sh contém código Python embutido ou padrão bash."""
    stripped = linha.strip()
    if any(stripped.startswith(p) for p in ("from ", "import ", "def ", "class ")):
        return True
    if re.match(r"^\w+\s*=", stripped):
        return True
    if re.match(r"^--\w+\)", stripped):
        return True
    if re.search(r"\w+\.\w+\(", stripped):
        return True
    return False


def _extrair_textos_python(conteudo: str) -> list[tuple[int, str]]:
    """Extrai textos de strings e comentários de código Python."""
    textos: list[tuple[int, str]] = []

    for match in _PADRAO_STRING.finditer(conteudo):
        texto = match.group(1) or match.group(2) or match.group(3) or match.group(4) or ""
        linha = conteudo[: match.start()].count("\n") + 1
        textos.append((linha, texto))

    for match in _PADRAO_COMENTARIO.finditer(conteudo):
        linha = conteudo[: match.start()].count("\n") + 1
        textos.append((linha, match.group(1)))

    return textos


def verificar_arquivo(caminho: Path) -> list[str]:
    """Verifica acentuação em um arquivo. Retorna lista de erros."""
    extensao = caminho.suffix.lower()
    if extensao not in EXTENSOES_VALIDAS:
        return []

    try:
        conteudo = caminho.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    erros: list[str] = []

    if extensao == ".py":
        textos = _extrair_textos_python(conteudo)
        for linha_base, texto in textos:
            for sub_linha, parte in enumerate(texto.split("\n")):
                if "noqa: accent" in parte:
                    continue
                # Strings sem espaço são provavelmente chaves de dict/column
                parte_limpa = parte.strip()
                if parte_limpa and " " not in parte_limpa:
                    continue
                # Remover referências a variáveis em f-strings ({var}, {var.attr})
                parte_check = _PADRAO_FSTRING_VAR.sub(" ", parte)
                for match in _PADRAO.finditer(parte_check):
                    errada = match.group().lower()
                    correta = DICIONARIO.get(errada, "?")
                    if correta.lower() in parte_check.lower():
                        continue
                    if _e_identificador(parte_check, match.start(), match.end()):
                        continue
                    num = linha_base + sub_linha
                    erros.append(f"  {caminho}:{num}: '{match.group()}' -> '{correta}'")
    else:
        em_bloco_codigo = False
        for num, linha in enumerate(conteudo.split("\n"), 1):
            if "noqa: accent" in linha:
                continue
            # Rastrear blocos de código em .md
            if extensao == ".md" and linha.strip().startswith("```"):
                em_bloco_codigo = not em_bloco_codigo
                continue
            if em_bloco_codigo:
                continue
            # Para .sh, pular linhas que são código Python embutido ou padrões bash
            if extensao == ".sh" and _e_linha_codigo_shell(linha):
                continue
            for match in _PADRAO.finditer(linha):
                errada = match.group().lower()
                correta = DICIONARIO.get(errada, "?")
                if correta.lower() in linha.lower():
                    continue
                # Para .md, ignorar referências a código
                if extensao == ".md" and _esta_em_codigo_md(linha, match.start(), match.end()):
                    continue
                # Para todos: verificar se é identificador no contexto
                if _e_identificador(linha, match.start(), match.end()):
                    continue
                erros.append(f"  {caminho}:{num}: '{match.group()}' -> '{correta}'")

    return erros


def obter_arquivos_staged() -> list[Path]:
    """Obtém lista de arquivos staged no git."""
    resultado = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True,
        text=True,
    )
    return [Path(f) for f in resultado.stdout.strip().split("\n") if f]


def obter_todos_arquivos() -> list[Path]:
    """Obtém todos os arquivos do projeto com extensões válidas."""
    raiz = Path(__file__).resolve().parents[1]
    arquivos: list[Path] = []
    for ext in EXTENSOES_VALIDAS:
        arquivos.extend(raiz.rglob(f"*{ext}"))
    excluir = {
        ".venv",
        "__pycache__",
        "node_modules",
        ".git",
        ".claude",
        "contexto",
        "fixtures",
        "auditorias",
    }
    excluir_arquivos = {"check_acentuacao.py", "duvidas.md"}
    return [
        a
        for a in arquivos
        if not any(ex in str(a) for ex in excluir) and a.name not in excluir_arquivos
    ]


def main() -> int:
    """Ponto de entrada principal."""
    if "--all" in sys.argv:
        arquivos = obter_todos_arquivos()
    elif len(sys.argv) > 1:
        arquivos = [Path(a) for a in sys.argv[1:] if a != "--all"]
    else:
        arquivos = obter_arquivos_staged()

    if not arquivos:
        return 0

    todos_erros: list[str] = []
    for arquivo in arquivos:
        if arquivo.exists():
            todos_erros.extend(verificar_arquivo(arquivo))

    if todos_erros:
        print(f"\n  Acentuação: {len(todos_erros)} problema(s) encontrado(s)\n")
        for erro in sorted(todos_erros):
            print(erro)
        print("\n  Corrija ou adicione '# noqa: accent' para suprimir.\n")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

# "Conhece-te a ti mesmo." -- Sócrates
