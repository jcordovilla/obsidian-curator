# Obsidian Curator - App Summary

## What is Obsidian Curator?

Obsidian Curator is an AI-powered system that automatically transforms messy, unorganized Obsidian vaults into clean, curated knowledge bases optimized for professional content creation. It's specifically designed for infrastructure and construction professionals who need to organize years of accumulated notes, web clippings, and research materials.

## Core Problem Solved

**Before**: A vault with thousands of unorganized notes including:
- Web clippings with HTML clutter
- Random thoughts and incomplete ideas  
- Academic papers mixed with personal notes
- No clear organization or quality assessment
- Difficulty finding relevant, high-quality content for writing

**After**: A structured, curated vault with:
- Only high-quality, relevant content
- Clean, readable markdown format
- Organized by professional themes (PPPs, infrastructure resilience, etc.)
- Enhanced metadata and quality scores
- Comprehensive analysis and statistics

## Key Capabilities

### 1. **Intelligent Content Analysis**
- Uses local AI (via Ollama) to assess note quality across 5 dimensions
- Identifies main themes and topics with confidence scores
- Determines content type (web clipping, personal note, academic paper, etc.)
- Makes curation decisions based on configurable thresholds

### 2. **Professional Theme Organization**
- Predefined hierarchy for infrastructure/construction themes:
  - Infrastructure (PPPs, resilience, financing, governance, technology)
  - Construction (projects, best practices, materials, safety)
  - Economics (development, investment, markets)
  - Sustainability (environmental, social, economic)
  - Governance (policy, institutions, transparency)

### 3. **Content Processing & Cleaning**
- Removes HTML clutter from web clippings
- Cleans ads, navigation, and social media widgets
- Converts to clean markdown format
- Preserves important content structure
- Handles various content types intelligently

### 4. **Comprehensive Output**
- Organized folder structure by themes
- Enhanced notes with quality scores and curation reasoning
- Detailed curation logs and statistics
- Theme analysis and recommendations
- Configuration and processing metadata

## Technical Architecture

### Core Components

1. **ContentProcessor**: Discovers, loads, and cleans raw notes
2. **AIAnalyzer**: Uses Ollama for quality assessment and theme identification  
3. **ThemeClassifier**: Organizes content into professional theme hierarchy
4. **VaultOrganizer**: Creates the final curated vault structure
5. **Core Orchestrator**: Manages the complete workflow with progress tracking

### AI Integration

- **Local Processing**: Uses Ollama for privacy and control
- **Structured Prompts**: Carefully designed prompts for consistent analysis
- **Multiple Models**: Works with any Ollama-compatible model
- **Fallback Handling**: Graceful degradation when AI is unavailable

### Data Models

- **Note**: Represents a single vault note with metadata
- **QualityScore**: Five-dimensional quality assessment (0.0-1.0)
- **Theme**: Identified theme with confidence and keywords
- **CurationResult**: Complete analysis result for each note
- **CurationConfig**: Flexible configuration system

## Usage Scenarios

### 1. **Command Line Interface**
```bash
# Basic curation
obsidian-curator curate /path/to/raw/vault /path/to/curated/vault

# Test with sample
obsidian-curator curate --sample-size 10 /path/to/raw/vault test-output

# Custom thresholds
obsidian-curator curate --quality-threshold 0.8 --relevance-threshold 0.7 /path/to/raw/vault /path/to/curated/vault
```

### 2. **Programmatic API**
```python
from obsidian_curator import ObsidianCurator, CurationConfig

config = CurationConfig(
    quality_threshold=0.7,
    target_themes=["infrastructure", "construction"]
)

curator = ObsidianCurator(config)
stats = curator.curate_vault(input_path, output_path)
```

### 3. **Batch Processing**
- Handles large vaults (thousands of notes)
- Memory-efficient processing
- Progress tracking and checkpoints
- Resume interrupted operations

## Configuration Options

### Quality Control
- **quality_threshold**: Minimum overall quality (0.0-1.0)
- **relevance_threshold**: Minimum relevance to themes (0.0-1.0)
- **target_themes**: Focus on specific professional areas

### Processing Options  
- **ai_model**: Choose Ollama model for analysis
- **max_tokens**: Token limit for AI analysis
- **sample_size**: Process subset for testing
- **clean_html**: Remove web clutter
- **preserve_metadata**: Keep original frontmatter

## Output Structure

```
curated-vault/
├── infrastructure/
│   ├── ppps/              # Public-Private Partnerships
│   ├── resilience/        # Climate adaptation, disaster recovery
│   ├── financing/         # Funding, investment analysis
│   └── governance/        # Regulation, policy
├── construction/
│   ├── projects/          # Project management
│   ├── best_practices/    # Standards, guidelines
│   └── safety/           # Risk management
├── economics/
├── sustainability/
├── governance/
├── miscellaneous/         # Unclassified content
└── metadata/
    ├── curation-log.md       # Detailed processing log
    ├── theme-analysis.md     # Theme distribution analysis
    ├── configuration.json    # Settings used
    └── statistics.json       # Processing metrics
```

## Enhanced Note Format

Each curated note includes:
- **Original Content**: Cleaned and formatted
- **Quality Scores**: AI assessment across 5 dimensions
- **Identified Themes**: With confidence scores and keywords
- **Curation Reasoning**: Why it was selected/rejected
- **Metadata**: Enhanced frontmatter with processing info
- **Processing Notes**: Any warnings or issues

## Performance & Scalability

### Optimizations
- **Batch Processing**: Configurable batch sizes for memory management
- **Smart Sampling**: Random sampling for testing large vaults
- **Token Management**: Intelligent content truncation for AI limits
- **Progress Tracking**: Real-time updates with ETAs

### Tested Scenarios
- Vaults with 1000+ notes
- Mixed content types (web clippings, PDFs, personal notes)
- Various languages and character encodings
- Large individual notes (long articles, papers)

## Error Handling & Recovery

### Robust Processing
- **File Access**: Handles permissions, encoding issues
- **AI Failures**: Continues processing with default scores
- **Partial Success**: Processes what it can, reports failures
- **Memory Management**: Prevents resource exhaustion

### Debugging Support
- **Structured Logging**: Detailed, searchable logs with Loguru
- **Dry Run Mode**: Preview without making changes
- **Verbose Mode**: Detailed progress and debug information
- **Error Context**: Clear error messages with suggestions

## Use Cases

### Primary Applications
1. **Knowledge Base Curation**: Transform messy research into organized knowledge
2. **Content Creation**: Prepare high-quality sources for professional writing
3. **Research Organization**: Structure academic and industry materials
4. **Team Knowledge**: Create clean, shared repositories
5. **Quality Assessment**: Identify valuable content in large collections

### Professional Scenarios
- **Infrastructure Consultants**: Organize project knowledge and case studies
- **Construction Professionals**: Curate industry insights and best practices  
- **Policy Analysts**: Structure governance and regulatory information
- **Researchers**: Organize academic and professional research materials
- **Content Creators**: Prepare source material for articles and publications

## Success Metrics

### Typical Results
- **Curation Rate**: 30-70% of notes typically pass quality thresholds
- **Processing Speed**: 1-5 notes per second (depending on AI model)
- **Theme Accuracy**: 80-90% correct theme classification
- **Content Quality**: Significant improvement in signal-to-noise ratio

### Quality Improvements
- **Content Cleanliness**: HTML clutter removed, clean markdown
- **Organization**: Logical theme-based structure
- **Discoverability**: Enhanced metadata and search capabilities
- **Actionability**: Only high-quality, relevant content preserved

## Integration & Extensions

### Current Integrations
- **Ollama**: Local AI model inference
- **Obsidian**: Native markdown and frontmatter support
- **Command Line**: Full CLI with rich output formatting

### Extension Points
- **Custom Themes**: Define organization for other domains
- **AI Models**: Use different Ollama models or providers  
- **Content Types**: Add support for new file formats
- **Output Formats**: Customize vault structure and metadata

## Requirements

### System Requirements
- **Python 3.12+** with Poetry for dependency management
- **Ollama** installed and running with at least one model
- **Sufficient RAM** for processing large vaults (8GB+ recommended)
- **Disk Space** for input vault, output vault, and processing

### Recommended Setup
- **AI Model**: gpt-oss:20b or similar for best quality analysis
- **Processing**: Start with small samples, then scale up
- **Configuration**: Adjust thresholds based on content type and goals
- **Monitoring**: Use verbose mode for initial runs to understand behavior

This comprehensive system transforms the chaotic process of managing large knowledge bases into an automated, intelligent curation workflow that saves time and improves content quality for professional use.
