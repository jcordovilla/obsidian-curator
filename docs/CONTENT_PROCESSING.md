# Content Processing and Normalization

This document explains the enhanced content processing capabilities for Evernote web clippings and note normalization.

## Overview

The Obsidian Note Curator now includes sophisticated preprocessing and normalization features designed specifically for:

1. **Evernote Web Clipping Cleanup** - Remove clutter from web clippings
2. **Note Structure Normalization** - Apply consistent templates to passed notes
3. **Content Quality Assessment** - Evaluate content substance and structure

## Evernote Web Clipping Preprocessing

### What Gets Removed

The system automatically detects and removes common Evernote web clipping clutter:

#### **Evernote-Specific Elements**
- Clipping headers ("Clipped from... on...")
- Evernote footers and branding
- Web annotations and link references
- Source attribution lines

#### **Web Page Clutter**
- Navigation elements (Home, About, Contact, etc.)
- Advertisement patterns (Ad, Sponsored, Promoted, etc.)
- Social media references (Facebook, Twitter, etc.)
- Tracking parameters (utm_, fbclid, gclid, etc.)

#### **Formatting Issues**
- HTML entities (&nbsp;, &amp;, etc.)
- Excessive whitespace (3+ spaces)
- Repeated characters (4+ same character)
- Broken or malformed links

### Detection and Processing

The system automatically detects Evernote clippings using these indicators:
- "Clipped from" in content
- "Evernote" references
- "Web Clipper" mentions
- "Saved from" patterns
- "Source:" headers

### Example Transformation

**Before (Evernote Clipping):**
```
Clipped from https://example.com on January 15, 2024

Infrastructure PPP Project Analysis

The project demonstrates significant value for money...

Home | About | Contact | Privacy Policy
Advertisement: Learn more about our services
Share on Facebook | Tweet this article

Evernote Web Clipper
```

**After (Cleaned Content):**
```
Infrastructure PPP Project Analysis

The project demonstrates significant value for money...
```

## Note Structure Normalization

### Automatic Template Application

Notes that pass classification (keep/refine) are automatically restructured using domain-specific templates:

#### **Literature/Research Notes**
```markdown
---
type: literature_research
pillar: ppp_fundamentals
created: 2024-01-15 14:30:00
status: processed
tags: [literature_research, ppp_fundamentals]
---

# Literature Review: PPP Fundamentals

## Key Findings
[Original content]

## Implications
- 

## Related Topics
- 

## References
- 

## Notes
- 
```

#### **Project Workflow Notes**
```markdown
---
type: project_workflow
pillar: operational_risk
created: 2024-01-15 14:30:00
status: processed
tags: [project_workflow, operational_risk]
---

# Project Workflow: Operational Risk

## Overview
[Original content]

## Steps
1. 
2. 
3. 

## Resources
- 

## Lessons Learned
- 

## Next Steps
- 
```

#### **Personal Reflection Notes**
```markdown
---
type: personal_reflection
pillar: digital_transformation
created: 2024-01-15 14:30:00
status: processed
tags: [personal_reflection, digital_transformation]
---

# Reflection: Digital Transformation

## Context
[Original content]

## Insights
- 

## Questions
- 

## Actions
- 

## Follow-up
- 
```

#### **Technical/Code Notes**
```markdown
---
type: technical_code
pillar: digital_transformation
created: 2024-01-15 14:30:00
status: processed
tags: [technical_code, digital_transformation]
---

# Technical Note: Digital Transformation

## Problem
[Original content]

## Solution
```python
# Code here
```

## Usage
- 

## Notes
- 

## References
- 
```

#### **Meeting Notes**
```markdown
---
type: meeting_template
pillar: governance_transparency
created: 2024-01-15 14:30:00
status: processed
tags: [meeting_template, governance_transparency]
---

# Meeting: Governance & Transparency

## Participants
- 

## Agenda
[Original content]

## Discussion Points
- 

## Decisions
- 

## Action Items
- [ ] 
- [ ] 
- [ ] 

## Next Meeting
- 
```

#### **Community Event Notes**
```markdown
---
type: community_event
pillar: value_for_money
created: 2024-01-15 14:30:00
status: processed
tags: [community_event, value_for_money]
---

# Event: Value for Money

## Event Details
[Original content]

## Key Takeaways
- 

## Connections Made
- 

## Follow-up Actions
- 

## Resources Shared
- 
```

## Content Quality Assessment

### Quality Metrics

The system assesses content quality using multiple indicators:

#### **Substantive Content Indicators**
- Years (2024, 2023, etc.)
- Percentages (25%, 50%, etc.)
- Dollar amounts ($1M, $500K, etc.)
- Acronyms (PPP, BIM, IoT, etc.)
- Number ranges (2020-2024, etc.)

#### **Technical Terms**
- Infrastructure terms (PPP, project, finance, risk, etc.)
- Digital transformation terms (BIM, automation, analytics, etc.)
- Governance terms (transparency, accountability, etc.)

#### **Structural Elements**
- Word count and sentence count
- Paragraph structure
- Key points and bullet lists
- Quotes and citations
- Data points and statistics

### Readability Scoring

The system calculates a simplified readability score based on:
- Average sentence length
- Content structure
- Technical term density
- Substantive content indicators

## Usage

### Automatic Processing

Normalization is enabled by default in the vault configuration:

```yaml
processing:
  normalize_notes: true
```

When enabled, the system will:
1. Preprocess Evernote clippings automatically
2. Normalize all "keep" and "refine" notes
3. Save normalized notes to `results/normalized_notes/`

### Manual Normalization

You can manually normalize individual notes:

```bash
# Normalize with automatic type/pillar detection
poetry run curate-notes normalize --input-file note.md

# Normalize with specific template
poetry run curate-notes normalize \
  --input-file note.md \
  --note-type literature_research \
  --pillar ppp_fundamentals \
  --output-dir normalized_notes
```

### Batch Processing

During vault analysis, normalization happens automatically:

```bash
# Analyze and normalize in one step
poetry run curate-notes analyze --sample-size 10
```

This will:
1. Process and classify notes
2. Generate analysis reports
3. Normalize all passed notes
4. Save structured notes to `results/normalized_notes/`

## Output Structure

### Normalized Notes Directory

```
results/
├── normalized_notes/
│   ├── keep/
│   │   ├── note1_20240115_143000.md
│   │   └── note2_20240115_143100.md
│   └── refine/
│       ├── note3_20240115_143200.md
│       └── note4_20240115_143300.md
```

### File Naming Convention

Normalized notes follow this naming pattern:
- `{original_name}_{YYYYMMDD_HHMMSS}.md`
- Timestamp ensures uniqueness
- Preserves original filename for reference

## Configuration

### Preprocessing Options

You can customize preprocessing behavior in the configuration:

```yaml
processing:
  # Enable/disable normalization
  normalize_notes: true
  
  # Maximum content length before truncation
  max_note_chars: 3000
  
  # Include frontmatter in analysis
  include_frontmatter: true
```

### Template Customization

Templates are defined in `note_curator/utils/content_processor.py` and can be customized for:

- Different note types
- Domain-specific sections
- Custom frontmatter fields
- Alternative formatting

## Benefits

### For Evernote Migrations
- **Automatic cleanup** of web clipping clutter
- **Consistent formatting** across all notes
- **Metadata preservation** (source URLs, dates)
- **Quality assessment** of migrated content

### For Knowledge Management
- **Structured templates** for different content types
- **Consistent organization** across your vault
- **Easy navigation** with standardized sections
- **Actionable insights** through quality metrics

### For Content Curation
- **Automatic categorization** by type and pillar
- **Quality scoring** to identify best content
- **Template application** for consistent structure
- **Metadata enrichment** with timestamps and tags

## Troubleshooting

### Common Issues

1. **Large file sizes after normalization**
   - Check `max_note_chars` setting
   - Review preprocessing patterns
   - Monitor content reduction ratios

2. **Template not applied correctly**
   - Verify note type detection
   - Check pillar classification
   - Review template definitions

3. **Preprocessing too aggressive**
   - Customize removal patterns
   - Adjust quality indicators
   - Review content before/after

### Performance Considerations

- **Memory usage** increases with large files
- **Processing time** scales with content length
- **Storage requirements** for normalized notes
- **Backup strategy** for original content

## Future Enhancements

Planned improvements include:

- **Custom template definitions** via YAML
- **Advanced content analysis** with ML models
- **Interactive preprocessing** with user approval
- **Version control** for normalized notes
- **Integration** with Obsidian plugins 