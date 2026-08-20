"""Adaptador das atividades do banco → conteúdo do plano (deck_content.py).

Usa objetos de mentira: o que importa é a REGRA de classificação (tabela,
imagem, descarte), não o ORM. O ponto sensível é o anexo cujo arquivo sumiu do
disco — se ele passasse, o planejador reservaria um slot de imagem para nada e
o slide sairia com um buraco.
"""
from datetime import date
from types import SimpleNamespace

from app.services.deck_content import MAX_DESCRIPTION_CHARS, activities_to_content


def _att(**kwargs):
    base = {"file_type": None, "mime_type": None, "kpi_data": None, "file_path": None}
    base.update(kwargs)
    return SimpleNamespace(**base)


def _activity(title="Atividade", description="", data=None, attachments=()):
    return SimpleNamespace(
        title=title, description=description,
        activity_date=data, attachments=list(attachments),
    )


def test_converte_campos_basicos():
    conteudo = activities_to_content([
        _activity("Auditoria", "Feita.", date(2026, 7, 20))
    ])[0]
    assert conteudo.title == "Auditoria"
    assert conteudo.description == "Feita."
    assert conteudo.date_label == "20/07"


def test_atividade_sem_data_nao_quebra():
    assert activities_to_content([_activity(data=None)])[0].date_label == ""


def test_anexo_com_tabela_vira_tabela():
    anexo = _att(kpi_data={"table": {"columns": ["A", "B"], "rows": [[1, 2]]}})
    conteudo = activities_to_content([_activity(attachments=[anexo])])[0]
    assert conteudo.tables == [{"columns": ["A", "B"], "rows": [[1, 2]]}]
    assert conteudo.images == []


def test_tabela_vazia_e_ignorada():
    anexo = _att(kpi_data={"table": {"columns": [], "rows": []}})
    conteudo = activities_to_content([_activity(attachments=[anexo])])[0]
    assert conteudo.tables == []


def test_imagem_existente_entra_por_tipo_ou_mime(tmp_path):
    arquivo = tmp_path / "foto.png"
    arquivo.write_bytes(b"x")
    por_tipo = _att(file_type="image", file_path=str(arquivo))
    por_mime = _att(mime_type="image/jpeg", file_path=str(arquivo))
    conteudo = activities_to_content([_activity(attachments=[por_tipo, por_mime])])[0]
    assert conteudo.images == [str(arquivo), str(arquivo)]


def test_imagem_sem_arquivo_em_disco_e_descartada(tmp_path):
    anexo = _att(file_type="image", file_path=str(tmp_path / "sumiu.png"))
    conteudo = activities_to_content([_activity(attachments=[anexo])])[0]
    assert conteudo.images == []


def test_anexo_generico_fica_de_fora(tmp_path):
    arquivo = tmp_path / "relatorio.pdf"
    arquivo.write_bytes(b"x")
    anexo = _att(file_type="document", mime_type="application/pdf",
                 file_path=str(arquivo))
    conteudo = activities_to_content([_activity(attachments=[anexo])])[0]
    assert conteudo.tables == [] and conteudo.images == []


def test_descricao_gigante_e_cortada():
    conteudo = activities_to_content([_activity(description="a" * 5000)])[0]
    assert len(conteudo.description) == MAX_DESCRIPTION_CHARS + 1  # +1 = reticências
    assert conteudo.description.endswith("…")


def test_preserva_a_ordem_das_atividades():
    conteudos = activities_to_content([_activity("Um"), _activity("Dois")])
    assert [c.title for c in conteudos] == ["Um", "Dois"]
