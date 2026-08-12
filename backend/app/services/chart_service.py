"""Chart generation service for PPTX presentations."""

import io
import logging
from pathlib import Path
from typing import Any, Optional

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

from app.core.config import get_settings
from app.services.pptx_templates import TemplateTheme

logger = logging.getLogger(__name__)
settings = get_settings()

# Use non-interactive backend for server environments
matplotlib.use("Agg")


class ChartService:
    """Service for generating charts as images."""

    def __init__(self, output_dir: Optional[str] = None):
        """Initialize chart service.

        Args:
            output_dir: Directory to save generated chart images
        """
        upload_root = Path(settings.UPLOAD_DIR)
        self.output_dir = Path(output_dir) if output_dir else upload_root / "charts"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_chart(
        self,
        data: dict[str, Any],
        chart_type: str = "bar",
        theme: Optional[TemplateTheme] = None,
        filename: Optional[str] = None,
    ) -> Optional[str]:
        """Generate a chart image.

        Args:
            data: Chart data (categories, series, values)
            chart_type: Type of chart (bar, column, line, pie)
            theme: Theme configuration
            filename: Output filename (auto-generated if not provided)

        Returns:
            Path to generated chart image or None if failed
        """
        theme = theme or TemplateTheme.default()

        try:
            if chart_type == "bar":
                return self._generate_bar_chart(data, theme, filename)
            elif chart_type == "column":
                return self._generate_column_chart(data, theme, filename)
            elif chart_type == "line":
                return self._generate_line_chart(data, theme, filename)
            elif chart_type == "pie":
                return self._generate_pie_chart(data, theme, filename)
            else:
                logger.warning("Unknown chart type: %s", chart_type)
                return None
        except Exception as e:
            logger.error("Chart generation failed: %s", e)
            return None

    def _generate_bar_chart(
        self,
        data: dict[str, Any],
        theme: TemplateTheme,
        filename: Optional[str] = None,
    ) -> Optional[str]:
        """Generate a horizontal bar chart."""
        try:
            categories = data.get("categories", [])
            series = data.get("series", [])

            if not categories or not series:
                return None

            fig, ax = plt.subplots(figsize=(10, 6))
            fig.patch.set_facecolor(self._rgb_to_hex(theme.background_color))

            # Prepare data
            y_pos = np.arange(len(categories))
            colors = self._get_series_colors(len(series), theme)

            # Plot bars
            for idx, s in enumerate(series):
                values = s.get("values", [])
                ax.barh(
                    y_pos + (idx * 0.25),
                    values,
                    0.25,
                    label=s.get("name", f"Series {idx + 1}"),
                    color=self._rgb_to_hex(colors[idx]),
                )

            # Customize chart
            ax.set_yticks(y_pos + 0.25 * (len(series) - 1) / 2)
            ax.set_yticklabels(categories)
            ax.invert_yaxis()
            ax.set_xlabel(data.get("x_label", ""))
            ax.set_title(data.get("title", "Bar Chart"), fontweight="bold", fontsize=14)

            # Styling
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.set_facecolor(self._rgb_to_hex(theme.background_color))
            ax.tick_params(colors=self._rgb_to_hex(theme.text_color))

            if len(series) > 1:
                ax.legend()

            plt.tight_layout()
            return self._save_figure(fig, filename or "bar_chart.png")
        finally:
            plt.close()

    def _generate_column_chart(
        self,
        data: dict[str, Any],
        theme: TemplateTheme,
        filename: Optional[str] = None,
    ) -> Optional[str]:
        """Generate a vertical column chart."""
        try:
            categories = data.get("categories", [])
            series = data.get("series", [])

            if not categories or not series:
                return None

            fig, ax = plt.subplots(figsize=(10, 6))
            fig.patch.set_facecolor(self._rgb_to_hex(theme.background_color))

            # Prepare data
            x_pos = np.arange(len(categories))
            colors = self._get_series_colors(len(series), theme)

            # Plot columns
            for idx, s in enumerate(series):
                values = s.get("values", [])
                ax.bar(
                    x_pos + (idx * 0.25),
                    values,
                    0.25,
                    label=s.get("name", f"Series {idx + 1}"),
                    color=self._rgb_to_hex(colors[idx]),
                )

            # Customize chart
            ax.set_xticks(x_pos + 0.25 * (len(series) - 1) / 2)
            ax.set_xticklabels(categories, rotation=45, ha="right")
            ax.set_ylabel(data.get("y_label", ""))
            ax.set_title(data.get("title", "Column Chart"), fontweight="bold", fontsize=14)

            # Styling
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.set_facecolor(self._rgb_to_hex(theme.background_color))
            ax.tick_params(colors=self._rgb_to_hex(theme.text_color))

            if len(series) > 1:
                ax.legend()

            plt.tight_layout()
            return self._save_figure(fig, filename or "column_chart.png")
        finally:
            plt.close()

    def _generate_line_chart(
        self,
        data: dict[str, Any],
        theme: TemplateTheme,
        filename: Optional[str] = None,
    ) -> Optional[str]:
        """Generate a line chart."""
        try:
            categories = data.get("categories", [])
            series = data.get("series", [])

            if not categories or not series:
                return None

            fig, ax = plt.subplots(figsize=(10, 6))
            fig.patch.set_facecolor(self._rgb_to_hex(theme.background_color))

            # Prepare data
            x_pos = np.arange(len(categories))
            colors = self._get_series_colors(len(series), theme)

            # Plot lines
            for idx, s in enumerate(series):
                values = s.get("values", [])
                ax.plot(
                    x_pos,
                    values,
                    marker="o",
                    label=s.get("name", f"Series {idx + 1}"),
                    color=self._rgb_to_hex(colors[idx]),
                    linewidth=2,
                )

            # Customize chart
            ax.set_xticks(x_pos)
            ax.set_xticklabels(categories, rotation=45, ha="right")
            ax.set_ylabel(data.get("y_label", ""))
            ax.set_title(data.get("title", "Line Chart"), fontweight="bold", fontsize=14)

            # Styling
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.set_facecolor(self._rgb_to_hex(theme.background_color))
            ax.tick_params(colors=self._rgb_to_hex(theme.text_color))
            ax.grid(True, alpha=0.3)

            if len(series) > 1:
                ax.legend()

            plt.tight_layout()
            return self._save_figure(fig, filename or "line_chart.png")
        finally:
            plt.close()

    def _generate_pie_chart(
        self,
        data: dict[str, Any],
        theme: TemplateTheme,
        filename: Optional[str] = None,
    ) -> Optional[str]:
        """Generate a pie chart."""
        try:
            categories = data.get("categories", [])
            values = data.get("values", [])

            if not categories or not values:
                return None

            fig, ax = plt.subplots(figsize=(8, 8))
            fig.patch.set_facecolor(self._rgb_to_hex(theme.background_color))

            colors = self._get_series_colors(len(categories), theme)
            colors = [self._rgb_to_hex(c) for c in colors]

            # Plot pie
            wedges, texts, autotexts = ax.pie(
                values,
                labels=categories,
                autopct="%1.1f%%",
                colors=colors,
                startangle=90,
            )

            # Customize
            for autotext in autotexts:
                autotext.set_color(self._rgb_to_hex(theme.background_color))
                autotext.set_fontweight("bold")

            ax.set_title(data.get("title", "Pie Chart"), fontweight="bold", fontsize=14)

            plt.tight_layout()
            return self._save_figure(fig, filename or "pie_chart.png")
        finally:
            plt.close()

    def generate_statistics_chart(
        self,
        stats: dict[str, Any],
        theme: Optional[TemplateTheme] = None,
    ) -> Optional[str]:
        """Generate a chart from statistics data."""
        theme = theme or TemplateTheme.default()

        try:
            # Extract data from stats
            labels = list(stats.keys())
            values = list(stats.values())

            # Create simple bar chart
            fig, ax = plt.subplots(figsize=(10, 6))
            fig.patch.set_facecolor(self._rgb_to_hex(theme.background_color))

            colors = self._get_series_colors(len(labels), theme)
            ax.bar(range(len(labels)), values, color=[self._rgb_to_hex(c) for c in colors])

            ax.set_xticks(range(len(labels)))
            ax.set_xticklabels(labels, rotation=45, ha="right")
            ax.set_title("Statistics", fontweight="bold", fontsize=14)

            # Styling
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.set_facecolor(self._rgb_to_hex(theme.background_color))

            plt.tight_layout()
            return self._save_figure(fig, "statistics.png")
        except Exception as e:
            logger.error("Statistics chart generation failed: %s", e)
            return None
        finally:
            plt.close()

    def generate_heatmap(
        self,
        data: list[list[float]],
        x_labels: list[str],
        y_labels: list[str],
        theme: Optional[TemplateTheme] = None,
    ) -> Optional[str]:
        """Generate a heatmap."""
        theme = theme or TemplateTheme.default()

        try:
            import matplotlib.patches as mpatches

            fig, ax = plt.subplots(figsize=(10, 6))
            fig.patch.set_facecolor(self._rgb_to_hex(theme.background_color))

            # Create heatmap
            im = ax.imshow(data, cmap="YlOrRd", aspect="auto")

            # Set ticks and labels
            ax.set_xticks(np.arange(len(x_labels)))
            ax.set_yticks(np.arange(len(y_labels)))
            ax.set_xticklabels(x_labels, rotation=45, ha="right")
            ax.set_yticklabels(y_labels)

            # Add colorbar
            cbar = plt.colorbar(im, ax=ax)
            cbar.set_label("Value", rotation=270, labelpad=15)

            plt.tight_layout()
            return self._save_figure(fig, "heatmap.png")
        except Exception as e:
            logger.error("Heatmap generation failed: %s", e)
            return None
        finally:
            plt.close()

    # ==================== Private helper methods ====================

    def _save_figure(self, fig, filename: str) -> str:
        """Save figure to file and return path."""
        output_path = self.output_dir / filename
        fig.savefig(
            output_path,
            dpi=150,
            bbox_inches="tight",
            facecolor=fig.get_facecolor(),
        )
        logger.info("Chart saved: %s", output_path)
        return str(output_path)

    @staticmethod
    def _rgb_to_hex(rgb: tuple) -> str:
        """Convert RGB tuple to hex color."""
        return "#{:02x}{:02x}{:02x}".format(int(rgb[0]), int(rgb[1]), int(rgb[2]))

    @staticmethod
    def _get_series_colors(count: int, theme: TemplateTheme) -> list[tuple]:
        """Get a list of colors for series."""
        colors = [
            theme.accent_color,
            theme.secondary_color,
            theme.success_color,
            theme.warning_color,
            theme.error_color,
            theme.highlight_color,
        ]

        # If more colors are needed, generate additional ones
        if count > len(colors):
            for i in range(count - len(colors)):
                # Generate complementary colors
                base = theme.accent_color
                shift = (i + 1) * 30
                r = (base[0] + shift) % 256
                g = (base[1] + shift) % 256
                b = (base[2] + shift) % 256
                colors.append((r, g, b))

        return colors[:count]

    def cleanup_old_charts(self, days: int = 7) -> int:
        """Delete chart images older than specified days.

        Args:
            days: Number of days to keep

        Returns:
            Number of files deleted
        """
        import time

        current_time = time.time()
        deleted_count = 0
        cutoff_time = current_time - (days * 24 * 60 * 60)

        for file_path in self.output_dir.glob("*.png"):
            if file_path.stat().st_mtime < cutoff_time:
                file_path.unlink()
                deleted_count += 1

        if deleted_count > 0:
            logger.info("Cleaned up %d old chart files", deleted_count)

        return deleted_count
