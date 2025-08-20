#!/usr/bin/env python3
"""
PyQt6 GUI for Obsidian Curator
Simple interface for vault curation with real-time progress and results.
"""

import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
import json
from datetime import datetime
import threading
import time

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QGridLayout, QLabel, QLineEdit, QPushButton, QRadioButton, 
    QSpinBox, QProgressBar, QTabWidget, QTextEdit, QListWidget, 
    QListWidgetItem, QSplitter, QFileDialog, QMessageBox, QFrame,
    QButtonGroup, QGroupBox
)
from PyQt6.QtCore import QTimer, QThread, pyqtSignal, Qt, QSize
from PyQt6.QtGui import QFont, QPalette, QColor

from .core import ObsidianCurator
from .models import CurationConfig, CurationStats, CurationResult


class CurationWorker(QThread):
    """Worker thread for running curation process."""
    
    # Signals for communication with main thread
    progress_updated = pyqtSignal(int, int, str)  # current, total, current_note
    stats_updated = pyqtSignal(dict)  # stats dictionary
    theme_updated = pyqtSignal(str, int)  # theme_name, count
    note_curated = pyqtSignal(dict)  # note data
    finished = pyqtSignal(dict)  # final stats
    error_occurred = pyqtSignal(str)  # error message
    
    def __init__(self, input_path: Path, output_path: Path, 
                 config: CurationConfig, parent=None):
        super().__init__(parent)
        self.input_path = input_path
        self.output_path = output_path
        self.config = config
        self.curator = None
        self._stop_requested = False
        self.current_stats = {
            'total_notes': 0,
            'curated_notes': 0,
            'rejected_notes': 0,
            'themes_distribution': {},
            'curated_notes_list': []
        }
    
    def run(self):
        """Run the curation process with real-time progress updates."""
        try:
            start_time = time.time()
            
            # Step 1: Discover notes
            self.progress_updated.emit(0, 100, "Discovering notes...")
            notes = self._discover_notes_with_progress()
            
            if not notes:
                self.error_occurred.emit("No notes found in input vault")
                return
            
            self.current_stats['total_notes'] = len(notes)
            self.stats_updated.emit(self.current_stats.copy())
            
            # Notes are already sampled during discovery, just update progress
            self.progress_updated.emit(20, 100, f"Ready to process {len(notes)} notes")
            
            # Debug: Show which notes were selected
            if self.config.sample_size:
                note_names = [note.title[:50] for note in notes]
                print(f"Selected {len(notes)} notes: {note_names}")  # Debug output
            
            # Step 2: Process and analyze notes
            self._process_and_analyze_notes(notes)
            
            if self._stop_requested:
                return
            
            # Step 3: Create curated vault
            self.progress_updated.emit(95, 100, "Creating curated vault...")
            final_stats = self._create_curated_vault()
            
            # Update final timing
            final_stats['processing_time'] = time.time() - start_time
            
            self.finished.emit(final_stats)
            
        except Exception as e:
            self.error_occurred.emit(str(e))
    
    def _discover_notes_with_progress(self):
        """Discover notes with progress updates."""
        from .content_processor import ContentProcessor
        
        # Create processor with optimized settings for GUI
        processor = ContentProcessor(
            clean_html=self.config.clean_html,
            preserve_metadata=self.config.preserve_metadata,
            intelligent_extraction=True,  # Always enabled - content extraction is core functionality
            ai_model=self.config.ai_model
        )
        
        # Override content extractor settings for faster processing in GUI
        if hasattr(processor, 'content_extractor') and processor.content_extractor:
            processor.content_extractor.request_timeout = 3  # Faster timeout
            processor.content_extractor.max_urls_per_note = 1  # Limit URLs for faster processing
            processor.content_extractor.max_pdf_pages = 20  # Limit PDF pages for faster processing
        
        # Find all markdown files
        markdown_files = []
        for pattern in ['*.md', '*.markdown']:
            markdown_files.extend(self.input_path.rglob(pattern))
        
        # Filter out system files
        excluded_patterns = ['.obsidian', '.trash', 'templates', 'template', '.git']
        valid_files = []
        
        for file_path in markdown_files:
            # Skip hidden files and system directories
            if any(part.startswith('.') for part in file_path.parts):
                continue
            
            # Skip excluded patterns
            if any(excluded in str(file_path).lower() for excluded in excluded_patterns):
                continue
            
            # Skip empty files
            try:
                if file_path.stat().st_size == 0:
                    continue
            except OSError:
                continue
            
            valid_files.append(file_path)
        
        # For sample runs, randomly shuffle files BEFORE processing
        if self.config.sample_size:
            import random
            random.shuffle(valid_files)
            # Only process the files we need for the sample
            valid_files = valid_files[:self.config.sample_size * 2]  # Get more than needed in case some fail
        else:
            # Sort by modification time (newest first) for full runs
            valid_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        
        # Load notes with progress
        notes = []
        total_files = len(valid_files)
        
        for i, file_path in enumerate(valid_files):
            if self._stop_requested:
                break
                
            # If we have enough notes for sample, stop early
            if self.config.sample_size and len(notes) >= self.config.sample_size:
                break
                
            try:
                note = processor.process_note(file_path)
                notes.append(note)
                
                # Update progress
                progress = max(1, int((i + 1) / total_files * 20))  # 20% for discovery, minimum 1%
                self.progress_updated.emit(progress, 100, f"Loading ({len(notes)}): {file_path.name}")
                
            except Exception as e:
                continue
        
        return notes
    
    def _process_and_analyze_notes(self, notes):
        """Process and analyze notes with progress updates."""
        from .ai_analyzer import AIAnalyzer
        from .models import QualityScore, ContentStructure
        
        ai_analyzer = AIAnalyzer(self.config)
        
        for i, note in enumerate(notes):
            if self._stop_requested:
                break
            
            try:
                # Update progress at start
                base_progress = 20 + int((i / len(notes)) * 70)  # 70% for analysis
                self.progress_updated.emit(base_progress, 100, f"Processing content ({i+1}/{len(notes)}): {note.title[:50]}...")
                
                # Perform AI analysis
                quality_scores, themes, content_structure, curation_reason = ai_analyzer.analyze_note(note)
                
                # Update progress after AI analysis
                final_progress = 20 + int(((i + 1) / len(notes)) * 70)  # Update after completion
                self.progress_updated.emit(final_progress, 100, f"Completed ({i+1}/{len(notes)}): {note.title[:50]}...")
                
                # Determine if note should be curated
                is_curated = self._should_curate(quality_scores, themes)
                
                if is_curated:
                    self.current_stats['curated_notes'] += 1
                    
                    # Create note data for preview
                    note_data = {
                        'title': note.title,
                        'theme': themes[0].name if themes else 'Unknown',
                        'quality_score': quality_scores.overall,
                        'professional_score': quality_scores.professional_writing_score,
                        'content_preview': note.content[:200] + '...' if len(note.content) > 200 else note.content,
                        'full_note': note,
                        'quality_scores': quality_scores,
                        'themes': themes,
                        'content_structure': content_structure
                    }
                    
                    self.current_stats['curated_notes_list'].append(note_data)
                    self.note_curated.emit(note_data)
                    
                    # Update theme distribution
                    for theme in themes:
                        theme_name = theme.name
                        self.current_stats['themes_distribution'][theme_name] = \
                            self.current_stats['themes_distribution'].get(theme_name, 0) + 1
                        self.theme_updated.emit(theme_name, self.current_stats['themes_distribution'][theme_name])
                else:
                    self.current_stats['rejected_notes'] += 1
                
                # Update stats
                self.stats_updated.emit(self.current_stats.copy())
                
            except Exception as e:
                self.current_stats['rejected_notes'] += 1
                self.stats_updated.emit(self.current_stats.copy())
                continue
    
    def _should_curate(self, quality_scores, themes) -> bool:
        """Determine if a note should be curated."""
        # Check quality and relevance thresholds
        if (quality_scores.overall >= self.config.quality_threshold and 
            quality_scores.relevance >= self.config.relevance_threshold):
            
            # If target themes specified, check theme alignment
            if self.config.target_themes:
                theme_names = [theme.name.lower() for theme in themes]
                theme_alignment = any(
                    target.lower() in theme_name or theme_name in target.lower()
                    for target in self.config.target_themes
                    for theme_name in theme_names
                )
                return theme_alignment
            
            return True
        
        return False
    
    def _create_curated_vault(self):
        """Create the curated vault and return final stats."""
        from .theme_classifier import ThemeClassifier
        from .vault_organizer import VaultOrganizer
        from .models import CurationResult
        
        # Create curation results from our processed data
        curation_results = []
        
        for note_data in self.current_stats['curated_notes_list']:
            result = CurationResult(
                note=note_data['full_note'],
                cleaned_content=note_data['full_note'].content,
                quality_scores=note_data['quality_scores'],
                themes=note_data['themes'],
                content_structure=note_data['content_structure'],
                is_curated=True,
                curation_reason="Passed quality and relevance thresholds",
                processing_notes=[]
            )
            curation_results.append(result)
        
        if curation_results:
            # Create theme groups and vault structure
            theme_classifier = ThemeClassifier()
            theme_groups = theme_classifier.classify_themes(curation_results)
            vault_structure = theme_classifier.create_vault_structure(self.output_path, theme_groups)
            
            # Create curated vault
            vault_organizer = VaultOrganizer(self.config)
            stats = vault_organizer.create_curated_vault(
                curation_results, self.output_path, vault_structure
            )
        else:
            from .models import CurationStats
            stats = CurationStats(
                total_notes=self.current_stats['total_notes'],
                curated_notes=0,
                rejected_notes=self.current_stats['rejected_notes'],
                processing_time=0.0,
                themes_distribution={},
                quality_distribution={}
            )
        
        # Convert to dict for signal
        return {
            'total_notes': stats.total_notes,
            'curated_notes': stats.curated_notes,
            'rejected_notes': stats.rejected_notes,
            'processing_time': 0.0,  # Will be updated by caller
            'curation_rate': stats.curation_rate,
            'themes_distribution': stats.themes_distribution,
            'quality_distribution': stats.quality_distribution
        }
    
    def stop(self):
        """Request to stop the curation process."""
        self._stop_requested = True
        self.terminate()


class ObsidianCuratorGUI(QMainWindow):
    """Main GUI window for Obsidian Curator."""
    
    def __init__(self):
        super().__init__()
        self.worker = None
        self.start_time = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time_display)
        
        # Stats tracking
        self.current_stats = {
            'total_notes': 0,
            'curated_notes': 0,
            'rejected_notes': 0,
            'processing_time': 0,
            'themes_distribution': {},
            'curated_notes_list': []
        }
        
        self.setup_ui()
        self.setup_connections()
        
    def setup_ui(self):
        """Set up the user interface."""
        self.setWindowTitle("Obsidian Curator - Professional Writing Assistant")
        self.setFixedSize(900, 700)
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Create sections
        self.create_path_selection_section(layout)
        self.create_run_options_section(layout)
        self.create_progress_section(layout)
        self.create_stats_section(layout)
        self.create_results_section(layout)
        
    def create_path_selection_section(self, parent_layout):
        """Create the path selection section."""
        group = QGroupBox("Vault Configuration")
        layout = QGridLayout(group)
        
        # Source vault path
        layout.addWidget(QLabel("Source Vault:"), 0, 0)
        self.source_path_edit = QLineEdit("/Users/jose/Documents/Obsidian/Evermd")
        self.source_path_edit.setMinimumWidth(400)
        layout.addWidget(self.source_path_edit, 0, 1)
        
        self.source_browse_btn = QPushButton("Browse")
        self.source_browse_btn.setMaximumWidth(80)
        layout.addWidget(self.source_browse_btn, 0, 2)
        
        # Output folder path
        layout.addWidget(QLabel("Output Folder:"), 1, 0)
        self.output_path_edit = QLineEdit()
        layout.addWidget(self.output_path_edit, 1, 1)
        
        self.output_browse_btn = QPushButton("Browse")
        self.output_browse_btn.setMaximumWidth(80)
        layout.addWidget(self.output_browse_btn, 1, 2)
        
        parent_layout.addWidget(group)
    
    def create_run_options_section(self, parent_layout):
        """Create the run options section."""
        group = QGroupBox("Run Configuration")
        layout = QHBoxLayout(group)
        
        # Run type selection
        self.run_type_group = QButtonGroup()
        
        self.full_run_radio = QRadioButton("Full Run (process all notes)")
        self.full_run_radio.setChecked(True)
        self.run_type_group.addButton(self.full_run_radio, 0)
        layout.addWidget(self.full_run_radio)
        
        # Test run with sample size
        test_layout = QHBoxLayout()
        self.test_run_radio = QRadioButton("Test Run - Sample size:")
        self.run_type_group.addButton(self.test_run_radio, 1)
        test_layout.addWidget(self.test_run_radio)
        
        self.sample_size_spin = QSpinBox()
        self.sample_size_spin.setRange(1, 1000)
        self.sample_size_spin.setValue(10)
        self.sample_size_spin.setMaximumWidth(80)
        test_layout.addWidget(self.sample_size_spin)
        test_layout.addWidget(QLabel("notes"))
        
        layout.addLayout(test_layout)
        layout.addStretch()
        
        # Action buttons
        self.start_btn = QPushButton("🚀 Start Curation")
        self.start_btn.setMinimumHeight(40)
        self.start_btn.setMinimumWidth(150)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
                color: #666666;
            }
        """)
        layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹️ Stop")
        self.stop_btn.setMinimumHeight(40)
        self.stop_btn.setMinimumWidth(100)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #F44336;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #D32F2F;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
                color: #666666;
            }
        """)
        layout.addWidget(self.stop_btn)
        
        parent_layout.addWidget(group)
    
    def create_progress_section(self, parent_layout):
        """Create the progress monitoring section."""
        group = QGroupBox("Progress")
        layout = QVBoxLayout(group)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimumHeight(25)
        layout.addWidget(self.progress_bar)
        
        # Progress label
        self.progress_label = QLabel("Ready to start curation...")
        layout.addWidget(self.progress_label)
        
        # Current operation label
        self.current_operation_label = QLabel("")
        self.current_operation_label.setStyleSheet("color: #666666; font-style: italic;")
        layout.addWidget(self.current_operation_label)
        
        parent_layout.addWidget(group)
    
    def create_stats_section(self, parent_layout):
        """Create the statistics display section."""
        group = QGroupBox("Curation Statistics")
        layout = QHBoxLayout(group)
        
        # Stats labels
        self.total_notes_label = QLabel("Total Notes: 0")
        self.curated_notes_label = QLabel("Curated: 0 (0%)")
        self.rejected_notes_label = QLabel("Rejected: 0 (0%)")
        self.time_label = QLabel("Time: 00:00")
        
        # Style the labels
        for label in [self.total_notes_label, self.curated_notes_label, 
                     self.rejected_notes_label, self.time_label]:
            label.setMinimumWidth(150)
            label.setStyleSheet("""
                QLabel {
                    font-weight: bold;
                    padding: 5px;
                    border: 1px solid #CCCCCC;
                    border-radius: 3px;
                    background-color: #F5F5F5;
                    color: #333333;
                }
            """)
        
        layout.addWidget(self.total_notes_label)
        layout.addWidget(self.curated_notes_label)
        layout.addWidget(self.rejected_notes_label)
        layout.addWidget(self.time_label)
        layout.addStretch()
        
        parent_layout.addWidget(group)
    
    def create_results_section(self, parent_layout):
        """Create the results tabs section."""
        self.results_tabs = QTabWidget()
        
        # Theme Analysis Tab
        self.create_theme_analysis_tab()
        
        # Note Preview Tab
        self.create_note_preview_tab()
        
        parent_layout.addWidget(self.results_tabs)
    
    def create_theme_analysis_tab(self):
        """Create the theme analysis tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Header
        header = QLabel("Theme Distribution")
        header.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(header)
        
        # Theme list widget
        self.theme_list = QListWidget()
        self.theme_list.setStyleSheet("""
            QListWidget {
                font-family: 'Courier New', monospace;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.theme_list)
        
        # Add header to theme list
        header_item = QListWidgetItem("Theme                    Count    Percentage")
        header_item.setFlags(header_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
        self.theme_list.addItem(header_item)
        
        separator_item = QListWidgetItem("─" * 44)
        separator_item.setFlags(separator_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
        self.theme_list.addItem(separator_item)
        
        self.results_tabs.addTab(tab, "Theme Analysis")
    
    def create_note_preview_tab(self):
        """Create the note preview tab."""
        tab = QWidget()
        layout = QHBoxLayout(tab)
        
        # Left side: Note list
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        notes_header = QLabel("Curated Notes")
        notes_header.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        left_layout.addWidget(notes_header)
        
        self.notes_list = QListWidget()
        left_layout.addWidget(self.notes_list)
        
        # Right side: Note preview
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        preview_header = QLabel("Note Preview")
        preview_header.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        right_layout.addWidget(preview_header)
        
        self.note_preview = QTextEdit()
        self.note_preview.setReadOnly(True)
        self.note_preview.setPlainText("Select a note to preview...")
        right_layout.addWidget(self.note_preview)
        
        # Create splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([300, 400])
        
        layout.addWidget(splitter)
        self.results_tabs.addTab(tab, "Note Preview")
    
    def setup_connections(self):
        """Set up signal connections."""
        # Button connections
        self.source_browse_btn.clicked.connect(self.browse_source_path)
        self.output_browse_btn.clicked.connect(self.browse_output_path)
        self.start_btn.clicked.connect(self.start_curation)
        self.stop_btn.clicked.connect(self.stop_curation)
        
        # Note list selection
        self.notes_list.itemClicked.connect(self.on_note_selected)
    
    def browse_source_path(self):
        """Open dialog to select source vault path."""
        folder = QFileDialog.getExistingDirectory(
            self, 
            "Select Source Vault",
            self.source_path_edit.text()
        )
        if folder:
            self.source_path_edit.setText(folder)
    
    def browse_output_path(self):
        """Open dialog to select output folder path."""
        folder = QFileDialog.getExistingDirectory(
            self, 
            "Select Output Folder",
            self.output_path_edit.text() or str(Path.home())
        )
        if folder:
            self.output_path_edit.setText(folder)
    
    def start_curation(self):
        """Start the curation process."""
        # Validate inputs
        source_path = Path(self.source_path_edit.text().strip())
        output_path = Path(self.output_path_edit.text().strip())
        
        if not source_path.exists():
            QMessageBox.warning(self, "Error", "Source vault path does not exist!")
            return
        
        if not output_path.parent.exists():
            QMessageBox.warning(self, "Error", "Output folder parent directory does not exist!")
            return
        
        # Create configuration
        config = CurationConfig()
        
        # Set sample size if test run
        if self.test_run_radio.isChecked():
            config.sample_size = self.sample_size_spin.value()
            # For small test runs, use faster processing
            if config.sample_size <= 10:
                config.max_tokens = 1000  # Reduce AI processing time
        
        # Reset UI for new run
        self.reset_ui_for_new_run()
        
        # Start worker thread
        self.worker = CurationWorker(source_path, output_path, config)
        self.worker.progress_updated.connect(self.on_progress_updated)
        self.worker.stats_updated.connect(self.on_stats_updated)
        self.worker.theme_updated.connect(self.on_theme_updated)
        self.worker.note_curated.connect(self.on_note_curated)
        self.worker.finished.connect(self.on_curation_finished)
        self.worker.error_occurred.connect(self.on_error_occurred)
        
        self.worker.start()
        
        # Update UI state
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.start_time = time.time()
        self.timer.start(1000)  # Update every second
        
        mode_text = f"test run ({config.sample_size} notes)" if config.sample_size else "full run"
        self.progress_label.setText(f"Starting {mode_text} with full content extraction...")
    
    def stop_curation(self):
        """Stop the curation process."""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(3000)  # Wait up to 3 seconds
        
        self.reset_ui_after_run()
        self.progress_label.setText("Curation stopped by user.")
    
    def reset_ui_for_new_run(self):
        """Reset UI elements for a new curation run."""
        # Clear previous results
        self.theme_list.clear()
        self.notes_list.clear()
        self.note_preview.setPlainText("Select a note to preview...")
        
        # Re-add theme list headers
        header_item = QListWidgetItem("Theme                    Count    Percentage")
        header_item.setFlags(header_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
        self.theme_list.addItem(header_item)
        
        separator_item = QListWidgetItem("─" * 44)
        separator_item.setFlags(separator_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
        self.theme_list.addItem(separator_item)
        
        # Reset progress
        self.progress_bar.setValue(0)
        self.current_operation_label.setText("")
        
        # Reset stats
        self.current_stats = {
            'total_notes': 0,
            'curated_notes': 0,
            'rejected_notes': 0,
            'processing_time': 0,
            'themes_distribution': {},
            'curated_notes_list': []
        }
        self.update_stats_display()
    
    def reset_ui_after_run(self):
        """Reset UI elements after curation run completes."""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.timer.stop()
        self.current_operation_label.setText("")
    
    def on_progress_updated(self, current: int, total: int, current_note: str):
        """Handle progress update from worker."""
        # Current is already a percentage (0-100)
        percentage = current if current <= 100 else int((current / total * 100)) if total > 0 else 0
        self.progress_bar.setValue(percentage)
        
        eta_text = ""
        if self.start_time and percentage > 0:
            elapsed = time.time() - self.start_time
            if percentage > 5:  # Only estimate after some progress
                estimated_total = elapsed * (100 / percentage)
                remaining = estimated_total - elapsed
                eta_text = f" - ETA: {int(remaining//60)}:{int(remaining%60):02d}"
        
        self.progress_label.setText(f"Progress: {percentage}%{eta_text}")
        self.current_operation_label.setText(current_note)
    
    def on_stats_updated(self, stats: Dict[str, Any]):
        """Handle stats update from worker."""
        self.current_stats.update(stats)
        self.update_stats_display()
    
    def on_theme_updated(self, theme_name: str, count: int):
        """Handle theme update from worker."""
        self.current_stats['themes_distribution'][theme_name] = count
        self.update_theme_display()
    
    def on_note_curated(self, note_data: Dict[str, Any]):
        """Handle new curated note from worker."""
        self.current_stats['curated_notes_list'].append(note_data)
        self.update_notes_list()
    
    def on_curation_finished(self, final_stats: Dict[str, Any]):
        """Handle curation completion."""
        self.current_stats.update(final_stats)
        self.update_stats_display()
        self.update_theme_display()
        
        self.reset_ui_after_run()
        self.progress_label.setText(f"Curation completed! {final_stats['curated_notes']} notes curated.")
        
        QMessageBox.information(
            self, 
            "Curation Complete",
            f"Successfully curated {final_stats['curated_notes']} out of {final_stats['total_notes']} notes.\n\n"
            f"Curation rate: {final_stats['curation_rate']:.1f}%\n"
            f"Processing time: {final_stats['processing_time']:.1f} seconds"
        )
    
    def on_error_occurred(self, error_message: str):
        """Handle error from worker."""
        self.reset_ui_after_run()
        self.progress_label.setText("Error occurred during curation.")
        
        QMessageBox.critical(self, "Curation Error", f"An error occurred:\n\n{error_message}")
    
    def update_stats_display(self):
        """Update the statistics display."""
        stats = self.current_stats
        
        self.total_notes_label.setText(f"Total Notes: {stats['total_notes']}")
        
        curated = stats['curated_notes']
        total = stats['total_notes']
        curated_pct = (curated / total * 100) if total > 0 else 0
        self.curated_notes_label.setText(f"Curated: {curated} ({curated_pct:.0f}%)")
        
        rejected = stats['rejected_notes']
        rejected_pct = (rejected / total * 100) if total > 0 else 0
        self.rejected_notes_label.setText(f"Rejected: {rejected} ({rejected_pct:.0f}%)")
    
    def update_theme_display(self):
        """Update the theme analysis display."""
        themes = self.current_stats['themes_distribution']
        total_themed = sum(themes.values())
        
        # Clear existing theme items (keep headers)
        while self.theme_list.count() > 2:
            self.theme_list.takeItem(2)
        
        # Add theme items
        for theme, count in sorted(themes.items()):
            percentage = (count / total_themed * 100) if total_themed > 0 else 0
            theme_display = theme.replace('_', ' ').title()[:20].ljust(20)
            text = f"{theme_display} {count:>4}      {percentage:>3.0f}%"
            
            item = QListWidgetItem(text)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.theme_list.addItem(item)
    
    def update_notes_list(self):
        """Update the curated notes list."""
        # Clear and repopulate
        self.notes_list.clear()
        
        for note_data in self.current_stats['curated_notes_list']:
            item = QListWidgetItem(f"📄 {note_data.get('title', 'Untitled')}")
            item.setData(Qt.ItemDataRole.UserRole, note_data)
            self.notes_list.addItem(item)
    
    def on_note_selected(self, item: QListWidgetItem):
        """Handle note selection in the notes list."""
        note_data = item.data(Qt.ItemDataRole.UserRole)
        if note_data:
            preview_text = self.format_note_preview(note_data)
            self.note_preview.setPlainText(preview_text)
    
    def format_note_preview(self, note_data: Dict[str, Any]) -> str:
        """Format note data for preview display."""
        title = note_data.get('title', 'Untitled')
        theme = note_data.get('theme', 'Unknown')
        quality_score = note_data.get('quality_score', 0)
        professional_score = note_data.get('professional_score', 0)
        content_preview = note_data.get('content_preview', '')
        
        return f"""Title: {title}
Theme: {theme}
Quality Score: {quality_score:.1f}/10
Professional Score: {professional_score:.1f}/10

───────────────────────────────────────

{content_preview}"""
    
    def update_time_display(self):
        """Update the time display."""
        if self.start_time:
            elapsed = time.time() - self.start_time
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            self.time_label.setText(f"Time: {minutes:02d}:{seconds:02d}")


def main():
    """Main entry point for the GUI application."""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Obsidian Curator")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Obsidian Curator")
    
    # Create and show main window
    window = ObsidianCuratorGUI()
    window.show()
    
    # Run the application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
