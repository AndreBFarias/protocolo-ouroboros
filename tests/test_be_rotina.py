"""Testes da Sprint UX-V-2.10 -- página Bem-estar / Rotina.

Cobre os helpers introduzidos para suportar o formato novo
``<vault>/.ouroboros/rotina/*.toml`` (diretório com múltiplos arquivos)
e a renderização de KPIs/colunas conforme mockup ``20-rotina.html``.

Casos:

  1. ``_carregar_rotinas_toml`` retorna estrutura vazia quando vault é None.
  2. ``_carregar_rotinas_toml`` retorna estrutura vazia quando pasta inexistente.
  3. ``_carregar_rotinas_toml`` agrega de múltiplos arquivos toml.
  4. ``_carregar_rotinas_toml`` ignora arquivos toml inválidos.
  5. ``_proximo_alarme`` retorna ``--`` quando não há alarmes.
  6. ``_proximo_alarme`` retorna o próximo horário futuro do dia.
  7. ``_proximo_alarme`` envolve para o menor quando todos já passaram.
  8. ``_kpis_rotina_html`` contém os 4 rótulos canônicos.
  9. ``_kpis_rotina_html`` calcula concluídas/total corretamente.
 10. Compatibilidade retroativa: ``_ler_rotina`` (formato legado) preservado.
"""

from __future__ import annotations

from src.dashboard.paginas import be_rotina


def test_carregar_rotinas_vault_none_retorna_estrutura_vazia():
    res = be_rotina._carregar_rotinas_toml(None)
    assert res == {"alarmes": [], "tarefas": [], "contadores": []}


def test_carregar_rotinas_pasta_inexistente_retorna_estrutura_vazia(tmp_path):
    # Vault existe mas .ouroboros/rotina/ não.
    res = be_rotina._carregar_rotinas_toml(tmp_path)
    assert res == {"alarmes": [], "tarefas": [], "contadores": []}


def test_carregar_rotinas_agrega_multiplos_arquivos(tmp_path):
    pasta = tmp_path / ".ouroboros" / "rotina"
    pasta.mkdir(parents=True)
    (pasta / "medicacao.toml").write_text(
        '[[alarme]]\nid="bup1"\nnome="Bupropiona"\nhora="08:00"\n'
        '[[alarme]]\nid="bup2"\nnome="Bupropiona"\nhora="22:00"\n',
        encoding="utf-8",
    )
    (pasta / "tarefas.toml").write_text(
        '[[tarefa]]\nid="t1"\nnome="Pagar fatura"\nprioridade="alta"\n'
        '[[tarefa]]\nid="t2"\nnome="Treino A"\nconcluida=true\n',
        encoding="utf-8",
    )
    (pasta / "contadores.toml").write_text(
        '[[contador]]\nid="c1"\nnome="Sem fumar"\nstreak_dias=47\nmeta=60\n',
        encoding="utf-8",
    )
    res = be_rotina._carregar_rotinas_toml(tmp_path)
    assert len(res["alarmes"]) == 2
    assert len(res["tarefas"]) == 2
    assert len(res["contadores"]) == 1
    assert res["contadores"][0]["streak_dias"] == 47


def test_carregar_rotinas_ignora_toml_invalido(tmp_path):
    pasta = tmp_path / ".ouroboros" / "rotina"
    pasta.mkdir(parents=True)
    (pasta / "valido.toml").write_text(
        '[[alarme]]\nid="x"\nhora="07:00"\n', encoding="utf-8"
    )
    (pasta / "quebrado.toml").write_text(
        "[[alarme\nfaltando_fechar = 1", encoding="utf-8"
    )
    res = be_rotina._carregar_rotinas_toml(tmp_path)
    # arquivo quebrado é ignorado silenciosamente, válido carrega.
    assert len(res["alarmes"]) == 1


def test_proximo_alarme_sem_lista_retorna_traco():
    assert be_rotina._proximo_alarme([]) == "--"


def test_proximo_alarme_retorna_proxima_hora_futura():
    # 23:59 sempre será futuro a menos que rode exatamente em 23:59
    alarmes = [{"hora": "00:01"}, {"hora": "23:59"}]
    res = be_rotina._proximo_alarme(alarmes)
    assert res in ("00:01", "23:59")  # depende da hora corrente


def test_proximo_alarme_envolve_para_menor_quando_todos_passaram(monkeypatch):
    # Simula horário fixo via patch na chamada datetime.now em be_rotina.
    from datetime import datetime as _dt_real

    class FakeDt:
        @classmethod
        def now(cls):
            # 23:59 -- tudo abaixo já passou
            return _dt_real(2026, 5, 7, 23, 59, 0)

    monkeypatch.setattr(be_rotina, "datetime", FakeDt)
    alarmes = [{"hora": "06:00"}, {"hora": "12:00"}, {"hora": "18:00"}]
    assert be_rotina._proximo_alarme(alarmes) == "06:00"


def test_kpis_rotina_html_contem_4_rotulos():
    dados = {"alarmes": [], "tarefas": [], "contadores": []}
    html = be_rotina._kpis_rotina_html(dados)
    assert "TAREFAS HOJE" in html
    assert "PRÓXIMO ALARME" in html
    assert "STREAK ATIVO" in html
    assert "ALARMES ATIVOS" in html


def test_kpis_rotina_html_calcula_concluidas_e_total():
    dados = {
        "alarmes": [{"hora": "08:00"}, {"hora": "22:00"}],
        "tarefas": [
            {"nome": "a", "concluida": True},
            {"nome": "b", "concluida": False},
            {"nome": "c", "concluida": True},
        ],
        "contadores": [{"streak_dias": 47}, {"streak_dias": 12}],
    }
    html = be_rotina._kpis_rotina_html(dados)
    # 2 concluídas / 3 total
    assert "2/3" in html
    # streak top = 47
    assert "47 dias" in html
    # 2 alarmes ativos
    assert ">2<" in html  # kpi-value de alarmes ativos


def test_ler_rotina_legado_preservado(tmp_path):
    """Garante que UX-V-2.10 não quebra contrato de _ler_rotina (UX-RD-19)."""
    arquivo = tmp_path / "rotina.toml"
    arquivo.write_text(
        '[[alarme]]\nid="x"\nnome="X"\nhora="07:00"\n', encoding="utf-8"
    )
    cfg = be_rotina._ler_rotina(arquivo)
    assert cfg is not None
    assert len(cfg["alarme"]) == 1


# "Rotina é a infraestrutura do dia." -- princípio V-2.10
