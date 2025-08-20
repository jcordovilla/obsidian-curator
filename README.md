# Obsidian Curator

An AI-powered curation system for Obsidian vaults that automatically analyzes, categorizes, and organizes your notes using local AI models via Ollama.

## Features

- **AI-Powered Analysis**: Uses Ollama with local AI models to analyze note quality and relevance
- **Intelligent Curation**: Automatically determines which notes meet your curation criteria
- **Theme Classification**: Organizes notes into hierarchical themes (infrastructure, construction, economics, etc.)
- **Content Processing**: Cleans and processes various content types including web clippings and markdown
- **Vault Organization**: Creates a well-structured curated vault with metadata and statistics
- **Flexible Configuration**: Customizable quality thresholds, target themes, and processing options

## Installation

### Prerequisites

1. **Python 3.12+** with Poetry
2. **Ollama** installed and running with at least one model (e.g., `gpt-oss:20b`)

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

### Pull an AI Model

```bash
ollama pull gpt-oss:20b
```

## Quick Start

### Prerequisites

1. **Python 3.12+** with Poetry
2. **Ollama** installed and running with at least one model (e.g., `gpt-oss:20b`)

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
# Test with a small sample first
poetry run obsidian-curator curate --sample-size 5 /Users/jose/Documents/Obsidian/Evermd test-curated-vault

# Full curation of your vault
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

**Default Settings:**
- Source vault: `/Users/jose/Documents/Obsidian/Evermd`
- Uses configuration from `config.yaml`
- Test run default: 10 notes sample

### Command Line Interface

The easiest way to use Obsidian Curator is through the command line:

```bash
# Basic curation with default settings
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

# Configuration
config = CurationConfig(
    ai_model="gpt-oss:20b",
    quality_threshold=0.7,
    relevance_threshold=0.6,
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
- **`quality_threshold`**: Minimum quality score for curation (0.0-1.0, default: 0.7)
- **`relevance_threshold`**: Minimum relevance score for curation (0.0-1.0, default: 0.6)
- **`max_tokens`**: Maximum tokens for AI analysis (default: 2000)
- **`target_themes`**: List of target themes to focus on (default: infrastructure themes)
- **`preserve_metadata`**: Whether to preserve original note metadata (default: True)
- **`clean_html`**: Whether to clean HTML content (default: True)

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

### 3. AI Analysis
- Uses Ollama to analyze note quality across multiple dimensions:
  - Overall quality
  - Relevance to target themes
  - Completeness of ideas
  - Credibility of source
  - Clarity of expression
- Identifies themes and assigns confidence scores
- Determines curation decision based on thresholds

### 4. Theme Classification
- Maps identified themes to the predefined hierarchy
- Uses fuzzy matching for theme names
- Creates nested folder structures for subthemes

### 5. Vault Organization
- Creates organized folder structure by themes
- Saves curated notes with enhanced metadata
- Generates comprehensive reports and statistics
- Preserves curation history and reasoning

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
    └── statistics.json
```

## Examples

See the `examples/` directory for complete working examples:

- **`basic_curation.py`**: Simple example of basic vault curation
- **`advanced_curation.py`**: Advanced usage with custom configuration and detailed analysis

## Troubleshooting

### Common Issues

1. **Ollama Connection Error**
   - Ensure Ollama is running: `ollama serve`
   - Check if the specified model is available: `ollama list`

2. **No Notes Found**
   - Verify the input path contains markdown files
   - Check if notes are in subdirectories

3. **Low Curation Rate**
   - Lower quality or relevance thresholds
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
├── core.py              # Main orchestration logic
├── models.py            # Data models and schemas
├── content_processor.py # Content processing and cleaning
├── ai_analyzer.py       # AI-powered analysis using Ollama
├── theme_classifier.py  # Theme classification and organization
├── vault_organizer.py   # Vault organization and file management
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

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built with [Ollama](https://ollama.ai) for local AI inference
- Uses [Pydantic](https://pydantic.dev) for data validation
- Powered by [Loguru](https://loguru.readthedocs.io) for logging
