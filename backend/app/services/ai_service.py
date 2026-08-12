"""AI Service - LLM integration for content generation"""
from typing import Optional, Dict, Any, List
import json
from app.models import Activity, ActivityMetadata


class AIService:
    """Service for AI-powered content generation"""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize AI service with optional API key"""
        self.api_key = api_key
        self.model = "gpt-4-turbo-preview"

        if api_key:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=api_key)
            except ImportError:
                raise ImportError("openai library not installed. Install with: pip install openai")
        else:
            self.client = None

    def process_activity(self, activity: Activity) -> ActivityMetadata:
        """Process activity with AI to extract metadata"""

        if not self.client:
            return self._create_empty_metadata(activity)

        try:
            # Prepare prompt
            prompt = self._prepare_activity_prompt(activity)

            # Call OpenAI
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a quality analyst that extracts structured metadata from activity descriptions. Return JSON only.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=500,
            )

            # Parse response
            content = response.choices[0].message.content
            metadata_dict = json.loads(content)

            # Create metadata
            return ActivityMetadata(
                activity_id=activity.id,
                project=metadata_dict.get("project"),
                supplier=metadata_dict.get("supplier"),
                line=metadata_dict.get("line"),
                process=metadata_dict.get("process"),
                product=metadata_dict.get("product"),
                category=metadata_dict.get("category"),
                activity_type=metadata_dict.get("activity_type"),
                defect_type=metadata_dict.get("defect_type"),
                related_kpis=metadata_dict.get("related_kpis", []),
                keywords=metadata_dict.get("keywords", []),
                technical_summary=metadata_dict.get("summary"),
            )

        except Exception as e:
            print(f"AI processing error: {str(e)}")
            return self._create_empty_metadata(activity)

    def generate_report_summary(self, activities: List[Activity]) -> str:
        """Generate AI summary of week activities"""

        if not self.client:
            return self._generate_fallback_summary(activities)

        try:
            prompt = self._prepare_summary_prompt(activities)

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a quality report writer. Generate a concise, professional summary in Portuguese.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=500,
            )

            return response.choices[0].message.content

        except Exception as e:
            print(f"Summary generation error: {str(e)}")
            return self._generate_fallback_summary(activities)

    def generate_image_caption(self, image_description: str) -> str:
        """Generate caption for image"""

        if not self.client:
            return f"Imagem: {image_description[:50]}"

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Generate a concise, professional caption in Portuguese for quality reports.",
                    },
                    {"role": "user", "content": f"Describe this image in one sentence: {image_description}"},
                ],
                temperature=0.5,
                max_tokens=100,
            )

            return response.choices[0].message.content

        except Exception:
            return image_description[:100]

    @staticmethod
    def _prepare_activity_prompt(activity: Activity) -> str:
        """Prepare activity for AI processing"""

        return f"""
Analyze this quality activity and extract structured metadata:

Title: {activity.title}
Description: {activity.description or 'N/A'}
Tags: {', '.join(activity.tags) if activity.tags else 'N/A'}
Project: {activity.project or 'N/A'}
Category: {activity.category or 'N/A'}

Extract and return JSON with these fields:
{{
  "project": "project name or null",
  "supplier": "supplier name or null",
  "line": "production line or null",
  "process": "process name or null",
  "product": "product code or null",
  "category": "quality category or null",
  "activity_type": "type of activity or null",
  "defect_type": "type of defect or null",
  "related_kpis": ["list", "of", "related", "kpis"],
  "keywords": ["extracted", "keywords"],
  "summary": "one-line technical summary"
}}
        """

    @staticmethod
    def _prepare_summary_prompt(activities: List[Activity]) -> str:
        """Prepare summary generation prompt"""

        activities_text = "\n".join(
            [f"- {a.title}: {a.description or 'N/A'}" for a in activities[:10]]
        )

        return f"""
Generate a professional weekly summary for these {len(activities)} quality activities:

{activities_text}

Write a concise summary highlighting:
1. Main issues identified
2. Areas of improvement
3. Key metrics
4. Recommended actions

Keep it to 5-7 sentences in Portuguese.
        """

    @staticmethod
    def _create_empty_metadata(activity: Activity) -> ActivityMetadata:
        """Create empty metadata when AI is unavailable"""

        return ActivityMetadata(
            activity_id=activity.id,
            related_kpis=[],
            keywords=activity.tags or [],
            technical_summary=activity.description[:200] if activity.description else None,
        )

    @staticmethod
    def _generate_fallback_summary(activities: List[Activity]) -> str:
        """Generate fallback summary without AI"""

        return f"""
Resumo da Semana: {len(activities)} atividades registradas.

Categorias: {', '.join(set(a.category for a in activities if a.category))}
Projetos: {', '.join(set(a.project for a in activities if a.project))}

Total de arquivos: {sum(len(a.attachments) for a in activities if a.attachments)}

Relatório gerado automaticamente pelo QWI.
        """
