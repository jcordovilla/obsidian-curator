"""Obsidian Curator - AI-powered curation system for Obsidian vaults."""

__version__ = "0.1.0"
__author__ = "Jose Cordovilla"
__email__ = "jose@example.com"

from .core import ObsidianCurator
from .models import Note, CurationResult, Theme, CurationConfig
from .ai_analyzer import AIAnalyzer
from .content_processor import ContentProcessor
from .theme_classifier import ThemeClassifier
from .vault_organizer import VaultOrganizer

__all__ = [
    "ObsidianCurator",
    "Note",
    "CurationResult", 
    "Theme",
    "CurationConfig",
    "AIAnalyzer",
    "ContentProcessor",
    "ThemeClassifier",
    "VaultOrganizer",
]
