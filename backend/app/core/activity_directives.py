"""Parse inline commands embedded in activity descriptions."""

from __future__ import annotations

import re
from dataclasses import dataclass

# Lines starting with / that request image vision analysis
_ANALYZE_IMAGE_PATTERNS = (
    re.compile(r"(?im)^/\s*analisar\s+imagem\b.*$"),
    re.compile(r"(?im)^/\s*quero\s+que\s+(?:vc|voce|a\s+ia)\s+analis(?:e|ar)\s+(?:a\s+)?imagem\b.*$"),
    re.compile(r"(?im)^/\s*analyze\s+image\b.*$"),
    re.compile(r"(?im)^/\s*analyse\s+image\b.*$"),
)


@dataclass(frozen=True)
class ActivityDirectives:
    analyze_images: bool
    clean_description: str


def parse_activity_directives(description: str | None) -> ActivityDirectives:
    """Extract directives from the registration text and return cleaned description."""
    if not description or not description.strip():
        return ActivityDirectives(analyze_images=False, clean_description="")

    analyze_images = False
    cleaned_lines: list[str] = []
    for line in description.splitlines():
        stripped = line.strip()
        if any(pattern.match(stripped) for pattern in _ANALYZE_IMAGE_PATTERNS):
            analyze_images = True
            continue
        cleaned_lines.append(line)

    clean = "\n".join(cleaned_lines).strip()
    clean = re.sub(r"\n{3,}", "\n\n", clean)
    return ActivityDirectives(analyze_images=analyze_images, clean_description=clean)


def activity_requests_image_analysis(activity) -> bool:
    """Whether the activity description explicitly requests image vision analysis."""
    return parse_activity_directives(getattr(activity, "description", None)).analyze_images
