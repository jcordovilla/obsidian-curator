# Scripts Directory

This directory contains the main execution scripts for the Obsidian Note Curator system.

## 🚀 Main Scripts

### `process_vault.py`
Process your entire Obsidian vault for classification and curation.

```bash
poetry run python scripts/process_vault.py
```

### `test_classification_system.py`
Test the classification system with a small sample of notes to validate performance.

```bash
poetry run python scripts/test_classification_system.py
```

### `analyze_test_results.py`
Simple analysis script that studies test outputs and draws conclusions.

```bash
poetry run python scripts/analyze_test_results.py
```

This script:
- Automatically finds the latest test results
- Analyzes classification performance
- Examines content relevance
- Identifies potential issues
- Draws conclusions and provides recommendations
- No interactive prompts - just runs and shows results

## 📊 Workflow

1. **Test the system**: `test_classification_system.py`
2. **Analyze results**: `analyze_test_results.py`
3. **Process full vault**: `process_vault.py` (when ready)

## 🛠️ Configuration

The system is optimized for:
- ✅ **CPU-only processing** for stability and compatibility
- ✅ **Optimized context windows** for better model utilization
- ✅ **Efficient thread allocation** for macOS performance
- ✅ **Caching and parallel processing** for improved speed

## 📁 Output

Results are saved to:
- `results/test_runs/` - Test results and detailed analysis
- `results/full_runs/` - Full vault processing results
- `results/normalized_notes/` - Processed and normalized notes 