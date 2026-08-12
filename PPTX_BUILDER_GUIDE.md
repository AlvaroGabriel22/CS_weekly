# PPTX Builder System - Comprehensive Guide

## Overview

The PPTX Builder System provides production-grade presentation generation capabilities for QWI (Quality Weekly Intelligence) reports. It includes:

- **Backend Services**: PPTX generation, template management, chart generation
- **Frontend Components**: Interactive editor for customizing presentations
- **API Routes**: REST endpoints for generation and management
- **Theme System**: Predefined themes with customization support

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React)                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ PPTXEditor Component                                │   │
│  │ - Slide management                                  │   │
│  │ - Theme/template selection                          │   │
│  │ - Preview and export                                │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ usePPTXEditor Hook                                  │   │
│  │ - State management                                  │   │
│  │ - PPTX generation API calls                         │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP/REST
┌──────────────────────▼──────────────────────────────────────┐
│                    Backend (FastAPI)                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ API Routes (app/api/routes/pptx.py)                 │   │
│  │ - /pptx/generate                                    │   │
│  │ - /pptx/templates/*                                 │   │
│  │ - /pptx/themes/*                                    │   │
│  │ - /pptx/export/*                                    │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ PPTXBuilder (pptx_builder.py)                       │   │
│  │ - Main PPTX generation engine                       │   │
│  │ - Slide composition                                 │   │
│  │ - Theme application                                 │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ TemplateEngine (pptx_templates.py)                  │   │
│  │ - Template management                               │   │
│  │ - Theme definitions                                 │   │
│  │ - Slide templates                                   │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ ChartService (chart_service.py)                     │   │
│  │ - Chart generation (matplotlib)                     │   │
│  │ - Image export                                      │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Backend Services

### 1. PPTXBuilder (`backend/app/services/pptx_builder.py`)

Main service for generating PPTX presentations.

#### Key Methods

```python
# Create and configure presentation
builder = PPTXBuilder(template_theme=TemplateTheme.default())
pres = builder.create_presentation()

# Add slides
builder.add_title_slide(
    title="Weekly Report",
    subtitle="Week 32, 2024",
    date="2024-08-10",
    author="QWI System"
)

builder.add_content_slide(
    title="Summary",
    content="Key findings...",
    images=["path/to/image.jpg"]
)

builder.add_chart_slide(
    title="Performance Metrics",
    data={
        "categories": ["Mon", "Tue", "Wed"],
        "series": [{"name": "Issues", "values": [5, 3, 2]}]
    },
    chart_type="bar"
)

builder.add_table_slide(
    title="KPIs",
    data=[["Defect Rate", "2.1%"], ["Cycle Time", "45 min"]],
    headers=["Metric", "Value"]
)

builder.add_image_slide(
    title="Evidence",
    images=["path/to/img1.jpg", "path/to/img2.jpg"]
)

builder.add_summary_slide({
    "Total Activities": 5,
    "Completed": 5,
    "Issues": 1
})

# Generate complete PPTX
pptx_path = builder.generate_pptx(
    weekly_report=report_data,
    template_name="executive",
    filename="weekly_report.pptx"
)
```

#### Features

- **Dynamic slide creation**: Add slides programmatically
- **Theme support**: Apply consistent styling
- **Image handling**: Auto-resize and position images
- **Chart integration**: Embed generated charts
- **Multiple export formats**: PPTX, PDF (with LibreOffice)

### 2. TemplateEngine (`backend/app/services/pptx_templates.py`)

Manages presentation templates and themes.

#### Predefined Templates

1. **Executive** - High-level summary template
   - Focus: Key metrics and decisions
   - Layout: 2-column with sidebar

2. **Operational** - Detailed operations template
   - Focus: Process details and actions
   - Layout: Multi-column with tables

3. **Analytical** - Data-driven template
   - Focus: Charts and statistics
   - Layout: Chart-heavy with minimal text

4. **Technical** - Technical details template
   - Focus: Specifications and measurements
   - Layout: Tables and images

#### Predefined Themes

1. **Default** - Standard business theme
2. **Corporate Blue** - Professional blue palette
3. **Modern Dark** - Dark mode with blue accents
4. **Minimalist** - Clean, minimal design

#### Usage

```python
from app.services.pptx_templates import TemplateEngine, TemplateTheme

engine = TemplateEngine()

# Load predefined template
template = engine.load_template("executive")

# Get theme
theme = TemplateTheme.corporate_blue()

# Create custom template
custom = engine.create_custom_template(
    name="my_template",
    description="Custom QWI template",
    template_type="custom",
    theme=TemplateTheme.default(),
    slide_templates=["title_slide", "content_slide", "chart_slide"]
)

# Save custom template
engine.save_template(custom)

# List templates
templates = engine.list_all_templates()
```

### 3. ChartService (`backend/app/services/chart_service.py`)

Generates charts as images for embedding in presentations.

#### Supported Chart Types

```python
service = ChartService()

# Bar chart
service.generate_chart(
    data={
        "title": "Activities by Status",
        "categories": ["Completed", "In Progress", "Pending"],
        "series": [{"name": "Count", "values": [10, 5, 3]}]
    },
    chart_type="bar"
)

# Pie chart
service.generate_chart(
    data={
        "title": "Distribution",
        "categories": ["Category A", "Category B", "Category C"],
        "values": [40, 30, 30]
    },
    chart_type="pie"
)

# Line chart
service.generate_chart(
    data={
        "title": "Trend",
        "categories": ["Week 1", "Week 2", "Week 3", "Week 4"],
        "series": [
            {"name": "Issues", "values": [10, 8, 5, 3]},
            {"name": "Resolved", "values": [8, 7, 5, 3]}
        ]
    },
    chart_type="line"
)

# Column chart
service.generate_chart(
    data={
        "title": "Comparison",
        "categories": ["Jan", "Feb", "Mar"],
        "series": [
            {"name": "Target", "values": [100, 110, 120]},
            {"name": "Actual", "values": [95, 105, 118]}
        ]
    },
    chart_type="column"
)

# Heatmap
service.generate_heatmap(
    data=[[1, 2, 3], [4, 5, 6]],
    x_labels=["A", "B", "C"],
    y_labels=["X", "Y"]
)
```

## API Routes

### Generate PPTX

**POST** `/api/pptx/generate`

Request:
```json
{
  "report_id": "week_32_2024",
  "report_data": {
    "title": "Weekly Report",
    "department": "QA",
    "summary": "...",
    "activities": [...],
    "kpi_table": [...]
  },
  "template": "executive",
  "theme": "corporate_blue"
}
```

Response:
```json
{
  "pptx_path": "/path/to/report.pptx",
  "filename": "report.pptx",
  "size": 1024000,
  "created_at": "2024-08-10T10:30:00"
}
```

### Generate with Custom Slides

**POST** `/api/pptx/generate-with-slides`

```json
{
  "report_id": "week_32_2024",
  "template": "executive",
  "theme": "default",
  "slides": [
    {
      "id": "slide-1",
      "type": "title",
      "title": "Weekly Report",
      "content": "Week 32, 2024"
    },
    {
      "id": "slide-2",
      "type": "content",
      "title": "Summary",
      "content": "Key findings..."
    }
  ]
}
```

### Template Management

**GET** `/api/pptx/templates/list` - List all templates

**GET** `/api/pptx/templates/{name}` - Get template details

**POST** `/api/pptx/templates/create` - Create custom template

**DELETE** `/api/pptx/templates/{name}` - Delete template

**POST** `/api/pptx/templates/upload` - Upload PPTX template

### Theme Management

**GET** `/api/pptx/themes/list` - List available themes

**GET** `/api/pptx/themes/{name}` - Get theme details

### Export

**POST** `/api/pptx/export/pdf/{pptx_id}` - Export to PDF

**POST** `/api/pptx/export/docx/{pptx_id}` - Export to DOCX

### File Management

**GET** `/api/pptx/files/list` - List generated files

**DELETE** `/api/pptx/files/{filename}` - Delete file

## Frontend Components

### PPTXEditor Component

Interactive editor for customizing PPTX presentations.

```tsx
import { PPTXEditor } from "@/components/weekly/PPTXEditor";

<PPTXEditor
  isOpen={isOpen}
  onClose={handleClose}
  reportData={weeklyReport}
  onGenerate={async (slides, config) => {
    // Generate PPTX
    const result = await generatePPTX(slides, config);
  }}
/>
```

#### Features

- **Slide Manager**: Add, remove, reorder slides
- **Slide Editor**: Edit title and content
- **Template Selection**: Choose from predefined templates
- **Theme Customization**: Select color schemes
- **Preview**: View slide structure and layout
- **Export**: Download PPTX, PDF, DOCX

### usePPTXEditor Hook

State management and operations for PPTX editing.

```typescript
const {
  slides,
  selectedSlideId,
  isGenerating,
  error,
  pptxPath,
  
  addSlide,
  deleteSlide,
  updateSlide,
  moveSlide,
  selectSlide,
  getSelectedSlide,
  generatePPTX,
  downloadPPTX,
  exportToPDF,
  cancel,
  clearError,
  reset,
} = usePPTXEditor(reportData);
```

## Usage Examples

### Basic PPTX Generation

```python
from app.services.pptx_builder import PPTXBuilder

builder = PPTXBuilder()
pptx_path = builder.generate_pptx(
    weekly_report={
        "title": "Weekly Report",
        "summary": "This week...",
        "activities": [],
        "kpi_table": [],
    },
    template_name="executive"
)
```

### Custom Theme

```python
from app.services.pptx_builder import PPTXBuilder
from app.services.pptx_templates import TemplateTheme

theme = TemplateTheme(
    name="custom",
    accent_color=(255, 0, 0),  # Red
    text_color=(0, 0, 0),
    background_color=(255, 255, 255)
)

builder = PPTXBuilder(theme=theme)
```

### Full Workflow

```python
from app.services.pptx_builder import PPTXBuilder
from app.services.pptx_templates import TemplateTheme

# Create builder with theme
theme = TemplateTheme.corporate_blue()
builder = PPTXBuilder(theme=theme)

# Create presentation
builder.create_presentation()

# Add slides
builder.add_title_slide(
    title="Quality Weekly Report",
    subtitle="Week 32, 2024",
    author="QWI System"
)

builder.add_content_slide(
    title="Executive Summary",
    content="Key findings and recommendations..."
)

# Add data from weekly report
report = get_weekly_report(week_id)
for activity in report["activities"]:
    builder.add_content_slide(
        title=activity["title"],
        content=activity["narrative"]
    )

# Add KPI table
builder.add_table_slide(
    title="KPIs",
    data=format_kpis(report["kpi_table"]),
    headers=["Metric", "Value", "Trend"]
)

# Save
pptx_path = builder._save_presentation("weekly_report.pptx")
```

## Customization Guide

### Creating Custom Templates

```python
from app.services.pptx_templates import (
    TemplateEngine,
    PresentationTemplate,
    TemplateType,
    TemplateTheme
)

engine = TemplateEngine()

# Create custom template
template = PresentationTemplate(
    name="my_custom",
    description="Custom corporate template",
    template_type=TemplateType.CUSTOM,
    theme=TemplateTheme.corporate_blue(),
    slide_templates=[
        "title_slide",
        "content_slide",
        "chart_slide",
        "table_slide",
        "closing_slide"
    ],
    page_width=10.0,
    page_height=7.5
)

# Save template
engine.save_template(template)

# Use template
builder = PPTXBuilder(template_theme=template.theme)
```

### Custom Color Schemes

```python
from app.services.pptx_templates import TemplateTheme

# Create custom theme
theme = TemplateTheme(
    name="company_branding",
    accent_color=(0, 102, 204),      # Company blue
    primary_color=(40, 40, 40),      # Dark gray
    secondary_color=(100, 149, 237), # Light blue
    text_color=(0, 0, 0),            # Black
    background_color=(245, 245, 245) # Light gray
)
```

## Performance Considerations

### Memory Management

- **Large presentations**: Stream slides instead of holding all in memory
- **Image optimization**: Compress images before embedding (max 2MB per image)
- **Chart caching**: Reuse generated charts across presentations

### File Storage

```python
# Cleanup old files
from app.services.chart_service import ChartService

chart_service = ChartService()
deleted = chart_service.cleanup_old_charts(days=7)
```

## Troubleshooting

### PDF Export Issues

Requires LibreOffice:
```bash
# Ubuntu/Debian
sudo apt-get install libreoffice

# macOS
brew install libreoffice

# Windows
# Download from https://www.libreoffice.org
```

### Image Not Appearing

```python
# Ensure image path exists and is readable
from pathlib import Path

if not Path(image_path).exists():
    logger.error(f"Image not found: {image_path}")
```

### Chart Generation Failures

```python
# Check matplotlib backend
import matplotlib
print(matplotlib.get_backend())  # Should be "Agg"

# Verify matplotlib is installed
pip install matplotlib>=3.8.0
```

## Testing

Run tests:
```bash
pytest backend/tests/test_pptx_builder.py -v
```

Key test coverage:
- Slide creation and ordering
- Theme application
- Chart generation
- Template management
- Export functionality

## Dependencies

### Backend
- `python-pptx>=0.6.21` - PPTX generation
- `pillow>=10.1.0` - Image processing
- `matplotlib>=3.8.2` - Chart generation

### Frontend
- React hooks for state management
- TailwindCSS for styling
- UI components (Button, Dialog, Tabs, etc.)

## Future Enhancements

1. **Master Slides**: Support for custom master slide templates
2. **Animations**: Slide transitions and element animations
3. **Batch Processing**: Generate multiple reports in parallel
4. **Cloud Storage**: Upload to S3, Google Drive, etc.
5. **Real-time Collaboration**: Multiple users editing same presentation
6. **AI-Powered Content**: Auto-generate summaries and insights
7. **Version Control**: Track template and presentation versions

## API Documentation

Full API documentation available at `/api/docs` (Swagger UI)

## License

Internal use only - Quality Weekly Intelligence System
