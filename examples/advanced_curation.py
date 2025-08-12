#!/usr/bin/env python3
"""Advanced example showing custom configuration and detailed analysis."""

import json
from pathlib import Path
from obsidian_curator import ObsidianCurator, CurationConfig

def analyze_vault_first(vault_path: Path):
    """Analyze vault content before curation."""
    print("🔍 Pre-curation analysis...")
    
    # Basic config for analysis
    config = CurationConfig(sample_size=10)  # Small sample for analysis
    curator = ObsidianCurator(config)
    
    # Discover notes
    notes = curator._discover_notes(vault_path)
    
    if not notes:
        print("❌ No notes found in vault")
        return None
    
    print(f"📊 Found {len(notes)} total notes")
    
    # Analyze content types
    content_types = {}
    for note in notes:
        content_type = note.content_type.value
        content_types[content_type] = content_types.get(content_type, 0) + 1
    
    print("📋 Content type distribution:")
    for content_type, count in sorted(content_types.items()):
        percentage = (count / len(notes)) * 100
        print(f"   • {content_type.replace('_', ' ').title()}: {count} ({percentage:.1f}%)")
    
    return notes

def custom_curation_with_analysis():
    """Run advanced curation with custom settings and detailed analysis."""
    
    # Define paths
    input_vault = Path("/Users/jose/Documents/Obsidian/Evermd")
    output_vault = Path("advanced-curated-vault")
    
    print("🤖 Obsidian Curator - Advanced Example")
    print(f"📁 Input vault: {input_vault}")
    print(f"📁 Output vault: {output_vault}")
    print()
    
    # Pre-analysis
    notes = analyze_vault_first(input_vault)
    if not notes:
        return 1
    
    print()
    
    # Create advanced configuration
    config = CurationConfig(
        ai_model="gpt-oss:20b",
        quality_threshold=0.8,      # Higher quality threshold
        relevance_threshold=0.7,    # Higher relevance threshold
        max_tokens=3000,           # More tokens for analysis
        target_themes=[            # Specific theme focus
            "infrastructure", 
            "construction", 
            "governance",
            "sustainability"
        ],
        sample_size=20,            # Larger sample for testing
        preserve_metadata=True,
        clean_html=True,
        remove_duplicates=True
    )
    
    print("⚙️ Advanced Configuration:")
    print(f"   • Quality threshold: {config.quality_threshold}")
    print(f"   • Relevance threshold: {config.relevance_threshold}")
    print(f"   • Max tokens: {config.max_tokens}")
    print(f"   • Target themes: {', '.join(config.target_themes)}")
    print(f"   • Sample size: {config.sample_size}")
    print()
    
    # Initialize curator
    curator = ObsidianCurator(config)
    
    try:
        # Run curation
        print("🔄 Starting advanced curation process...")
        stats = curator.curate_vault(input_vault, output_vault)
        
        # Detailed results analysis
        print("✅ Advanced curation completed!")
        print()
        
        print("📊 Detailed Results:")
        print(f"   • Total notes processed: {stats.total_notes}")
        print(f"   • Notes curated: {stats.curated_notes}")
        print(f"   • Notes rejected: {stats.rejected_notes}")
        print(f"   • Curation rate: {stats.curation_rate:.1f}%")
        print(f"   • Processing time: {stats.processing_time:.1f} seconds")
        print()
        
        # Theme analysis
        if stats.themes_distribution:
            print("📂 Theme Distribution:")
            total_themed = sum(stats.themes_distribution.values())
            for theme, count in sorted(stats.themes_distribution.items()):
                percentage = (count / total_themed * 100) if total_themed > 0 else 0
                print(f"   • {theme.replace('_', ' ').title()}: {count} notes ({percentage:.1f}%)")
            print()
        
        # Quality analysis
        if stats.quality_distribution:
            print("📈 Quality Score Distribution:")
            for score_range, count in stats.quality_distribution.items():
                print(f"   • {score_range}: {count} notes")
            print()
        
        # Save detailed analysis
        analysis_file = output_vault / "metadata" / "advanced_analysis.json"
        if analysis_file.exists():
            analysis_data = {
                "configuration": config.dict(),
                "statistics": {
                    "total_notes": stats.total_notes,
                    "curated_notes": stats.curated_notes,
                    "rejected_notes": stats.rejected_notes,
                    "curation_rate": stats.curation_rate,
                    "processing_time": stats.processing_time
                },
                "themes_distribution": stats.themes_distribution,
                "quality_distribution": stats.quality_distribution
            }
            
            with open(analysis_file, 'w') as f:
                json.dump(analysis_data, f, indent=2, default=str)
            
            print(f"💾 Detailed analysis saved to: {analysis_file}")
        
        print(f"\n🎉 Advanced curated vault created: {output_vault}")
        print("💡 Recommendations:")
        
        # Provide recommendations based on results
        if stats.curation_rate < 30:
            print("   • Consider lowering quality/relevance thresholds")
        elif stats.curation_rate > 80:
            print("   • Consider raising quality/relevance thresholds for more selectivity")
        
        if stats.themes_distribution.get("unknown", 0) > stats.curated_notes * 0.2:
            print("   • Many notes couldn't be classified - consider expanding theme categories")
        
        print("   • Review the curation log for detailed decision reasoning")
        print("   • Check theme analysis for content organization insights")
        
    except Exception as e:
        print(f"❌ Error during advanced curation: {e}")
        return 1
    
    return 0

def main():
    """Main function."""
    return custom_curation_with_analysis()

if __name__ == "__main__":
    exit(main())