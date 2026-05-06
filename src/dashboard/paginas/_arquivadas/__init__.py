"""Páginas arquivadas — não chamadas pelo dispatcher.

UX-T-01 eliminou as tabs duplicadas no cluster Home, removendo o uso
de ``home_dinheiro``/``home_docs``/``home_analise``/``home_metas`` e
``_home_helpers``. Os arquivos permanecem aqui para retrocompat
histórica e referência (e podem ser deletados em uma sprint
DEPRECATED-DELETE-01 futura quando passar a confiança).

Não importar deste pacote em código de produção.
"""
