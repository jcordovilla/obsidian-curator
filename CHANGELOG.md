# Changelog

All notable changes to Obsidian Curator will be documented in this file.

## [1.1.0] - 2024-08-24

### Fixed
- **Critical Bug Fix**: Resolved systematic 0.30 scoring bias in AI analysis
- **JSON Parsing Issue**: Fixed corrupted field names in Ollama responses that were causing all notes to receive identical low scores
- **AI Response Handling**: Enhanced JSON extraction and malformation repair for reliable Ollama responses
- **Quality Scoring**: Restored proper quality score distribution across 0.6-0.8 range instead of fixed 0.30

### Changed
- **Configuration**: Updated config.yaml to use proper optimized thresholds (0.65) instead of temporary lowered ones (0.25)
- **Documentation**: Updated README.md with testing validation results and bug fix information
- **Thresholds**: Restored quality_threshold and relevance_threshold to 0.65 for optimal content capture

### Added
- **Testing Validation**: Comprehensive 20-note test demonstrating 94.4% curation rate with zero false positives
- **Quality Metrics**: Documented processing time, curation rate, and quality distribution improvements
- **Bug Fix Documentation**: Added troubleshooting information for the 0.30 scoring issue

### Technical Details
- **File Modified**: `obsidian_curator/ai_analyzer.py`
  - Fixed `_fix_malformed_json` function to preserve field names
  - Removed regex that was stripping letters from JSON field names
  - Added debug logging for AI response troubleshooting
- **File Modified**: `config.yaml`
  - Restored proper thresholds: quality=0.65, relevance=0.65
  - Cleaned up configuration structure
- **File Modified**: `README.md`
  - Added Critical Bug Fixes section
  - Added Testing and Validation section with comprehensive results
  - Updated configuration examples

## [1.0.0] - 2024-08-23

### Added
- Initial release of Obsidian Curator
- AI-powered note curation using Ollama
- Multi-model architecture for specialized tasks
- Theme classification and vault organization
- Command-line and GUI interfaces
- Comprehensive documentation

### Features
- Quality analysis across 10 dimensions
- Professional writing assessment
- Enhanced content processing
- Performance optimization
- Flexible configuration system
