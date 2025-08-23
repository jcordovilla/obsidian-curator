# Obsidian Curator - Setup Guide

## Quick Start

### 1. Prerequisites Check

Before starting, ensure you have:
- **Python 3.12+** installed
- **Poetry** for dependency management
- **Ollama** installed and running with **multiple AI models for optimal performance**
- **PyYAML** dependency for configuration validation
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

### 3. Pull AI Models for Optimal Performance

```bash
# Start Ollama service
ollama serve

# In a new terminal, pull the recommended models for multi-model architecture
# Core model for content curation
ollama pull phi3:mini

# High-quality model for detailed analysis
ollama pull llama3.1:8b

# Premium model for complex reasoning
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

# Install dependencies (including PyYAML)
poetry install

# Verify installation
poetry run obsidian-curator --help
```

## First Run

### Test with Sample Data

```bash
# Test the system with your writings folder first (recommended for new users)
poetry run obsidian-curator curate --sample-size 5 my-writings test-output

# Check the results
ls -la test-output/
cat test-output/metadata/curation-log.md
```

### Full Vault Curation

```bash
# Process your full vault with optimized thresholds (replace paths with your actual vault location)
poetry run obsidian-curator curate /Users/jose/Documents/Obsidian/Evermd curated-vault

# Monitor progress and results
tail -f curated-vault/metadata/curation-log.md
```

## Configuration

### **Optimized Default Configuration** 🎯

The system now uses **optimized thresholds** for better content capture. Create a `config.yaml` file:

```yaml
# AI Configuration - Multi-Model Architecture
ai_model: "gpt-oss:20b"  # Primary model for complex reasoning
max_tokens: 2000

# Quality Thresholds - Optimized for Better Content Capture
quality_threshold: 0.65  # Lowered from 0.75 for broader capture
relevance_threshold: 0.65 # Maintained for precision
analytical_depth_threshold: 0.65  # For publication-ready content
professional_writing_threshold: 0.65  # Lowered from 0.70 for analytical content
min_content_length: 300   # Reduced from 500 for valuable short notes

# Target Themes
target_themes:
  - infrastructure
  - construction
  - governance

# Processing Options
preserve_metadata: true
clean_html: true
```

### **Performance-Optimized Configuration**

For **maximum content capture** with maintained quality:

```yaml
# Optimized for broader content inclusion
quality_threshold: 0.65
professional_writing_threshold: 0.65
min_content_length: 300
relevance_threshold: 0.65
```

For **high-quality curation** (more selective):

```yaml
# More selective curation
quality_threshold: 0.75
professional_writing_threshold: 0.70
min_content_length: 500
relevance_threshold: 0.70
```

For **balanced approach**:

```yaml
# Balanced curation
quality_threshold: 0.70
professional_writing_threshold: 0.68
min_content_length: 400
relevance_threshold: 0.68
```

## Multi-Model AI Architecture

### **Model Specialization**

The system now uses **multiple AI models** for specialized tasks:

- **`phi3:mini`**: Efficient content curation and initial screening
- **`llama3.1:8b`**: Detailed quality analysis and assessment
- **`gpt-oss:20b`**: Complex reasoning and theme classification

### **Performance Benefits**

- **Efficient Processing**: Smaller models for simple tasks, larger for complex ones
- **Specialized Analysis**: Each model optimized for specific functions
- **Fallback Handling**: Graceful degradation when models are unavailable
- **Resource Optimization**: Better memory and processing efficiency

## Advanced Configuration

### **Enhanced Processing Options**

```yaml
# Advanced Processing Configuration
processing:
  batch_size: 10                    # Notes processed per batch
  max_concurrent_ai: 3             # Maximum concurrent AI analysis
  preserve_metadata: true           # Keep original note metadata
  clean_html: true                  # Remove web clutter
  enhanced_content_processing: true # Advanced content type handling

# Performance Monitoring
performance:
  enable_metrics: true              # Track processing performance
  log_timing: true                  # Detailed timing analysis
  throughput_analysis: true         # Notes processed per minute
```

### **Theme Customization**

```yaml
# Custom Theme Hierarchy
custom_themes:
  infrastructure:
    - ppps: "Public-Private Partnerships"
    - resilience: "Climate Adaptation & Disaster Recovery"
    - financing: "Funding & Investment Analysis"
    - governance: "Regulation & Policy"
    - technology: "Innovation & Digital Transformation"
  
  construction:
    - projects: "Project Management"
    - best_practices: "Standards & Guidelines"
    - materials: "Construction Materials"
    - safety: "Risk Management & Safety"
```

## Performance Optimization

### **Recommended Settings for Different Use Cases**

#### **Large Vaults (1000+ notes)**
```yaml
# Optimize for processing speed
batch_size: 20
max_concurrent_ai: 5
quality_threshold: 0.65  # Broader capture
min_content_length: 300  # Include short notes
```

#### **High-Quality Curation**
```yaml
# Focus on quality over quantity
quality_threshold: 0.75
professional_writing_threshold: 0.70
min_content_length: 500
batch_size: 5  # Smaller batches for detailed analysis
```

#### **Testing and Development**
```yaml
# Quick testing configuration
sample_size: 10
quality_threshold: 0.60  # Very broad capture for testing
verbose_logging: true
performance_metrics: true
```

### **Performance Monitoring**

Enable performance tracking to optimize your setup:

```bash
# Run with performance metrics
poetry run obsidian-curator curate --performance-metrics /path/to/input /path/to/output

# Check performance report
cat curated-vault/metadata/performance-metrics.md
```

## Troubleshooting

### **Common Setup Issues**

#### **1. PyYAML Dependency Error**
```bash
# If you get "ModuleNotFoundError: No module named 'yaml'"
poetry add pyyaml
poetry install
```

#### **2. Ollama Connection Issues**
```bash
# Check if Ollama is running
ollama serve

# Verify models are available
ollama list

# Test model response
ollama run phi3:mini "Hello, world!"
```

#### **3. Configuration Validation**
```bash
# Validate your configuration
poetry run obsidian-curator validate-config

# Check configuration syntax
poetry run obsidian-curator curate --dry-run /path/to/input /path/to/output
```

### **Performance Issues**

#### **Low Curation Rate**
- **Use optimized thresholds**: quality: 0.65, professional writing: 0.65
- Check theme alignment with your content
- Verify AI model performance and availability

#### **Slow Processing**
- Monitor multi-model usage and resource allocation
- Check batch processing configuration
- Verify Ollama service status

#### **Memory Issues**
- Reduce batch size for large vaults
- Use smaller models for initial testing
- Monitor system resource usage

## Testing and Validation

### **Step-by-Step Testing Process**

1. **Configuration Test**
```bash
# Validate configuration
poetry run obsidian-curator validate-config
```

2. **Small Sample Test**
```bash
# Test with 5 notes
poetry run obsidian-curator curate --sample-size 5 /path/to/vault test-output
```

3. **Performance Test**
```bash
# Test with performance metrics
poetry run obsidian-curator curate --performance-metrics --sample-size 20 /path/to/vault test-output
```

4. **Full Run Test**
```bash
# Full vault curation
poetry run obsidian-curator curate /path/to/vault curated-output
```

### **Validation Checklist**

- [ ] Configuration file loads without errors
- [ ] AI models respond correctly
- [ ] Sample curation produces expected results
- [ ] Performance metrics are generated
- [ ] Theme classification works correctly
- [ ] Output structure is as expected

## Next Steps

After successful setup:

1. **Run a full curation** of your vault
2. **Review the results** and adjust thresholds if needed
3. **Monitor performance** and optimize configuration
4. **Explore advanced features** like custom themes and processing options
5. **Check the documentation** for additional configuration options

## Support and Resources

- **Documentation**: Check the `docs/` folder for comprehensive guides
- **Performance Reports**: Review generated performance metrics
- **Configuration Examples**: See `config.yaml` for reference
- **Troubleshooting**: Use verbose logging and performance metrics for debugging

The enhanced Obsidian Curator now provides **significantly improved performance and content capture capabilities** through optimized thresholds, multi-model AI architecture, and enhanced processing options.
