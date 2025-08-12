#!/usr/bin/env python3
"""Basic example of using Obsidian Curator programmatically."""

from pathlib import Path
from obsidian_curator import ObsidianCurator, CurationConfig

def main():
    """Run basic curation example."""
    
    # Define paths
    input_vault = Path("my-writings")  # Example input vault
    output_vault = Path("curated-vault")  # Output location
    
    # Create configuration
    config = CurationConfig(
        ai_model="gpt-oss:20b",
        quality_threshold=0.7,
        relevance_threshold=0.6,
        target_themes=["infrastructure", "construction", "economics"],
        sample_size=5  # Process only 5 notes for this example
    )
    
    print("🤖 Obsidian Curator - Basic Example")
    print(f"📁 Input vault: {input_vault}")
    print(f"📁 Output vault: {output_vault}")
    print(f"🎯 Target themes: {', '.join(config.target_themes)}")
    print(f"📊 Sample size: {config.sample_size}")
    print()
    
    # Initialize curator
    curator = ObsidianCurator(config)
    
    try:
        # Run curation
        print("🔄 Starting curation process...")
        stats = curator.curate_vault(input_vault, output_vault)
        
        # Display results
        print("✅ Curation completed!")
        print(f"📊 Results:")
        print(f"   • Total notes: {stats.total_notes}")
        print(f"   • Curated: {stats.curated_notes} ({stats.curation_rate:.1f}%)")
        print(f"   • Rejected: {stats.rejected_notes}")
        print(f"   • Processing time: {stats.processing_time:.1f}s")
        
        if stats.themes_distribution:
            print(f"📂 Theme distribution:")
            for theme, count in stats.themes_distribution.items():
                print(f"   • {theme.replace('_', ' ').title()}: {count}")
        
        print(f"\n🎉 Curated vault saved to: {output_vault}")
        print("💡 Check the metadata folder for detailed logs and analysis")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())