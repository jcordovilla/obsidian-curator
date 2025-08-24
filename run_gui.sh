#!/bin/bash

# Obsidian Curator GUI Launcher Script
# This script launches the PyQt6 GUI for the Obsidian Curator application

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check Python version
check_python_version() {
    if command_exists python3; then
        python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        required_version="3.12"
        
        if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
            print_error "Python $python_version is installed, but Python $required_version+ is required."
            print_error "Please upgrade Python to version 3.12 or higher."
            exit 1
        fi
        
        print_success "Python $python_version detected"
        return 0
    else
        print_error "Python 3 is not installed. Please install Python 3.12+ first."
        exit 1
    fi
}

# Function to check if Ollama is available
check_ollama() {
    if ! command_exists ollama; then
        print_warning "Ollama is not installed or not in PATH."
        print_warning "The GUI will work but AI features may not function properly."
        print_warning "Install Ollama from: https://ollama.ai/download"
        return 1
    fi
    
    # Check if Ollama is running
    if ! ollama list &>/dev/null; then
        print_warning "Ollama is not running. Starting Ollama..."
        ollama serve &
        sleep 3
    fi
    
    print_success "Ollama is available"
    return 0
}

# Function to check if Poetry is available
check_poetry() {
    if ! command_exists poetry; then
        print_error "Poetry is not installed. Please install Poetry first:"
        print_error "  curl -sSL https://install.python-poetry.org | python3 -"
        print_error "  or: pip3 install poetry"
        exit 1
    fi
    
    print_success "Poetry detected"
}

# Function to install dependencies if needed
install_dependencies() {
    print_status "Checking if dependencies are installed..."
    
    if [ ! -f "poetry.lock" ]; then
        print_warning "Poetry lock file not found. Installing dependencies..."
        poetry install
    else
        print_status "Dependencies appear to be up to date"
    fi
}

# Function to run the GUI
run_gui() {
    print_status "Launching Obsidian Curator GUI..."
    
    # Try to run using Poetry first
    if command_exists poetry; then
        print_status "Using Poetry to run the GUI..."
        poetry run obsidian-curator-gui
    else
        # Fallback to direct Python execution
        print_status "Using direct Python execution..."
        python3 -m obsidian_curator.gui
    fi
}

# Main execution
main() {
    echo "🚀 Obsidian Curator GUI Launcher"
    echo "=================================="
    echo ""
    
    # Change to script directory if not already there
    cd "$(dirname "$0")"
    
    # Check prerequisites
    print_status "Checking prerequisites..."
    check_python_version
    check_ollama
    check_poetry
    
    # Install dependencies if needed
    install_dependencies
    
    # Run the GUI
    run_gui
}

# Handle script interruption
trap 'print_error "Script interrupted. Exiting..."; exit 1' INT TERM

# Run main function
main "$@"
