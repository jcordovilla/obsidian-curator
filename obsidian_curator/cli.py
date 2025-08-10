"""Command-line interface for the Obsidian curator system."""

import argparse
import sys
from pathlib import Path
from typing import Optional

from loguru import logger

from .core import ObsidianCurator
from .models import CurationConfig


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration.
    
    Args:
        verbose: Whether to enable verbose logging
    """
    # Remove default handler
    logger.remove()
    
    # Add console handler
    if verbose:
        logger.add(sys.stderr, level="DEBUG", format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")
    else:
        logger.add(sys.stderr, level="INFO", format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")


def create_default_config() -> CurationConfig:
    """Create a default curation configuration.
    
    Returns:
        Default CurationConfig object
    """
    return CurationConfig(
        ai_model="gpt-oss:20b",
        quality_threshold=0.7,
        relevance_threshold=0.6,
        max_tokens=2000,
        target_themes=[
            "infrastructure",
            "construction", 
            "economics",
            "sustainability",
            "governance"
        ],
        preserve_metadata=True,
        clean_html=True
    )


def validate_paths(input_path: Path, output_path: Path) -> None:
    """Validate input and output paths.
    
    Args:
        input_path: Input vault path
        output_path: Output vault path
        
    Raises:
        ValueError: If paths are invalid
    """
    if not input_path.exists():
        raise ValueError(f"Input path does not exist: {input_path}")
    
    if not input_path.is_dir():
        raise ValueError(f"Input path is not a directory: {input_path}")
    
    # Check if input path contains markdown files
    md_files = list(input_path.rglob("*.md"))
    if not md_files:
        raise ValueError(f"No markdown files found in input path: {input_path}")
    
    # Create output directory if it doesn't exist
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Check if output directory is empty or can be written to
    if output_path.exists() and any(output_path.iterdir()):
        logger.warning(f"Output directory is not empty: {output_path}")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            sys.exit(1)


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="AI-powered curation system for Obsidian vaults",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Curate a vault with default settings
  obsidian-curator curate /Users/jose/Documents/Obsidian/Evermd /path/to/output/vault
  
  # Curate with custom quality threshold
  obsidian-curator curate --quality-threshold 0.8 /Users/jose/Documents/Obsidian/Evermd /path/to/output/vault
  
  # Curate with specific target themes
  obsidian-curator curate --target-themes infrastructure,construction /Users/jose/Documents/Obsidian/Evermd /path/to/output/vault
  
  # Test on a random sample of 10 notes
  obsidian-curator curate --sample-size 10 /Users/jose/Documents/Obsidian/Evermd /path/to/output/vault
  
  # Resume interrupted processing
  obsidian-curator curate --resume /Users/jose/Documents/Obsidian/Evermd /path/to/output/vault
  
  # Verbose logging
  obsidian-curator curate --verbose /Users/jose/Documents/Obsidian/Evermd /path/to/output/vault
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Curate command
    curate_parser = subparsers.add_parser('curate', help='Curate an Obsidian vault')
    curate_parser.add_argument('input_path', type=Path, help='Path to input Obsidian vault')
    curate_parser.add_argument('output_path', type=Path, help='Path for curated vault output')
    
    # Configuration options
    curate_parser.add_argument('--ai-model', default='gpt-oss:20b', 
                              help='AI model to use for analysis (default: gpt-oss:20b)')
    curate_parser.add_argument('--quality-threshold', type=float, default=0.7,
                              help='Minimum quality score for curation (default: 0.7)')
    curate_parser.add_argument('--relevance-threshold', type=float, default=0.6,
                              help='Minimum relevance score for curation (default: 0.6)')
    curate_parser.add_argument('--max-tokens', type=int, default=2000,
                              help='Maximum tokens for AI analysis (default: 2000)')
    curate_parser.add_argument('--target-themes', 
                              help='Comma-separated list of target themes')
    curate_parser.add_argument('--sample-size', type=int,
                              help='Process only a random sample of N notes for testing')
    curate_parser.add_argument('--no-preserve-metadata', action='store_true',
                              help='Do not preserve original metadata')
    curate_parser.add_argument('--no-clean-html', action='store_true',
                              help='Do not clean HTML content')
    
    # General options
    curate_parser.add_argument('--verbose', '-v', action='store_true',
                              help='Enable verbose logging')
    curate_parser.add_argument('--dry-run', action='store_true',
                              help='Show what would be done without actually doing it')
    curate_parser.add_argument('--resume', action='store_true',
                              help='Resume processing from last checkpoint if available')
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Setup logging
    setup_logging(args.verbose)
    
    try:
        if args.command == 'curate':
            run_curate(args)
        else:
            logger.error(f"Unknown command: {args.command}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        if args.verbose:
            logger.exception("Full traceback:")
        sys.exit(1)


def run_curate(args: argparse.Namespace) -> None:
    """Run the curation command.
    
    Args:
        args: Parsed command line arguments
    """
    logger.info("Starting Obsidian vault curation")
    
    # Validate paths
    validate_paths(args.input_path, args.output_path)
    
    # Create configuration
    config = CurationConfig(
        ai_model=args.ai_model,
        quality_threshold=args.quality_threshold,
        relevance_threshold=args.relevance_threshold,
        max_tokens=args.max_tokens,
        target_themes=args.target_themes.split(',') if args.target_themes else [],
        sample_size=args.sample_size,
        preserve_metadata=not args.no_preserve_metadata,
        clean_html=not args.no_clean_html
    )
    
    logger.info(f"Configuration: {config.dict()}")
    
    if args.dry_run:
        logger.info("DRY RUN MODE - No actual changes will be made")
        logger.info(f"Would curate vault from {args.input_path} to {args.output_path}")
        logger.info(f"Would use AI model: {config.ai_model}")
        logger.info(f"Quality threshold: {config.quality_threshold}")
        logger.info(f"Relevance threshold: {config.relevance_threshold}")
        if config.sample_size:
            logger.info(f"Sample size: {config.sample_size} notes (random sample)")
        return
    
    # Create curator and run
    curator = ObsidianCurator(config)
    
    try:
        stats = curator.curate_vault(args.input_path, args.output_path)
        
        # Print summary
        logger.info("Curation completed successfully!")
        logger.info(f"Total notes processed: {stats.total_notes}")
        logger.info(f"Notes curated: {stats.curated_notes}")
        logger.info(f"Notes rejected: {stats.rejected_notes}")
        logger.info(f"Curation rate: {stats.curation_rate:.1f}%")
        logger.info(f"Processing time: {stats.processing_time:.1f} seconds")
        
        # Theme distribution
        if stats.themes_distribution:
            logger.info("Theme distribution:")
            for theme, count in sorted(stats.themes_distribution.items(), 
                                      key=lambda x: x[1], reverse=True):
                logger.info(f"  {theme}: {count} notes")
        
        # Quality distribution
        if stats.quality_distribution:
            logger.info("Quality distribution:")
            for range_name, count in stats.quality_distribution.items():
                logger.info(f"  {range_name}: {count} notes")
        
        logger.info(f"Curated vault created at: {args.output_path}")
        
    except Exception as e:
        logger.error(f"Curation failed: {e}")
        raise


if __name__ == '__main__':
    main()
