# PPTX Builder System - Quick Reference

## Project Structure

```
Quality_weekly_AI/
├── backend/
│   ├── app/
│   │   ├── services/
│   │   │   ├── pptx_builder.py (492 lines)
│   │   │   ├── pptx_templates.py (485 lines)
│   │   │   └── chart_service.py (368 lines)
│   │   └── api/
│   │       └── routes/
│   │           └── pptx.py (426 lines)
│   ├── tests/
│   │   └── test_pptx_builder.py (398 lines)
│   └── requirements.txt (+ matplotlib, Pillow)
│
├── frontend/
│   └── src/
│       ├── components/
│       │   └── weekly/
│       │       └── PPTXEditor.tsx (398 lines)
│       └── hooks/
│           └── usePPTXEditor.ts (393 lines)
│
└── Documentation/
    ├── PPTX_BUILDER_GUIDE.md (600+ lines)
    ├── PPTX_IMPLEMENTATION_SUMMARY.md (400+ lines)
    └── PPTX_QUICK_REFERENCE.md (this file)
```

---

## Core Services

### 1. PPTXBuilder
**File**: `backend/app/services/pptx_builder.py`

```python
# Initialize
builder = PPTXBuilder(theme=TemplateTheme.default())

# Add slides
builder.add_title_slide(title, subtitle, date, author)
builder.add_content_slide(title, content, images)
builder.add_chart_slide(title, data, chart_type)
builder.add_table_slide(title, data, headers)
builder.add_image_slide(title, images)
builder.add_summary_slide(activities_summary)

# Generate
pptx_path = builder.generate_pptx(weekly_report, template_name)

# Export
pdf_path = builder.export_to_pdf(pptx_path)
```

### 2. TemplateEngine
**File**: `backend/app/services/pptx_templates.py`

```python
# Initialize
engine = TemplateEngine()

# Load templates
template = engine.load_template("executive")
templates = engine.list_all_templates()

# Create custom
custom = engine.create_custom_template(
    name, description, template_type, theme, slide_templates
)

# Manage
engine.save_template(template)
engine.delete_template(name)
```

### 3. ChartService
**File**: `backend/app/services/chart_service.py`

```python
# Initialize
service = ChartService()

# Generate charts
bar_path = service.generate_chart(data, chart_type="bar")
pie_path = service.generate_chart(data, chart_type="pie")
line_path = service.generate_chart(data, chart_type="line")
heatmap_path = service.generate_heatmap(data, x_labels, y_labels)

# Cleanup
deleted_count = service.cleanup_old_charts(days=7)
```

---

## API Endpoints

### Generate PPTX
```
POST /api/pptx/generate
POST /api/pptx/generate-with-slides
```

### Templates
```
GET  /api/pptx/templates/list
GET  /api/pptx/templates/{name}
POST /api/pptx/templates/create
POST /api/pptx/templates/upload
DELETE /api/pptx/templates/{name}
```

### Themes
```
GET /api/pptx/themes/list
GET /api/pptx/themes/{name}
```

### Export
```
POST /api/pptx/export/pdf/{pptx_id}
POST /api/pptx/export/docx/{pptx_id}
```

### Files
```
GET /api/pptx/files/list
DELETE /api/pptx/files/{filename}
```

---

## React Components

### PPTXEditor
**File**: `frontend/src/components/weekly/PPTXEditor.tsx`

```tsx
<PPTXEditor
  isOpen={true}
  onClose={() => {}}
  reportData={report}
  onGenerate={async (slides, config) => {...}}
/>
```

**Features**:
- Slide management
- Template/theme selection
- Content editing
- Preview
- Export options

### usePPTXEditor Hook
**File**: `frontend/src/hooks/usePPTXEditor.ts`

```typescript
const editor = usePPTXEditor(initialData);

// State
editor.slides
editor.selectedSlideId
editor.isGenerating
editor.error
editor.pptxPath

// Methods
editor.addSlide(type)
editor.deleteSlide(id)
editor.updateSlide(id, updates)
editor.moveSlide(id, direction)
editor.selectSlide(id)
editor.generatePPTX(config)
editor.downloadPPTX(pptxPath)
editor.exportToPDF(pptxPath)
```

---

## Themes

### Built-in Themes
```python
TemplateTheme.default()
TemplateTheme.corporate_blue()
TemplateTheme.modern_dark()
TemplateTheme.minimalist()
```

### Custom Theme
```python
theme = TemplateTheme(
    name="custom",
    accent_color=(0, 102, 204),
    primary_color=(40, 40, 40),
    text_color=(0, 0, 0),
    background_color=(255, 255, 255)
)
```

---

## Templates

### Built-in Templates
1. **executive** - High-level summary
2. **operational** - Detailed operations
3. **analytical** - Data-driven
4. **technical** - Technical specs

### Slide Types
- `title` - Cover slide
- `content` - Text with images
- `chart` - Data visualization
- `table` - Structured data
- `images` - Photo gallery

---

## Chart Types

```python
# Bar Chart (horizontal)
data = {
    "title": "Activities by Status",
    "categories": ["Done", "In Progress", "Pending"],
    "series": [{"name": "Count", "values": [10, 5, 3]}]
}

# Column Chart (vertical)
data = {
    "title": "Trend",
    "categories": ["Week 1", "Week 2", "Week 3"],
    "series": [{"name": "Issues", "values": [10, 8, 5]}]
}

# Line Chart
data = {
    "categories": ["Jan", "Feb", "Mar"],
    "series": [
        {"name": "Target", "values": [100, 110, 120]},
        {"name": "Actual", "values": [95, 105, 118]}
    ]
}

# Pie Chart
data = {
    "categories": ["A", "B", "C"],
    "values": [40, 30, 30]
}
```

---

## Common Workflows

### Basic Generation
```python
from app.services.pptx_builder import PPTXBuilder

builder = PPTXBuilder()
pptx_path = builder.generate_pptx(
    weekly_report={
        "title": "Weekly Report",
        "summary": "...",
        "activities": [...],
        "kpi_table": [...]
    }
)
```

### Custom Slides
```python
builder = PPTXBuilder()
builder.create_presentation()
builder.add_title_slide("Report", "Week 32")
builder.add_content_slide("Summary", "Content...")
builder.add_chart_slide("Chart", chart_data, "bar")
pptx_path = builder._save_presentation()
```

### With Custom Theme
```python
theme = TemplateTheme.corporate_blue()
builder = PPTXBuilder(theme=theme)
pptx_path = builder.generate_pptx(report_data)
```

### Frontend Generation
```tsx
const { generatePPTX, downloadPPTX } = usePPTXEditor(data);

const result = await generatePPTX({
  template: "executive",
  theme: "corporate_blue",
  report_data: report
});

if (result) {
  downloadPPTX(result);
}
```

---

## Testing

### Run Tests
```bash
pytest backend/tests/test_pptx_builder.py -v
```

### Test Coverage
- Builder functionality
- Template operations
- Theme management
- Chart generation
- File operations
- All template types
- All themes

---

## Dependencies

### Backend
```
python-pptx>=0.6.21
matplotlib>=3.8.2
Pillow>=10.1.0
```

### Installation
```bash
pip install -r backend/requirements.txt
```

---

## Configuration

### Environment Variables
```bash
UPLOAD_DIR=/path/to/uploads
APP_NAME="Quality Weekly Intelligence"
CORS_ORIGINS=["http://localhost:3000"]
```

### Directory Structure
```
${UPLOAD_DIR}/
├── reports/        # Generated PPTX files
├── templates/      # Custom templates
└── charts/         # Generated chart images
```

---

## Error Handling

### Backend Errors
```python
try:
    pptx_path = builder.generate_pptx(report_data)
except Exception as e:
    logger.error("PPTX generation failed: %s", e)
    raise HTTPException(status_code=500, detail=str(e))
```

### Frontend Errors
```typescript
try {
  await generatePPTX(config);
} catch (error) {
  console.error("Generation failed:", error);
  clearError();
}
```

---

## Performance Tips

1. **Image Optimization**
   - Compress images before embedding
   - Limit image size to <100KB each
   - Use appropriate resolution

2. **Chart Generation**
   - Cache frequently used charts
   - Reuse chart data across presentations
   - Limit number of data points

3. **Template Management**
   - Load templates once, reuse
   - Cache theme objects
   - Batch template operations

4. **File Cleanup**
   - Delete old presentations regularly
   - Clean up temporary chart files
   - Monitor storage usage

---

## Troubleshooting

### Import Errors
```python
# Check if services are properly imported
from app.services.pptx_builder import PPTXBuilder
from app.services.pptx_templates import TemplateEngine
from app.services.chart_service import ChartService
```

### Missing Dependencies
```bash
pip install matplotlib pillow python-pptx
```

### PDF Export Failed
```bash
# Install LibreOffice
apt-get install libreoffice  # Linux
brew install libreoffice      # macOS
```

### Template Not Found
```python
# Check if template file exists
import os
template_path = os.path.join(UPLOAD_DIR, "templates", "name.json")
if os.path.exists(template_path):
    print("Template found")
```

---

## Integration Checklist

- [x] Backend services implemented
- [x] API routes added
- [x] Frontend components created
- [x] Hooks for state management
- [x] Tests written
- [x] Dependencies added
- [x] Routes registered in main.py
- [x] Documentation complete
- [x] Error handling added
- [x] Logging configured

---

## Next Steps

1. **Deploy Backend**
   ```bash
   pip install -r requirements.txt
   python -m pytest tests/test_pptx_builder.py
   uvicorn app.main:app --reload
   ```

2. **Build Frontend**
   ```bash
   npm install
   npm run build
   npm start
   ```

3. **Test Integration**
   - Generate sample PPTX
   - Verify all slide types
   - Test export options
   - Check theme application

4. **Monitor Performance**
   - Track generation times
   - Monitor file sizes
   - Review error logs
   - Optimize as needed

---

## Support Resources

- **Full Guide**: `PPTX_BUILDER_GUIDE.md`
- **Implementation Details**: `PPTX_IMPLEMENTATION_SUMMARY.md`
- **Code**: `backend/app/services/pptx_*.py`
- **Tests**: `backend/tests/test_pptx_builder.py`
- **API Docs**: `/api/docs` (Swagger UI)

---

## Version Info

- **Version**: 1.0.0
- **Status**: Production Ready
- **Last Updated**: August 10, 2026
- **Python**: 3.8+
- **Dependencies**: python-pptx, matplotlib, pillow

---

**Ready to generate professional PPTX presentations!** ✅
