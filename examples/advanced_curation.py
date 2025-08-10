#!/usr/bin/env python3
"""Advanced example of using the Obsidian curator system with custom configuration."""

from pathlib import Path
from obsidian_curator import ObsidianCurator, CurationConfig, ThemeClassifier, VaultOrganizer


def main():
    """Example of advanced vault curation with custom configuration."""
    
    # Custom configuration for infrastructure-focused curation
    config = CurationConfig(
        ai_model="gpt-oss:20b",
        quality_threshold=0.8,  # Higher quality threshold
        relevance_threshold=0.7,  # Higher relevance threshold
        max_tokens=3000,  # More tokens for detailed analysis
        target_themes=[
            "infrastructure/ppps",
            "infrastructure/financing",
            "infrastructure/governance",
            "construction/projects",
            "economics/investment"
        ],
        preserve_metadata=True,
        clean_html=True
    )
    
    print("=== Advanced Obsidian Curation Example ===")
    print(f"Configuration: {config.dict()}")
    print()
    
    # Create curator
    curator = ObsidianCurator(config)
    
    # Paths
    input_vault = Path("my-writings")
    output_vault = Path("curated-infrastructure-vault")
    
    print(f"Input vault: {input_vault}")
    print(f"Output vault: {output_vault}")
    print()
    
    try:
        # Step 1: Discover and process notes
        print("Step 1: Discovering notes...")
        notes = curator._discover_notes(input_vault)
        print(f"Found {len(notes)} notes to process")
        
        # Step 2: Process and clean content
        print("Step 2: Processing notes...")
        processed_notes = curator._process_notes(notes)
        print(f"Successfully processed {len(processed_notes)} notes")
        
        # Step 3: AI analysis and curation
        print("Step 3: AI analysis and curation...")
        curation_results = curator._curate_notes(processed_notes)
        
        # Analyze results before organization
        curated_count = sum(1 for r in curation_results if r.is_curated)
        rejected_count = len(curation_results) - curated_count
        
        print(f"AI analysis completed:")
        print(f"  - Curated: {curated_count}")
        print(f"  - Rejected: {rejected_count}")
        print(f"  - Curation rate: {(curated_count/len(curation_results)*100):.1f}%")
        print()
        
        # Step 4: Create vault structure
        print("Step 4: Creating vault structure...")
        vault_structure = curator._create_vault_structure(output_vault, curation_results)
        print(f"Vault structure created at: {vault_structure.root_path}")
        
        # Step 5: Organize and save curated content
        print("Step 5: Organizing and saving content...")
        stats = curator.vault_organizer.create_curated_vault(
            curation_results, output_vault, vault_structure
        )
        
        print("=== Curation Results ===")
        print(f"Total notes processed: {stats.total_notes}")
        print(f"Notes curated: {stats.curated_notes}")
        print(f"Notes rejected: {stats.rejected_notes}")
        print(f"Curation rate: {stats.curation_rate:.1f}%")
        print(f"Processing time: {stats.processing_time:.1f} seconds")
        print()
        
        # Detailed theme analysis
        print("=== Theme Analysis ===")
        theme_classifier = ThemeClassifier()
        theme_groups = theme_classifier.classify_themes(curation_results)
        
        for theme_name, results in sorted(theme_groups.items(), 
                                         key=lambda x: len(x[1]), reverse=True):
            if results:
                curated_in_theme = sum(1 for r in results if r.is_curated)
                avg_quality = sum(r.quality_scores.overall for r in results) / len(results)
                print(f"{theme_name}:")
                print(f"  - Total notes: {len(results)}")
                print(f"  - Curated: {curated_in_theme}")
                print(f"  - Average quality: {avg_quality:.2f}")
                print()
        
        # Quality distribution analysis
        print("=== Quality Distribution ===")
        quality_ranges = {"0.0-0.2": 0, "0.2-0.4": 0, "0.4-0.6": 0, "0.6-0.8": 0, "0.8-1.0": 0}
        for result in curation_results:
            score = result.quality_scores.overall
            if score < 0.2:
                quality_ranges["0.0-0.2"] += 1
            elif score < 0.4:
                quality_ranges["0.2-0.4"] += 1
            elif score < 0.6:
                quality_ranges["0.4-0.6"] += 1
            elif score < 0.8:
                quality_ranges["0.6-0.8"] += 1
            else:
                quality_ranges["0.8-1.0"] += 1
        
        for range_name, count in quality_ranges.items():
            if count > 0:
                percentage = (count / len(curation_results)) * 100
                print(f"{range_name}: {count} notes ({percentage:.1f}%)")
        
        print()
        
        # Generate and save detailed report
        print("Step 6: Generating detailed report...")
        report_path = output_vault / "curation-report.md"
        curator.export_curation_report(curation_results, report_path)
        print(f"Detailed report saved to: {report_path}")
        
        # Theme improvement suggestions
        print("Step 7: Analyzing theme improvements...")
        suggestions = theme_classifier.suggest_theme_improvements(theme_groups)
        if suggestions:
            print("Theme improvement suggestions:")
            for suggestion in suggestions:
                print(f"  - {suggestion}")
        else:
            print("No theme improvements suggested")
        
        print()
        print("=== Curation Complete ===")
        print(f"Curated vault created at: {output_vault}")
        print("The vault contains:")
        print(f"  - Curated notes organized by themes")
        print(f"  - Metadata and statistics")
        print(f"  - Curation log and analysis")
        print(f"  - Detailed curation report")
        
    except Exception as e:
        print(f"Curation failed: {e}")
        raise


if __name__ == "__main__":
    main()
