"""API routes for PPTX generation and management."""

import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, UploadFile, File, Query, Body
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.services.pptx_builder import PPTXBuilder
from app.services.pptx_templates import TemplateEngine, TemplateTheme, PresentationTemplate

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/pptx", tags=["pptx"])


# ==================== Request/Response Models ====================

class SlideRequest(BaseModel):
    """Request model for a slide."""
    id: str
    type: str  # title, content, chart, table, images
    title: str
    content: str | None = None
    data: dict[str, Any] | None = None
    images: list[str] | None = None
    order: int


class GeneratePPTXRequest(BaseModel):
    """Request model for PPTX generation."""
    report_id: str
    report_data: dict[str, Any]
    template: str = "executive"
    theme: str = "default"
    slides: list[SlideRequest] = Field(default_factory=list)


class PPTXResponse(BaseModel):
    """Response model for PPTX generation."""
    pptx_path: str
    filename: str
    size: int
    created_at: str


class TemplateResponse(BaseModel):
    """Response model for template info."""
    name: str
    description: str
    type: str
    is_custom: bool = False


class ThemeResponse(BaseModel):
    """Response model for theme info."""
    name: str
    colors: dict[str, tuple[int, int, int]]


# ==================== PPTX Generation ====================

@router.post("/generate", response_model=PPTXResponse)
async def generate_pptx(request: GeneratePPTXRequest) -> PPTXResponse:
    """Generate a PPTX file from report data.

    Args:
        request: PPTX generation request

    Returns:
        Generated PPTX file info
    """
    try:
        # Get template theme
        theme = _get_theme(request.theme)

        # Create builder
        builder = PPTXBuilder(theme=theme)

        # Generate PPTX
        pptx_path = builder.generate_pptx(
            weekly_report=request.report_data,
            template_name=request.template,
            filename=f"report_{request.report_id}.pptx",
        )

        # Get file info
        file_path = Path(pptx_path)
        file_size = file_path.stat().st_size
        created_at = file_path.stat().st_ctime

        return PPTXResponse(
            pptx_path=str(pptx_path),
            filename=file_path.name,
            size=file_size,
            created_at=str(created_at),
        )
    except Exception as e:
        logger.error("PPTX generation failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate PPTX: {str(e)}",
        )


@router.post("/generate-with-slides")
async def generate_pptx_with_slides(request: GeneratePPTXRequest) -> PPTXResponse:
    """Generate PPTX with custom slide configuration.

    Args:
        request: PPTX generation request with custom slides

    Returns:
        Generated PPTX file info
    """
    try:
        theme = _get_theme(request.theme)
        builder = PPTXBuilder(theme=theme)

        # Add custom slides
        for slide in request.slides:
            if slide.type == "title":
                builder.add_title_slide(
                    title=slide.title,
                    subtitle=slide.content or "",
                )
            elif slide.type == "content":
                builder.add_content_slide(
                    title=slide.title,
                    content=slide.content or "",
                    images=slide.images,
                )
            elif slide.type == "chart":
                builder.add_chart_slide(
                    title=slide.title,
                    data=slide.data or {},
                    chart_type=slide.data.get("chart_type", "bar") if slide.data else "bar",
                )
            elif slide.type == "table":
                builder.add_table_slide(
                    title=slide.title,
                    data=slide.data.get("rows", []) if slide.data else [],
                    headers=slide.data.get("headers") if slide.data else None,
                )
            elif slide.type == "images":
                builder.add_image_slide(
                    title=slide.title,
                    images=slide.images or [],
                )

        # Save presentation
        pptx_path = builder._save_presentation(
            filename=f"report_{request.report_id}.pptx"
        )

        # Get file info
        file_path = Path(pptx_path)
        return PPTXResponse(
            pptx_path=str(pptx_path),
            filename=file_path.name,
            size=file_path.stat().st_size,
            created_at=str(file_path.stat().st_ctime),
        )
    except Exception as e:
        logger.error("PPTX generation with slides failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate PPTX: {str(e)}",
        )


# ==================== Template Management ====================

@router.get("/templates/list")
async def list_templates() -> dict[str, Any]:
    """List all available templates."""
    try:
        engine = TemplateEngine()
        templates = engine.list_all_templates()
        return {
            "templates": templates,
            "count": len(templates),
        }
    except Exception as e:
        logger.error("Failed to list templates: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Failed to list templates",
        )


@router.get("/templates/{template_name}")
async def get_template(template_name: str) -> dict[str, Any]:
    """Get template details.

    Args:
        template_name: Name of the template

    Returns:
        Template details
    """
    try:
        engine = TemplateEngine()
        template = engine.load_template(template_name)

        if not template:
            raise HTTPException(
                status_code=404,
                detail=f"Template '{template_name}' not found",
            )

        return template.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get template: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Failed to get template",
        )


@router.post("/templates/create")
async def create_custom_template(
    name: str,
    description: str,
    template_type: str,
    theme: TemplateTheme,
    slide_templates: list[str],
) -> dict[str, Any]:
    """Create a custom template.

    Args:
        name: Template name
        description: Template description
        template_type: Type of template
        theme: Theme configuration
        slide_templates: List of slide template names

    Returns:
        Created template details
    """
    try:
        engine = TemplateEngine()
        template = engine.create_custom_template(
            name=name,
            description=description,
            template_type=template_type,
            theme=theme,
            slide_templates=slide_templates,
        )
        return template.to_dict()
    except Exception as e:
        logger.error("Failed to create template: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Failed to create template",
        )


@router.delete("/templates/{template_name}")
async def delete_template(template_name: str) -> dict[str, str]:
    """Delete a custom template.

    Args:
        template_name: Name of the template to delete

    Returns:
        Deletion confirmation
    """
    try:
        engine = TemplateEngine()
        success = engine.delete_template(template_name)

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Template '{template_name}' not found",
            )

        return {"message": f"Template '{template_name}' deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete template: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Failed to delete template",
        )


@router.post("/templates/upload")
async def upload_template(
    name: str,
    file: UploadFile = File(...),
) -> dict[str, str]:
    """Upload a PPTX template file.

    Args:
        name: Template name
        file: Template file

    Returns:
        Upload confirmation
    """
    try:
        engine = TemplateEngine()
        content = await file.read()
        file_path = engine.templates_dir / f"{name}.pptx"
        file_path.write_bytes(content)

        logger.info("Template uploaded: %s", file_path)
        return {"message": f"Template '{name}' uploaded successfully"}
    except Exception as e:
        logger.error("Failed to upload template: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Failed to upload template",
        )


# ==================== Themes ====================

@router.get("/themes/list")
async def list_themes() -> dict[str, Any]:
    """List available themes."""
    themes = [
        "default",
        "corporate_blue",
        "modern_dark",
        "minimalist",
    ]
    return {"themes": themes}


@router.get("/themes/{theme_name}")
async def get_theme(theme_name: str) -> ThemeResponse:
    """Get theme details.

    Args:
        theme_name: Name of the theme

    Returns:
        Theme details
    """
    engine = TemplateEngine()
    theme_preview = engine.preview_theme(theme_name)

    if not theme_preview:
        raise HTTPException(
            status_code=404,
            detail=f"Theme '{theme_name}' not found",
        )

    return ThemeResponse(
        name=theme_preview["name"],
        colors=theme_preview["colors"],
    )


# ==================== Export ====================

@router.post("/export/pdf/{pptx_id}")
async def export_to_pdf(pptx_id: str) -> dict[str, str]:
    """Export PPTX to PDF.

    Args:
        pptx_id: ID or filename of the PPTX file

    Returns:
        PDF file path
    """
    try:
        builder = PPTXBuilder()
        pptx_path = builder.output_dir / pptx_id

        if not pptx_path.exists():
            raise HTTPException(
                status_code=404,
                detail="PPTX file not found",
            )

        pdf_path = builder.export_to_pdf(str(pptx_path))

        if not pdf_path:
            raise HTTPException(
                status_code=500,
                detail="PDF export failed",
            )

        return {"pdf_path": pdf_path}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("PDF export failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Failed to export PDF",
        )


@router.post("/export/docx/{pptx_id}")
async def export_to_docx(pptx_id: str) -> dict[str, str]:
    """Export PPTX to DOCX.

    Args:
        pptx_id: ID or filename of the PPTX file

    Returns:
        DOCX file path
    """
    # Note: This is a stub for future implementation
    raise HTTPException(
        status_code=501,
        detail="DOCX export is not yet implemented",
    )


# ==================== File Management ====================

@router.get("/files/list")
async def list_pptx_files() -> dict[str, Any]:
    """List all generated PPTX files."""
    try:
        builder = PPTXBuilder()
        files = []

        for file_path in builder.output_dir.glob("*.pptx"):
            stat = file_path.stat()
            files.append({
                "filename": file_path.name,
                "size": stat.st_size,
                "created_at": stat.st_ctime,
            })

        return {
            "files": sorted(files, key=lambda x: x["created_at"], reverse=True),
            "count": len(files),
        }
    except Exception as e:
        logger.error("Failed to list files: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Failed to list files",
        )


@router.delete("/files/{filename}")
async def delete_pptx_file(filename: str) -> dict[str, str]:
    """Delete a PPTX file.

    Args:
        filename: Name of the file to delete

    Returns:
        Deletion confirmation
    """
    try:
        builder = PPTXBuilder()
        file_path = builder.output_dir / filename

        if not file_path.exists():
            raise HTTPException(
                status_code=404,
                detail="File not found",
            )

        file_path.unlink()
        logger.info("PPTX file deleted: %s", file_path)

        return {"message": f"File '{filename}' deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete file: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Failed to delete file",
        )


# ==================== Helper Functions ====================

def _get_theme(theme_name: str) -> TemplateTheme:
    """Get theme by name."""
    theme_map = {
        "default": TemplateTheme.default,
        "corporate_blue": TemplateTheme.corporate_blue,
        "modern_dark": TemplateTheme.modern_dark,
        "minimalist": TemplateTheme.minimalist,
    }

    theme_factory = theme_map.get(theme_name, TemplateTheme.default)
    return theme_factory()
