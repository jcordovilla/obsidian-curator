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
Obsidian-curator/
├── 📂 config/                 # Configuration files
│   ├── vault_config.yaml     # Vault paths and settings
│   ├── classification_config.yaml  # Expert pillars and criteria
│   └── models_config.yaml    # LLM model configurations
├── 📂 note_curator/          # Main package (core functionality)
├── 📂 scripts/               # Main execution scripts
│   ├── process_vault.py      # Process entire vault
│   ├── test_classification_system.py  # System testing
│   ├── analyze_test_results.py  # Results analysis
│   ├── human_validation_classification.py  # Human validation interface
│   ├── analyze_validation_results.py  # Validation analysis
│   ├── test_human_validation.py  # Validation testing
│   └── run_validation_demo.py  # Validation demo
├── 📂 tools/                 # Utility tools and examples
├── 📂 docs/                  # Comprehensive documentation
├── 📂 results/               # Analysis results and reports
│   ├── test_runs/           # AI classification results
│   ├── full_runs/           # Full vault processing results
│   └── human_validation/    # Human validation sessions and analysis
├── 📂 models/                # LLM model files
└── 📄 README.md              # This file
```

## 🎯 Key Features

- **Domain-Aware Classification**: Based on your expert pillars (PPP, Infrastructure, Digital Transformation)
- **Hybrid Model Approach**: Llama 3.2 1B for speed, Llama 3.1 8B for quality
- **Batch Processing**: Efficiently processes large vaults
- **Rich Output**: Detailed analysis with confidence scores and reasoning
- **Professional CLI**: Progress tracking and comprehensive reporting
- **Human-in-the-Loop Validation**: Interactive review and validation of AI classifications

## 🏛️ Expert Pillars

The system is designed around these knowledge domains:

1. **PPP Fundamentals** - Public-private partnerships, project finance, governance
2. **Operational Risk** - Risk management in complex infrastructure projects
3. **Value for Money** - Lifecycle value, resilience, and long-term outcomes
4. **Digital Transformation** - BIM, data analytics, automation
5. **Governance & Transparency** - Stakeholder alignment, open data

## 👤 Human-in-the-Loop Validation

The system now includes comprehensive human validation capabilities:

### **Interactive Review Process**
- **AI Classification**: System processes notes using expert criteria
- **Human Validation**: Interactive interface for reviewing AI decisions
- **Feedback Collection**: Capture human reasoning and confidence levels
- **Disagreement Analysis**: Identify patterns in human-AI disagreements

### **Validation Tools**
- **`human_validation_classification.py`** - Interactive classification validation interface
- **`review_classification_results.py`** - Legacy review interface
- **`analyze_validation_results.py`** - Analysis of validation patterns
- **`test_human_validation_pipeline.py`** - Complete validation workflow

### **Benefits**
- **Quality Assurance**: Human oversight of AI decisions
- **System Improvement**: Data-driven refinement of classification criteria
- **Trust Building**: Transparent decision-making process
- **Iterative Learning**: Continuous improvement through feedback

### **New Human Validation Interface**
The system now includes a dedicated classification validation interface:

```bash
# Run the interactive validation interface
python3 scripts/human_validation_classification.py

# Test the validation logic
python3 scripts/test_human_validation.py
```

**Features:**
- **Interactive Note Review**: Display note content and AI classifications
- **Human Input Collection**: Collect human judgments on classifications
- **Agreement Analysis**: Track human-AI agreement rates
- **Quality Assessment**: Compare AI and human quality scores
- **Improvement Recommendations**: Generate actionable insights
- **Results Export**: Save validation data for analysis

See [Human Validation Documentation](docs/HUMAN_VALIDATION.md) for detailed usage instructions.

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
# Run system tests
poetry run python scripts/test_classification_system.py

# Test optimized pipeline
poetry run python scripts/test_optimized_pipeline.py

# Advanced evaluation
poetry run python scripts/test_self_evaluating_pipeline.py

# Analyze test results
poetry run python scripts/analyze_test_results.py

# Human-in-the-loop validation (NEW!)
poetry run python scripts/test_human_validation_pipeline.py

# Review AI classifications manually
poetry run python scripts/review_classification_results.py

# Analyze validation results
poetry run python scripts/analyze_validation_results.py
```

## 📝 License

This project is designed for personal knowledge management and infrastructure consulting domains. 