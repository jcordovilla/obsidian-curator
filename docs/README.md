# Documentation

This directory contains comprehensive documentation for the Obsidian Note Curator system.

## 📚 Documentation Index

### Getting Started
- **[Setup Guide](SETUP.md)** - Complete setup instructions, configuration, and troubleshooting
- **[Testing Guide](TESTING_GUIDE.md)** - How to test and validate the system
- **[Overhaul Summary](OVERHAUL_SUMMARY.md)** - Details about the system transformation and improvements

### Advanced Features
- **[Content Processing](CONTENT_PROCESSING.md)** - Evernote web clipping cleanup and note normalization
- **[Performance Guide](PERFORMANCE.md)** - Optimization and performance tips

## 🎯 System Overview

The Obsidian Note Curator is an AI-powered note classification system designed specifically for expert knowledge management in infrastructure consulting, PPP, and digital transformation domains.

### Key Features

- **Domain-aware classification** based on expert pillars
- **Multi-stage processing** with different LLM models
- **Rich configuration** via YAML files
- **Professional CLI interface** with progress tracking
- **Comprehensive reporting** in multiple formats

### Expert Pillars

The system is designed around five expert knowledge domains:

1. **PPP Fundamentals** - Public-private partnerships, project finance, governance
2. **Operational Risk** - Risk management in complex infrastructure projects
3. **Value for Money** - Lifecycle value, resilience, and long-term outcomes
4. **Digital Transformation** - BIM, data analytics, automation
5. **Governance & Transparency** - Stakeholder alignment, open data

## 🚀 Quick Commands

```bash
# Check system status
poetry run curate-notes status

# Analyze sample notes
poetry run curate-notes analyze --sample-size 10

# Analyze single note
poetry run curate-notes analyze-single --file /path/to/note.md

# Show configuration
poetry run curate-notes config
```

## 📁 Project Organization

The project is now organized into logical directories:

- **`scripts/`** - Main execution scripts
- **`tools/`** - Utility tools and examples
- **`config/`** - Configuration files
- **`docs/`** - This documentation
- **`results/`** - Analysis results and reports

For detailed setup and usage instructions, see the [Setup Guide](SETUP.md). 