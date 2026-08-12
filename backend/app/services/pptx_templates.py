"""Template engine and predefined themes for PPTX generation."""

import json
import logging
from dataclasses import dataclass, asdict, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class TemplateType(str, Enum):
    """Template types."""
    EXECUTIVE = "executive"
    OPERATIONAL = "operational"
    ANALYTICAL = "analytical"
    TECHNICAL = "technical"
    CUSTOM = "custom"


@dataclass
class TemplateTheme:
    """Color and styling theme for presentations."""

    name: str = "default"
    accent_color: tuple = field(default_factory=lambda: (0, 102, 204))  # Blue
    primary_color: tuple = field(default_factory=lambda: (33, 33, 33))  # Dark gray
    secondary_color: tuple = field(default_factory=lambda: (100, 149, 237))  # Cornflower blue
    text_color: tuple = field(default_factory=lambda: (33, 33, 33))  # Dark gray
    secondary_text_color: tuple = field(default_factory=lambda: (119, 119, 119))  # Medium gray
    background_color: tuple = field(default_factory=lambda: (255, 255, 255))  # White
    highlight_color: tuple = field(default_factory=lambda: (255, 193, 7))  # Amber
    success_color: tuple = field(default_factory=lambda: (76, 175, 80))  # Green
    warning_color: tuple = field(default_factory=lambda: (255, 152, 0))  # Orange
    error_color: tuple = field(default_factory=lambda: (244, 67, 54))  # Red

    @classmethod
    def default(cls) -> "TemplateTheme":
        """Get default theme."""
        return cls(name="default")

    @classmethod
    def corporate_blue(cls) -> "TemplateTheme":
        """Corporate blue theme."""
        return cls(
            name="corporate_blue",
            accent_color=(0, 102, 204),
            primary_color=(0, 60, 120),
            secondary_color=(100, 149, 237),
            text_color=(33, 33, 33),
            background_color=(255, 255, 255),
        )

    @classmethod
    def modern_dark(cls) -> "TemplateTheme":
        """Modern dark theme."""
        return cls(
            name="modern_dark",
            accent_color=(100, 200, 255),
            primary_color=(50, 50, 50),
            secondary_color=(100, 149, 237),
            text_color=(220, 220, 220),
            secondary_text_color=(150, 150, 150),
            background_color=(30, 30, 30),
        )

    @classmethod
    def minimalist(cls) -> "TemplateTheme":
        """Minimalist theme."""
        return cls(
            name="minimalist",
            accent_color=(0, 0, 0),
            primary_color=(0, 0, 0),
            secondary_color=(100, 100, 100),
            text_color=(0, 0, 0),
            secondary_text_color=(128, 128, 128),
            background_color=(255, 255, 255),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert theme to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TemplateTheme":
        """Create theme from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in asdict(cls()).keys()})


@dataclass
class SlideTemplate:
    """Configuration for a slide template."""

    name: str
    title: str
    description: str
    layout: str  # "title", "content", "two_column", "chart", "table"
    slide_type: str  # "cover", "section", "content", "close"

    # Layout configuration
    has_header: bool = True
    has_footer: bool = True
    columns: int = 1
    image_enabled: bool = False
    chart_enabled: bool = False
    table_enabled: bool = False

    # Styling
    theme_name: str = "default"
    accent_bar: bool = True
    page_numbers: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class TemplateLibrary:
    """Library of predefined templates."""

    TEMPLATES: dict[str, SlideTemplate] = {
        "title_slide": SlideTemplate(
            name="title_slide",
            title="Title Slide",
            description="Cover slide with title, subtitle, and author",
            layout="title",
            slide_type="cover",
            has_footer=False,
            accent_bar=True,
        ),
        "content_slide": SlideTemplate(
            name="content_slide",
            title="Content Slide",
            description="Standard content slide with text",
            layout="content",
            slide_type="content",
            columns=1,
            image_enabled=True,
        ),
        "two_column": SlideTemplate(
            name="two_column",
            title="Two Column Layout",
            description="Two-column layout for comparison",
            layout="two_column",
            slide_type="content",
            columns=2,
        ),
        "chart_slide": SlideTemplate(
            name="chart_slide",
            title="Chart Slide",
            description="Full-width chart with title",
            layout="chart",
            slide_type="content",
            chart_enabled=True,
        ),
        "table_slide": SlideTemplate(
            name="table_slide",
            title="Table Slide",
            description="Table with data",
            layout="table",
            slide_type="content",
            table_enabled=True,
        ),
        "image_gallery": SlideTemplate(
            name="image_gallery",
            title="Image Gallery",
            description="Grid of images",
            layout="content",
            slide_type="content",
            image_enabled=True,
        ),
        "section_divider": SlideTemplate(
            name="section_divider",
            title="Section Divider",
            description="Section break slide",
            layout="title",
            slide_type="section",
            has_footer=False,
        ),
        "closing_slide": SlideTemplate(
            name="closing_slide",
            title="Closing Slide",
            description="Thank you / closing slide",
            layout="title",
            slide_type="close",
            has_footer=False,
        ),
    }

    @classmethod
    def get_template(cls, name: str) -> Optional[SlideTemplate]:
        """Get template by name."""
        return cls.TEMPLATES.get(name)

    @classmethod
    def list_templates(cls) -> list[SlideTemplate]:
        """List all available templates."""
        return list(cls.TEMPLATES.values())

    @classmethod
    def get_by_type(cls, slide_type: str) -> list[SlideTemplate]:
        """Get templates by slide type."""
        return [t for t in cls.TEMPLATES.values() if t.slide_type == slide_type]


@dataclass
class PresentationTemplate:
    """Complete presentation template configuration."""

    name: str
    description: str
    template_type: TemplateType
    theme: TemplateTheme
    slide_templates: list[str] = field(default_factory=list)
    page_width: float = 10.0
    page_height: float = 7.5

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "template_type": self.template_type.value,
            "theme": self.theme.to_dict(),
            "slide_templates": self.slide_templates,
            "page_width": self.page_width,
            "page_height": self.page_height,
        }


class TemplateEngine:
    """Engine for managing and loading templates."""

    def __init__(self):
        """Initialize template engine."""
        upload_root = Path(settings.UPLOAD_DIR)
        self.templates_dir = upload_root / "templates"
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self._custom_templates: dict[str, PresentationTemplate] = {}

    def get_predefined_templates(self) -> dict[str, PresentationTemplate]:
        """Get predefined templates."""
        return {
            "executive": PresentationTemplate(
                name="executive",
                description="Executive summary template",
                template_type=TemplateType.EXECUTIVE,
                theme=TemplateTheme.corporate_blue(),
                slide_templates=["title_slide", "content_slide", "chart_slide", "table_slide", "closing_slide"],
            ),
            "operational": PresentationTemplate(
                name="operational",
                description="Operational details template",
                template_type=TemplateType.OPERATIONAL,
                theme=TemplateTheme.default(),
                slide_templates=["title_slide", "content_slide", "two_column", "table_slide", "closing_slide"],
            ),
            "analytical": PresentationTemplate(
                name="analytical",
                description="Data-driven analytical template",
                template_type=TemplateType.ANALYTICAL,
                theme=TemplateTheme.default(),
                slide_templates=["title_slide", "chart_slide", "table_slide", "content_slide", "closing_slide"],
            ),
            "technical": PresentationTemplate(
                name="technical",
                description="Technical details template",
                template_type=TemplateType.TECHNICAL,
                theme=TemplateTheme.minimalist(),
                slide_templates=["title_slide", "content_slide", "table_slide", "image_gallery", "closing_slide"],
            ),
        }

    def load_template(self, template_name: str) -> Optional[PresentationTemplate]:
        """Load a template by name."""
        # Check predefined templates first
        predefined = self.get_predefined_templates()
        if template_name in predefined:
            return predefined[template_name]

        # Check custom templates
        if template_name in self._custom_templates:
            return self._custom_templates[template_name]

        # Try to load from file
        return self._load_from_file(template_name)

    def save_template(self, template: PresentationTemplate) -> str:
        """Save a custom template.

        Args:
            template: Template to save

        Returns:
            Path to saved template file
        """
        file_path = self.templates_dir / f"{template.name}.json"
        with open(file_path, "w") as f:
            json.dump(template.to_dict(), f, indent=2)

        self._custom_templates[template.name] = template
        logger.info("Template saved: %s", file_path)
        return str(file_path)

    def _load_from_file(self, template_name: str) -> Optional[PresentationTemplate]:
        """Load template from file."""
        file_path = self.templates_dir / f"{template_name}.json"
        if not file_path.exists():
            logger.warning("Template file not found: %s", file_path)
            return None

        try:
            with open(file_path, "r") as f:
                data = json.load(f)

            theme_data = data.get("theme", {})
            theme = TemplateTheme.from_dict(theme_data)

            return PresentationTemplate(
                name=data.get("name"),
                description=data.get("description", ""),
                template_type=TemplateType(data.get("template_type", "custom")),
                theme=theme,
                slide_templates=data.get("slide_templates", []),
                page_width=data.get("page_width", 10.0),
                page_height=data.get("page_height", 7.5),
            )
        except Exception as e:
            logger.error("Failed to load template %s: %s", template_name, e)
            return None

    def delete_template(self, template_name: str) -> bool:
        """Delete a custom template."""
        file_path = self.templates_dir / f"{template_name}.json"
        if not file_path.exists():
            logger.warning("Template file not found: %s", file_path)
            return False

        file_path.unlink()
        self._custom_templates.pop(template_name, None)
        logger.info("Template deleted: %s", file_path)
        return True

    def list_all_templates(self) -> list[dict[str, Any]]:
        """List all available templates."""
        templates = []

        # Add predefined templates
        for template in self.get_predefined_templates().values():
            templates.append({
                "name": template.name,
                "description": template.description,
                "type": template.template_type.value,
                "is_custom": False,
            })

        # Add custom templates
        for template in self._custom_templates.values():
            templates.append({
                "name": template.name,
                "description": template.description,
                "type": template.template_type.value,
                "is_custom": True,
            })

        return templates

    def create_custom_template(
        self,
        name: str,
        description: str,
        template_type: str,
        theme: TemplateTheme,
        slide_templates: list[str],
    ) -> PresentationTemplate:
        """Create a custom template."""
        template = PresentationTemplate(
            name=name,
            description=description,
            template_type=TemplateType(template_type),
            theme=theme,
            slide_templates=slide_templates,
        )
        self.save_template(template)
        return template

    def get_slide_template(self, name: str) -> Optional[SlideTemplate]:
        """Get a slide template by name."""
        return TemplateLibrary.get_template(name)

    def preview_theme(self, theme_name: str) -> Optional[dict[str, Any]]:
        """Get theme preview data."""
        theme_methods = {
            "default": TemplateTheme.default,
            "corporate_blue": TemplateTheme.corporate_blue,
            "modern_dark": TemplateTheme.modern_dark,
            "minimalist": TemplateTheme.minimalist,
        }

        if theme_name not in theme_methods:
            return None

        theme = theme_methods[theme_name]()
        return {
            "name": theme.name,
            "colors": {
                "accent": theme.accent_color,
                "primary": theme.primary_color,
                "secondary": theme.secondary_color,
                "text": theme.text_color,
                "background": theme.background_color,
            },
        }
