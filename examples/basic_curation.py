#!/usr/bin/env python3
"""Basic example of using the Obsidian curator system programmatically."""

from pathlib import Path
from obsidian_curator import ObsidianCurator, CurationConfig


def main():
    """Example of basic vault curation."""
    
    # Configuration
    config = CurationConfig(
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
        sample_size=5,  # Process only 5 notes for testing
        preserve_metadata=True,
        clean_html=True
    )
    
    # Create curator
    curator = ObsidianCurator(config)
    
    # Paths
    input_vault = Path("my-writings")  # Your input vault path
    output_vault = Path("curated-vault")  # Your output vault path
    
    print(f"Starting curation of vault: {input_vault}")
    print(f"Output will be saved to: {output_vault}")
    print(f"Using AI model: {config.ai_model}")
    print(f"Quality threshold: {config.quality_threshold}")
    print(f"Relevance threshold: {config.relevance_threshold}")
    print()
    
    try:
        # Run curation
        stats = curator.curate_vault(input_vault, output_vault)
        
        # Print results
        print("Curation completed successfully!")
        print(f"Total notes processed: {stats.total_notes}")
        print(f"Notes curated: {stats.curated_notes}")
        print(f"Notes rejected: {stats.rejected_notes}")
        print(f"Curation rate: {stats.curation_rate:.1f}%")
        print(f"Processing time: {stats.processing_time:.1f} seconds")
        print()
        
        # Theme distribution
        if stats.themes_distribution:
            print("Theme distribution:")
            for theme, count in sorted(stats.themes_distribution.items(), 
                                      key=lambda x: x[1], reverse=True):
                print(f"  {theme}: {count} notes")
            print()
        
        # Quality distribution
        if stats.quality_distribution:
            print("Quality distribution:")
            for range_name, count in stats.quality_distribution.items():
                print(f"  {range_name}: {count} notes")
            print()
        
        print(f"Curated vault created at: {output_vault}")
        
    except Exception as e:
        print(f"Curation failed: {e}")
        raise


if __name__ == "__main__":
    main()
