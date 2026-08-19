"""Análise de planilha a pedido do usuário.

Fluxo: o usuário anexa a planilha (já existe), escreve o que quer em português,
e recebe a PRÉVIA calculada (tabela + gráfico + resumo). Se aprovar, a receita
fica salva e é REOFERTADA na semana seguinte para ele apenas selecionar.

Garantias: a IA só interpreta o pedido; todo número vem de aritmética
determinística (analysis_engine). Erros sempre com mensagem clara em PT.
"""
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.exceptions import NotFoundError, QWIException
from app.models import Activity, AnalysisRecipe, Attachment, User
from app.services.analysis_ai import build_recipes, recipe_signature
from app.services.analysis_engine import (
    AnalysisError,
    _norm,
    compare_with_previous,
    resolve_column,
    run_recipe,
)
from app.services.table_extract import extract_full_table

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analysis", tags=["Analysis"])

MAX_RECIPES_PER_USER = 20


# ── Schemas ─────────────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    attachment_id: str
    request_text: str = Field(min_length=3, max_length=500)
    # Reexecutar uma receita salva (o usuário selecionou a sugestão anterior).
    recipe_id: str | None = None
    # Confirmação manual de colunas quando a IA não tiver certeza.
    column_overrides: dict[str, str] | None = None


class ApproveRequest(BaseModel):
    attachment_id: str
    request_text: str = Field(min_length=3, max_length=500)
    recipe: dict
    label: str = Field(default="Análise", max_length=120)
    total: float | None = None


class RecipeResponse(BaseModel):
    id: str
    label: str
    request_text: str
    last_used_at: datetime | None
    matches_current_file: bool = False


# ── Helpers ─────────────────────────────────────────────────────────────────

def _load_attachment(db: Session, attachment_id: str, user: User) -> Attachment:
    attachment = (
        db.query(Attachment)
        .options(joinedload(Attachment.activity))
        .filter(Attachment.id == attachment_id)
        .first()
    )
    if not attachment or not attachment.activity or attachment.activity.user_id != user.id:
        raise NotFoundError("Anexo")
    return attachment


def _read_table(attachment: Attachment) -> dict:
    from pathlib import Path

    path = Path(attachment.file_path)
    if not path.exists():
        raise QWIException("O arquivo deste anexo não está mais disponível.", 404)
    table = extract_full_table(path.read_bytes(), attachment.original_filename)
    if not table or not table.get("columns"):
        raise QWIException(
            "Não consegui ler esta planilha. Envie um .xlsx, .xls ou .csv com "
            "cabeçalho na primeira linha.",
            422,
        )
    return table


def signature_of(columns: list[str]) -> str:
    """Assinatura do formato da planilha (colunas normalizadas e ordenadas)."""
    return "|".join(sorted(_norm(c) for c in columns if c))[:500]


# ── Endpoints ───────────────────────────────────────────────────────────────

@router.post("/preview")
async def analyze_preview(
    data: AnalyzeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Calcula a prévia da análise (não salva nada)."""
    attachment = _load_attachment(db, data.attachment_id, current_user)
    table = _read_table(attachment)
    columns, rows = table["columns"], table["rows"]

    source = "saved"
    previous_total = None
    if data.recipe_id:
        saved = (
            db.query(AnalysisRecipe)
            .filter(AnalysisRecipe.id == data.recipe_id,
                    AnalysisRecipe.user_id == current_user.id)
            .first()
        )
        if not saved:
            raise NotFoundError("Análise salva")
        recipes = [dict(saved.recipe or {})]
        previous_total = saved.last_total
    else:
        try:
            # O pedido pode conter mais de uma análise ("top 3 sintomas E
            # top 3 assistências") → uma receita por análise.
            recipes, source = await build_recipes(data.request_text, columns, rows)
        except ValueError as error:
            raise QWIException(str(error), 422)

    # Confirmação manual de colunas (quando a IA não teve certeza).
    if data.column_overrides:
        for key, value in data.column_overrides.items():
            if key in {"numerator", "denominator", "value", "group_by", "group_by2"} and value:
                if resolve_column(value, columns) is not None:
                    for recipe in recipes:
                        recipe[key] = value

    results: list[dict] = []
    failures: list[str] = []
    for recipe in recipes:
        try:
            results.append({"recipe": recipe, "result": run_recipe(recipe, columns, rows)})
        except AnalysisError as error:
            failures.append(str(error))

    if not results:
        # Nenhuma análise saiu → a UI pede confirmação das colunas.
        return {
            "ok": False,
            "message": failures[0] if failures else "Não consegui calcular.",
            "needs_columns": True,
            "columns": columns,
            "recipe": recipes[0] if recipes else {},
            "source": source,
        }

    first = results[0]["result"]
    comparison = compare_with_previous(first, previous_total)
    logger.info(
        "Análise gerada | user=%s | origem=%s | análises=%d | falhas=%d",
        current_user.id, source, len(results), len(failures),
    )
    return {
        "ok": True,
        "source": source,           # ai | heuristic | saved
        "recipe": first and results[0]["recipe"],   # compat: 1ª receita
        "columns": columns,         # p/ o formulário de ajuste, se ele quiser
        "result": first,            # compat: 1º resultado
        "results": results,         # TODAS as análises: [{recipe, result}, ...]
        "comparison": comparison,   # frase vs. semana anterior (ou null)
        "partial": failures or None,  # análises que não deram certo
    }


@router.post("/approve", response_model=RecipeResponse)
def approve_analysis(
    data: ApproveRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Aprova a análise: salva a receita para reofertar nas próximas semanas."""
    attachment = _load_attachment(db, data.attachment_id, current_user)
    table = _read_table(attachment)
    signature = signature_of(table["columns"])

    # A mesma análise é reofertada toda semana; aprovar de novo deve ATUALIZAR
    # a receita existente, não empilhar cópias até estourar o limite.
    target = recipe_signature(data.recipe, table["columns"])
    for item in (
        db.query(AnalysisRecipe)
        .filter(AnalysisRecipe.user_id == current_user.id,
                AnalysisRecipe.columns_signature == signature)
        .all()
    ):
        if recipe_signature(item.recipe or {}, table["columns"]) == target:
            item.request_text = data.request_text.strip()
            item.recipe = data.recipe
            item.label = data.label.strip()[:120] or item.label
            item.last_total = data.total
            item.last_used_at = datetime.now(UTC)
            db.commit()
            db.refresh(item)
            return RecipeResponse(
                id=item.id, label=item.label, request_text=item.request_text,
                last_used_at=item.last_used_at, matches_current_file=True,
            )

    count = (
        db.query(AnalysisRecipe)
        .filter(AnalysisRecipe.user_id == current_user.id)
        .count()
    )
    if count >= MAX_RECIPES_PER_USER:
        raise QWIException(
            f"Limite de {MAX_RECIPES_PER_USER} análises salvas. Remova uma antes.",
            409,
        )

    saved = AnalysisRecipe(
        user_id=current_user.id,
        request_text=data.request_text.strip(),
        recipe=data.recipe,
        columns_signature=signature,
        label=data.label.strip()[:120] or "Análise",
        last_total=data.total,
        last_used_at=datetime.now(UTC),
    )
    db.add(saved)
    db.commit()
    db.refresh(saved)
    return RecipeResponse(
        id=saved.id, label=saved.label, request_text=saved.request_text,
        last_used_at=saved.last_used_at, matches_current_file=True,
    )


@router.get("/recipes", response_model=list[RecipeResponse])
def list_recipes(
    attachment_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Análises salvas do usuário. Com `attachment_id`, marca as que combinam
    com o formato daquela planilha (para reofertar 'a mesma da semana passada')."""
    rows = (
        db.query(AnalysisRecipe)
        .filter(AnalysisRecipe.user_id == current_user.id)
        .order_by(AnalysisRecipe.last_used_at.desc().nullslast())
        .all()
    )
    signature = ""
    if attachment_id:
        try:
            attachment = _load_attachment(db, attachment_id, current_user)
            signature = signature_of(_read_table(attachment)["columns"])
        except Exception:
            signature = ""
    return [
        RecipeResponse(
            id=r.id, label=r.label, request_text=r.request_text,
            last_used_at=r.last_used_at,
            matches_current_file=bool(signature) and r.columns_signature == signature,
        )
        for r in rows
    ]


@router.delete("/recipes/{recipe_id}", status_code=204)
def delete_recipe(
    recipe_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    saved = (
        db.query(AnalysisRecipe)
        .filter(AnalysisRecipe.id == recipe_id, AnalysisRecipe.user_id == current_user.id)
        .first()
    )
    if not saved:
        raise NotFoundError("Análise salva")
    db.delete(saved)
    db.commit()
