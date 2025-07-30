# Obsidian Note Curator

An AI-powered note classification system designed to curate Obsidian vaults based on expert knowledge domains and personal knowledge management (PKM) principles.

## 🚀 Quick Start

### 1. Install Dependencies
```bash
# Install Poetry if you haven't already
curl -sSL https://install.python-poetry.org | python3 -

# Install project dependencies
poetry install
```

### 2. Configure Your Vault
Edit `config/vault_config.yaml` to point to your Obsidian vault:
```yaml
vault:
  path: "/path/to/your/obsidian/vault"
```

### 3. Run Analysis
```bash
# Process your entire vault
poetry run python scripts/process_vault.py

# Or test with a sample first
poetry run python scripts/test_classification_system.py
```

## 📁 Project Structure

```
Obsidian-test2/
├── 📂 config/                 # Configuration files
│   ├── vault_config.yaml     # Vault paths and settings
│   ├── classification_config.yaml  # Expert pillars and criteria
│   └── models_config.yaml    # LLM model configurations
├── 📂 note_curator/          # Main package (core functionality)
├── 📂 scripts/               # Main execution scripts
│   ├── process_vault.py      # Process entire vault
│   ├── test_classification_system.py  # System testing
│   └── review_classification_results.py  # Results review
├── 📂 tools/                 # Utility tools and examples
├── 📂 docs/                  # Comprehensive documentation
├── 📂 results/               # Analysis results and reports
├── 📂 models/                # LLM model files
├── 📂 legacy/                # Old system files (reference only)
└── 📄 README.md              # This file
```

## 🎯 Key Features

- **Domain-Aware Classification**: Based on your expert pillars (PPP, Infrastructure, Digital Transformation)
- **Hybrid Model Approach: Llama 3.2 1B for speed, Llama 3.1 8B for quality
- **Batch Processing**: Efficiently processes large vaults
- **Rich Output**: Detailed analysis with confidence scores and reasoning
- **Professional CLI**: Progress tracking and comprehensive reporting

## 🏛️ Expert Pillars

The system is designed around these knowledge domains:

1. **PPP Fundamentals** - Public-private partnerships, project finance, governance
2. **Operational Risk** - Risk management in complex infrastructure projects
3. **Value for Money** - Lifecycle value, resilience, and long-term outcomes
4. **Digital Transformation** - BIM, data analytics, automation
5. **Governance & Transparency** - Stakeholder alignment, open data

## 📖 Documentation

- **[Setup Guide](docs/SETUP.md)** - Complete setup and configuration instructions
- **[Testing Guide](docs/TESTING_GUIDE.md)** - How to test and validate the system
- **[Content Processing](docs/CONTENT_PROCESSING.md)** - Evernote cleanup and note normalization
- **[Performance Guide](docs/PERFORMANCE.md)** - Optimization and performance tips
- **[Overhaul Summary](docs/OVERHAUL_SUMMARY.md)** - System transformation details

## 🔧 Configuration

The system uses YAML configuration files in the `config/` directory:

- **`vault_config.yaml`** - Vault paths and processing settings
- **`classification_config.yaml`** - Expert pillars and classification criteria
- **`models_config.yaml`** - LLM model configurations

## 📊 Output

Results are organized in the `results/` directory:

- **JSON files** - Complete analysis data for programmatic access
- **Markdown reports** - Human-readable summaries and recommendations
- **Normalized notes** - Structured and templated notes (when enabled)

## 🛠️ Development

For development and testing:

```bash
# Run system tests (recommended - no warnings)
poetry run python scripts/run_quiet.py

# Run system tests (with warnings)
poetry run python scripts/test_classification_system.py

# Run utility examples
poetry run python tools/example_usage.py

# Analyze test results
poetry run python scripts/analyze_test_results.py
```

## 📝 License

This project is designed for personal knowledge management and infrastructure consulting domains. 