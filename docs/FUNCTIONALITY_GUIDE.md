# Obsidian Curator - Complete Functionality Guide

## Overview

Obsidian Curator is an AI-powered system that transforms raw Obsidian vaults into curated, organized knowledge bases. It uses local AI models via Ollama to intelligently analyze, clean, categorize, and organize notes based on quality, relevance, and thematic content.

## Core Architecture

The system consists of five main components that work together to process and curate content:

### 1. Content Processor (`content_processor.py`)
**Purpose**: Handles the initial processing and cleaning of raw notes from the Obsidian vault.

**Key Functions**:
- **Note Discovery**: Scans the input vault directory for markdown files (`.md` extension)
- **Metadata Extraction**: Parses YAML frontmatter from notes to extract:
  - Title, tags, source URLs, creation/modification dates
  - Custom metadata fields preserved for context
- **Content Type Detection**: Automatically identifies note types:
  - `WEB_CLIPPING`: Full articles scraped from websites with substantial HTML content
  - `URL_REFERENCE`: Simple bookmarks or URL references with minimal content  
  - `PERSONAL_NOTE`: User-created notes and drafts
  - `ACADEMIC_PAPER`: Research papers, journal articles, academic content
  - `PDF_ANNOTATION`: Notes containing PDF references or annotations
  - `IMAGE_ANNOTATION`: Notes with embedded images or image references
  - `PROFESSIONAL_PUBLICATION`: Industry publications, LinkedIn articles
- **HTML Cleaning**: Removes web clutter, ads, navigation elements, and formatting artifacts
- **Content Normalization**: Converts HTML to clean markdown, preserves structure

**Input**: Raw markdown files from Obsidian vault
**Output**: `Note` objects with cleaned content and metadata

### 2. AI Analyzer (`ai_analyzer.py`)
**Purpose**: Uses Ollama to perform intelligent analysis of note content for quality assessment and theme identification.

**Key Functions**:
- **Quality Assessment**: Evaluates notes across five dimensions (0.0-1.0 scale):
  - **Overall Quality**: General value and usefulness of content
  - **Relevance**: Alignment with target professional themes (infrastructure/construction)
  - **Completeness**: How comprehensive and complete the ideas are
  - **Credibility**: Trustworthiness and authority of source and content
  - **Clarity**: How well-organized and understandable the content is
- **Theme Identification**: Uses AI to identify main themes and topics:
  - Assigns confidence scores to each identified theme
  - Extracts keywords and subthemes
  - Maps themes to predefined professional categories
- **Curation Decision Making**: Determines if notes meet curation criteria:
  - Compares quality scores against configurable thresholds
  - Checks theme alignment with target areas
  - Provides detailed reasoning for decisions

**Input**: Processed `Note` objects
**Output**: `QualityScore`, list of `Theme` objects, curation reasoning

### 3. Theme Classifier (`theme_classifier.py`)
**Purpose**: Organizes content into a hierarchical theme structure optimized for infrastructure and construction professionals.

**Key Functions**:
- **Theme Mapping**: Maps AI-identified themes to predefined hierarchy:
  - **Infrastructure**: PPPs, resilience, financing, governance, technology
  - **Construction**: Projects, best practices, materials, safety
  - **Economics**: Development, investment, markets
  - **Sustainability**: Environmental, social, economic aspects
  - **Governance**: Policy, institutions, transparency
- **Fuzzy Matching**: Uses intelligent matching to handle theme variations:
  - Handles synonyms and related terms
  - Calculates similarity scores for theme assignment
  - Provides fallback categorization for unmatched themes
- **Vault Structure Creation**: Designs folder hierarchy for curated vault:
  - Main theme folders with subtheme organization
  - Metadata folder for reports and statistics
  - Handles unknown/miscellaneous content appropriately

**Input**: List of `CurationResult` objects
**Output**: Theme-organized groups, `VaultStructure` definition

### 4. Vault Organizer (`vault_organizer.py`)
**Purpose**: Creates the final curated vault with organized files, metadata, and comprehensive reports.

**Key Functions**:
- **File Organization**: Saves curated notes to theme-based folder structure
- **Enhanced Metadata**: Adds curation information to each note:
  - Quality scores and curation reasoning
  - Identified themes and confidence levels
  - Processing timestamps and source tracking
- **Report Generation**: Creates comprehensive documentation:
  - **Curation Log**: Detailed record of all processed notes with decisions
  - **Theme Analysis**: Statistical breakdown of theme distribution
  - **Configuration File**: Complete settings used for curation
  - **Statistics**: Processing metrics, quality distributions, success rates
- **Progress Tracking**: Monitors and reports processing progress

**Input**: `CurationResult` objects, target output path
**Output**: Organized curated vault with reports and statistics

### 5. Core Orchestrator (`core.py`)
**Purpose**: Coordinates all components and manages the complete curation workflow.

**Key Functions**:
- **Workflow Management**: Orchestrates the complete curation process
- **Progress Monitoring**: Tracks processing across all stages with detailed logging
- **Error Handling**: Manages failures gracefully, provides meaningful error messages
- **Batch Processing**: Handles large vaults efficiently with memory management
- **Configuration Management**: Applies user settings across all components

## Data Models

### Core Data Structures

#### `Note`
Represents a single note from the Obsidian vault:
```python
{
    "file_path": Path,           # Original file location
    "title": str,                # Extracted or derived title
    "content": str,              # Cleaned content
    "content_type": ContentType, # Detected content type
    "metadata": dict,            # Original frontmatter data
    "created_date": datetime,    # Creation timestamp
    "modified_date": datetime,   # Last modification
    "tags": List[str],          # Extracted tags
    "source_url": str           # Original source if web clipping
}
```

#### `QualityScore`
AI-assessed quality metrics:
```python
{
    "overall": float,      # 0.0-1.0 overall quality
    "relevance": float,    # Relevance to target themes
    "completeness": float, # Completeness of ideas
    "credibility": float,  # Source credibility
    "clarity": float       # Clarity of expression
}
```

#### `Theme`
Identified content theme:
```python
{
    "name": str,              # Theme name
    "confidence": float,      # 0.0-1.0 confidence score
    "subthemes": List[str],  # Related subthemes
    "keywords": List[str]    # Associated keywords
}
```

#### `CurationResult`
Complete curation analysis for a note:
```python
{
    "note": Note,                    # Original note
    "cleaned_content": str,          # Processed content
    "quality_scores": QualityScore,  # AI quality assessment
    "themes": List[Theme],           # Identified themes
    "is_curated": bool,             # Curation decision
    "curation_reason": str,         # Decision reasoning
    "processing_notes": List[str]   # Processing warnings/notes
}
```

## Configuration System

### `CurationConfig`
Comprehensive configuration for the curation process:

```python
{
    "ai_model": "gpt-oss:20b",           # Ollama model to use
    "quality_threshold": 0.7,            # Minimum quality for curation
    "relevance_threshold": 0.6,          # Minimum relevance for curation
    "max_tokens": 2000,                  # Token limit for AI analysis
    "target_themes": ["infrastructure"], # Focus themes
    "sample_size": None,                 # Random sample size (testing)
    "preserve_metadata": True,           # Keep original metadata
    "clean_html": True,                  # Clean web content
    "remove_duplicates": True            # Remove duplicate content
}
```

## AI Integration

### Ollama Integration
The system uses Ollama for local AI inference:

- **Model Support**: Works with any Ollama-compatible model (default: `gpt-oss:20b`)
- **Local Processing**: All AI analysis happens locally for privacy
- **Structured Prompts**: Uses carefully crafted prompts for consistent analysis
- **JSON Response Parsing**: Extracts structured data from AI responses
- **Error Handling**: Graceful fallbacks when AI analysis fails

### AI Prompt Engineering

#### Quality Assessment Prompt
```
Analyze this content for:
1. Overall Quality: How valuable and well-crafted is this content?
2. Relevance: How relevant to infrastructure and construction professionals?
3. Completeness: How complete and comprehensive are the ideas?
4. Credibility: How trustworthy and authoritative is the source?
5. Clarity: How clear, well-organized, and understandable?

Respond with JSON: {"overall": 0.8, "relevance": 0.9, ...}
```

#### Theme Identification Prompt
```
Identify main themes relevant to infrastructure, construction, governance.
For each theme provide: name, confidence, subthemes, keywords.

Respond with JSON array: [{"name": "Theme", "confidence": 0.9, ...}]
```

## Content Processing Pipeline

### Stage 1: Discovery and Loading
1. **Vault Scanning**: Recursively finds all `.md` files in input directory
2. **File Filtering**: Skips system files, templates, and empty files
3. **Priority Sorting**: Orders by modification date (newest first) for relevance
4. **Sample Selection**: Optionally selects random sample for testing

### Stage 2: Content Processing
1. **File Reading**: Handles various encodings (UTF-8, Latin-1 fallback)
2. **Frontmatter Parsing**: Extracts YAML metadata using custom parser
3. **Content Type Detection**: Uses multiple heuristics to classify content
4. **HTML Cleaning**: Comprehensive cleaning for web clippings:
   - Removes navigation, ads, social widgets
   - Converts HTML structures to markdown
   - Preserves important content structure
5. **Metadata Enhancement**: Adds processing timestamps and file info

### Stage 3: AI Analysis
1. **Content Preparation**: Formats content for AI analysis with context
2. **Token Management**: Truncates content to fit model limits while preserving meaning
3. **Quality Assessment**: Multi-dimensional quality scoring
4. **Theme Identification**: Extracts themes with confidence scores
5. **Decision Logic**: Applies curation criteria to make keep/reject decisions

### Stage 4: Organization
1. **Theme Mapping**: Maps AI themes to predefined hierarchy
2. **Folder Creation**: Creates organized directory structure
3. **File Generation**: Saves curated notes with enhanced metadata
4. **Report Creation**: Generates comprehensive analysis reports

## Theme Hierarchy System

### Predefined Categories
The system includes a comprehensive theme hierarchy designed for infrastructure and construction professionals:

```
infrastructure/
├── ppps/              # Public-Private Partnerships
├── resilience/        # Climate adaptation, disaster recovery
├── financing/         # Funding, investment analysis
├── governance/        # Regulation, policy, legal frameworks
└── technology/        # Innovation, digital transformation

construction/
├── projects/          # Project management, construction projects
├── best_practices/    # Standards, guidelines, methodologies
├── materials/         # Construction materials, sustainability
└── safety/           # Risk management, health and safety

economics/
├── development/       # Economic development, regional planning
├── investment/        # Investment analysis, cost-benefit analysis
└── markets/          # Market analysis, industry trends

sustainability/
├── environmental/     # Environmental impact, climate change
├── social/           # Social impact, community development
└── economic/         # Economic sustainability, long-term value

governance/
├── policy/           # Public policy, regulatory framework
├── institutions/     # Government institutions, regulatory bodies
└── transparency/     # Accountability, public participation
```

### Theme Mapping Algorithm
1. **Direct Matching**: Exact matches with hierarchy names
2. **Keyword Matching**: Searches for related keywords in content
3. **Fuzzy Matching**: Uses Jaccard similarity for partial matches
4. **Alias Resolution**: Handles synonyms and alternative terms
5. **Fallback Logic**: Assigns to "unknown" if no good match found

## Output Structure

### Curated Vault Organization
```
curated-vault/
├── infrastructure/
│   ├── ppps/
│   │   ├── note1.md
│   │   └── note2.md
│   ├── financing/
│   └── governance/
├── construction/
│   ├── projects/
│   └── best_practices/
├── economics/
├── sustainability/
├── governance/
├── miscellaneous/        # Unknown/unclassified content
└── metadata/
    ├── curation-log.md      # Detailed processing log
    ├── theme-analysis.md    # Theme distribution analysis
    ├── configuration.json   # Complete configuration used
    └── statistics.json      # Processing statistics
```

### Enhanced Note Format
Each curated note includes:

```markdown
---
title: "Note Title"
curated_date: "2024-01-01T12:00:00"
original_source: "https://example.com"
content_type: "web_clipping"
quality_scores:
  overall: 0.85
  relevance: 0.90
  completeness: 0.80
  credibility: 0.85
  clarity: 0.90
themes:
  - "Infrastructure Resilience"
  - "Public-Private Partnerships"
curation_reason: "Passed all criteria: quality=0.85, relevance=0.90"
---

# Note Title

## Curation Information
- **Curated Date**: 2024-01-01T12:00:00
- **Quality Score**: 0.85/1.0
- **Relevance Score**: 0.90/1.0
- **Primary Theme**: Infrastructure Resilience
- **Curation Reason**: Passed all criteria

## Identified Themes
### Infrastructure Resilience
- **Confidence**: 0.90
- **Sub-themes**: Climate Adaptation, Disaster Recovery
- **Keywords**: resilience, infrastructure, adaptation

## Content
[Original cleaned content here]

## Processing Notes
- Cleaned HTML content from web clipping
- Removed navigation and advertisement elements
```

## Command Line Interface

### Basic Commands
```bash
# Basic curation
obsidian-curator curate /path/to/input /path/to/output

# Test with sample
obsidian-curator curate --sample-size 10 /path/to/input /path/to/output

# Custom thresholds
obsidian-curator curate --quality-threshold 0.8 --relevance-threshold 0.7 /path/to/input /path/to/output

# Target specific themes
obsidian-curator curate --target-themes infrastructure,construction /path/to/input /path/to/output

# Dry run (preview without executing)
obsidian-curator curate --dry-run /path/to/input /path/to/output

# Verbose logging
obsidian-curator curate --verbose /path/to/input /path/to/output
```

### Advanced Options
- `--config`: Use custom configuration file
- `--model`: Specify different Ollama model
- `--max-tokens`: Adjust token limit for AI analysis
- `--no-clean-html`: Skip HTML cleaning
- `--no-preserve-metadata`: Don't preserve original metadata

## Error Handling and Recovery

### Robust Error Management
- **File Access Errors**: Handles permission issues, missing files
- **Encoding Issues**: Automatic fallback to different character encodings
- **AI Service Errors**: Graceful degradation when Ollama is unavailable
- **Memory Management**: Efficient processing of large vaults
- **Partial Processing**: Continues processing even if individual notes fail

### Logging and Debugging
- **Structured Logging**: Uses Loguru for comprehensive, searchable logs
- **Progress Tracking**: Real-time progress updates with ETA estimates
- **Error Context**: Detailed error messages with context and suggestions
- **Debug Mode**: Verbose logging for troubleshooting issues

## Performance and Scalability

### Optimization Features
- **Batch Processing**: Processes notes in configurable batches
- **Memory Management**: Efficient handling of large content volumes
- **Token Optimization**: Smart content truncation to fit model limits
- **Caching**: Reuses AI analysis results where appropriate
- **Checkpoint System**: Ability to resume interrupted processing

### Scalability Considerations
- **Large Vaults**: Tested with vaults containing thousands of notes
- **Content Size**: Handles notes from small snippets to long documents
- **AI Model Flexibility**: Works with various Ollama models and sizes
- **Resource Management**: Configurable limits to prevent resource exhaustion

## Integration and Extensibility

### Programmatic API
```python
from obsidian_curator import ObsidianCurator, CurationConfig

# Custom configuration
config = CurationConfig(
    ai_model="custom-model",
    quality_threshold=0.8,
    target_themes=["custom", "themes"]
)

# Initialize curator
curator = ObsidianCurator(config)

# Process vault
stats = curator.curate_vault(input_path, output_path)
```

### Extension Points
- **Custom Content Processors**: Add support for new content types
- **Theme Hierarchies**: Define custom theme organizations
- **AI Models**: Use different Ollama models or analysis approaches
- **Output Formats**: Customize output structure and metadata

## Use Cases and Applications

### Primary Use Cases
1. **Knowledge Base Curation**: Transform messy vaults into organized knowledge bases
2. **Content Quality Assessment**: Identify high-quality content for further use
3. **Research Organization**: Organize research materials by themes and topics
4. **Professional Writing**: Curate source material for articles and publications
5. **Team Knowledge Sharing**: Create clean, organized shared knowledge repositories

### Professional Applications
- **Infrastructure Consultants**: Organize project knowledge and best practices
- **Construction Professionals**: Curate industry insights and technical resources
- **Policy Analysts**: Organize governance and regulatory information
- **Researchers**: Structure academic and professional research materials
- **Content Creators**: Curate source material for professional writing

This comprehensive functionality guide provides a complete understanding of how Obsidian Curator works, enabling effective communication with other AI agents and systems about its capabilities, architecture, and use cases.
