from dataclasses import dataclass, field

from app.models import Language, ObjectivityLevel, QualitySector, TechnicalLevel, User, WritingTone


@dataclass
class PromptSection:
    name: str
    content: str


@dataclass
class ComposedPrompt:
    system_prompt: str
    user_prompt: str
    sections: list[PromptSection] = field(default_factory=list)

    @property
    def full_prompt(self) -> str:
        return f"SYSTEM:\n{self.system_prompt}\n\nUSER:\n{self.user_prompt}"


TONE_PROMPTS = {
    WritingTone.ANALYST: "Write as a quality analyst. Focus on data, metrics, and detailed observations.",
    WritingTone.SPECIALIST: "Write as a quality specialist. Balance technical detail with practical insights.",
    WritingTone.SUPERVISOR: "Write as a quality supervisor. Emphasize team performance and process adherence.",
    WritingTone.MANAGER: "Write as a quality manager. Focus on strategic impact and departmental goals.",
    WritingTone.DIRECTOR: "Write as a quality director. Use executive language, highlight business impact.",
}

OBJECTIVITY_PROMPTS = {
    ObjectivityLevel.LOW: "Use descriptive language with context and background information.",
    ObjectivityLevel.MEDIUM: "Balance description with actionable insights.",
    ObjectivityLevel.HIGH: "Be extremely objective. No filler words. Direct statements only.",
}

TECHNICAL_PROMPTS = {
    TechnicalLevel.LOW: "Use accessible language understandable by non-technical stakeholders.",
    TechnicalLevel.MEDIUM: "Use standard quality engineering terminology.",
    TechnicalLevel.HIGH: "Use advanced technical language appropriate for engineering specialists.",
}

LANGUAGE_PROMPTS = {
    Language.PT: "Write ALL report content in Brazilian Portuguese.",
    Language.EN: "Write ALL report content in English.",
}

DEPARTMENT_CONTEXT = """You write for the Quality department of the MX CS division. The department is composed of these sectors:
- QM (Quality Management): quality system management, audits, procedures, and quality planning.
- QA (Quality Assurance): process assurance, prevention, and compliance across production.
- OQC (Outgoing Quality Control): final inspection of finished products before shipment.
- IQC (Incoming Quality Control): inspection of incoming materials and supplier quality.
- FIELD: field quality, market returns, and customer-side failure analysis.
- CSI (innovation sector inside Quality): develops software and automation solutions to improve quality performance and activities.
When an activity clearly belongs to one of these sectors, name the sector explicitly. Use the department's terminology (NC, PPM, FPY, retrabalho/rework, plano de ação/action plan, FMEA, 8D, etc.) correctly."""

ANALYSIS_MANDATE = """EXECUTIVE WRITING MANDATE — the reader is senior management with no time:
1. Write like a quality analyst, not like an AI assistant. Each sentence must state a decision, number, or status — nothing else.
2. FORBIDDEN phrasing (never use): "indica que", "sugere que", "demonstra", "avanço significativo", "em conclusão", "vale ressaltar", "it is worth noting", "indicates that", "suggests that", "demonstrates that", "in conclusion".
3. Per activity: factual title (≤6 words) + at most 1–2 direct sentences OR short objective bullets. No interpretive paragraphs.
4. CONTENT MODE — choose per activity before writing:
   - transcribe: registration text is already clear, professional, and executive-ready → copy with minimal edits (typos, standardization only). Do NOT rewrite.
   - compress: text is long, informal, repetitive, or lacks a clear conclusion → extract only conclusion + numeric facts.
5. Documents and spreadsheets: extract numbers and conclusions only; do not add interpretive prose.
6. Images marked "visual reference only" in the dossier are NOT analyzed — do not describe their content unless analyze_images_requested=True for that activity.
7. When analyze_images_requested=True, add at most ONE objective sentence on what the image shows (from ai_analysis), never a paragraph."""

SECTOR_PLAYBOOKS: dict[QualitySector, str] = {
    QualitySector.FIELD: """FIELD SECTOR PLAYBOOK — the author is a field quality analyst reporting device/market failures:
- For each activity, classify activity_kind as one of: field_failure, market_return, customer_complaint, field_audit, measurement_analysis.
- When evidence mentions a product/device, extract: model, serial/code, failure mode, customer/location, quantity affected.
- When measurements exist (spreadsheet or image), list each parameter with value, unit, limit/spec and pass/fail status.
- Countermeasures must include action, owner, status and due date when present in evidence.
- Typical visual needs: device_info block, measurement_table, image_row (evidence photos), countermeasure_table, chart (defect trend or KPI) ONLY when numeric series exist.""",
    QualitySector.IQC: """IQC SECTOR PLAYBOOK — incoming material and supplier quality:
- Classify activity_kind as: incoming_inspection, supplier_audit, material_disposition, ppm_review, supplier_escalation.
- Extract: supplier, lot/batch, part number, qty inspected, defect qty/rate, disposition (accept/reject/hold/sort).
- Connect spreadsheet PPM/defect data to supplier risk and incoming hold decisions.
- Typical visual needs: generic_table (lot summary), kpi_table, chart (PPM trend) when time series exist.""",
    QualitySector.OQC: """OQC SECTOR PLAYBOOK — outgoing/final inspection:
- Classify activity_kind as: final_inspection, shipment_hold, line_audit, fpy_review, customer_shipment.
- Extract: line, product/model, lot, FPY/defect rate, blocked qty, release status.
- Typical visual needs: kpi_table, generic_table, chart (FPY or defect Pareto) when numbers exist.""",
    QualitySector.QM: """QM SECTOR PLAYBOOK — quality system and audits:
- Classify activity_kind as: system_audit, procedure_update, nc_management, management_review, action_plan.
- Extract: audit finding, NC number, severity, root cause status, action plan owner/deadline.
- Typical visual needs: generic_table (findings), countermeasure_table.""",
    QualitySector.QA: """QA SECTOR PLAYBOOK — process assurance:
- Classify activity_kind as: process_audit, cpk_study, fmea_update, line_validation, preventive_action.
- Extract: process, line, parameter, capability result, risk level, preventive action status.
- Typical visual needs: generic_table, measurement_table when applicable.""",
    QualitySector.CSI: """CSI SECTOR PLAYBOOK — quality innovation and software:
- Classify activity_kind as: software_delivery, automation, dashboard, ai_module, process_improvement.
- Extract: deliverable, KPI impacted, users/processes benefited, completion status.
- Typical visual needs: chart (progress/KPI) when numbers exist; keep narrative executive.""",
}

SUPPORTED_BLOCKS_DOC = """Supported visual block types for the presentation plan (use ONLY these):
- device_info: {type, title?, fields: {label: value}} — product/device identification
- measurement_table: {type, title, columns[], rows[][]} — parametric measurements
- generic_table: {type, title, columns[], rows[][]} — audit findings, lots, any tabular data
- countermeasure_table: {type, title, rows[{action, owner, status, due}]}
- chart: {type, title, chart_type, categories[], series[{name, values[]}], insight?} — ONLY with real numbers
- image_row: {type, title?, images[{attachment_id, caption?}]} — reference photos (max 3 per row)
- text / highlight: {type, text} — analytical emphasis"""


class PromptComposer:
    """Composes prompts for weekly analysis, presentation planning, and activity metadata."""

    def _profile_sections(
        self,
        user: User,
        language: Language | None,
    ) -> list[PromptSection]:
        profile = user.writing_profile
        sections: list[PromptSection] = []

        if language:
            sections.append(PromptSection("Language", LANGUAGE_PROMPTS.get(language, "")))
        elif profile:
            sections.append(
                PromptSection("Language", LANGUAGE_PROMPTS.get(profile.default_language, ""))
            )

        if profile:
            sections.append(
                PromptSection("Writing Tone", TONE_PROMPTS.get(profile.writing_tone, ""))
            )
            sections.append(
                PromptSection("Objectivity", OBJECTIVITY_PROMPTS.get(profile.objectivity, ""))
            )
            sections.append(
                PromptSection(
                    "Technical Level",
                    TECHNICAL_PROMPTS.get(profile.technical_level, ""),
                )
            )
            if profile.personal_prompt:
                sections.append(
                    PromptSection("Personal Instructions", profile.personal_prompt)
                )
            if not profile.auto_conclusions:
                sections.append(
                    PromptSection(
                        "Conclusions",
                        "Do NOT include a CONCLUSIONS section in the draft.",
                    )
                )
            if not profile.auto_next_steps:
                sections.append(
                    PromptSection(
                        "Next Steps",
                        "Do NOT include a NEXT STEPS section in the draft.",
                    )
                )
            if not profile.auto_impact:
                sections.append(
                    PromptSection(
                        "Impact",
                        "Do NOT write impact lines per activity unless explicitly supported by evidence.",
                    )
                )
        return sections

    def compose_weekly_prompt(
        self,
        user: User,
        evidence_dossier: str,
        week_number: int,
        year: int,
        language: Language | None = None,
        period_label: str | None = None,
        attachment_inventory: str | None = None,
    ) -> ComposedPrompt:
        """Step 1: deep analytical draft."""
        sector = getattr(user, "sector", QualitySector.CSI)
        sector_playbook = SECTOR_PLAYBOOKS.get(sector, SECTOR_PLAYBOOKS[QualitySector.CSI])
        sections = self._profile_sections(user, language)

        system_parts = [
            "You are Quality Weekly Intelligence (QWI), the senior quality analyst AI of the MX CS Quality department. You produce the weekly report presented to senior management.",
            DEPARTMENT_CONTEXT,
            ANALYSIS_MANDATE,
            f"The report author belongs to sector {sector.value}. Apply this sector playbook:\n{sector_playbook}",
            "Never invent information not present in the provided evidence. When impact is not supported by the data, write 'no measured impact' instead of speculating.",
            "Write an executive report DRAFT with exactly these sections (internal use only — SUMMARY/HIGHLIGHTS/CONCLUSIONS are NOT rendered in the PPT):",
            "SUMMARY: one sentence, most decision-relevant finding with a number if available.",
            "HIGHLIGHTS: 2 to 3 short findings (max 8 words each).",
            "ACTIVITIES: one entry per '### Activity N' block — no more, no less. Keep dossier activity number. Order by relevance. For each:",
            "  - Content mode: transcribe | compress (see mandate).",
            "  - Activity kind: classify per sector playbook.",
            "  - Title: max 6 words, factual.",
            "  - Date: dd/mm from dossier.",
            "  - Narrative: in transcribe mode, cleaned registration text; in compress mode, 1–2 direct sentences max.",
            "  - Structured data: device fields, measurements, countermeasures when evidence supports (write 'none' when absent).",
            "  - Facts: up to 4 short bullets with numbers/codes from evidence.",
            "  - Treatments: up to 3 corrective actions, or 'none'.",
            "  - Impact: factual outcome with numbers, or 'no measured impact'.",
            "KPIS: indicator names present in evidence.",
            "KPI TABLE: rows 'KPI | result | trend' with trend ▲/▼/► when numbers exist; else 'none'.",
            "CONCLUSIONS: at most 2 cross-activity takeaways (internal only).",
            "NEXT STEPS: at most 2 concrete actions (internal only).",
            "ARCHETYPE: executivo | operacional | analitico.",
        ]

        sections.append(
            PromptSection(
                "Author",
                f"Sector: {sector.value} | Department: {user.department} | Role: {user.role}",
            )
        )

        period = f"Week {week_number} of {year}"
        if period_label:
            period += f" ({period_label})"
        sections.append(PromptSection("Reporting Period", period))

        if attachment_inventory:
            sections.append(
                PromptSection("Attachment Inventory", attachment_inventory)
            )

        sections.append(
            PromptSection(
                "Evidence Dossier",
                "Complete evidence for the period. Base ALL analysis strictly on this dossier.\n\n"
                + evidence_dossier,
            )
        )

        sections.append(
            PromptSection(
                "Output",
                "Write the analytical draft with sections SUMMARY, HIGHLIGHTS, ACTIVITIES, "
                "KPIS, KPI TABLE, CONCLUSIONS, NEXT STEPS and ARCHETYPE. "
                "Cover EVERY dossier activity with its number.",
            )
        )

        user_prompt = "\n\n".join(f"## {s.name}\n{s.content}" for s in sections if s.content)
        return ComposedPrompt(
            system_prompt="\n".join(system_parts),
            user_prompt=user_prompt,
            sections=sections,
        )

    def compose_presentation_plan_prompt(
        self,
        user: User,
        analysis_draft: str,
        attachment_inventory: str,
        language: Language | None = None,
    ) -> ComposedPrompt:
        """Step 2: editorial plan — which blocks and layout profile to use."""
        sector = getattr(user, "sector", QualitySector.CSI)
        sector_playbook = SECTOR_PLAYBOOKS.get(sector, SECTOR_PLAYBOOKS[QualitySector.CSI])

        system_parts = [
            "You are the presentation editor for Quality Weekly Intelligence (QWI).",
            "Given a completed analytical draft and attachment inventory, design the optimal PowerPoint structure.",
            SUPPORTED_BLOCKS_DOC,
            f"Author sector: {sector.value}. Sector playbook:\n{sector_playbook}",
            "Rules:",
            "- Choose layout_profile: executive (few activities, decision focus), operational (many activities + evidence), analytical (KPIs/charts dominate), field_case (device failure analysis with measurements and photos).",
            "- For field_case: dedicate rich blocks (device_info, measurement_table, image_row, countermeasure_table) to critical activities.",
            "- Propose charts ONLY when the draft or attachments contain real numeric series — never invent data.",
            "- Map images using attachment_id from the inventory.",
            "- Order activities by management relevance.",
            "- sidebar must be empty [] — the PPT shows activities only, full-width, no global synthesis sidebar.",
        ]

        if language:
            lang_note = LANGUAGE_PROMPTS.get(language, "")
        elif user.writing_profile:
            lang_note = LANGUAGE_PROMPTS.get(user.writing_profile.default_language, "")
        else:
            lang_note = ""

        user_prompt = f"""## Language
{lang_note}

## Analytical Draft
{analysis_draft}

## Attachment Inventory
{attachment_inventory}

## Output
Write a PRESENTATION PLAN draft with:
LAYOUT PROFILE: executive | operational | analytical | field_case
SIDEBAR: (always empty — no sidebar in executive PPT)
GLOBAL BLOCKS: any week-level charts or tables (describe each block type and data)
ACTIVITIES: for each activity (by dossier number), list:
  - source number
  - recommended blocks in render order (type + key data, attachment_ids for images)
  - whether it deserves a full-width slide (yes/no)
"""
        return ComposedPrompt(system_prompt="\n".join(system_parts), user_prompt=user_prompt)

    def compose_activity_analysis_prompt(self, title: str, description: str, tags: list[str]) -> str:
        return (
            f"Analyze this quality activity from the MX CS Quality department "
            f"(sectors: QM, QA, OQC, IQC, FIELD, CSI) and extract structured metadata:\n"
            f"Title: {title}\n"
            f"Description: {description or 'N/A'}\n"
            f"Tags: {', '.join(tags) if tags else 'N/A'}\n"
        )
