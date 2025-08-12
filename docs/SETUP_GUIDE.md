# Obsidian Curator - Setup Guide

## Quick Start

### 1. Prerequisites Check

Before starting, ensure you have:
- **Python 3.12+** installed
- **Poetry** for dependency management
- **Ollama** installed and running
- Access to your Obsidian vault with notes to curate

### 2. Install Ollama

```bash
# macOS
brew install ollama

# Linux  
curl -fsSL https://ollama.ai/install.sh | sh

# Windows
# Download from https://ollama.ai/download
```

### 3. Pull an AI Model

```bash
# Start Ollama service
ollama serve

# In a new terminal, pull the recommended model
ollama pull gpt-oss:20b

# Verify installation
ollama list
```

### 4. Install Obsidian Curator

```bash
# Clone the repository
git clone https://github.com/yourusername/obsidian-curator.git
cd obsidian-curator

# Install Poetry if needed
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Verify installation
poetry run obsidian-curator --help
```

## First Run

### Test with Sample Data

```bash
# Test the system with your writings folder first
poetry run obsidian-curator curate --sample-size 5 my-writings test-output

# Check the results
ls -la test-output/
cat test-output/metadata/curation-log.md
```

### Full Vault Curation

```bash
# Process your full vault (replace paths with your actual vault location)
poetry run obsidian-curator curate /Users/jose/Documents/Obsidian/Evermd curated-vault

# Monitor progress and results
tail -f curated-vault/metadata/curation-log.md
```

## Configuration

### Basic Configuration

Create a `config.yaml` file:

```yaml
# AI Configuration
ai_model: "gpt-oss:20b"
max_tokens: 2000

# Quality Thresholds
quality_threshold: 0.7
relevance_threshold: 0.6

# Target Themes
target_themes:
  - infrastructure
  - construction
  - governance

# Processing Options
preserve_metadata: true
clean_html: true
sample_size: null  # Process all notes
```

### Advanced Configuration

```yaml
# Higher quality standards
quality_threshold: 0.8
relevance_threshold: 0.7
max_tokens: 3000

# Specific theme focus
target_themes:
  - infrastructure
  - ppps
  - resilience
  - sustainability

# Processing tweaks
preserve_metadata: true
clean_html: true
remove_duplicates: true

# Large vault handling
sample_size: 100  # Process in smaller batches
```

## Troubleshooting

### Common Issues

#### 1. Ollama Connection Error
```
Error: Failed to connect to Ollama
```

**Solution:**
```bash
# Check if Ollama is running
ollama list

# If not running, start it
ollama serve

# Verify the model is available
ollama run gpt-oss:20b
```

#### 2. No Notes Found
```
Warning: No notes found in input vault
```

**Solution:**
```bash
# Check vault path is correct
ls -la /path/to/your/vault/

# Look for markdown files
find /path/to/your/vault/ -name "*.md" | head -10

# Check permissions
ls -la /path/to/your/vault/
```

#### 3. Low Curation Rate
```
Results: 5/100 notes curated (5.0%)
```

**Solution:**
```bash
# Lower thresholds for more inclusive curation
poetry run obsidian-curator curate --quality-threshold 0.5 --relevance-threshold 0.4 /path/to/vault /path/to/output

# Check what themes are being identified
poetry run obsidian-curator analyze /path/to/vault --verbose
```

#### 4. Memory Issues
```
Error: Out of memory during processing
```

**Solution:**
```bash
# Use smaller sample size
poetry run obsidian-curator curate --sample-size 50 /path/to/vault /path/to/output

# Reduce token limit
poetry run obsidian-curator curate --max-tokens 1000 /path/to/vault /path/to/output
```

### Debug Mode

Enable verbose logging to diagnose issues:

```bash
# Verbose output
poetry run obsidian-curator curate --verbose /path/to/vault /path/to/output

# Dry run to see what would happen
poetry run obsidian-curator curate --dry-run /path/to/vault /path/to/output
```

## Optimization Tips

### 1. Start Small
- Begin with `--sample-size 10` to test configuration
- Gradually increase sample size
- Process full vault only after testing

### 2. Adjust Thresholds
- **High Standards**: quality=0.8, relevance=0.7
- **Balanced**: quality=0.7, relevance=0.6 (default)
- **Inclusive**: quality=0.5, relevance=0.4

### 3. Theme Targeting
```bash
# Focus on specific areas
poetry run obsidian-curator curate --target-themes infrastructure,construction /path/to/vault /path/to/output

# Process everything
poetry run obsidian-curator curate /path/to/vault /path/to/output
```

### 4. Batch Processing
For large vaults (1000+ notes):

```python
# Use programmatic API for batch processing
from obsidian_curator import ObsidianCurator, CurationConfig

config = CurationConfig(quality_threshold=0.7)
curator = ObsidianCurator(config)

# Process in batches
stats = curator.batch_process_vault(input_path, output_path, batch_size=100)
```

## Understanding Results

### Curation Log
Check `curated-vault/metadata/curation-log.md` for:
- Which notes were curated/rejected and why
- Quality scores for each note
- Processing errors or warnings

### Theme Analysis
Review `curated-vault/metadata/theme-analysis.md` for:
- Distribution of themes in your content
- Quality statistics by theme
- Suggestions for improvement

### Statistics
Examine `curated-vault/metadata/statistics.json` for:
- Processing metrics
- Quality score distributions
- Performance data

## Next Steps

### 1. Review Results
- Check the curated vault structure
- Verify theme organization makes sense
- Review quality of selected content

### 2. Refine Configuration
- Adjust thresholds based on results
- Add or modify target themes
- Tune processing options

### 3. Iterate
- Process additional content
- Update configuration based on learnings
- Build comprehensive curated knowledge base

### 4. Integration
- Import curated vault into Obsidian
- Set up regular curation workflows
- Share curated content with team

## Performance Expectations

### Typical Processing Speeds
- **Small vault** (50-100 notes): 1-2 minutes
- **Medium vault** (500-1000 notes): 10-20 minutes  
- **Large vault** (2000+ notes): 30-60 minutes

### Expected Curation Rates
- **High-quality vaults**: 60-80% curation rate
- **Mixed content vaults**: 30-50% curation rate
- **Research/clip vaults**: 20-40% curation rate

### Resource Usage
- **Memory**: 1-2GB for typical processing
- **CPU**: Moderate usage during AI analysis
- **Disk**: 2x input vault size for output and processing

## Support

### Getting Help
1. Check this setup guide first
2. Review the functionality guide for detailed explanations
3. Run with `--verbose` for detailed logging
4. Use `--dry-run` to preview without changes

### Common Commands Reference
```bash
# Basic commands
poetry run obsidian-curator curate INPUT OUTPUT
poetry run obsidian-curator analyze VAULT_PATH
poetry run obsidian-curator models

# Testing commands  
poetry run obsidian-curator curate --sample-size 5 INPUT OUTPUT
poetry run obsidian-curator curate --dry-run INPUT OUTPUT

# Configuration commands
poetry run obsidian-curator curate --quality-threshold 0.8 INPUT OUTPUT
poetry run obsidian-curator curate --target-themes infrastructure,construction INPUT OUTPUT

# Debug commands
poetry run obsidian-curator curate --verbose INPUT OUTPUT
poetry run python test_basic_functionality.py
```

This setup guide should get you up and running with Obsidian Curator quickly and help resolve common issues.
