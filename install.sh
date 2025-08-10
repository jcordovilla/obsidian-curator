#!/bin/bash

# Obsidian Curator Installation Script

echo "🚀 Installing Obsidian Curator..."
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.9+ first."
    exit 1
fi

# Check Python version
python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
required_version="3.9"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python $python_version is installed, but Python $required_version+ is required."
    exit 1
fi

echo "✅ Python $python_version detected"

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo "❌ Ollama is not installed."
    echo ""
    echo "Please install Ollama first:"
    echo "  macOS: brew install ollama"
    echo "  Linux: curl -fsSL https://ollama.ai/install.sh | sh"
    echo "  Windows: Download from https://ollama.ai/download"
    echo ""
    echo "After installing Ollama, run this script again."
    exit 1
fi

echo "✅ Ollama detected"

# Check if Ollama is running
if ! ollama list &> /dev/null; then
    echo "⚠️  Ollama is not running. Starting Ollama..."
    ollama serve &
    sleep 5
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip3 install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Failed to install Python dependencies"
    exit 1
fi

# Install the package in development mode
echo "🔧 Installing Obsidian Curator..."
pip3 install -e .

if [ $? -ne 0 ]; then
    echo "❌ Failed to install Obsidian Curator"
    exit 1
fi

# Check if a model is available
echo "🤖 Checking for AI models..."
if ! ollama list | grep -q "gpt-oss:20b"; then
    echo "⚠️  GPT-OSS:20B model not found. Pulling it now..."
    echo "This may take a while depending on your internet connection..."
    ollama pull gpt-oss:20b
    
    if [ $? -ne 0 ]; then
        echo "❌ Failed to pull GPT-OSS:20B model"
        echo "You can try pulling it manually later with: ollama pull gpt-oss:20b"
    fi
else
    echo "✅ GPT-OSS:20B model found"
fi

echo ""
echo "🎉 Installation completed successfully!"
echo ""
echo "You can now use Obsidian Curator:"
echo ""
echo "  # Basic usage"
echo "  obsidian-curator curate /path/to/input/vault /path/to/output/vault"
echo ""
echo "  # With custom settings"
echo "  obsidian-curator curate --quality-threshold 0.8 --verbose /path/to/input/vault /path/to/output/vault"
echo ""
echo "  # See all options"
echo "  obsidian-curator curate --help"
echo ""
echo "For more information, see the README.md file."
