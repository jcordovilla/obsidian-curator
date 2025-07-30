# Testing Guide for Obsidian Note Curator

This guide explains how to test and evaluate the classification system to ensure it's working correctly for your specific use case.

## Installation

```bash
# Install Poetry if you haven't already
curl -sSL https://install.python-poetry.org | python3 -

# Install project dependencies
poetry install

# The project uses Poetry for dependency management
# No need for standard Python venv - Poetry manages its own environment
```

## Overview

The system consists of three main scripts:

1. **`test_classification_system.py`** - **TESTING ONLY**: Runs classification on 100 randomly sampled notes for evaluation
2. **`process_vault.py`** - **NORMAL PROCESSING**: Processes ALL notes sequentially by folder structure
3. **`review_classification_results.py`** - Helps you manually review and validate the results

**Important**: The test script uses random sampling for unbiased evaluation, while the normal process preserves your folder structure and processes all notes.

## Quick Start

### Step 1: Test the System (Recommended First)

```bash
poetry run python test_classification_system.py
```

This will:
- **Randomly sample** 100 notes from your vault using Python's `random.sample()`
- Run the full classification pipeline
- Generate comprehensive evaluation metrics
- Save detailed results to `results/test_runs/` directory
- Verify the randomness of the sample

**Note**: This is for testing only. The sampling is truly random and unbiased.

### Step 2: Process Your Entire Vault (After Testing)

```bash
poetry run python process_vault.py
```

This will:
- **Process ALL notes** sequentially by folder structure
- Preserve your thematic organization
- Consider folder context in classification
- Generate comprehensive results for your entire vault
- Save results to `results/full_runs/` directory

### Step 3: Review the Results

```bash
poetry run python review_classification_results.py
```

This will:
- Let you choose between test results (`results/test_runs/`) or full vault results (`results/full_runs/`)
- Automatically detect if results are from testing or full processing
- Allow you to manually review individual notes
- Collect validation data on accuracy
- Provide a summary assessment
- Show guidance specific to the results type

## What the Tests Evaluate

### Automated Evaluation Metrics

The test script automatically evaluates:

1. **Basic Statistics**
   - Average, median, and standard deviation of scores
   - Confidence levels and distributions
   - Processing efficiency

2. **Action Distribution**
   - How many notes are marked for each action (keep, refine, archive, delete)
   - Average scores for each action type
   - Percentage breakdowns

3. **Quality Distribution**
   - High-value notes (>0.7 score)
   - Medium-value notes (0.5-0.7 score)
   - Low-value notes (<0.5 score)

4. **Pillar Classification**
   - Distribution across your expert pillars
   - Average scores per pillar
   - Unclassified notes percentage

5. **Confidence Analysis**
   - High/medium/low confidence breakdowns
   - Correlation between scores and confidence
   - Average scores by confidence level

6. **Processing Efficiency**
   - Success/failure rates
   - Batch processing performance
   - Average processing times

### Manual Validation

The review script helps you validate:

1. **Action Accuracy** - Are the right notes being kept/refined/archived/deleted?
2. **Pillar Classification** - Are notes correctly assigned to your expert domains?
3. **Note Type Classification** - Are notes correctly categorized by type?
4. **Score Accuracy** - Are the quality scores reasonable?
5. **Confidence Accuracy** - Does the confidence match your assessment?

### Review Script Capabilities

The review script works with **both test results and full vault results**:

- **🧪 Test Results** (≤100 notes): Perfect for validating system performance
  - Review random samples to assess accuracy
  - Focus on high-value and low-confidence notes
  - Use for configuration tuning

- **📚 Full Vault Results** (>100 notes): Comprehensive validation
  - Review representative samples of each action type
  - Validate keep/delete decisions across your entire vault
  - Assess pillar classifications for all content

The script automatically detects which type of results you're reviewing and provides appropriate guidance.

## Results Organization

Results are now organized in separate subfolders for better management:

```
results/
├── test_runs/                    # Test results (≤100 notes)
│   ├── classification_test_*.json
│   ├── analysis_report_test_*.md
│   ├── curation_actions_test_*.md
│   └── evaluation_report_*.json
└── full_runs/                    # Full vault results (>100 notes)
    ├── classification_full_*.json
    ├── analysis_report_full_*.md
    └── curation_actions_full_*.md
```

### Benefits of Separate Folders

- **Clear separation**: Test and full results are kept apart
- **Easy comparison**: Compare test vs. full results side by side
- **Better organization**: No confusion about which results are which
- **Historical tracking**: Keep multiple test runs for comparison
- **Clean workflow**: Test → Tune → Full processing → Review

### Folder Structure Consideration

The system now considers your folder organization as thematic context:

- **Folder Context**: The folder name is included in the analysis prompt
- **Thematic Organization**: Notes are processed sequentially by folder structure
- **Domain Indication**: Folder names may indicate the note's domain or category
- **Quality Assessment**: Folder organization may influence quality scoring

This ensures that your existing knowledge organization is respected and utilized in the classification process.

## Interpreting Results

### Excellent Performance (🟢)
- High-value notes: ≥30%
- High confidence: ≥60%
- Action accuracy: ≥85%
- No major issues detected

### Good Performance (🟡)
- High-value notes: ≥20%
- High confidence: ≥40%
- Action accuracy: ≥70%
- Minor issues that can be addressed

### Needs Attention (🔴)
- High-value notes: <20%
- High confidence: <40%
- Action accuracy: <70%
- Multiple issues detected

## Common Issues and Solutions

### Issue: Too Many Notes Marked for Deletion
**Symptoms**: >50% of notes marked for deletion
**Solutions**:
- Review classification criteria in `config/classification_config.yaml`
- Adjust quality thresholds
- Check if the model is being too strict

### Issue: Too Many Notes Marked as "Keep"
**Symptoms**: >80% of notes marked to keep
**Solutions**:
- Review classification criteria
- Lower the "keep" threshold
- Check if the model is being too lenient

### Issue: Low Confidence Classifications
**Symptoms**: >30% of notes with low confidence
**Solutions**:
- Consider using a larger model
- Improve prompts in the configuration
- Check for content preprocessing issues

### Issue: Poor Score-Confidence Correlation
**Symptoms**: Correlation <0.3
**Solutions**:
- Review scoring algorithm
- Check model calibration
- Validate quality criteria weights

## Configuration Tuning

### Adjusting Quality Thresholds

Edit `config/classification_config.yaml`:

```yaml
curation_actions:
  keep:
    threshold: 0.7  # Increase for stricter keeping
  refine:
    threshold: 0.5  # Adjust refinement threshold
  archive:
    threshold: 0.3  # Adjust archive threshold
```

### Adjusting Quality Weights

```yaml
quality_criteria:
  relevance:
    weight: 0.3  # Adjust importance of relevance
  depth:
    weight: 0.25  # Adjust importance of depth
  actionability:
    weight: 0.2   # Adjust importance of actionability
  uniqueness:
    weight: 0.15  # Adjust importance of uniqueness
  structure:
    weight: 0.1   # Adjust importance of structure
```

### Model Configuration

Edit `config/models_config.yaml` to adjust:
- Context window sizes
- Temperature settings
- Batch processing parameters
- Model selection for different tasks

## Best Practices

### 1. Start Small
- Begin with 100 notes to get a baseline
- Review results thoroughly before scaling up
- Use the manual review tool to validate

### 2. Iterate Gradually
- Make small configuration changes
- Test after each change
- Keep track of improvements

### 3. Focus on High-Impact Areas
- Prioritize fixing high-severity issues
- Address confidence problems first
- Balance precision vs. recall

### 4. Document Changes
- Keep notes on configuration changes
- Track performance improvements
- Document successful settings

## Advanced Testing

### Custom Sample Sizes

Modify the test script to use different sample sizes:

```python
# In test_classification_system.py
results = curator.analyze_vault(sample_size=50)  # Test with 50 notes
```

### Using Poetry Commands

All scripts should be run with Poetry to ensure proper dependency management:

```bash
# Test the system
poetry run python test_classification_system.py

# Process entire vault
poetry run python process_vault.py

# Review results
poetry run python review_classification_results.py

# Or activate the Poetry shell for multiple commands
poetry shell
python test_classification_system.py
python process_vault.py
```

### Reproducible Testing

For reproducible results (same sample each time), uncomment the random seed line in the test script:

```python
# In test_classification_system.py, line ~470
random.seed(42)  # Uncomment for reproducible results
```

**Note**: By default, each run uses a different random sample to ensure unbiased testing across your entire vault.

### Targeted Testing

Use the review script to focus on specific areas:

```bash
# Review only high-value notes
python review_classification_results.py
# Select option 3: Review high-value notes

# Review only low-confidence notes
python review_classification_results.py
# Select option 4: Review low-confidence notes
```

### Batch Testing

Create a script to test multiple configurations:

```python
# Example batch testing
configs = [
    {'keep_threshold': 0.6, 'refine_threshold': 0.4},
    {'keep_threshold': 0.7, 'refine_threshold': 0.5},
    {'keep_threshold': 0.8, 'refine_threshold': 0.6},
]

for config in configs:
    # Apply configuration
    # Run test
    # Save results
```

## Troubleshooting

### Common Errors

1. **Model not found**
   - Ensure the LLM model file exists in `models/`
   - Check the path in `config/models_config.yaml`

2. **Vault path not found**
   - Verify the vault path in `config/vault_config.yaml`
   - Ensure the path is absolute and correct

3. **No notes found**
   - Check include/exclude patterns in vault config
   - Verify note files have `.md` extension

4. **Processing failures**
   - Check model memory requirements
   - Reduce batch size in configuration
   - Verify system resources

### Performance Issues

1. **Slow processing**
   - Reduce context window size
   - Use smaller models for classification
   - Increase batch size for efficiency

2. **Memory issues**
   - Reduce batch size
   - Use quantized models
   - Process smaller samples

3. **Low accuracy**
   - Review and improve prompts
   - Adjust quality criteria weights
   - Consider using larger models

## Next Steps

After successful testing:

1. **Scale up**: Run on larger samples or full vault
2. **Automate**: Set up regular classification runs
3. **Integrate**: Use results in your note management workflow
4. **Monitor**: Track performance over time
5. **Improve**: Continuously refine based on results

## Support

If you encounter issues:

1. Check the logs in the console output
2. Review configuration files for errors
3. Test with smaller samples first
4. Verify all dependencies are installed
5. Check the documentation in `docs/` directory 