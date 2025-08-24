# Obsidian Curator

An AI-powered curation system for Obsidian vaults that automatically analyzes, categorizes, and organizes your notes using local AI models via Ollama. **Now with enhanced performance and optimized curation thresholds for better content capture.**

## 🚀 Recent Updates (Latest Release)

### **Critical Bug Fixes** 🐛
- **Fixed JSON Parsing Issue**: Resolved systematic 0.30 scoring bias that was corrupting AI analysis responses
- **Improved AI Response Handling**: Enhanced JSON extraction and malformation repair for reliable Ollama responses
- **Restored Quality Scoring**: Quality scores now properly distributed across 0.6-0.8 range instead of fixed 0.30

### **Performance Optimizations** ✨
- **Lowered Quality Threshold**: From 0.75 to 0.65 for broader content capture
- **Reduced Professional Writing Threshold**: From 0.70 to 0.65 for better analytical content inclusion
- **Optimized Content Length**: Minimum length reduced from 500 to 300 characters to capture valuable short notes
- **Enhanced AI Analysis**: Multi-model architecture with specialized models for different tasks

### **New Features** 🆕
- **Professional Writing Assessment**: Advanced evaluation of analytical depth and critical thinking
- **Enhanced Theme Classification**: Improved tagging system aligned with writing purposes
- **Comprehensive Performance Metrics**: Detailed timing analysis and throughput optimization
- **Advanced Content Processing**: Better handling of web clippings, PDF annotations, and mixed content

### **Documentation & Analysis** 📊
- **Performance Analysis Reports**: Detailed system evaluation and optimization insights
- **Thematic Classification Analysis**: Writing purpose alignment and enhancement recommendations
- **Curation Quality Diagnosis**: Comprehensive analysis of accepted vs. rejected content
- **Optimization Implementation Guide**: Step-by-step improvement documentation

## Features

- **AI-Powered Analysis**: Uses Ollama with local AI models to analyze note quality and relevance
- **Intelligent Curation**: Automatically determines which notes meet your curation criteria with **optimized thresholds**
- **Theme Classification**: Organizes notes into hierarchical themes (infrastructure, construction, economics, etc.)
- **Content Processing**: Cleans and processes various content types including web clippings and markdown
- **Vault Organization**: Creates a well-structured curated vault with metadata and statistics
- **Flexible Configuration**: Customizable quality thresholds, target themes, and processing options
- **Professional Writing Assessment**: Advanced evaluation of analytical depth and publication readiness
- **Performance Optimization**: Multi-model AI architecture for efficient processing

## Installation

### Prerequisites

1. **Python 3.12+** with Poetry
2. **Ollama** installed and running with multiple models for optimal performance

### Install Ollama

```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.ai/install.sh | sh

# Windows
# Download from https://ollama.ai/download
```

### Install Python Dependencies

```bash
# Install Poetry if you don't have it
curl -sSL https://install.python-poetry.org | python3 -

# Install project dependencies
poetry install
```

### Pull AI Models for Optimal Performance

```bash
# Core model for content curation
ollama pull phi3:mini

# High-quality model for detailed analysis
ollama pull llama3.1:8b

# Premium model for complex reasoning
ollama pull gpt-oss:20b
```

## Quick Start

### Prerequisites

1. **Python 3.12+** with Poetry
2. **Ollama** installed and running with multiple models
3. **PyYAML** dependency for configuration validation

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/obsidian-curator.git
cd obsidian-curator

# Install Poetry if you don't have it
curl -sSL https://install.python-poetry.org | python3 -

# Install project dependencies
poetry install
```

### Using Poetry

```bash
# Activate the virtual environment
poetry shell

# Or run commands directly
poetry run obsidian-curator --help
```

### Basic Usage

The system processes raw notes from your Obsidian vault and outputs curated, cleaned content. The `my-writings/` folder contains examples of your final published work to demonstrate the target quality and style.

```bash
# Test with a small sample first (recommended for new users)
poetry run obsidian-curator curate --sample-size 5 /Users/jose/Documents/Obsidian/Evermd test-curated-vault

# Full curation of your vault with optimized thresholds
poetry run obsidian-curator curate /Users/jose/Documents/Obsidian/Evermd curated-vault
```

### Graphical User Interface (GUI)

Launch the intuitive PyQt6 GUI for easy vault curation:

```bash
# Launch the GUI application
poetry run obsidian-curator-gui

# Or run directly
poetry run python -m obsidian_curator.gui
```

**GUI Features:**
- **Simple Configuration**: Set source vault and output folder with browse dialogs
- **Run Options**: Choose between full run or test run with custom sample size
- **Real-time Progress**: Live progress bar and current operation display
- **Live Statistics**: See total, curated, and rejected notes with processing time
- **Theme Analysis**: View theme distribution as notes are processed
- **Note Preview**: Browse curated notes with quality scores and content preview
- **Professional Quality Metrics**: Track analytical depth, evidence quality, and writing readiness
- **Performance Monitoring**: Real-time processing speed and throughput metrics

**Default Settings:**
- Source vault: `/Users/jose/Documents/Obsidian/Evermd`
- Uses configuration from `config.yaml` with **optimized thresholds**
- Test run default: 10 notes sample

### Command Line Interface

The easiest way to use Obsidian Curator is through the command line:

```bash
# Basic curation with optimized default settings
poetry run obsidian-curator curate /path/to/input/vault /path/to/output/vault

# Custom quality threshold and reasoning level
poetry run obsidian-curator curate --quality-threshold 0.8 --reasoning-level medium /path/to/input/vault /path/to/output/vault

# Target specific themes
poetry run obsidian-curator curate --target-themes infrastructure,construction /path/to/input/vault /path/to/output/vault

# High reasoning level for better analysis
poetry run obsidian-curator curate --reasoning-level high /path/to/input/vault /path/to/output/vault

# Verbose logging
poetry run obsidian-curator curate --verbose /path/to/input/vault /path/to/output/vault

# Dry run (see what would be done without doing it)
poetry run obsidian-curator curate --dry-run /path/to/input/vault /path/to/output/vault
```

### Programmatic Usage

```python
from pathlib import Path
from obsidian_curator import ObsidianCurator, CurationConfig

# Configuration with optimized thresholds
config = CurationConfig(
    ai_model="gpt-oss:20b",
    quality_threshold=0.65,  # Optimized for better content capture
    relevance_threshold=0.65,  # Maintained for precision
    professional_writing_threshold=0.65,  # Lowered for analytical content
    min_content_length=300,  # Reduced to capture valuable short notes
    target_themes=["infrastructure", "construction", "economics"]
)

# Create curator
curator = ObsidianCurator(config)

# Curate vault
stats = curator.curate_vault(
    input_path=Path("my-writings"),
    output_path=Path("curated-vault")
)

print(f"Curated {stats.curated_notes}/{stats.total_notes} notes")
```

## Configuration

### CurationConfig Options

- **`ai_model`**: Ollama model to use (default: `"gpt-oss:20b"`)
- **`reasoning_level`**: AI reasoning level - `"low"`, `"medium"`, or `"high"` (default: `"low"`)
- **`quality_threshold`**: Minimum quality score for curation (0.0-1.0, **default: 0.65** - optimized)
- **`relevance_threshold`**: Minimum relevance score for curation (0.0-1.0, **default: 0.65** - maintained)
- **`professional_writing_threshold`**: Minimum professional writing score for curation (0.0-1.0, **default: 0.65** - optimized)
- **`min_content_length`**: Minimum content length in characters (**default: 300** - reduced for valuable short notes)
- **`max_tokens`**: Maximum tokens for AI analysis (default: 2000)
- **`target_themes`**: List of target themes to focus on (default: infrastructure themes)
- **`preserve_metadata`**: Whether to preserve original note metadata (default: True)
- **`clean_html`**: Whether to clean HTML content (default: True)

### **Optimized Default Thresholds** 🎯

The system now uses **optimized thresholds** for better content capture:

```yaml
# Quality Thresholds (0.0 - 1.0) - Optimized for better content capture
quality_threshold: 0.65  # Minimum overall quality score for curation (lowered for broader capture)
relevance_threshold: 0.65 # Minimum relevance score for curation (maintained for precision)
analytical_depth_threshold: 0.65  # Minimum analytical depth for publication-ready content
professional_writing_threshold: 0.65  # Minimum professional writing score for curation (lowered from 0.70)
min_content_length: 300   # Minimum content length (characters) for useful notes (lowered for valuable short notes)
```

### Default Theme Hierarchy

The system comes with a predefined theme hierarchy focused on infrastructure and construction:

- **infrastructure/**
  - **ppps**: Public-private partnerships
  - **resilience**: Climate adaptation, disaster recovery
  - **financing**: Funding, investment, economic analysis
  - **governance**: Regulation, policy, legal framework
  - **technology**: Innovation, digital transformation
- **construction/**
  - **projects**: Project management, construction projects
  - **best_practices**: Standards, guidelines, methodologies
  - **materials**: Construction materials, sustainability
  - **safety**: Risk management, health and safety
- **economics/**
  - **development**: Economic development, regional planning
  - **investment**: Investment analysis, cost-benefit analysis
  - **markets**: Market analysis, industry trends
- **sustainability/**
  - **environmental**: Environmental impact, climate change
  - **social**: Social impact, community development
  - **economic**: Economic sustainability, long-term value
- **governance/**
  - **policy**: Public policy, regulatory framework
  - **institutions**: Government institutions, regulatory bodies
  - **transparency**: Accountability, public participation

## How It Works

### 1. Note Discovery
- Scans your Obsidian vault for markdown files
- Skips system files, templates, and non-content directories
- Sorts notes by modification date (newest first)

### 2. Content Processing
- Extracts metadata from YAML frontmatter
- Determines content type (web clipping, personal note, etc.)
- Cleans HTML content if needed
- Preserves important metadata
- **Enhanced processing for mixed content types**

### 3. AI Analysis
- Uses **multi-model Ollama architecture** for specialized tasks:
  - **Content Curation**: `phi3:mini` for efficient initial screening
  - **Quality Analysis**: `llama3.1:8b` for detailed assessment
  - **Theme Classification**: `gpt-oss:20b` for complex reasoning
- Analyzes note quality across **10 dimensions** including:
  - Overall quality, relevance, completeness, credibility, clarity
  - **Professional writing quality** and analytical depth
  - Critical thinking and evidence quality
- Identifies themes and assigns confidence scores
- Determines curation decision based on **optimized thresholds**

### 4. Theme Classification
- Maps identified themes to the predefined hierarchy
- Uses fuzzy matching for theme names
- Creates nested folder structures for subthemes
- **Enhanced tagging system aligned with writing purposes**

### 5. Vault Organization
- Creates organized folder structure by themes
- Saves curated notes with enhanced metadata
- Generates comprehensive reports and statistics
- Preserves curation history and reasoning
- **Performance metrics and optimization insights**

## Output Structure

The curated vault contains:

```
curated-vault/
├── infrastructure/
│   ├── ppps/
│   ├── financing/
│   └── governance/
├── construction/
│   ├── projects/
│   └── best_practices/
├── economics/
├── sustainability/
├── governance/
├── miscellaneous/
└── metadata/
    ├── curation-log.md
    ├── theme-analysis.md
    ├── configuration.json
    ├── statistics.json
    └── performance-metrics.md
```

## Examples

See the `examples/` directory for complete working examples:

- **`basic_curation.py`**: Simple example of basic vault curation
- **`advanced_curation.py`**: Advanced usage with custom configuration and detailed analysis

## Performance & Optimization

### **Recent Performance Improvements** 📈

- **AI Analysis Optimization**: Multi-model architecture for specialized tasks
- **Threshold Optimization**: Better content capture with maintained quality
- **Content Length Flexibility**: Captures valuable short notes (300+ characters)
- **Professional Writing Assessment**: Advanced evaluation of analytical content
- **Enhanced Processing**: Better handling of mixed content types

### **Performance Metrics**

The system now provides detailed performance analysis:
- Processing time per note
- AI analysis efficiency
- Curation rate optimization
- Throughput improvements
- Quality distribution analysis

## Testing and Validation

### Recent System Validation (August 2024)

The system has been thoroughly tested and validated with comprehensive test runs:

#### **Test Results Summary**
- **20-Note Comprehensive Test**: 94.4% curation rate with proper thresholds (0.65)
- **Quality Scoring Validation**: Fixed systematic 0.30 bias, now properly distributed (0.6-0.8 range)
- **False Positive Analysis**: **Zero false positives detected** - all curated content has genuine value
- **Appropriate Filtering**: System correctly rejects minimal content (<300 characters) without false negatives

#### **Test Configuration**
```bash
# Comprehensive test with proper thresholds
poetry run obsidian-curator curate --quality-threshold 0.65 --relevance-threshold 0.65 --sample-size 20 /Users/jose/Documents/Obsidian/Evermd test-20-notes-comprehensive
```

#### **Quality Metrics**
- **Processing Time**: 276.0s for 20 notes (~13.8s per note)
- **Curation Rate**: 94.4% (17/18 notes curated)
- **Quality Distribution**: All notes scored 0.6-0.8 range (no more 0.30 bias)
- **Theme Classification**: Accurate categorization with 82.4% specific theme identification

#### **Content Quality Validation**
All curated notes demonstrate genuine professional value:
- **Infrastructure Development**: 47.1% (8 notes) - WSJ articles, detailed case studies
- **Governance & Regulation**: 23.5% (4 notes) - FT articles, policy analysis
- **Digital Transformation**: 5.9% (1 note) - Technical analysis with actionable insights
- **Renewable Energy**: 5.9% (1 note) - Comprehensive industry analysis

### Testing Recommendations

#### **For New Users**
```bash
# Start with small test to verify setup
poetry run obsidian-curator curate --sample-size 5 /path/to/vault test-vault

# Validate results and adjust thresholds if needed
poetry run obsidian-curator curate --quality-threshold 0.65 --relevance-threshold 0.65 /path/to/vault curated-vault
```

#### **For Production Use**
```bash
# Full vault curation with optimized thresholds
poetry run obsidian-curator curate /path/to/vault curated-vault

# Monitor quality distribution (should be 0.6-0.8 range, not fixed 0.30)
# Check curation rate (should be 80-95% with 0.65 thresholds)
```

## Troubleshooting

### Common Issues

1. **Ollama Connection Error**
   - Ensure Ollama is running: `ollama serve`
   - Check if the specified model is available: `ollama list`
   - **Verify PyYAML dependency**: `poetry install`

2. **No Notes Found**
   - Verify the input path contains markdown files
   - Check if notes are in subdirectories

3. **Low Curation Rate**
   - **Use optimized thresholds** (quality: 0.65, professional writing: 0.65)
   - Check if target themes match your content
   - Review AI model performance

4. **Memory Issues**
   - Reduce `max_tokens` in configuration
   - Process smaller vaults in batches

### Debug Mode

Use verbose logging to see detailed information:

```bash
poetry run obsidian-curator curate --verbose /path/to/input/vault /path/to/output/vault
```

### Poetry Commands

```bash
# Check Poetry environment
poetry env info

# List installed packages
poetry show

# Add new dependencies
poetry add package-name

# Add development dependencies
poetry add --group dev package-name

# Update dependencies
poetry update
```

## Development

**Note**: This project requires Python 3.12+ and uses Poetry for dependency management.

### Project Structure

```
obsidian_curator/
├── __init__.py          # Package initialization
├── core.py              # Main orchestration logic with optimized thresholds
├── models.py            # Data models and schemas with enhanced configuration
├── content_processor.py # Content processing and cleaning
├── ai_analyzer.py       # AI-powered analysis using multi-model Ollama
├── theme_classifier.py  # Theme classification and organization
├── vault_organizer.py   # Vault organization and file management
├── clutter_patterns.txt # Enhanced content cleaning patterns
└── cli.py               # Command-line interface
```

### Running Tests

```bash
# Run tests using Poetry
poetry run pytest

# Or run the basic functionality test
poetry run python test_basic_functionality.py
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Documentation

Comprehensive documentation is available in the `docs/` folder:

- **`APP_SUMMARY.md`**: High-level overview and problem-solving approach
- **`FUNCTIONALITY_GUIDE.md`**: Detailed technical architecture and component descriptions
- **`PERFORMANCE_ANALYSIS_REPORT.md`**: System performance evaluation and optimization insights
- **`CURATION_DETAILED_ANALYSIS.md`**: Comprehensive analysis of curation decisions
- **`THEMATIC_CLASSIFICATION_ANALYSIS.md`**: Writing purpose alignment and enhancement recommendations
- **`OPTIMIZATION_IMPLEMENTATION_SUMMARY.md`**: Step-by-step improvement documentation
- **`SETUP_GUIDE.md`**: Detailed installation and configuration instructions

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built with [Ollama](https://ollama.ai) for local AI inference
- Uses [Pydantic](https://pydantic.dev) for data validation
- Powered by [Loguru](https://loguru.readthedocs.io) for logging
- Enhanced with [PyYAML](https://pyyaml.org/) for configuration management
