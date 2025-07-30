# Obsidian Note Curator - Setup Guide

This guide will help you set up the overhauled note classification system.

## Overview

The new system provides:
- **Domain-aware classification** based on your expert pillars (PPP, Infrastructure, Digital Transformation)
- **Multi-stage processing** with different LLM models for different tasks
- **Rich configuration** via YAML files
- **Professional CLI interface** with progress tracking and detailed reports
- **Poetry-based dependency management** for easy installation and updates

## Quick Start

### 1. Install Poetry

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

### 2. Install Dependencies

```bash
poetry install
```

### 3. Configure Your Vault

Edit `config/vault_config.yaml` to point to your Obsidian vault:

```yaml
vault:
  path: "/path/to/your/obsidian/vault"
```

### 4. Check System Status

```bash
poetry run curate-notes status
```

### 5. Run Analysis

```bash
# Analyze a sample of 10 notes
poetry run curate-notes analyze --sample-size 10

# Analyze all notes
poetry run curate-notes analyze

# Analyze a single note
poetry run curate-notes analyze-single --file /path/to/note.md
```

## Configuration

### Vault Configuration (`config/vault_config.yaml`)

```yaml
vault:
  path: "/Users/jose/Documents/Evermd"
  include_patterns:
    - "*.md"
  exclude_patterns:
    - "**/node_modules/**"
    - "**/.git/**"
    - "**/attachments/**"

processing:
  max_notes_per_batch: 20
  max_note_chars: 3000
  process_attachments: false
  include_frontmatter: true

output:
  results_dir: "results"
  formats: ["json", "markdown", "csv"]
  detailed_logging: true
```

### Classification Configuration (`config/classification_config.yaml`)

This file defines your expert pillars and classification criteria. The system is pre-configured for:

1. **PPP Fundamentals** - Public-private partnerships, project finance
2. **Operational Risk** - Risk management in complex projects
3. **Value for Money** - Lifecycle value and resilience
4. **Digital Transformation** - BIM, data analytics, automation
5. **Governance & Transparency** - Stakeholder alignment, open data

### Models Configuration (`config/models_config.yaml`)

Configure different LLM models for different tasks:

- **Analysis model** - For detailed content analysis
- **Classification model** - For quick classification decisions
- **Summary model** - For content summarization

## Expert Pillars

The system is designed around your specific knowledge domains:

### Pillar 1: PPP Fundamentals
- Public-private partnerships
- Project finance and infrastructure financing
- Concession models (BOT, BOOT, PFI)
- Value for money assessments
- Risk allocation strategies

### Pillar 2: Operational Risk Management
- Cyber risk in infrastructure
- Climate risk and adaptation
- Resource scarcity challenges
- Risk assessment methodologies
- Mitigation and contingency planning

### Pillar 3: Value for Money Beyond Numbers
- Lifecycle cost analysis
- Resilience and adaptability
- Long-term outcomes
- Sustainability considerations
- Social and environmental value

### Pillar 4: Digital Transformation
- Building Information Modeling (BIM)
- Data analytics and automation
- AI and machine learning applications
- IoT and smart infrastructure
- Digital twins and simulation

### Pillar 5: Governance & Transparency
- Stakeholder engagement
- Public trust and legitimacy
- Open data initiatives
- Accountability frameworks
- Communication strategies

## Note Types

The system classifies notes into these categories:

- **Literature/Research Notes** - Academic summaries, key points, references
- **Project Plans & Workflows** - Step-by-step instructions, process guides
- **Personal Reflections** - Journals, learning diaries, insights
- **Technical/Code Notes** - Scripts, technical documentation
- **Meeting Notes & Templates** - Meeting summaries, templates, checklists
- **Community & Events** - Community summaries, event analyses

## Quality Assessment

Notes are scored on five criteria:

1. **Relevance** (30%) - How well the note relates to your expert domains
2. **Depth** (25%) - Level of analysis and insight provided
3. **Actionability** (20%) - How actionable the content is
4. **Uniqueness** (15%) - How unique or novel the insights are
5. **Structure** (10%) - How well organized the content is

## Curation Actions

Based on quality scores, notes are assigned one of four actions:

- **Keep** (Score > 0.7) - High-value content worth preserving as-is
- **Refine** (Score 0.5-0.7) - Good content that needs improvement
- **Archive** (Score 0.3-0.5) - Potentially useful but not immediately actionable
- **Delete** (Score < 0.3) - Low value, redundant, or outdated content

## Output Files

The system generates three types of output:

1. **JSON Results** (`results/classification_YYYYMMDD_HHMMSS.json`)
   - Complete analysis data in machine-readable format

2. **Markdown Report** (`results/analysis_report_YYYYMMDD_HHMMSS.md`)
   - Human-readable summary with statistics and insights

3. **Curation Actions** (`results/curation_actions_YYYYMMDD_HHMMSS.md`)
   - Detailed recommendations for each note, grouped by action

## CLI Commands

### Main Commands

```bash
# Analyze vault
poetry run curate-notes analyze [--sample-size N] [--vault-path PATH]

# Analyze single note
poetry run curate-notes analyze-single --file /path/to/note.md

# Show configuration
poetry run curate-notes config

# Check system status
poetry run curate-notes status
```

### Options

- `--verbose, -v` - Enable detailed logging
- `--config-dir PATH` - Use custom configuration directory
- `--sample-size N` - Process only N notes (for testing)
- `--vault-path PATH` - Override vault path from config

## Migration from Old System

If you're upgrading from the old `filter_notes.py` system:

1. **Run migration script**:
   ```bash
   python migrate_from_old.py
   ```

2. **Install new system**:
   ```bash
   poetry install
   ```

3. **Test the new system**:
   ```bash
   poetry run curate-notes status
   poetry run curate-notes analyze --sample-size 5
   ```

## Troubleshooting

### Common Issues

1. **Model not found**
   - Ensure your LLM model is in the `models/` directory
   - Check the path in `config/models_config.yaml`

2. **Vault path not found**
   - Verify the vault path in `config/vault_config.yaml`
   - Use `--vault-path` to override

3. **Memory issues**
   - Reduce `max_notes_per_batch` in vault config
   - Reduce `max_note_chars` for very long notes
   - Use `--sample-size` for testing

4. **Slow processing**
   - Check GPU availability for LLM models
   - Reduce `n_threads` in models config
   - Use smaller models for classification tasks

### Getting Help

- Check system status: `poetry run curate-notes status`
- Enable verbose logging: `poetry run curate-notes --verbose analyze`
- Review configuration: `poetry run curate-notes config`

## Advanced Usage

### Custom Classification Criteria

Edit `config/classification_config.yaml` to:
- Add new expert pillars
- Modify keyword lists
- Adjust quality criteria weights
- Change curation action thresholds

### Custom Models

Edit `config/models_config.yaml` to:
- Use different LLM models for different tasks
- Adjust context windows and token limits
- Configure GPU/CPU usage
- Set temperature and sampling parameters

### Batch Processing

For large vaults:
1. Start with small samples: `--sample-size 10`
2. Gradually increase batch size in config
3. Monitor memory usage and processing time
4. Use `--verbose` for detailed progress tracking

## Performance Tips

1. **Use appropriate model sizes**:
   - Large models for analysis
   - Smaller models for classification
   - Summary models for quick tasks

2. **Optimize batch processing**:
   - Balance batch size with memory usage
   - Use GPU acceleration when available
   - Monitor system resources

3. **Efficient file handling**:
   - Exclude unnecessary directories
   - Limit note character count
   - Process attachments selectively

## Future Enhancements

The system is designed for extensibility:

- **Custom pillar definitions** - Add domain-specific knowledge areas
- **Advanced filtering** - Filter by date, tags, or content patterns
- **Integration APIs** - Connect with Obsidian plugins or external tools
- **Machine learning** - Train custom models on your specific content
- **Collaborative features** - Share classifications and insights

---

For questions or issues, please refer to the troubleshooting section or check the system status with `poetry run curate-notes status`. 