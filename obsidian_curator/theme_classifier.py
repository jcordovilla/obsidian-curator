"""Theme classification and organization for curated content."""

import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from loguru import logger

from .models import Theme, CurationResult, VaultStructure


class ThemeClassifier:
    """Classifies and organizes content by themes."""
    
    def __init__(self):
        """Initialize the theme classifier."""
        # Predefined theme hierarchy for infrastructure and construction
        self.theme_hierarchy = {
            "infrastructure": {
                "ppps": ["public-private partnerships", "ppp", "public private partnerships"],
                "resilience": ["resilience", "climate adaptation", "disaster recovery", "sustainability"],
                "financing": ["financing", "funding", "investment", "economic analysis"],
                "governance": ["governance", "regulation", "policy", "legal framework"],
                "technology": ["technology", "innovation", "digital transformation", "smart infrastructure"]
            },
            "construction": {
                "projects": ["project management", "construction projects", "infrastructure projects"],
                "best_practices": ["best practices", "standards", "guidelines", "methodologies"],
                "materials": ["materials", "construction materials", "sustainability"],
                "safety": ["safety", "risk management", "health and safety"]
            },
            "economics": {
                "development": ["economic development", "regional development", "urban planning"],
                "investment": ["investment analysis", "cost-benefit analysis", "financial modeling"],
                "markets": ["market analysis", "industry trends", "economic indicators"]
            },
            "sustainability": {
                "environmental": ["environmental impact", "climate change", "green infrastructure"],
                "social": ["social impact", "community development", "stakeholder engagement"],
                "economic": ["economic sustainability", "long-term value", "resource efficiency"]
            },
            "governance": {
                "policy": ["public policy", "regulatory framework", "legislation"],
                "institutions": ["government institutions", "regulatory bodies", "public administration"],
                "transparency": ["transparency", "accountability", "public participation"]
            }
        }
        
        # Theme aliases for better matching
        self.theme_aliases = {
            "ppp": "public-private partnerships",
            "public private partnerships": "public-private partnerships",
            "climate adaptation": "resilience",
            "disaster recovery": "resilience",
            "economic development": "development",
            "urban planning": "development",
            "investment analysis": "investment",
            "cost-benefit analysis": "investment",
            "environmental impact": "environmental",
            "climate change": "environmental",
            "green infrastructure": "environmental",
            "social impact": "social",
            "community development": "social",
            "public policy": "policy",
            "regulatory framework": "policy",
            "government institutions": "institutions",
            "regulatory bodies": "institutions"
        }
    
    def classify_themes(self, curation_results: List[CurationResult]) -> Dict[str, List[CurationResult]]:
        """Classify curation results by primary themes.
        
        Args:
            curation_results: List of curation results to classify
            
        Returns:
            Dictionary mapping theme names to lists of curation results
        """
        theme_groups = defaultdict(list)
        
        for result in curation_results:
            if not result.themes:
                # Assign to unknown theme if no themes identified
                theme_groups["unknown"].append(result)
                continue
            
            # Get primary theme
            primary_theme = result.primary_theme
            if primary_theme:
                # Map to our theme hierarchy
                mapped_theme = self._map_to_hierarchy(primary_theme.name)
                theme_groups[mapped_theme].append(result)
            else:
                theme_groups["unknown"].append(result)
        
        return dict(theme_groups)
    
    def _map_to_hierarchy(self, theme_name: str) -> str:
        """Map a theme name to our predefined hierarchy.
        
        Args:
            theme_name: Theme name to map
            
        Returns:
            Mapped theme name from hierarchy
        """
        theme_lower = theme_name.lower()
        
        # Check aliases first
        if theme_lower in self.theme_aliases:
            theme_lower = self.theme_aliases[theme_lower]
        
        # Search through hierarchy
        for main_theme, subthemes in self.theme_hierarchy.items():
            # Check main theme
            if theme_lower in main_theme or main_theme in theme_lower:
                return main_theme
            
            # Check subthemes
            for subtheme, keywords in subthemes.items():
                if (theme_lower in subtheme or subtheme in theme_lower or
                    any(keyword in theme_lower for keyword in keywords)):
                    return f"{main_theme}/{subtheme}"
        
        # If no match found, try fuzzy matching
        return self._fuzzy_theme_match(theme_lower)
    
    def _fuzzy_theme_match(self, theme_name: str) -> str:
        """Perform fuzzy matching for theme names.
        
        Args:
            theme_name: Theme name to match
            
        Returns:
            Best matching theme from hierarchy
        """
        best_match = "unknown"
        best_score = 0
        
        for main_theme, subthemes in self.theme_hierarchy.items():
            # Check main theme similarity
            main_score = self._calculate_similarity(theme_name, main_theme)
            if main_score > best_score:
                best_score = main_score
                best_match = main_theme
            
            # Check subtheme similarity
            for subtheme, keywords in subthemes.items():
                sub_score = self._calculate_similarity(theme_name, subtheme)
                if sub_score > best_score:
                    best_score = sub_score
                    best_match = f"{main_theme}/{subtheme}"
                
                # Check keywords
                for keyword in keywords:
                    keyword_score = self._calculate_similarity(theme_name, keyword)
                    if keyword_score > best_score:
                        best_score = keyword_score
                        best_match = f"{main_theme}/{subtheme}"
        
        # Only return match if similarity is above threshold
        if best_score > 0.3:
            return best_match
        
        return "unknown"
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings.
        
        Args:
            str1: First string
            str2: Second string
            
        Returns:
            Similarity score between 0 and 1
        """
        # Simple Jaccard similarity for word overlap
        words1 = set(str1.split())
        words2 = set(str2.split())
        
        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union
    
    def create_vault_structure(self, output_path: Path, theme_groups: Dict[str, List[CurationResult]]) -> VaultStructure:
        """Create the folder structure for the curated vault.
        
        Args:
            output_path: Root path for the curated vault
            theme_groups: Theme groups with curation results
            
        Returns:
            VaultStructure object describing the organization
        """
        # Create root directory
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Create theme folders
        theme_folders = {}
        for theme_name in theme_groups.keys():
            if theme_name == "unknown":
                continue
            
            # Create nested folder structure for themes with subthemes
            if "/" in theme_name:
                main_theme, subtheme = theme_name.split("/", 1)
                theme_path = output_path / main_theme / subtheme
            else:
                theme_path = output_path / theme_name
            
            theme_path.mkdir(parents=True, exist_ok=True)
            theme_folders[theme_name] = theme_path
        
        # Create metadata folder
        metadata_folder = output_path / "metadata"
        metadata_folder.mkdir(exist_ok=True)
        
        # Create curation log and theme analysis paths
        curation_log_path = metadata_folder / "curation-log.md"
        theme_analysis_path = metadata_folder / "theme-analysis.md"
        
        return VaultStructure(
            root_path=output_path,
            theme_folders=theme_folders,
            metadata_folder=metadata_folder,
            curation_log_path=curation_log_path,
            theme_analysis_path=theme_analysis_path
        )
    
    def generate_theme_analysis(self, theme_groups: Dict[str, List[CurationResult]], vault_structure: VaultStructure) -> str:
        """Generate theme analysis report.
        
        Args:
            theme_groups: Theme groups with curation results
            vault_structure: Vault structure information
            
        Returns:
            Markdown content for theme analysis
        """
        analysis = "# Theme Analysis Report\n\n"
        analysis += f"Generated on: {vault_structure.root_path}\n\n"
        
        # Summary statistics
        total_notes = sum(len(results) for results in theme_groups.values())
        analysis += f"## Summary\n\n"
        analysis += f"- **Total Notes Processed**: {total_notes}\n"
        analysis += f"- **Themes Identified**: {len(theme_groups)}\n"
        analysis += f"- **Notes Curated**: {sum(len(results) for results in theme_groups.values() if results)}\n\n"
        
        # Theme breakdown
        analysis += "## Theme Breakdown\n\n"
        
        for theme_name, results in sorted(theme_groups.items()):
            if not results:
                continue
                
            analysis += f"### {theme_name.replace('_', ' ').title()}\n\n"
            analysis += f"- **Notes**: {len(results)}\n"
            analysis += f"- **Percentage**: {(len(results) / total_notes * 100):.1f}%\n"
            
            # Quality statistics
            if results:
                avg_quality = sum(r.quality_scores.overall for r in results) / len(results)
                avg_relevance = sum(r.quality_scores.relevance for r in results) / len(results)
                analysis += f"- **Average Quality**: {avg_quality:.2f}\n"
                analysis += f"- **Average Relevance**: {avg_relevance:.2f}\n"
            
            analysis += "\n"
            
            # Sample titles
            sample_titles = [r.note.title for r in results[:5]]
            analysis += f"**Sample Titles**:\n"
            for title in sample_titles:
                analysis += f"- {title}\n"
            analysis += "\n"
        
        return analysis
    
    def suggest_theme_improvements(self, theme_groups: Dict[str, List[CurationResult]]) -> List[str]:
        """Suggest improvements for theme classification.
        
        Args:
            theme_groups: Theme groups with curation results
            
        Returns:
            List of improvement suggestions
        """
        suggestions = []
        
        # Check for large "unknown" groups
        if "unknown" in theme_groups and len(theme_groups["unknown"]) > 0:
            unknown_count = len(theme_groups["unknown"])
            total_count = sum(len(results) for results in theme_groups.values())
            unknown_percentage = (unknown_count / total_count) * 100
            
            if unknown_percentage > 20:
                suggestions.append(
                    f"High percentage of unknown themes ({unknown_percentage:.1f}%). "
                    "Consider adding more theme categories or improving AI theme detection."
                )
        
        # Check for theme balance
        theme_counts = {name: len(results) for name, results in theme_groups.items()}
        if theme_counts:
            max_count = max(theme_counts.values())
            min_count = min(theme_counts.values())
            
            if max_count > 0 and min_count > 0:
                ratio = max_count / min_count
                if ratio > 10:
                    suggestions.append(
                        f"Unbalanced theme distribution (ratio {ratio:.1f}:1). "
                        "Consider adjusting theme thresholds or adding subthemes."
                    )
        
        # Check for potential theme merges
        potential_merges = self._identify_potential_merges(theme_groups)
        if potential_merges:
            suggestions.append(
                f"Consider merging related themes: {', '.join(potential_merges)}"
            )
        
        return suggestions
    
    def _identify_potential_merges(self, theme_groups: Dict[str, List[CurationResult]]) -> List[str]:
        """Identify themes that could potentially be merged.
        
        Args:
            theme_groups: Theme groups with curation results
            
        Returns:
            List of potential merge suggestions
        """
        merges = []
        
        # Look for themes with very few notes that might be related
        small_themes = {name: results for name, results in theme_groups.items() 
                       if len(results) < 3 and name != "unknown"}
        
        for theme1 in small_themes:
            for theme2 in small_themes:
                if theme1 != theme2:
                    # Check if themes are semantically related
                    if self._are_themes_related(theme1, theme2):
                        merges.append(f"{theme1} + {theme2}")
        
        return list(set(merges))
    
    def _are_themes_related(self, theme1: str, theme2: str) -> bool:
        """Check if two themes are semantically related.
        
        Args:
            theme1: First theme name
            theme2: Second theme name
            
        Returns:
            True if themes are related
        """
        # Simple keyword-based relatedness check
        theme1_words = set(theme1.lower().replace('_', ' ').split())
        theme2_words = set(theme2.lower().replace('_', ' ').split())
        
        # Check for word overlap
        overlap = len(theme1_words.intersection(theme2_words))
        total = len(theme1_words.union(theme2_words))
        
        if total > 0:
            similarity = overlap / total
            return similarity > 0.3
        
        return False
