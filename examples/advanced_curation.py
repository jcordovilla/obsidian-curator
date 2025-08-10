#!/usr/bin/env python3
"""Advanced example of using the Obsidian curator system with all features."""

import json
from pathlib import Path
from obsidian_curator import ObsidianCurator, CurationConfig


def main():
    """Example of advanced vault curation with all features."""
    
    # Advanced configuration
    config = CurationConfig(
        ai_model="gpt-oss:20b",
        quality_threshold=0.8,  # Higher quality threshold
        relevance_threshold=0.7,  # Higher relevance threshold
        max_tokens=3000,  # More tokens for analysis
        target_themes=[
            "infrastructure",
            "construction",
            "economics", 
            "sustainability",
            "governance",
            "public-private-partnerships",
            "risk-management",
            "innovation"
        ],
        sample_size=None,  # Process all notes
        preserve_metadata=True,
        clean_html=True
    )
    
    # Create curator
    curator = ObsidianCurator(config)
    
    # Paths
    input_vault = Path("/Users/jose/Documents/Obsidian/Evermd")  # Your raw Obsidian vault
    output_vault = Path("curated-vault-advanced")  # Output for curated notes
    
    print("🚀 Advanced Obsidian Vault Curation")
    print("=" * 50)
    print(f"Input vault: {input_vault}")
    print(f"Output vault: {output_vault}")
    print(f"AI model: {config.ai_model}")
    print(f"Quality threshold: {config.quality_threshold}")
    print(f"Relevance threshold: {config.relevance_threshold}")
    print(f"Target themes: {', '.join(config.target_themes)}")
    print(f"Sample size: {'All notes' if config.sample_size is None else config.sample_size}")
    print()
    
    try:
        # Run curation with progress bars
        print("Starting curation process...")
        stats = curator.curate_vault(input_vault, output_vault)
        
        # Detailed results
        print("\n🎯 Curation Results")
        print("=" * 50)
        print(f"✅ Total notes processed: {stats.total_notes}")
        print(f"✅ Notes curated: {stats.curated_notes}")
        print(f"❌ Notes rejected: {stats.rejected_notes}")
        print(f"📊 Curation rate: {stats.curation_rate:.1f}%")
        print(f"⏱️  Processing time: {stats.processing_time:.1f} seconds")
        print()
        
        # Theme distribution
        if stats.themes_distribution:
            print("🏷️  Theme Distribution")
            print("-" * 30)
            for theme, count in sorted(stats.themes_distribution.items(), 
                                      key=lambda x: x[1], reverse=True):
                percentage = (count / stats.total_notes) * 100
                print(f"  {theme}: {count} notes ({percentage:.1f}%)")
            print()
        
        # Quality distribution
        if stats.quality_distribution:
            print("📈 Quality Distribution")
            print("-" * 30)
            for range_name, count in sorted(stats.quality_distribution.items()):
                percentage = (count / stats.total_notes) * 100
                print(f"  {range_name}: {count} notes ({percentage:.1f}%)")
            print()
        
        print(f"🎉 Curated vault created at: {output_vault}")
        
        # Export detailed report
        report_path = output_vault / "curation_report.json"
        curator.export_curation_report(stats, report_path)
        print(f"📋 Detailed report exported to: {report_path}")
        
    except Exception as e:
        print(f"❌ Curation failed: {e}")
        raise


if __name__ == "__main__":
    main()
